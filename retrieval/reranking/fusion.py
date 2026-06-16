"""fusion.py — Node 7: hợp nhất BM25 + vector bằng RRF + boost. Node 7C: business rerank.

Logic thuần (không phụ thuộc service) -> verify bằng dữ liệu giả. Port công thức từ
test_pipeline_nodes (Node 7 RRF, Node 7C business score), điều chỉnh:
  - graph_boost (Neo4j) -> profile_boost (semantic_profile của KE) vì repo không có Neo4j.

Input: list kết quả BM25 + list kết quả vector, mỗi item shape thống nhất:
  {chunk_id, hotel_id, text, metadata, score, source}
Output: list đã fuse, sort theo điểm cuối.
"""

from __future__ import annotations

from typing import Any

RRF_K = 60
PROFILE_BOOST_WEIGHT = 0.05   # mỗi feel-concept khớp + score, cộng nhẹ vào RRF
BUSINESS_WEIGHTS = {"neural": 0.5, "review": 0.2, "review_count": 0.1, "price_fit": 0.1, "concept": 0.1}


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


def business_rerank(
    fused: list[dict[str, Any]],
    concepts: list[str] | None = None,
    weights: dict[str, float] | None = None,
    intent_max_price: int | None = None,
) -> list[dict[str, Any]]:
    """Node 7C: rerank theo tín hiệu business (review_score/count, price_fit, concept match).

    Dùng metadata sẵn trên doc (ke_* / range_filters / ontology_concepts). KHÔNG cần DB —
    metadata đã đính từ Nhóm 0. neural_score = fused_score (chưa có cross-encoder thật ở đây;
    cross-encoder là Node 7B, gọi riêng khi có model)."""
    import math

    w = {**BUSINESS_WEIGHTS, **(weights or {})}
    concepts = set(concepts or [])
    max_rc = max(
        [(d.get("metadata") or {}).get("review_count") or 0 for d in fused] + [1]
    )
    for doc in fused:
        md = doc.get("metadata") or {}
        neural = doc.get("fused_score", doc.get("rrf_score", 0.0))
        review_score = (md.get("ke_review_score") or md.get("review_score") or 0.0) / 10.0
        review_count = math.log1p(md.get("review_count") or 0) / math.log1p(max_rc)
        price = md.get("ke_price_min_vnd") or md.get("price_min_vnd") or 0
        price_fit = 1.0 if (not intent_max_price or not price or price <= intent_max_price) else 0.0
        oc = set(md.get("ontology_concepts") or [])
        concept_match = len(concepts & oc) / max(len(concepts), 1) if concepts else 0.0
        doc["business_score"] = (
            w["neural"] * neural
            + w["review"] * review_score
            + w["review_count"] * review_count
            + w["price_fit"] * price_fit
            + w["concept"] * concept_match
        )
    fused.sort(key=lambda d: -d["business_score"])
    return fused


def aggregate_by_hotel(reranked: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    """Gom chunk theo hotel, lấy chunk điểm cao nhất mỗi hotel + bonus thông tin phong phú.
    Trả top_n hotel (mỗi hotel 1 đại diện). Port logic aggregation Node 7C."""
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
    return out[:top_n]
