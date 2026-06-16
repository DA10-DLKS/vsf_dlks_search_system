"""pipeline.py — Orchestrator hybrid retrieval: nối Node 1→8.

Gom các tầng đã build thành 1 luồng gọi được (API dùng cái này):
  Node 1  parse_intent (query_processing)
  Node 2  hard filter  (filtering: in-memory / SQL)
  Node 3  concept lookup (filtering: inverted index)
  Node 4  candidate builder (filtering)
  Node 6  BM25 (lexical) + Vector (qdrant) trên candidate
  Node 7  RRF fusion + profile boost
  Node 7B neural rerank (cross-encoder, fallback density)
  Node 7C business rerank + aggregate theo hotel
  Node 8  ContextPackage + prompt

Thiết kế để TỪNG node có thể vắng (service chưa sẵn) mà pipeline vẫn chạy: nếu không có
vector/bm25 service thì bỏ nguồn đó; nếu cả hai vắng thì xếp hạng candidate bằng business
score trực tiếp (vẫn trả kết quả từ nhãn KE). Phù hợp verify khi hạ tầng chưa đủ.
"""

from __future__ import annotations

from typing import Any

from context import build_context_package, build_prompt
from retrieval.filtering import (
    build_candidates,
    inmemory_hard_filter,
    lookup_hotels_by_concepts,
    review_scores,
)
from retrieval.query_processing import parse_intent
from retrieval.reranking import (
    aggregate_by_hotel,
    apply_profile_boost,
    business_rerank,
    neural_rerank,
    reciprocal_rank_fusion,
)


def _candidate_concepts(intent) -> list[str]:
    """Concept dùng cho Node 3 lookup (hard + feel + obj + price + lmk + location)."""
    return (
        intent.hard_concepts
        + intent.feel_concepts
        + intent.object_types
        + intent.price_tiers
        + intent.landmarks
        + intent.location_concepts
    )


def run_hybrid_search(
    query: str,
    *,
    vector_service=None,
    bm25_service=None,
    use_reranker_model: bool = False,
    top_n: int = 5,
    candidate_pool: int = 100,
    generate_answer: bool = False,
) -> dict[str, Any]:
    """Chạy pipeline hybrid end-to-end. Trả {intent, candidates, context_package, prompt[, answer]}.

    vector_service / bm25_service: nếu None thì bỏ nguồn đó (vẫn chạy bằng nguồn còn lại hoặc
    chỉ candidate). generate_answer=True -> gọi Node 9 (LLM) sinh câu trả lời.
    """
    # Node 1
    intent = parse_intent(query)

    # Node 3: concept whitelist
    concepts = _candidate_concepts(intent)
    cw = lookup_hotels_by_concepts(concepts, require_all=False)

    # Node 2: hard filter (in-memory; production có thể thay sql_hard_filter)
    sw = inmemory_hard_filter(
        city=intent.city,
        star_eq=intent.range.get("star_eq"),
        score_min=intent.range.get("score_min"),
    )

    # Node 4: candidate
    rs = review_scores()
    candidates = build_candidates(
        sw or None, cw.hotel_ids or None, cap=candidate_pool, review_score_by_hotel=rs
    )

    # Node 6: text retrieval trên candidate
    bm25_results: list[dict[str, Any]] = []
    vector_results: list[dict[str, Any]] = []
    if bm25_service is not None:
        bm25_results = bm25_service.search_for_fusion(
            query, candidate_hotel_ids=candidates
        )["results"]
    if vector_service is not None:
        vector_results = vector_service.search(
            query, candidate_hotel_ids=candidates
        )["results"]

    # Node 7: fusion. Nếu KHÔNG có nguồn text nào -> dựng "doc" giả từ candidate để vẫn xếp hạng
    # bằng business score (dựa nhãn KE). Đảm bảo pipeline luôn trả kết quả.
    if bm25_results or vector_results:
        fused = reciprocal_rank_fusion(bm25_results, vector_results)
    else:
        fused = _candidates_as_docs(candidates)

    fused = apply_profile_boost(fused, intent.feel_concepts)

    # Node 7B
    reranked = neural_rerank(query, fused, top_k=max(top_n * 4, 20), use_model=use_reranker_model)

    # Node 7C
    reranked = business_rerank(
        reranked, concepts=intent.concepts, intent_max_price=intent.range.get("price_max")
    )
    top_hotels = aggregate_by_hotel(reranked, top_n=top_n)

    # Node 8
    pkg = build_context_package(query, top_hotels, extra_metadata={"intent": intent.to_dict()})
    prompt = build_prompt(pkg)

    out = {
        "intent": intent.to_dict(),
        "n_candidates": len(candidates),
        "n_fused": len(fused),
        "top_hotels": top_hotels,
        "context_package": pkg.to_dict(),
        "prompt": prompt,
    }

    # Node 9 (tùy chọn): sinh câu trả lời bằng LLM
    if generate_answer:
        from context import generate_answer as _gen
        out["answer"] = _gen(pkg)

    return out


def _candidates_as_docs(candidate_ids: list[int]) -> list[dict[str, Any]]:
    """Khi chưa có text retrieval: bọc candidate thành 'doc' để xếp hạng bằng nhãn KE.
    Mỗi candidate -> 1 doc mang metadata KE (concept/profile/range) để business_rerank dùng."""
    from knowledge_engineering.common.ke_labels import labels_for

    docs = []
    for hid in candidate_ids:
        ke = labels_for(hid)
        docs.append({
            "chunk_id": f"cand_{hid}",
            "hotel_id": hid,
            "text": "",
            "source": "candidate",
            "rrf_score": 0.0,
            "metadata": {
                "hotel_name": ke.get("title"),
                "ontology_concepts": ke.get("ontology_concepts", []),
                "semantic_profile": ke.get("semantic_profile", {}),
                "city": ke.get("city"),
                "ke_review_score": (ke.get("range_filters") or {}).get("review_score"),
                "ke_star_rating": (ke.get("range_filters") or {}).get("star_rating"),
                "ke_price_min_vnd": (ke.get("range_filters") or {}).get("price_min_vnd"),
            },
        })
    return docs
