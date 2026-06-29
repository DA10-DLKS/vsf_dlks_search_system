"""fusion.py — Node 7: hợp nhất BM25 + vector bằng RRF + boost. Node 7C: business rerank.

Logic thuần (không phụ thuộc service) -> verify bằng dữ liệu giả. Port công thức từ
test_pipeline_nodes (Node 7 RRF, Node 7C business score), điều chỉnh:
  - graph_boost (Neo4j) -> profile_boost (semantic_profile của KE) vì repo không có Neo4j.

Input: list kết quả BM25 + list kết quả vector, mỗi item shape thống nhất:
  {chunk_id, hotel_id, text, metadata, score, source}
Output: list đã fuse, sort theo điểm cuối.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

RRF_K = 60
PROFILE_BOOST_WEIGHT = 0.05   # mỗi feel-concept khớp + score, cộng nhẹ vào RRF
# neural=0.05: calibrate bằng sweep trên golden_set_v2 (59 câu). Sau khi chuẩn hóa text-signal
# [0,1] (V1), trọng số cao làm text retrieval ÁP ĐẢO nhãn KE — vốn MẠNH HƠN text trên corpus này
# (vector-only recall 0.42 < KE-only 0.51). neural_w=0.05 cho recall 0.5114 + MRR 0.9065 + Hit
# 0.9831 (đỉnh cả 3). Text-signal đóng vai trò TINH CHỈNH thứ hạng, không phải động lực recall.
# Xem evaluation/retrieval_metrics/sweep_neural.py để tái lập. (V1 + V9 đợt 1.)
# relation=0.05: boost hotel có amenity-MINH-CHỨNG cho purpose trong câu (PURPOSE_FAMILY ->
# AMEN_KIDS_CLUB...). Port từ query_demo (purpose_hit). ADDITIVE + nhỏ: câu KHÔNG có purpose ->
# signal=0 -> business_score y HỆT cũ (không phá luồng/không đổi golden khi không có purpose).
BUSINESS_WEIGHTS = {"neural": 0.05, "review": 0.2, "review_count": 0.1, "price_fit": 0.1,
                    "concept": 0.1, "relation": 0.05}


# Bảng tĩnh fallback — ĐỒNG BỘ với query_demo._PURPOSE_EVIDENCE_FALLBACK. Dùng khi relation_loader
# lỗi/rỗng (retrieval không được vỡ vì thiếu file relation). Nguồn chính là relation graph verified.
_PURPOSE_EVIDENCE_FALLBACK = {
    "PURPOSE_FAMILY": {"AMEN_KIDS_CLUB", "AMEN_KIDS_POOL", "AMEN_BABYSITTING"},
    "PURPOSE_ROMANTIC": {"AMEN_SEA_VIEW", "AMEN_PRIVATE_POOL", "STYLE_ROMANTIC"},
    "PURPOSE_BUSINESS": {"AMEN_MEETING_ROOM", "AMEN_WIFI"},
    "PURPOSE_WELLNESS": {"AMEN_SPA", "STYLE_QUIET"},
    "PURPOSE_GROUP": {"AMEN_KARAOKE", "AMEN_GAME_ROOM", "AMEN_MEETING_ROOM"},
}


@lru_cache(maxsize=1)
def _boost_evidence() -> dict[str, frozenset]:
    """{concept_source -> frozenset(target)} từ relation graph verified (use_as=boost).
    Fallback bảng tĩnh nếu loader lỗi/rỗng. Load 1 lần (lru_cache) — không đọc file mỗi query.

    KHÔNG chỉ purpose: mọi cạnh boost verified (vd cũng có thể SETTING->AMEN). query trong
    business_rerank lọc theo concept thực có trong câu nên thừa cạnh không gây hại."""
    try:
        from knowledge_engineering.common.relation_loader import load_relations
        rels = load_relations(status={"verified"}, use_as={"boost"})
        out: dict[str, set] = {}
        for r in rels:
            out.setdefault(r.source, set()).add(r.target)
        if out:
            return {k: frozenset(v) for k, v in out.items()}
    except Exception:
        pass
    return {k: frozenset(v) for k, v in _PURPOSE_EVIDENCE_FALLBACK.items()}


def reciprocal_rank_fusion(
    bm25_results: list[dict[str, Any]],
    vector_results: list[dict[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """RRF: mỗi doc cộng 1/(k+rank) từ mỗi nguồn. Dedupe theo chunk_id."""
    scores: dict[str, float] = {}
    details: dict[str, dict[str, Any]] = {}

    for source_results in (bm25_results, vector_results):
        for rank, doc in enumerate(source_results, start=1):
            doc_id = doc.get("chunk_id") or f"{doc.get('source')}_{doc.get('hotel_id')}_{rank}"
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in details:
                details[doc_id] = dict(doc)
            details[doc_id].setdefault(f"{doc.get('source')}_rank", rank)

    fused = []
    for doc_id, score in scores.items():
        item = details[doc_id]
        item["rrf_score"] = score
        fused.append(item)
    fused.sort(key=lambda d: -d["rrf_score"])
    return fused


def _best_rank_per_hotel(results: list[dict[str, Any]]) -> dict[Any, tuple[int, dict[str, Any]]]:
    """Gom kết quả 1 nguồn về hotel_id, giữ rank TỐT NHẤT (nhỏ nhất) của hotel trong nguồn đó."""
    seen: dict[Any, tuple[int, dict[str, Any]]] = {}
    for rank, doc in enumerate(results, start=1):
        hid = doc.get("hotel_id")
        if hid is None:
            continue
        if hid not in seen or rank < seen[hid][0]:
            seen[hid] = (rank, doc)
    return seen


def rrf_by_hotel(
    bm25_results: list[dict[str, Any]],
    vector_results: list[dict[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """V9 fix: RRF hợp nhất ở CẤP HOTEL thay vì chunk_id.

    Vấn đề cũ: BM25 trả chunk_id `bm25_hotel_<id>` (document-level), Qdrant trả chunk_id thật
    (chunk-level) -> dedupe theo chunk_id KHÔNG BAO GIỜ trùng -> RRF không cộng dồn điểm của
    cùng hotel từ 2 nguồn (mất toàn bộ ý nghĩa của RRF). Giải pháp A của V9: gom mỗi nguồn về
    hotel_id (rank tốt nhất), RRF trên hotel_id -> hotel ở cả 2 nguồn được cộng dồn đúng.
    (Không cần reindex OpenSearch chunk-level — đảo ngược dễ, an toàn cho đợt 1.)"""
    scores: dict[Any, float] = {}
    details: dict[Any, dict[str, Any]] = {}

    for source_name, results in (("bm25", bm25_results), ("vector", vector_results)):
        for hid, (rank, doc) in _best_rank_per_hotel(results).items():
            scores[hid] = scores.get(hid, 0.0) + 1.0 / (k + rank)
            if hid not in details:
                details[hid] = dict(doc)
            details[hid][f"{source_name}_rank"] = rank

    fused = []
    for hid, score in scores.items():
        item = details[hid]
        item["hotel_id"] = hid
        item["rrf_score"] = score
        fused.append(item)
    fused.sort(key=lambda d: -d["rrf_score"])
    return fused


def apply_profile_boost(
    fused: list[dict[str, Any]],
    feel_concepts: list[str],
    weight: float = PROFILE_BOOST_WEIGHT,
) -> list[dict[str, Any]]:
    """Boost doc theo semantic_profile của KE: hotel có feel-concept (style/aspect) trong câu
    với score cao -> cộng điểm. Thay cho graph_boost của file pipeline (repo không có Neo4j)."""
    if not feel_concepts:
        return fused
    for doc in fused:
        prof = (doc.get("metadata") or {}).get("semantic_profile") or {}
        boost = sum(
            (prof.get(c, {}) or {}).get("score", 0.0)
            for c in feel_concepts
        )
        doc["profile_boost"] = boost
        doc["fused_score"] = doc.get("rrf_score", 0.0) + weight * boost
    fused.sort(key=lambda d: -d.get("fused_score", d.get("rrf_score", 0.0)))
    return fused


def _minmax_norm(values: list[float]) -> tuple[float, float]:
    """Trả (lo, hi) để chuẩn hóa min-max. Port từ develop-2 calibrated_rrf_fusion."""
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def business_rerank(
    fused: list[dict[str, Any]],
    concepts: list[str] | None = None,
    weights: dict[str, float] | None = None,
    intent_max_price: int | None = None,
    intent_min_price: int | None = None,
) -> list[dict[str, Any]]:
    """Node 7C: rerank theo tín hiệu business (review_score/count, price_fit, concept match).

    Dùng metadata sẵn trên doc (ke_* / range_filters / ontology_concepts). KHÔNG cần DB —
    metadata đã đính từ Nhóm 0.

    V1 fix (score scale mismatch): tín hiệu text retrieval (`rerank_score`/`fused_score`/`rrf_score`)
    nằm trong thang RRF [0, ~0.016], trong khi review/price/concept đã ở [0,1]. Cộng thẳng làm
    text-signal bị nuốt ~24×. -> Chuẩn hóa text-signal về [0,1] bằng min-max TRÊN TẬP candidate
    trước khi fuse (port _minmax của develop-2 calibrated_rrf_fusion). Ưu tiên rerank_score nếu
    cross-encoder đã chạy (Node 7B), nếu không dùng fused_score/rrf_score."""
    import math

    w = {**BUSINESS_WEIGHTS, **(weights or {})}
    # Sweep-only hook (V1 calibration): cho phép override trọng số neural qua env để quét nhanh.
    import os as _os
    _nw = _os.environ.get("NEURAL_WEIGHT")
    if _nw is not None:
        w = {**w, "neural": float(_nw)}
    concepts = set(concepts or [])
    # relation boost: tập concept-MINH-CHỨNG cho MỌI concept trong câu có cạnh boost verified
    # (PURPOSE_FAMILY -> AMEN_KIDS_CLUB; SETTING_COASTAL -> AMEN_SEA_VIEW...). Rỗng khi câu không
    # khớp cạnh boost nào -> signal=0 (không đổi business_score cũ). Nguồn = relation graph verified.
    evidence = _boost_evidence()
    boost_targets: set[str] = set()
    for c in concepts:
        boost_targets |= evidence.get(c, frozenset())
    max_rc = max(
        [(d.get("metadata") or {}).get("review_count") or 0 for d in fused] + [1]
    )

    def _raw_text(d: dict[str, Any]) -> float:
        # rerank_score (cross-encoder, đã [0,1]) > fused_score > rrf_score
        return d.get("rerank_score", d.get("fused_score", d.get("rrf_score", 0.0)))

    t_lo, t_hi = _minmax_norm([_raw_text(d) for d in fused])
    t_span = t_hi - t_lo

    for doc in fused:
        md = doc.get("metadata") or {}
        raw = _raw_text(doc)
        neural = (raw - t_lo) / t_span if t_span > 0 else 0.0
        review_score = (md.get("ke_review_score") or md.get("review_score") or 0.0) / 10.0
        review_count = math.log1p(md.get("review_count") or 0) / math.log1p(max_rc)
        # price_fit: hotel khớp tầm giá user thì điểm 1.0. Dùng DẢI giá hotel [min,max] giao với
        # [intent_min, intent_max] (nhất quán hard-filter). Hard-filter đã loại hotel ngoài khoảng;
        # price_fit ở đây chủ yếu tie-break + xử lý hotel price_capped (lọt qua hard-filter).
        p_lo = md.get("ke_price_min_vnd") or md.get("price_min_vnd") or 0
        p_hi = md.get("ke_price_max_vnd") or md.get("price_max_vnd") or p_lo
        if not intent_max_price and not intent_min_price:
            price_fit = 1.0
        elif not p_lo:
            price_fit = 1.0  # thiếu giá -> không phạt
        else:
            q_lo = intent_min_price or 0
            q_hi = intent_max_price or float("inf")
            price_fit = 1.0 if (p_lo <= q_hi and p_hi >= q_lo) else 0.0
        oc = set(md.get("ontology_concepts") or [])
        concept_match = len(concepts & oc) / max(len(concepts), 1) if concepts else 0.0
        # relation_match: tỉ lệ amenity-minh-chứng hotel CÓ trên tổng minh-chứng cần. boost_targets
        # rỗng (câu không có purpose) -> 0.0 -> business_score KHÔNG đổi so với trước.
        relation_match = (
            len(boost_targets & oc) / len(boost_targets) if boost_targets else 0.0
        )
        doc["text_signal_norm"] = neural  # debug: text-signal sau chuẩn hóa [0,1] (V8 breakdown)
        doc["relation_match"] = relation_match  # debug: xem hotel khớp minh-chứng purpose bao nhiêu
        doc["business_score"] = (
            w["neural"] * neural
            + w["review"] * review_score
            + w["review_count"] * review_count
            + w["price_fit"] * price_fit
            + w["concept"] * concept_match
            + w["relation"] * relation_match
        )
    fused.sort(key=lambda d: -d["business_score"])
    return fused


def _doc_price(doc: dict[str, Any]) -> int | None:
    """Giá đại diện hotel (VND) cho superlative sort. None nếu data thiếu giá."""
    md = doc.get("metadata") or {}
    return md.get("ke_price_min_vnd") or md.get("price_min_vnd") or None


def aggregate_by_hotel(
    reranked: list[dict[str, Any]], top_n: int = 5, sort: str | None = None
) -> list[dict[str, Any]]:
    """Gom chunk theo hotel, lấy chunk điểm cao nhất mỗi hotel + bonus thông tin phong phú.
    Trả top_n hotel (mỗi hotel 1 đại diện). Port logic aggregation Node 7C.

    sort: superlative giá ("price_asc"/"price_desc"). Khi set, relevance vẫn quyết định hotel nào
    HỢP LỆ (giữ nguyên hard filter + business_score upstream), nhưng top_n hiển thị sắp theo giá.
    Hotel thiếu giá xếp cuối (không lẫn vào "rẻ nhất"/"đắt nhất")."""
    groups: dict[Any, dict[str, Any]] = {}
    for doc in reranked:
        hid = doc.get("hotel_id")
        if hid is None:
            continue
        score = doc.get("business_score", doc.get("fused_score", 0.0))
        g = groups.get(hid)
        if g is None:
            groups[hid] = {"best": doc, "max_score": score, "count": 1}
        else:
            g["count"] += 1
            if score > g["max_score"]:
                g["max_score"] = score
                g["best"] = doc
    out = []
    for hid, g in groups.items():
        bonus = 0.01 * min(g["count"] - 1, 5)
        rep = dict(g["best"])
        rep["final_score"] = g["max_score"] + bonus
        rep["matched_chunks"] = g["count"]
        out.append(rep)
    out.sort(key=lambda d: -d["final_score"])

    if sort in ("price_asc", "price_desc"):
        # Sắp theo giá trên TOÀN nhóm hợp lệ rồi mới cắt top_n (để "rẻ nhất" ra đúng cái rẻ nhất,
        # không chỉ rẻ nhất trong top relevance). Hotel thiếu giá -> đẩy về cuối cả 2 chiều bằng
        # cờ (price is None) đứng trước key giá.
        asc = sort == "price_asc"
        def _key(d):
            p = _doc_price(d)
            return (p is None, p if asc else -p) if p is not None else (True, 0)
        out.sort(key=_key)
    return out[:top_n]
