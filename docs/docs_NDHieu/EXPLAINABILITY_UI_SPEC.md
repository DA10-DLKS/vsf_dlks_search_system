# EXPLAINABILITY_UI_SPEC.md

Spec giao diện **Explainable Search Journey** cho DA10 OTA AI Search Platform.

Mục tiêu: mentor nhìn vào UI phải hiểu được:

- Hệ thống hiểu query thế nào.
- Ontology được dùng ở đâu.
- Retrieval đi qua các bước nào.
- Ranking hoạt động thế nào.
- Vì sao hotel A đứng trên hotel B.

Phạm vi tài liệu này: đọc code runtime thật, không suy đoán từ docs. Nếu output chưa chạy được do thiếu dependency, ghi rõ.

## 1. Runtime Evidence Map

| Responsibility | Runtime File | Function/Class | Status |
| --- | --- | --- | --- |
| Query input vào API | `api/main.py` | `hybrid_search`, `fe_search`, `fe_context` | IMPLEMENTED |
| Parse intent/query | `retrieval/query_processing/intent_parser.py` | `parse_intent`, `ParsedIntent` | IMPLEMENTED, nhưng local run đang lỗi thiếu `underthesea` |
| Normalize/tokenize query | `knowledge_engineering/common/normalize.py` | imported by intent parser | IMPLEMENTED, dependency missing |
| Implicit intent | `knowledge_engineering/common/implicit_intent.py` | `parse_implicit_intent` | IMPLEMENTED |
| Map concept/synonym | `retrieval/query_processing/intent_parser.py` | `_lookup_concepts` | IMPLEMENTED |
| Concept index | `retrieval/filtering/concept_index.py` | `build_concept_index`, `lookup_hotels_by_concepts` | IMPLEMENTED |
| Hard filters | `retrieval/filtering/hard_filter.py` | `inmemory_hard_filter`, `sql_hard_filter` | IMPLEMENTED |
| Build candidates | `retrieval/filtering/hard_filter.py` | `build_candidates` | IMPLEMENTED |
| BM25 retrieval | `retrieval/lexical_search/service.py` | `BM25SearchService.search_for_fusion` | IMPLEMENTED |
| Vector retrieval | `retrieval/vector_search/qdrant_service.py` | `QdrantSearchService.search` | IMPLEMENTED, requires Qdrant/index/model |
| Hybrid orchestration | `retrieval/hybrid_search/pipeline.py` | `run_hybrid_search` | IMPLEMENTED |
| RRF fusion | `retrieval/reranking/fusion.py` | `rrf_by_hotel` | IMPLEMENTED |
| Profile boost | `retrieval/reranking/fusion.py` | `apply_profile_boost` | IMPLEMENTED |
| Neural rerank | `retrieval/reranking/neural_rerank.py` | `neural_rerank` | IMPLEMENTED with fallback |
| Business rerank | `retrieval/reranking/fusion.py` | `business_rerank` | IMPLEMENTED |
| Aggregate final hotels | `retrieval/reranking/fusion.py` | `aggregate_by_hotel` | IMPLEMENTED |
| Context package | `context/context_package.py` | `ContextPackage`, `build_context_package`, `build_prompt` | IMPLEMENTED |
| Context answer/evidence | `api/frontend_adapter.py` | `build_hotel_context`, `_grounded_evidence` | IMPLEMENTED |
| Frontend adapter | `api/frontend_adapter.py` | `to_search_response` | IMPLEMENTED |

## 2. Runtime Check For Sample Query

Sample query:

```text
khách sạn phù hợp cho trẻ nhỏ gần Vinwonders Phú Quốc
```

Attempted runtime command:

```bash
python -c "from retrieval.query_processing.intent_parser import parse_intent; ..."
.venv\Scripts\python -c "from retrieval.query_processing.intent_parser import parse_intent; ..."
```

Observed output:

```text
ModuleNotFoundError: No module named 'underthesea'
```

Conclusion:

- Full runtime execution could not be verified on current machine because `knowledge_engineering/common/normalize.py` imports `underthesea`.
- The simulation below is based on code path and ontology assets that exist in the repository.
- Do not label exact counts/confidences as “measured” until dependency is installed and `/hybrid_search` is executed.

## 3. Sample Query Pipeline Simulation

### Step 1: Query Parsing

| Field | Value |
| --- | --- |
| INPUT | `khách sạn phù hợp cho trẻ nhỏ gần Vinwonders Phú Quốc` |
| Runtime file | `retrieval/query_processing/intent_parser.py` |
| Runtime function | `parse_intent` |
| Data source | `ontology/synonym_dictionary.yaml`, `knowledge_engineering/common/implicit_intent.py`, `knowledge_engineering/common/normalize.py` |
| Expected OUTPUT | `ParsedIntent` object |
| CONFIDENCE | Not exposed by backend |

Expected output shape from code:

```json
{
  "query": "...",
  "concepts": [],
  "hard_concepts": [],
  "feel_concepts": [],
  "object_types": [],
  "purposes": [],
  "price_tiers": [],
  "landmarks": [],
  "location_concepts": [],
  "city": null,
  "range": {},
  "implicit": {}
}
```

Evidence:

- `retrieval/query_processing/intent_parser.py`: `ParsedIntent.to_dict`.
- `api/main.py`: `/hybrid_search` returns `result = run_hybrid_search(...)`, and pipeline returns `intent.to_dict()`.

Backend status:

- Backend has this logic.
- Backend exposes it through `GET /hybrid_search` as `intent`.
- Frontend can display immediately from `/hybrid_search.intent`.

Need backend bổ sung:

- Per-concept `matched_text`.
- Per-concept `source`.
- Per-concept `confidence`.

### Step 2: Concept Detection

Expected concepts for sample query based on assets:

| Concept | Evidence in Repo | Source Type | Confidence |
| --- | --- | --- | --- |
| `OBJ_HOTEL` | `ontology/synonym_dictionary.yaml` contains `khach san` | synonym lookup | Not exposed |
| `PURPOSE_FAMILY` | surface forms include `có trẻ nhỏ`, `gia đình có trẻ nhỏ`; implicit intent likely catches family/children | synonym/implicit | Not exposed |
| `LOC_PHU_QUOC` | `ontology/core/location.generated.yaml` has `LOC_PHU_QUOC`; synonyms contain `phu quoc` | location synonym | Not exposed |
| `LMK_VINWONDERS_PHU_QUOC` | `ontology/core/location.generated.yaml` has `LMK_VINWONDERS_PHU_QUOC`; synonyms contain `vinwonders phu quoc` | landmark synonym | Not exposed |

Important caveat:

- `Vinwonders Phú Quốc` appears as `vinwonders phu quoc` and `vinwonders phú_quốc` in generated location/synonym assets.
- The runtime result depends on normalization and tokenization, which could not be executed due missing `underthesea`.

Backend status:

- Concept detection exists.
- `/hybrid_search` exposes grouped concepts in `intent`.
- It does not expose matched text/confidence/source per concept.

Frontend display now:

- Can show concept badges grouped by:
  - object type
  - purpose
  - location
  - landmark
  - hard concepts
  - feel concepts

Need backend bổ sung:

```json
{
  "concept_trace": [
    {
      "concept": "PURPOSE_FAMILY",
      "matched_text": "trẻ nhỏ",
      "source": "implicit_intent",
      "confidence": 0.92,
      "ontology_node": "ontology/core/purpose.yaml"
    }
  ]
}
```

### Step 3: Intent Detection

| Field | Value |
| --- | --- |
| INPUT | Detected concepts + parsed city/range |
| Runtime file | `retrieval/query_processing/intent_parser.py` |
| Runtime function | `parse_intent` |
| Data source | concept prefixes and `parse_city`, `parse_range` |
| Expected OUTPUT | `object_types`, `purposes`, `landmarks`, `location_concepts`, `city`, `range` |
| CONFIDENCE | Not exposed |

Expected intent interpretation:

```json
{
  "object_types": ["OBJ_HOTEL"],
  "purposes": ["PURPOSE_FAMILY"],
  "landmarks": ["LMK_VINWONDERS_PHU_QUOC"],
  "location_concepts": ["LOC_PHU_QUOC"],
  "city": "phú quốc",
  "range": {}
}
```

This is expected, not verified by runtime due missing dependency.

Backend status:

- Implemented and exposed via `GET /hybrid_search`.

Frontend display now:

- Yes, if calling `/hybrid_search`.

Need backend bổ sung:

- Intent confidence.
- Explicit route classification, e.g. `hotel_search`, `near_landmark_search`, `family_trip_search`.

### Step 4: Query Expansion

| Field | Value |
| --- | --- |
| INPUT | `PURPOSE_FAMILY`, `LOC_PHU_QUOC`, `LMK_VINWONDERS_PHU_QUOC`, `OBJ_HOTEL` |
| Runtime file | `ontology/query_expansion.yaml` asset exists |
| Runtime function | No direct call found in `run_hybrid_search` |
| Data source | `ontology/query_expansion.yaml`, `ontology/relations/*.yaml` |
| Expected OUTPUT | expansion edges |
| CONFIDENCE | Exists in expansion YAML |

Relevant expansion assets:

```text
PURPOSE_FAMILY
-> AMEN_KIDS_CLUB
   relation_type: evidence_for
   source_type: curated
   use_as: boost
   confidence: 0.85

PURPOSE_FAMILY
-> AMEN_KIDS_POOL
   relation_type: evidence_for
   source_type: curated
   use_as: boost
   confidence: 0.85

LOC_PHU_QUOC
-> SETTING_ISLAND
   relation_type: implies
   use_as: filter
   confidence: 1.0
```

Evidence:

- `ontology/query_expansion.yaml`: rules for `PURPOSE_FAMILY`, `LOC_PHU_QUOC`.
- `knowledge_engineering/common/relation_loader.py`: relation schema supports `type`, `source_type`, `confidence`, `use_as`, `status`.

Backend status:

- Expansion asset exists.
- Runtime `run_hybrid_search` does not visibly apply `ontology/query_expansion.yaml`.
- Backend does not expose expansion trace.

Frontend display now:

- Can display “Available Ontology Expansion” from a static/loaded YAML-derived source only if exposed or embedded.
- Should not say “used in ranking” yet.

Need backend bổ sung:

- `expanded_concepts`.
- `expansion_edges_used`.
- `used_in_filter` / `used_in_boost`.

### Step 5: Candidate Generation

| Field | Value |
| --- | --- |
| INPUT | intent concepts + city/range |
| Runtime files | `retrieval/filtering/concept_index.py`, `retrieval/filtering/hard_filter.py`, `retrieval/hybrid_search/pipeline.py` |
| Runtime functions | `_candidate_concepts`, `lookup_hotels_by_concepts`, `inmemory_hard_filter`, `build_candidates` |
| Data source | `knowledge_engineering/enrichment/knowledge_objects.json` via `ke_labels.py` |
| OUTPUT | candidate hotel ids |
| CONFIDENCE | Not applicable |

Pipeline behavior from code:

1. `_candidate_concepts(intent)` combines:
   - `hard_concepts`
   - `feel_concepts`
   - `object_types`
   - `price_tiers`
   - `landmarks`
   - `location_concepts`
2. `lookup_hotels_by_concepts(concepts, require_all=False)` returns:
   - `hotel_ids`
   - `match_count`
   - `idf_score`
3. `inmemory_hard_filter(city=..., star_eq=..., score_min=...)` returns SQL-like whitelist without DB.
4. `build_candidates` intersects/fallbacks and caps candidate list.

Backend status:

- Implemented.
- `/hybrid_search` exposes only `n_candidates`.
- It does not expose all counts and candidate reason.

Frontend display now:

- Can show `n_candidates`.
- Cannot show 520 -> 63 -> 28 funnel unless backend adds counts.

Need backend bổ sung:

```json
{
  "candidate_trace": {
    "total_hotels": 520,
    "concept_lookup_count": 128,
    "hard_filter_count": 63,
    "intersection_count": 28,
    "final_candidate_count": 100,
    "fallback_reason": null
  }
}
```

### Step 6: Retrieval

| Field | Value |
| --- | --- |
| INPUT | candidates + query |
| Runtime files | `retrieval/lexical_search/service.py`, `retrieval/vector_search/qdrant_service.py` |
| Runtime functions | `search_for_fusion`, `QdrantSearchService.search` |
| Data source | OpenSearch BM25 index, Qdrant collection |
| OUTPUT | BM25 results + vector results |
| CONFIDENCE | Retrieval scores exist, but no confidence field |

Runtime behavior:

- BM25 uses OpenSearch `multi_match` with fields:
  - `name`
  - `description^2`
  - `city`
  - `address`
  - `amenities`
- Vector search embeds query and searches Qdrant with optional `candidate_hotel_ids` filter.

Backend status:

- Implemented.
- `/hybrid_search` uses services if available.
- If services unavailable, pipeline falls back to candidate/ranking logic.
- API currently does not expose BM25 hit count/vector hit count separately.

Frontend display now:

- Can show top hotel fields after fusion.
- Can show `bm25_rank`/`vector_rank` if present in `top_hotels`.

Need backend bổ sung:

- `retrieval_trace.bm25_results`.
- `retrieval_trace.vector_results`.
- `retrieval_trace.service_status`.

### Step 7: Ranking

| Field | Value |
| --- | --- |
| INPUT | candidate docs + BM25/vector results |
| Runtime files | `retrieval/reranking/fusion.py`, `retrieval/reranking/neural_rerank.py` |
| Runtime functions | `rrf_by_hotel`, `apply_profile_boost`, `neural_rerank`, `business_rerank`, `aggregate_by_hotel` |
| OUTPUT | `top_hotels` |
| CONFIDENCE | Ranking scores, not confidence |

Ranking factors implemented:

| Factor | Code |
| --- | --- |
| RRF score | `rrf_by_hotel` |
| BM25 rank | `_merge_text_signal` attaches `bm25_rank` |
| Vector rank | `_merge_text_signal` attaches `vector_rank` |
| Profile boost | `apply_profile_boost` |
| Rerank score | `neural_rerank` |
| Text signal normalization | `business_rerank` writes `text_signal_norm` |
| Review score component | internal in `business_rerank` |
| Review count component | internal in `business_rerank` |
| Price fit component | internal in `business_rerank` |
| Concept match component | internal in `business_rerank` |
| Final score | `aggregate_by_hotel` |

Backend status:

- Implemented.
- `/hybrid_search` exposes `top_hotels` with many fields.
- It does not expose full contribution breakdown.

Frontend display now:

- Can show ranking factors that exist on `top_hotels`.
- Cannot honestly show “Location bonus +1.2 / Kids Club +0.9” unless backend adds those components.

Need backend bổ sung:

```json
{
  "ranking_breakdown": {
    "rrf_score": 0.015,
    "profile_boost": 0.08,
    "review_component": 0.18,
    "review_count_component": 0.04,
    "price_fit_component": 0.10,
    "concept_match_component": 0.07,
    "final_score": 0.47
  }
}
```

### Step 8: Context Building

| Field | Value |
| --- | --- |
| INPUT | top hotels or selected `result_id` |
| Runtime files | `context/context_package.py`, `api/frontend_adapter.py`, `context/answer_generator.py` |
| Runtime functions | `build_context_package`, `build_prompt`, `build_hotel_context`, `_grounded_evidence`, `generate_answer` |
| Data source | `knowledge_objects.json`, `semantic_profile`, `negative_style_profile`, review evidence |
| OUTPUT | context chunks, prompt, `llm_context`, citation/source/chunk ids, evidence |
| CONFIDENCE | ABSA/profile scores exist in evidence, not standardized confidence |

Backend status:

- Implemented.
- `/hybrid_search` exposes `context_package` and `prompt`.
- `/context` exposes `llm_context`, `citations`, `source_documents`, `context_chunks`, `evidence`.

Frontend display now:

- Can display immediately.

Need backend bổ sung:

- Rich citation objects rather than only ids.
- Full context chunk objects from `/context`.
- Provenance per evidence span.

## 4. Explainable Search Journey UI Spec

The UI should not start with hotel cards. It should start with journey stages.

```text
Query
-> Understanding
-> Ontology
-> Candidate Funnel
-> Retrieval
-> Ranking
-> Evidence
-> Context
```

### Component 1: QueryInputBar

| Field | Value |
| --- | --- |
| Component Name | `QueryInputBar` |
| Purpose | Accept user query and trigger explainability flow |
| Input Data | raw text query |
| Output Data | query string |
| Priority | P0 |

### Component 2: QueryUnderstandingPanel

| Field | Value |
| --- | --- |
| Component Name | `QueryUnderstandingPanel` |
| Purpose | Show how the system parsed the query |
| Input Data | `/hybrid_search.intent` |
| Output Data | concept groups, city, range filters, implicit intents |
| Priority | P0 |

Display:

- Original query.
- Parsed concept groups.
- `city`.
- `range`.
- `implicit`.
- Badge if exact matched text/confidence is unavailable.

### Component 3: ConceptTraceTable

| Field | Value |
| --- | --- |
| Component Name | `ConceptTraceTable` |
| Purpose | Explain detected concepts |
| Input Data | `intent.concepts`, `intent.object_types`, `intent.purposes`, `intent.landmarks`, `intent.location_concepts` |
| Output Data | table of concept id, facet, evidence availability |
| Priority | P0 now, richer P1 |

Current limitation:

- `matched_text`, `source`, `confidence` not exposed.

### Component 4: QueryExpansionGraph

| Field | Value |
| --- | --- |
| Component Name | `QueryExpansionGraph` |
| Purpose | Show ontology expansion edges |
| Input Data | `ontology/query_expansion.yaml` or future `expansion_trace` |
| Output Data | graph/table of source concept -> target concept |
| Priority | P1 |

UI warning:

- Label edges as `available ontology expansion` unless backend marks them runtime-used.

### Component 5: RetrievalFunnel

| Field | Value |
| --- | --- |
| Component Name | `RetrievalFunnel` |
| Purpose | Show count reduction and candidate construction |
| Input Data | `n_candidates`, `n_fused`, future `candidate_trace` |
| Output Data | funnel stages and counts |
| Priority | P0 partial, P1 full |

Can show now:

- `n_candidates`
- `n_fused`
- `top_hotels.length`

Needs backend:

- total hotels, hard filter count, concept lookup count, BM25/vector count.

### Component 6: RetrievalSourceComparison

| Field | Value |
| --- | --- |
| Component Name | `RetrievalSourceComparison` |
| Purpose | Explain BM25 vs vector vs hybrid |
| Input Data | `GET /search`, `GET /hybrid_search.top_hotels` |
| Output Data | BM25-only top list vs hybrid top list |
| Priority | P1 |

### Component 7: RankingBreakdownPanel

| Field | Value |
| --- | --- |
| Component Name | `RankingBreakdownPanel` |
| Purpose | Explain why hotel A ranks above hotel B |
| Input Data | `top_hotels[]` |
| Output Data | score bars/table |
| Priority | P0 partial, P1 full |

Can show now:

- `final_score`
- `business_score`
- `rrf_score`
- `bm25_rank`
- `vector_rank`
- `rerank_score`
- `text_signal_norm`
- `matched_chunks`

Needs backend:

- score contribution breakdown.

### Component 8: EvidencePanel

| Field | Value |
| --- | --- |
| Component Name | `EvidencePanel` |
| Purpose | Link ranking signals to evidence |
| Input Data | `/context.evidence`, search citations/source docs/chunks |
| Output Data | positive evidence, negative evidence, citation/source/chunk ids |
| Priority | P0 |

### Component 9: ContextPackagePanel

| Field | Value |
| --- | --- |
| Component Name | `ContextPackagePanel` |
| Purpose | Show what DA10 passes to LLM/DA09 |
| Input Data | `/hybrid_search.context_package`, `/hybrid_search.prompt`, `/context.llm_context` |
| Output Data | context package, prompt, LLM consumption preview |
| Priority | P0 |

### Component 10: OntologyImpactPanel

| Field | Value |
| --- | --- |
| Component Name | `OntologyImpactPanel` |
| Purpose | Show why ontology improves retrieval |
| Input Data | BM25 `/search`, hybrid `/hybrid_search`, evaluation outputs if available |
| Output Data | side-by-side comparison |
| Priority | P1 |

### Component 11: ReviewerMode

| Field | Value |
| --- | --- |
| Component Name | `ReviewerMode` |
| Purpose | Full debug/review view for mentor |
| Input Data | raw API payloads |
| Output Data | raw JSON, trace tables, warnings |
| Priority | P0 |

## 5. Per-Step Implementation Readiness

| Step | Backend Has Logic | Backend Exposes API | Frontend Can Show Now | Needs Backend Change |
| --- | --- | --- | --- | --- |
| Query Parsing | Yes | Yes via `/hybrid_search.intent` | Yes | matched text/confidence |
| Concept Detection | Yes | Partial via `intent` | Yes, concept badges | concept trace |
| Intent Detection | Yes | Yes via `intent` | Yes | route/confidence |
| Query Expansion | Asset exists | No runtime trace | Partial as static/asset view | expansion trace |
| Candidate Generation | Yes | Partial via `n_candidates` | Partial | full counts/fallback reason |
| Retrieval | Yes | Partial via `top_hotels` | Partial | BM25/vector hit lists |
| Ranking | Yes | Partial via `top_hotels` | Partial | score contribution breakdown |
| Context Building | Yes | Yes via `/context` and `/hybrid_search` | Yes | richer citation/source/chunk objects |

## 6. IMPLEMENTABLE NOW

Can code immediately using existing backend:

1. Use `GET /hybrid_search?q=<query>&top_n=10` as the main explainability endpoint.
2. Render `QueryUnderstandingPanel` from `intent`.
3. Render `RetrievalFunnel` with available counts:
   - `n_candidates`
   - `n_fused`
   - `top_hotels.length`
4. Render `RankingBreakdownPanel` from fields present in `top_hotels`.
5. Render `ContextPackagePanel` from:
   - `context_package`
   - `prompt`
6. On selected hotel, call `POST /context` and render:
   - `llm_context`
   - `evidence.positives`
   - `evidence.negatives`
   - citation/source/chunk ids
7. Add `ReviewerMode` raw JSON tabs.

## 7. NEEDS BACKEND CHANGE

Required to make UI fully explainable:

1. Add `concept_trace`.
2. Add `expansion_trace`.
3. Add candidate funnel counts.
4. Add retrieval source counts and top hits.
5. Add score contribution breakdown in `business_rerank`.
6. Add rich citation/source/chunk objects in `/context`.
7. Add service status flags:
   - BM25 available?
   - Qdrant available?
   - reranker model used or fallback?
   - LLM provider used or fallback?

## 8. FUTURE IMPROVEMENT

1. Add interactive graph for ontology expansion.
2. Add BM25-only vs Hybrid vs Hybrid+Ontology ablation.
3. Add evaluation metrics panel consuming `eval_golden.py` output.
4. Add exportable mentor report per query.
5. Add per-query screenshot/report generation.
6. Add UX for negative evidence and limitations.

