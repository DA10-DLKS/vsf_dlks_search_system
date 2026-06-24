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

import contextvars
import time
from contextlib import contextmanager
from typing import Any

# Sink per-request để gom thời gian từng stage (ms) phục vụ truy vết request chậm trong log.
# Khác histogram Prometheus (tổng hợp): cái này gắn được vào ĐÚNG request (kèm request_id/query).
_stage_sink: contextvars.ContextVar["dict | None"] = contextvars.ContextVar(
    "da10_stage_sink", default=None
)

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


@contextmanager
def _stage(name: str):
    """Đo latency một nhóm node, ghi vào da10_stage_duration_seconds{stage=name}.
    Nuốt lỗi observability (không bao giờ làm vỡ pipeline vì lý do đo đạc)."""
    t = time.perf_counter()
    try:
        yield
    finally:
        dur = time.perf_counter() - t
        try:
            from observability.metrics import STAGE_DURATION
            STAGE_DURATION.labels(stage=name).observe(dur)
        except Exception:
            pass
        sink = _stage_sink.get()
        if sink is not None:
            sink[name] = round(dur * 1000, 1)  # ms cho từng stage của riêng request này


def _emit_degraded(bm25_service, vector_service) -> None:
    """Đếm da10_search_degraded_total khi thiếu nguồn text retrieval. Nuốt lỗi observability."""
    missing = None
    if bm25_service is None and vector_service is None:
        missing = "both"
    elif bm25_service is None:
        missing = "bm25"
    elif vector_service is None:
        missing = "vector"
    if missing is None:
        return
    try:
        from observability.metrics import SEARCH_DEGRADED
        SEARCH_DEGRADED.labels(source=missing).inc()
    except Exception:
        pass


def _emit_rerank_method(method: str) -> None:
    """Đếm da10_rerank_method_total{method}. Nuốt lỗi observability."""
    try:
        from observability.metrics import RERANK_METHOD
        RERANK_METHOD.labels(method=method or "unknown").inc()
    except Exception:
        pass


# Câu CẢM TÍNH thuần (không concept/city/giá/sao/brand/loc): vector ĐỀ CỬ top hotel vào pool.
# N + sàn điểm cosine — số đo thật (2026-06): câu cảm tính ~0.57-0.60 lọt, câu vô nghĩa ~0.40 bị
# chặn. Sàn 0.5 phân biệt được. Mục tiêu: hotel vector hiểu đúng ("Old Quarter 1961") vốn KHÔNG
# lọt pool review-cao chung chung -> nay được union vào để rerank phân xử. Xem plan + memory.
SEMANTIC_VECTOR_N = 40
SEMANTIC_VECTOR_FLOOR = 0.5


def _is_semantic_only(intent) -> bool:
    """True khi câu KHÔNG có tín hiệu CẤU TRÚC nào để lọc, chỉ còn ngữ nghĩa thuần. Đây là lúc
    DUY NHẤT cho vector đề cử hotel vào pool (câu có city/concept thì pool đã đúng, không đụng).

    OBJ_HOTEL là concept TRỐNG NGHĨA ('mọi lưu trú', soft, không lọc — xem _obj_ok) nên KHÔNG tính
    là tín hiệu cấu trúc. OBJ_RESORT/VILLA... thì CÓ (lọc loại cụ thể) -> tính. Vì vậy 'khách sạn
    cũ kỹ hoài niệm' (chỉ OBJ_HOTEL) vẫn là semantic-only, còn 'resort đẹp' (OBJ_RESORT) thì không."""
    meaningful_concepts = [c for c in intent.concepts if c != "OBJ_HOTEL"]
    return not (
        meaningful_concepts
        or intent.city
        or intent.location_concepts
        or intent.brand
        or intent.range
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
    # Khởi tạo sink stage-timing cho request hiện tại (mỗi _stage sẽ ghi ms vào đây).
    stage_ms: dict[str, float] = {}
    _stage_sink.set(stage_ms)

    # Degraded mode: thiếu nguồn text retrieval -> pipeline tụt về candidate-only (chất lượng kém
    # hơn) mà API vẫn 200. Đếm để dashboard/alert phát hiện, tránh "âm thầm phục vụ kết quả kém".
    _emit_degraded(bm25_service, vector_service)

    # Node 1
    with _stage("intent"):
        intent = parse_intent(query)

    # Node 2-4: concept lookup + hard filter + candidate builder
    with _stage("filter"):
        # Node 3: concept whitelist
        concepts = _candidate_concepts(intent)
        cw = lookup_hotels_by_concepts(concepts, require_all=False)

        # Node 2: hard filter (in-memory; production có thể thay sql_hard_filter)
        sw = inmemory_hard_filter(
            city=intent.city,
            star_eq=intent.range.get("star_eq"),
            score_min=intent.range.get("score_min"),
            brand=intent.brand,
            price_min=intent.range.get("price_min"),
            price_max=intent.range.get("price_max"),
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

        # Node 4c: NEGATION exclude — loại hotel MANG concept user nói KHÔNG muốn ("không có trẻ em"
        # -> loại hotel gắn PURPOSE_FAMILY). Chỉ exclude concept HARD/PURPOSE/OBJ (rõ có-không);
        # feel (STYLE_/ASPECT_) để rerank lo bằng penalty, không loại cứng (tránh mixed-signal).
        excl = {c for c in intent.exclude_concepts if not c.startswith(("STYLE_", "ASPECT_"))}
        if excl:
            candidates = [
                h for h in candidates
                if excl.isdisjoint(set((labels_for(h) or {}).get("ontology_concepts", [])))
            ]

        # Node 4d: VECTOR ĐỀ CỬ (câu cảm tính thuần). Khi câu không có tín hiệu cấu trúc, pool hiện
        # rơi về 'top review chung chung' (hard-filter trả full 520 -> build_candidates sort review),
        # khiến hotel vector hiểu đúng KHÔNG lọt pool -> rerank vô hiệu (đã đo). Union top-N hotel
        # vector điểm cao (>= sàn) VÀO pool (không thay thế) -> rerank phân xử. Câu có city/concept
        # KHÔNG vào đây (_is_semantic_only=False) nên pool đúng giữ nguyên.
        if _is_semantic_only(intent) and vector_service is not None:
            vr = vector_service.search(query, candidate_hotel_ids=None, top_k=SEMANTIC_VECTOR_N * 4)["results"]
            best: dict[int, float] = {}
            for r in vr:
                hid = r.get("hotel_id")
                if hid is not None:
                    best[hid] = max(best.get(hid, 0.0), r.get("score") or 0.0)
            vec_ids = [hid for hid, sc in sorted(best.items(), key=lambda x: -x[1])
                       if sc >= SEMANTIC_VECTOR_FLOOR][:SEMANTIC_VECTOR_N]
            candidates = list(dict.fromkeys(candidates + vec_ids))

        # V3: candidate rỗng (query không khớp city/concept nào) → KHÔNG trả màn hình trắng.
        # Để vector quyết định (broad semantic), nếu vector vắng thì lấy top hotel theo review.
        if not candidates:
            if vector_service is not None:
                vr = vector_service.search(query, candidate_hotel_ids=None, top_k=candidate_pool)["results"]
                candidates = list(dict.fromkeys(h["hotel_id"] for h in vr if h.get("hotel_id")))
            if not candidates:
                candidates = [h for h, _ in sorted(rs.items(), key=lambda x: -x[1])[:candidate_pool]]

    # Node 6: text retrieval trên candidate. Lấy NHIỀU chunk (rộng) để phủ candidate, không chỉ top-N.
    bm25_results: list[dict[str, Any]] = []
    vector_results: list[dict[str, Any]] = []
    text_topk = max(len(candidates), 50)
    with _stage("text_retrieval"):
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
    with _stage("fusion"):
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
    with _stage("rerank"):
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

        # Node 7C. Câu CẢM TÍNH thuần: nâng trọng số vector (neural) + hạ review — vì lúc này ngữ
        # nghĩa MỚI là tín hiệu đúng, không phải "hotel review cao chung chung". Đã đo: chỉ union
        # hotel vào pool CHƯA đủ (neural 0.05 vẫn để review dìm hotel vector), phải nâng neural thì
        # "Khách sạn Hoài Cổ"/"Old Quarter" mới lên top cho câu "cũ kỹ hoài niệm". Câu có cấu trúc
        # giữ trọng số mặc định (review/concept dẫn dắt như cũ).
        rerank_weights = {"neural": 0.4, "review": 0.1} if _is_semantic_only(intent) else None
        reranked = business_rerank(
            reranked, concepts=intent.concepts, weights=rerank_weights,
            intent_max_price=intent.range.get("price_max"),
            intent_min_price=intent.range.get("price_min"),
        )
        top_hotels = aggregate_by_hotel(reranked, top_n=top_n, sort=intent.range.get("sort"))

    # Đếm phương pháp rerank thực tế (cross-encoder vs density-fallback) để theo dõi tỉ lệ
    # reranker neural có thực sự chạy hay luôn rơi về fallback.
    _emit_rerank_method(rerank_method)

    # Node 8
    with _stage("context"):
        pkg = build_context_package(query, top_hotels, extra_metadata={"intent": intent.to_dict()})
        prompt = build_prompt(pkg)

    out = {
        "intent": intent.to_dict(),
        "n_candidates": len(candidates),
        "n_fused": len(fused),
        "rerank_method": rerank_method,
        "stage_ms": stage_ms,   # breakdown latency từng stage của request này (cho log/truy vết)
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
                "ke_price_max_vnd": (ke.get("range_filters") or {}).get("price_max_vnd"),
            },
        })
    return docs
