# Sơ đồ luồng Retrieval & Ranking

Nguồn: [`retrieval/hybrid_search/pipeline.py`](../../../retrieval/hybrid_search/pipeline.py) — hàm `run_hybrid_search()`, và [`retrieval/reranking/fusion.py`](../../../retrieval/reranking/fusion.py).

Pipeline gồm 8 node (Node 1→8), thiết kế để **từng node có thể vắng service** mà luồng vẫn chạy (degrade về candidate KE thuần).

---

## 1. Luồng tổng quan (end-to-end)

```mermaid
flowchart TD
    Q["Query (text)"] --> N1

    subgraph QP["Node 1 · Query processing"]
        N1["parse_intent(query)<br/>→ city, range, concepts,<br/>feel/hard/object/price/lmk/location"]
    end

    N1 --> N3 & N2

    subgraph FILTER["Node 2–4 · Filtering"]
        N3["Node 3 · concept lookup<br/>lookup_hotels_by_concepts<br/>(inverted index, require_all=False)"]
        N2["Node 2 · hard filter<br/>inmemory_hard_filter<br/>(city / star_eq / score_min)"]
        N4["Node 4 · build_candidates<br/>cap=candidate_pool (100)<br/>ưu tiên IDF concept đặc trưng"]
    end

    N3 --> N4
    N2 --> N4

    N4 --> EMPTY{"candidates rỗng?"}
    EMPTY -- "có vector" --> VBROAD["vector broad semantic<br/>(không lọc candidate)"]
    EMPTY -- "không vector" --> RTOP["top hotel theo review_score"]
    EMPTY -- "không" --> N6
    VBROAD --> N6
    RTOP --> N6

    subgraph RETR["Node 6 · Text retrieval (trên candidate)"]
        N6["BM25 search_for_fusion + Vector search<br/>text_topk = max(len(candidates), 50)"]
    end

    N6 --> N7

    subgraph FUSE["Node 7 · Fusion + boost"]
        N7["nền = TOÀN BỘ candidate (giữ recall)<br/>rrf_by_hotel(bm25, vector) → text_ranked<br/>_merge_text_signal: gắn rrf_score vào hotel<br/>apply_profile_boost(feel_concepts)"]
    end

    N7 --> N7B

    subgraph RERANK["Node 7B · Neural rerank"]
        N7B{"USE_RERANKER=1?"}
        N7B -- "có" --> CE["cross-encoder<br/>(chỉ doc CÓ text)"]
        N7B -- "không / lỗi" --> DENS["density-fallback"]
    end

    CE --> N7C
    DENS --> N7C

    subgraph BIZ["Node 7C · Business rerank + aggregate"]
        N7C["business_rerank<br/>(text_signal chuẩn hóa [0,1] + review<br/>+ review_count + price_fit + concept)"]
        AGG["aggregate_by_hotel(top_n)<br/>gom chunk → hotel, +bonus đa chunk"]
    end

    N7C --> AGG

    AGG --> N8

    subgraph CTX["Node 8 · Context"]
        N8["build_context_package<br/>+ build_prompt"]
    end

    N8 --> GEN{"generate_answer?"}
    GEN -- "có" --> N9["Node 9 · LLM answer"]
    GEN -- "không" --> OUT
    N9 --> OUT["{intent, top_hotels,<br/>context_package, prompt[, answer]}"]
```

---

## 2. Chi tiết tính điểm ranking

Hai tầng cho điểm độc lập rồi hợp nhất: **RRF (cấp hotel)** → **business score** → **final score**.

```mermaid
flowchart LR
    subgraph SRC["Tín hiệu text retrieval"]
        BM["BM25 results"] --> RRF
        VEC["Vector results"] --> RRF
    end

    RRF["rrf_by_hotel<br/>Σ 1/(k+rank), k=60<br/>gom theo hotel_id"] --> RRFS["rrf_score"]

    RRFS --> PB["apply_profile_boost<br/>+ 0.05 × Σ profile.score<br/>(feel_concepts)"]
    PB --> FS["fused_score"]

    FS --> NEU["neural_rerank<br/>(cross-encoder → rerank_score<br/>hoặc density-fallback)"]

    NEU --> BR

    subgraph BR["business_rerank — chuẩn hóa text-signal [0,1] trước khi fuse"]
        direction TB
        NORM["neural = minmax(rerank/ fused/ rrf)"]
        RV["review = ke_review_score / 10"]
        RC["review_count = log1p(n)/log1p(max)"]
        PF["price_fit = 1 nếu price ≤ intent_max_price"]
        CM["concept = |concepts ∩ ontology| / |concepts|"]
    end

    BR --> BS["business_score =<br/>0.05·neural + 0.2·review<br/>+ 0.1·review_count<br/>+ 0.1·price_fit + 0.1·concept"]

    BS --> AGG2["aggregate_by_hotel<br/>max_score/hotel<br/>+ 0.01·min(count-1, 5)"]
    AGG2 --> FINAL["final_score → top_n"]
```

> **Lưu ý quan trọng (xem memory):** text-signal RRF nằm thang `[0, ~0.016]` còn review/price/concept đã ở `[0,1]`. Nếu cộng thẳng, text-signal bị nuốt ~24×. `business_rerank` **chuẩn hóa min-max text-signal về `[0,1]` trên tập candidate** trước khi fuse. Trọng số `neural=0.05` được calibrate bằng sweep trên `golden_set_v2` (recall 0.5114 / MRR 0.9065 / Hit 0.9831).

---

## Hằng số & trọng số

| Tham số | Giá trị | Vị trí |
|---|---|---|
| `RRF_K` | 60 | `fusion.py` |
| `PROFILE_BOOST_WEIGHT` | 0.05 | `fusion.py` |
| `BUSINESS_WEIGHTS.neural` | 0.05 | `fusion.py` |
| `BUSINESS_WEIGHTS.review` | 0.2 | `fusion.py` |
| `BUSINESS_WEIGHTS.review_count` | 0.1 | `fusion.py` |
| `BUSINESS_WEIGHTS.price_fit` | 0.1 | `fusion.py` |
| `BUSINESS_WEIGHTS.concept` | 0.1 | `fusion.py` |
| `candidate_pool` | 100 | `pipeline.py` |
| `top_n` | 5 | `pipeline.py` |
| aggregate bonus | `0.01 × min(count-1, 5)` | `fusion.py` |
