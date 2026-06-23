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
    METHOD_DENSITY_FALLBACK,
    aggregate_by_hotel,
    apply_profile_boost,
    business_rerank,
    neural_rerank,
    rrf_by_hotel,
)


def _candidate_concepts(intent) -> list[str]:
    """Concept dùng cho Node 3 lookup (hard + feel + price + lmk). KHÔNG gồm:
    - location_concepts: xử lý RIÊNG bằng hierarchy (hotel ở xã con khớp query thành phố cha) —
      nếu để concept index khớp ĐÚNG loc thì 'Phú Quốc' loại hotel 'Gành Dầu' (con).
    - object_types: OBJ là SOFT (port query_demo). 'khách sạn'(OBJ_HOTEL)=mọi lưu trú, KHÔNG lọc;
      chỉ lọc khi câu nêu LOẠI CỤ THỂ (resort/villa) mà KHÔNG kèm OBJ_HOTEL. Xử lý ở _obj_ok."""
    return (
        intent.hard_concepts
        + intent.feel_concepts
        + intent.price_tiers
        + intent.landmarks
    )


def _location_whitelist(intent) -> set[int] | None:
    """Hotel khớp location query theo HIERARCHY (LOC con khớp LOC cha). None nếu câu không nêu
    location_concepts (để city-text filter ở Node 2 lo)."""
    from retrieval.filtering import hotels_in_location
    locs = intent.location_concepts
    if not locs:
        return None
    out: set[int] = set()
    for loc in locs:
        out |= set(hotels_in_location(loc))
    return out


def _obj_ok(intent, hotel_concepts: set[str]) -> bool:
    """OBJ filter SOFT (port query_demo): chỉ loại khi câu nêu loại CỤ THỂ (resort/villa...) mà
    KHÔNG kèm OBJ_HOTEL, và hotel không thuộc loại đó. 'khách sạn' hoặc không nêu loại -> luôn OK."""
    want = [c for c in intent.object_types if c != "OBJ_HOTEL"]
    if not want or "OBJ_HOTEL" in intent.object_types:
        return True
    return not hotel_concepts.isdisjoint(want)


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
        brand=intent.brand,
    )

    # Node 2b: LOCATION hierarchy. Nếu câu nêu LOC_* -> giao sw với tập hotel thuộc loc (hoặc xã
    # con). Đây thay cho việc đưa LOC vào concept giao cứng (vốn loại oan hotel ở xã con).
    loc_wl = _location_whitelist(intent)
    if loc_wl is not None:
        sw = [h for h in sw if h in loc_wl] if sw else list(loc_wl)

    # Node 4: candidate
    rs = review_scores()
    candidates = build_candidates(
        sw or None, cw.hotel_ids or None, cap=candidate_pool, review_score_by_hotel=rs,
        match_count_by_hotel=cw.match_count,
        idf_score_by_hotel=cw.idf_score,   # V5: ưu tiên concept ĐẶC TRƯNG (IDF) khi cắt cap
    )

    # Node 4b: OBJ soft filter — loại hotel sai loại CHỈ khi câu nêu loại cụ thể (không OBJ_HOTEL).
    from knowledge_engineering.common.ke_labels import labels_for
    if any(c != "OBJ_HOTEL" for c in intent.object_types) and "OBJ_HOTEL" not in intent.object_types:
        candidates = [
            h for h in candidates
            if _obj_ok(intent, set((labels_for(h) or {}).get("ontology_concepts", [])))
        ]

    # V3: candidate rỗng (query không khớp city/concept nào) → KHÔNG trả màn hình trắng.
    # Để vector quyết định (broad semantic), nếu vector vắng thì lấy top hotel theo review.
    if not candidates:
        if vector_service is not None:
            vr = vector_service.search(query, candidate_hotel_ids=None, top_k=candidate_pool)["results"]
            candidates = list(dict.fromkeys(h["hotel_id"] for h in vr if h.get("hotel_id")))
        if not candidates:
            candidates = [h for h, _ in sorted(rs.items(), key=lambda x: -x[1])[:candidate_pool]]

    # Node 6: text retrieval trên candidate
    # Node 6: text retrieval. Lấy NHIỀU chunk (rộng) để phủ candidate, không chỉ top-N.
    bm25_results: list[dict[str, Any]] = []
    vector_results: list[dict[str, Any]] = []
    text_topk = max(len(candidates), 50)
    if bm25_service is not None:
        bm25_results = bm25_service.search_for_fusion(
            query, candidate_hotel_ids=candidates, size=text_topk
        )["results"]
    if vector_service is not None:
        vector_results = vector_service.search(
            query, candidate_hotel_ids=candidates, top_k=text_topk
        )["results"]

    # Node 7: fusion. NGUYÊN TẮC: vector/BM25 BỔ SUNG, KHÔNG thay thế candidate. Nền là TOÀN BỘ
    # candidate (giữ recall theo multi-signal); điểm text retrieval gắn vào hotel tương ứng làm
    # tín hiệu RERANK. Hotel candidate không có chunk text vẫn ở lại (không bị loại) -> không
    # tụt recall. (Trước đây fused = chỉ chunk vector top-k -> bỏ sót hotel relevant -> recall ↓.)
    fused = _candidates_as_docs(candidates)
    if bm25_results or vector_results:
        # V9: RRF hợp nhất ở CẤP HOTEL (bm25 doc-level vs vector chunk-level không trùng chunk_id).
        text_ranked = rrf_by_hotel(bm25_results, vector_results)
        _merge_text_signal(fused, text_ranked)

    fused = apply_profile_boost(fused, intent.feel_concepts)

    # Node 7B: rerank GIỮ toàn bộ fused (không cắt) -> aggregate_by_hotel mới chọn top_n hotel.
    # Cắt ở đây sẽ bỏ sót hotel relevant trước khi gom theo hotel -> tụt recall.
    # V2: bật cross-encoder qua env USE_RERANKER=1 (mặc định off vì đắt + đã biết không kéo recall;
    # mục tiêu là MRR/thứ hạng). Cross-encoder CHỈ có nghĩa với doc CÓ text thật → chỉ rerank nhóm
    # đó, doc text rỗng (candidate thuần KE) giữ nguyên rồi gộp lại để không tụt recall.
    import os as _os
    use_model = use_reranker_model or _os.environ.get("USE_RERANKER", "0") == "1"
    if use_model:
        with_text = [d for d in fused if (d.get("text") or "").strip()]
        without_text = [d for d in fused if not (d.get("text") or "").strip()]
        reranked = neural_rerank(query, with_text, top_k=len(with_text), use_model=True)
        reranked = reranked + without_text
    else:
        reranked = neural_rerank(query, fused, top_k=len(fused), use_model=False)

    # Chế độ rerank THỰC TẾ đã chạy (cross-encoder vs density-fallback). neural_rerank gắn
    # doc["rerank_method"]; đọc lại để expose ra API — kể cả khi USE_RERANKER=1 nhưng model
    # load lỗi thì giá trị này tự là density-fallback (phản ánh đúng cái đã xảy ra).
    rerank_method = next(
        (d["rerank_method"] for d in reranked if d.get("rerank_method")),
        METHOD_DENSITY_FALLBACK,
    )

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
        "rerank_method": rerank_method,
        "top_hotels": top_hotels,
        "context_package": pkg.to_dict(),
        "prompt": prompt,
    }

    # Node 9 (tùy chọn): sinh câu trả lời bằng LLM
    if generate_answer:
        from context import generate_answer as _gen
        out["answer"] = _gen(pkg)

    return out


def _merge_text_signal(candidate_docs: list[dict[str, Any]], text_ranked: list[dict[str, Any]]) -> None:
    """Gắn tín hiệu text retrieval (rrf_score + text chunk) vào candidate doc theo hotel_id.
    Mỗi hotel lấy chunk điểm CAO NHẤT. Hotel không có chunk text giữ rrf_score=0 (vẫn ở lại,
    xếp hạng bằng business score). Sửa tại chỗ (in-place)."""
    best: dict[Any, dict[str, Any]] = {}
    for d in text_ranked:
        hid = d.get("hotel_id")
        if hid is None:
            continue
        if hid not in best or d.get("rrf_score", 0) > best[hid].get("rrf_score", 0):
            best[hid] = d
    for doc in candidate_docs:
        t = best.get(doc.get("hotel_id"))
        if t:
            doc["rrf_score"] = t.get("rrf_score", 0.0)
            if t.get("text"):
                doc["text"] = t["text"]          # thay text rỗng bằng chunk thật (cho Node 8/9)
            doc["bm25_rank"] = t.get("bm25_rank")
            doc["vector_rank"] = t.get("vector_rank")


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
