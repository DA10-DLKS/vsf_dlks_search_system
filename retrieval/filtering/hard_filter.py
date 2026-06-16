"""hard_filter.py — Node 2 (SQL hard filter) + Node 4 (candidate builder).

Node 2: lọc cứng điều kiện CÓ CẤU TRÚC (city, price, star) ở PostgreSQL — mạnh nhất cho
numeric/range/equality. Trả sql_whitelist (hotel_ids).

Có 2 backend:
  - sql_hard_filter(conn, ...): query Postgres thật (production, như file pipeline).
  - inmemory_hard_filter(...): lọc từ ke_labels.range_filters — để chạy/verify khi CHƯA có DB.

Node 4: candidate builder — giao sql_whitelist ∩ concept_whitelist, fallback theo thứ tự ưu
tiên (port logic file pipeline Node 4). Giới hạn kích thước tập ứng viên.
"""

from __future__ import annotations

from typing import Any

from knowledge_engineering.common.ke_labels import load_ke_labels
from knowledge_engineering.common.normalize import normalize

DEFAULT_CANDIDATE_CAP = 300


def inmemory_hard_filter(
    *,
    city: str | None = None,
    star_eq: int | None = None,
    score_min: float | None = None,
) -> list[int]:
    """Node 2 không cần DB: lọc hotel theo city text + star/score trong ke_labels.

    City match: fold 2 chiều substring giữa city query và city/province của KE — bắt biến thể
    "phú quốc" vs "Đảo Phú Quốc", "cát bà" vs "Quần Đảo Cát Bà". GIÁ là placeholder trong KE
    -> KHÔNG lọc cứng giá (giống query_demo), chỉ star/score. Production: dùng sql_hard_filter.
    """
    labels = load_ke_labels()
    city_norm = normalize(city, fold=True) if city else None
    out: list[int] = []
    for hid, ke in labels.items():
        rf = ke.get("range_filters") or {}
        if star_eq is not None and rf.get("star_rating") != star_eq:
            continue
        if score_min is not None and (rf.get("review_score") or 0) < score_min:
            continue
        if city_norm:
            blob = normalize(" ".join(str(ke.get(k) or "") for k in ("city", "province")), fold=True)
            if city_norm not in blob and blob and not any(
                tok in blob for tok in city_norm.split() if len(tok) > 2
            ):
                continue
        out.append(hid)
    return out


def sql_hard_filter(
    connection,
    *,
    city: str | None = None,
    star_eq: int | None = None,
    max_price: int | None = None,
    score_min: float | None = None,
) -> list[int]:
    """Node 2 production: lọc city/star/price/score ở Postgres. Trả hotel_ids.

    Port từ test_pipeline_nodes Node 2 (JOIN hotels+rooms). connection = psycopg2 connection.
    """
    query = [
        "SELECT h.id FROM hotels h",
        "JOIN rooms r ON h.id = r.hotel_id",
        "WHERE 1=1",
    ]
    params: list[Any] = []
    if city:
        query.append("AND h.city = %s")
        params.append(city)
    if star_eq is not None:
        query.append("AND h.star_rating = %s")
        params.append(float(star_eq))
    if score_min is not None:
        query.append("AND h.review_score >= %s")
        params.append(score_min)
    if max_price is not None:
        query.append("AND r.price_per_night <= %s")
        params.append(max_price)
    query.append("GROUP BY h.id ORDER BY h.review_score DESC NULLS LAST")
    sql = "\n".join(query)
    with connection.cursor() as cur:
        cur.execute(sql, params)
        return [row[0] for row in cur.fetchall()]


def build_candidates(
    sql_whitelist: list[int] | None,
    concept_whitelist: list[int] | None,
    *,
    cap: int = DEFAULT_CANDIDATE_CAP,
    review_score_by_hotel: dict[int, float] | None = None,
) -> list[int]:
    """Node 4: giao 2 whitelist + fallback (port logic file pipeline).

      sql ∩ concept (nếu cả hai có và giao khác rỗng) -> dùng giao
      giao rỗng -> fallback SQL whitelist (concept soft boost để rerank lo)
      chỉ 1 whitelist -> dùng cái đó
      không có gì -> rỗng (tầng trên quyết định broad search)
    """
    sql_set = set(sql_whitelist or [])
    concept_set = set(concept_whitelist or [])

    if sql_set and concept_set:
        inter = sql_set & concept_set
        candidates = inter if inter else sql_set
    elif sql_set:
        candidates = sql_set
    elif concept_set:
        candidates = concept_set
    else:
        candidates = set()

    ranked = sorted(
        candidates,
        key=lambda h: -((review_score_by_hotel or {}).get(h, 0.0)),
    )
    return ranked[:cap]


def review_scores() -> dict[int, float]:
    """hotel_id -> review_score từ ke_labels (dùng sort candidate khi không có DB)."""
    return {
        hid: (ke.get("range_filters") or {}).get("review_score") or 0.0
        for hid, ke in load_ke_labels().items()
    }
