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

from functools import lru_cache
from typing import Any

from knowledge_engineering.common.ke_labels import load_ke_labels
from knowledge_engineering.common.normalize import normalize

DEFAULT_CANDIDATE_CAP = 300


@lru_cache(maxsize=1)
def _city_blobs() -> dict[int, str]:
    """V11: city/province blob đã normalize per hotel, cache 1 lần (bất biến giữa request).
    Trước đây normalize lại 520 hotel MỖI request có city → ~227ms/query. Cache → ~0ms."""
    return {
        hid: normalize(" ".join(str(ke.get(k) or "") for k in ("city", "province")), fold=True)
        for hid, ke in load_ke_labels().items()
    }


def inmemory_hard_filter(
    *,
    city: str | None = None,
    star_eq: int | None = None,
    score_min: float | None = None,
    brand: str | None = None,
) -> list[int]:
    """Node 2 không cần DB: lọc hotel theo city text + star/score + brand trong ke_labels.

    City match: fold 2 chiều substring giữa city query và city/province của KE — bắt biến thể
    "phú quốc" vs "Đảo Phú Quốc", "cát bà" vs "Quần Đảo Cát Bà". GIÁ là placeholder trong KE
    -> KHÔNG lọc cứng giá (giống query_demo), chỉ star/score. Production: dùng sql_hard_filter.

    Brand (chuỗi KS): LỌC CỨNG — "thuộc Vinpearl" chỉ trả hotel brand=Vinpearl. So khớp canonical
    (cùng extract_brand cho query lẫn data nên khớp đúng). brand=None -> không lọc brand.
    """
    labels = load_ke_labels()
    city_norm = normalize(city, fold=True) if city else None
    blobs = _city_blobs() if city_norm else {}
    city_toks = [tok for tok in city_norm.split() if len(tok) > 2] if city_norm else []
    out: list[int] = []
    for hid, ke in labels.items():
        rf = ke.get("range_filters") or {}
        if star_eq is not None and rf.get("star_rating") != star_eq:
            continue
        if score_min is not None and (rf.get("review_score") or 0) < score_min:
            continue
        if brand is not None and ke.get("brand") != brand:
            continue
        if city_norm:
            blob = blobs.get(hid, "")
            # khớp city: full substring HOẶC TẤT CẢ token đặc trưng có trong blob (AND, không OR).
            # OR cũ làm "phú quốc"=[phu,quoc] khớp "phu ly" (chỉ trùng "phu") -> Phủ Lý lọt vào
            # kết quả Phú Quốc. AND đòi cả "phu" VÀ "quoc" -> Phủ Lý thiếu "quoc" -> loại đúng.
            if city_norm not in blob and not (city_toks and blob and all(tok in blob for tok in city_toks)):
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
    match_count_by_hotel: dict[int, int] | None = None,
    idf_score_by_hotel: dict[int, float] | None = None,
) -> list[int]:
    """Node 4: giao 2 whitelist + fallback (port logic file pipeline).

      sql ∩ concept (nếu cả hai có và giao khác rỗng) -> dùng giao
      giao rỗng -> fallback SQL whitelist (concept soft boost để rerank lo)
      chỉ 1 whitelist -> dùng cái đó
      không có gì -> rỗng (tầng trên quyết định broad search)

    V5 fix: khi câu KHÔNG có city (vd "khách sạn sôi động"), concept whitelist có thể ~400 hotel
    > cap. Trước đây sort thuần review_score → hotel khớp NHIỀU concept query (sát ý) nhưng review
    thấp bị hotel review-cao-chỉ-khớp-1-concept chen mất khỏi cap (vd GS-015 hotel đúng hạng 205/394
    → rớt). Sửa: sort theo (match_count GIẢM, review_score GIẢM) — ưu tiên hotel sát query nhất."""
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

    # V5: ưu tiên IDF concept (concept đặc trưng như STYLE_LIVELY > OBJ_HOTEL phổ thông),
    # rồi match_count, cuối cùng review_score. IDF kéo hotel sát ý nhất vào trong cap.
    idf = idf_score_by_hotel or {}
    mc = match_count_by_hotel or {}
    rs = review_score_by_hotel or {}
    ranked = sorted(candidates, key=lambda h: (-idf.get(h, 0.0), -mc.get(h, 0), -rs.get(h, 0.0)))
    return ranked[:cap]


def review_scores() -> dict[int, float]:
    """hotel_id -> review_score từ ke_labels (dùng sort candidate khi không có DB)."""
    return {
        hid: (ke.get("range_filters") or {}).get("review_score") or 0.0
        for hid, ke in load_ke_labels().items()
    }
