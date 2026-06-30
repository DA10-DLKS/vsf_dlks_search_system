# Explainability Signal Inventory

Generated date: 2026-06-18

Scope: audit runtime explainability signals that can help frontend explain why a hotel was retrieved and why it was ranked.

Evidence priority used here: source code first. Documentation is not used as proof unless the signal is backed by code.

## 1. Runtime Files Inspected

| Area | Runtime Evidence |
| --- | --- |
| API entrypoints | `api/main.py`: `search_bm25`, `hybrid_search`, `fe_search`, `fe_context` |
| Frontend adapter | `api/frontend_adapter.py`: `to_search_response`, `build_hotel_context`, `_grounded_evidence` |
| Query parsing | `retrieval/query_processing/intent_parser.py`: `parse_intent`, `_lookup_concepts`, `parse_range`, `parse_city` |
| Candidate generation | `retrieval/filtering/concept_index.py`, `retrieval/filtering/hard_filter.py` |
| Hybrid pipeline | `retrieval/hybrid_search/pipeline.py`: `run_hybrid_search` |
| Ranking | `retrieval/reranking/fusion.py`, `retrieval/reranking/neural_rerank.py` |
| BM25 | `retrieval/lexical_search/service.py` |
| Vector search | `retrieval/vector_search/qdrant_service.py`, `retrieval/vector_search/service.py` |
| Context | `context/context_package.py`, `context/answer_generator.py` |
| KE labels | `knowledge_engineering/common/ke_labels.py` |
| Implicit intent | `knowledge_engineering/common/implicit_intent.py` |
| Ontology relation/expansion assets | `knowledge_engineering/common/relation_loader.py`, `knowledge_engineering/common/build_expansion.py`, `ontology/query_expansion.yaml` |
| ABSA/review evidence generation | `knowledge_engineering/enrichment/absa.py` |
| Metadata enrichment | `knowledge_engineering/enrichment/metadata_pipeline.py` |

Runtime verification note:

```text
python -c "from retrieval.query_processing.intent_parser import parse_intent; ..."
.\.venv\Scripts\python -c "from retrieval.query_processing.intent_parser import parse_intent; ..."
```

Both local runtime checks failed with:

```text
ModuleNotFoundError: No module named 'underthesea'
```

Therefore, this audit marks most signals as "code-path verified" but not "locally executed successfully". If the backend environment has `underthesea` installed, these paths may run.

## 2. API Exposure Summary

| API | Source | What It Exposes | Explainability Value |
| --- | --- | --- | --- |
| `GET /search` | `api/main.py:114`, `retrieval/lexical_search/service.py:49` | BM25 hotel results: `id`, `name`, metadata fields, `_score`, `took_ms`, `total_hits` | Good for BM25 baseline and "without hybrid" comparison |
| `GET /hybrid_search` | `api/main.py:157`, `retrieval/hybrid_search/pipeline.py:52` | Full pipeline output: `intent`, `n_candidates`, `n_fused`, `top_hotels`, `context_package`, `prompt`, optional `answer` | Best current endpoint for explainability without backend changes |
| `POST /search` | `api/main.py:197`, `api/frontend_adapter.py:146` | Frontend-friendly flattened results | Good for simple cards, weak for explainability because ranking breakdown is mostly flattened away |
| `POST /context` | `api/main.py:222`, `api/frontend_adapter.py:180` | Selected hotel context: `llm_context`, `citations`, `source_documents`, `context_chunks`, `evidence` | Good for evidence/ABSA display after hotel selection |

## 3. Signal Inventory

Legend:

- Runtime Verified:
  - `Code path`: function exists and is called by runtime endpoint.
  - `Local run blocked`: attempted execution failed due missing dependency.
  - `Asset only`: data/artifact exists but not found in live search path.
- Already Exposed By API:
  - `Yes /hybrid_search`: exposed in raw hybrid response.
  - `Yes /context`: exposed by selected-hotel context endpoint.
  - `Yes /search GET`: exposed by BM25 baseline endpoint.
  - `Partial`: available but nested, transformed, or missing detail.
  - `No`: not returned by current API response.
- Frontend Ready:
  - `Yes`: can be displayed without backend changes.
  - `Partial`: usable but needs frontend-side derivation or careful labeling.
  - `No`: needs backend response change or reliable runtime dependency.

| Signal Name | Source File | Generated At | Runtime Verified? | Already Exposed By API? | Frontend Ready? | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Raw user query | `api/main.py:157`, `api/main.py:197`, `api/main.py:222` | API request input | Code path | Yes `/hybrid_search`, `POST /search`, `POST /context` | Yes | High |
| Parsed intent object | `retrieval/query_processing/intent_parser.py:44`, `:58`, `:165`; `retrieval/hybrid_search/pipeline.py:74`, `:150` | `parse_intent(query)` in `run_hybrid_search` | Code path, local run blocked | Yes `/hybrid_search` via `intent`; partial in `context_package.metadata.intent` | Yes | High |
| Detected concepts | `intent_parser.py:94`, `:165`; `ParsedIntent.concepts` | Synonym lookup + implicit intent | Code path, local run blocked | Yes `/hybrid_search.intent.concepts` | Yes | High |
| Hard concepts | `intent_parser.py:180` | Split parsed concepts by `AMEN_`, `SETTING_` | Code path, local run blocked | Yes `/hybrid_search.intent.hard_concepts` | Yes | High |
| Feel concepts | `intent_parser.py:181` | Split parsed concepts by `STYLE_`, `ASPECT_` | Code path, local run blocked | Yes `/hybrid_search.intent.feel_concepts` | Yes | High |
| Object type concepts | `intent_parser.py:182` | Split parsed concepts by `OBJ_` | Code path, local run blocked | Yes `/hybrid_search.intent.object_types` | Yes | High |
| Purpose concepts | `intent_parser.py:183` | Split parsed concepts by `PURPOSE_` | Code path, local run blocked | Yes `/hybrid_search.intent.purposes` | Yes | High |
| Price tier concepts | `intent_parser.py:184` | Split parsed concepts by `PRICE_` | Code path, local run blocked | Yes `/hybrid_search.intent.price_tiers` | Yes | High |
| Landmark concepts | `intent_parser.py:185` | Split parsed concepts by `LMK_` | Code path, local run blocked | Yes `/hybrid_search.intent.landmarks` | Yes | High |
| Location concepts | `intent_parser.py:186` | Split parsed concepts by `LOC_` | Code path, local run blocked | Yes `/hybrid_search.intent.location_concepts` | Yes | High |
| City text filter | `intent_parser.py:154`; `hard_filter.py:30` | `parse_city(query)` then `inmemory_hard_filter(city=...)` | Code path, local run blocked | Yes `/hybrid_search.intent.city`; filtering effect not detailed | Partial | High |
| Numeric/range filters | `intent_parser.py:128`; `hard_filter.py:30` | `parse_range(query)` then `inmemory_hard_filter(star_eq, score_min)` | Code path, local run blocked | Yes `/hybrid_search.intent.range`; filtering effect not detailed | Partial | High |
| Implicit intent evidence | `knowledge_engineering/common/implicit_intent.py:90`; `intent_parser.py:168` | `parse_implicit_intent(query)` returns `{concept_id: matched_text}` | Code path, local run blocked | Yes `/hybrid_search.intent.implicit` | Yes | High |
| Synonym/surface-form expansion to concepts | `intent_parser.py:94`; `ontology/synonym_dictionary.yaml` | `_lookup_concepts` matches n-grams to concept IDs | Code path, local run blocked | Detected concept IDs exposed, matched surface spans not exposed except implicit rules | Partial | Medium |
| Landmark-vs-setting conflict suppression | `intent_parser.py:94` | `_lookup_concepts` suppresses `SETTING_` covered by `LMK_` span | Code path, local run blocked | No explicit trace | No | Medium |
| Ontology relation expansion rules | `knowledge_engineering/common/build_expansion.py:36`; `ontology/query_expansion.yaml` | Offline compiler from verified relations | Asset only for current search path | No evidence `run_hybrid_search` reads it | No | High |
| Relation edge metadata | `build_expansion.py:48`; `relation_loader.py` | Expansion artifact fields: target, relation_type, source_type, use_as, weight, confidence | Asset only | Not exposed by API | No | High |
| Concept inverted index hit set | `retrieval/filtering/concept_index.py:33`, `:52` | `lookup_hotels_by_concepts(concepts)` | Code path | Not directly; only downstream candidates/results | No | High |
| Concept match count per hotel | `concept_index.py:28`, `:73`, `:78`; `hard_filter.py:109` | `ConceptLookupResult.match_count` passed to `build_candidates` | Code path | Not exposed | No | High |
| Concept IDF score per hotel | `concept_index.py:29`, `:74`, `:79`; `hard_filter.py:110` | `ConceptLookupResult.idf_score` passed to `build_candidates` | Code path | Not exposed | No | High |
| Concept candidate whitelist size | `concept_index.py:52`; `pipeline.py:78` | `cw.hotel_ids` | Code path | Not exposed except indirectly via `n_candidates` after candidate merge | Partial | Medium |
| Structured hard filter whitelist | `hard_filter.py:30`; `pipeline.py:81` | `inmemory_hard_filter(city, star_eq, score_min)` | Code path | Not exposed | No | High |
| Candidate set | `hard_filter.py:103`; `pipeline.py:88` | `build_candidates(...)` | Code path | Count exposed as `n_candidates`; IDs not exposed separately | Partial | High |
| Candidate fallback reason | `pipeline.py:97` | If candidates empty, vector broad search or review-score fallback | Code path | Not exposed | No | Medium |
| Candidate count | `pipeline.py:151` | `len(candidates)` | Code path | Yes `/hybrid_search.n_candidates` | Yes | High |
| Fused count | `pipeline.py:152` | `len(fused)` | Code path | Yes `/hybrid_search.n_fused` | Yes | High |
| BM25 baseline `_score` | `lexical_search/service.py:49`, `:125`, `:142` | OpenSearch hit `_score` | Code path, depends OpenSearch | Yes `GET /search.results[].score` | Yes | High |
| BM25 baseline total hits | `lexical_search/service.py:66`, `:146` | OpenSearch total hits | Code path, depends OpenSearch | Yes `GET /search.total_hits` | Yes | High |
| BM25 baseline latency | `lexical_search/service.py:59`, `:65`; `api/main.py:125` | Time around OpenSearch search | Code path, depends OpenSearch | Yes `GET /search.took_ms`; Prometheus also records | Yes | High |
| BM25 fusion score | `lexical_search/service.py:83`, `:117` | `search_for_fusion` result item `score` | Code path if BM25 index available | Not directly in `/hybrid_search.top_hotels`; only ranks may survive | Partial | Medium |
| BM25 rank per hotel | `fusion.py:64`, `pipeline.py:166`, `:181` | `rrf_by_hotel` and `_merge_text_signal` set `bm25_rank` | Code path if BM25 results exist | Yes in `/hybrid_search.top_hotels[]` if not removed | Yes | High |
| Vector score | `qdrant_service.py:53`, `:86`; `vector_search/service.py:31`, `:113` | Qdrant cosine or pgvector `1-distance` | Code path if vector service available | Not directly after hotel-level RRF unless raw vector result selected into detail | Partial | Medium |
| Vector rank per hotel | `fusion.py:64`; `pipeline.py:181` | `rrf_by_hotel` and `_merge_text_signal` set `vector_rank` | Code path if vector results exist | Yes in `/hybrid_search.top_hotels[]` if not removed | Yes | High |
| RRF score | `fusion.py:64`, `:90`; `pipeline.py:176` | `rrf_by_hotel` sets `rrf_score` | Code path if BM25/vector results exist; candidate fallback gives 0 | Yes `/hybrid_search.top_hotels[].rrf_score` likely preserved | Yes | High |
| Text chunk chosen for hotel | `pipeline.py:176`, `:179`; `context_package.py:53` | `_merge_text_signal` replaces empty text with best retrieval chunk | Code path | Yes in `top_hotels[].text` and `context_package.chunks[].text` | Yes | High |
| Retrieval source | `lexical_search/service.py:118`; `qdrant_service.py:87`; `_candidates_as_docs` `pipeline.py:199` | `source` field: `bm25`, `vector`, `candidate` | Code path | Yes in raw `top_hotels[]` if preserved; `context_package.chunks` exposes `source_type`, not `source` | Partial | Medium |
| Profile boost | `fusion.py:96`, `:111` | `apply_profile_boost` over `semantic_profile` and `feel_concepts` | Code path | Yes in `/hybrid_search.top_hotels[].profile_boost` when `feel_concepts` exist | Yes | High |
| Fused score | `fusion.py:112` | `rrf_score + weight * profile_boost` | Code path when feel concepts exist | Yes if present in `top_hotels[]` | Yes | High |
| Neural rerank score | `neural_rerank.py:25`, `:43`, `:55` | Cross-encoder sigmoid or fallback keyword density | Code path | Yes in `top_hotels[].rerank_score` likely preserved | Yes, with label fallback/model unknown | Medium |
| Reranker mode | `pipeline.py:122` | `USE_RERANKER=1` or function param decides model vs fallback | Code path | Not exposed | No | Medium |
| Text signal normalized | `fusion.py:154`, `:170` | Min-max normalization of text signal for business score | Code path | Yes in `top_hotels[].text_signal_norm` likely preserved | Yes | High |
| Review score contribution | `fusion.py:164`, `:171`; `ke_labels.py:72` | Business score uses `ke_review_score / 10` | Code path | Raw `ke_review_score` exposed in `top_hotels[].metadata`; contribution not exposed separately | Partial | High |
| Review count contribution | `fusion.py:146`, `:165`, `:173` | Business score uses log-normalized review count | Code path | Not reliably exposed; metadata may lack review_count in candidate docs | No | Medium |
| Price fit contribution | `fusion.py:166`, `:174` | `price_fit = 1.0` if no max price or price <= intent max | Code path | Not exposed | No | High |
| Concept match contribution | `fusion.py:167`, `:175` | `len(intent.concepts & doc.ontology_concepts)/len(intent.concepts)` | Code path | Inputs exposed in parts, contribution not exposed | Partial via frontend derivation | High |
| Business score | `fusion.py:171`, `:178` | Weighted sum of text, review, review_count, price_fit, concept | Code path | Yes `top_hotels[].business_score` likely preserved | Yes | High |
| Final score | `fusion.py:203`, `:206` | `max business_score + matched_chunks bonus` | Code path | Yes `top_hotels[].final_score`; also context chunk score | Yes | High |
| Matched chunks | `fusion.py:204`; `context_package.py:72` | Number of docs/chunks grouped for hotel | Code path | Yes `top_hotels[].matched_chunks`; context package metadata may include | Yes | High |
| Context package chunk score | `context_package.py:17`, `:43`, `:69` | Uses `final_score` or `business_score` | Code path | Yes `/hybrid_search.context_package.chunks[].score` | Yes | High |
| Citation index | `context_package.py:23`, `:44`, `:70` | Sequential citation number per selected chunk | Code path | Yes `/hybrid_search.context_package.chunks[].citation_index`; `POST /context` returns citation IDs | Yes | High |
| Context metadata intent | `context_package.py:84`; `pipeline.py:146` | `metadata={"total_hotels": ..., "intent": intent.to_dict()}` | Code path | Yes `/hybrid_search.context_package.metadata.intent` | Yes | High |
| Prompt for LLM | `context_package.py:88`, `:124`; `pipeline.py:147`, `:155` | `build_prompt(pkg)` | Code path | Yes `/hybrid_search.prompt` | Yes | High |
| LLM answer | `api/main.py:161`, `pipeline.py:158`, `answer_generator.py:23` | Optional `generate_answer=True` in `/hybrid_search` | Code path but external LLM dependency | Yes if `answer=true` | Partial | Medium |
| Answer citations | `answer_generator.py:37` | Citations from context chunks | Code path if answer generated | Yes in optional `answer` object | Partial | Medium |
| Selected-hotel ABSA positives | `api/frontend_adapter.py:50`, `:59`, `:64`; `ke_labels.py:72` | `_grounded_evidence` from `semantic_profile` | Code path in `POST /context` | Yes `/context.evidence.positives` | Yes | High |
| Selected-hotel ABSA negatives | `frontend_adapter.py:68`, `:75`; `ke_labels.py:73` | `_grounded_evidence` from `negative_style_profile` | Code path in `POST /context` | Yes `/context.evidence.negatives` | Yes | High |
| Review evidence count | `frontend_adapter.py:60`, `:65` | `semantic_profile[*].evidence_count` | Code path in `POST /context` | Yes `/context.evidence.positives[].evidence_count` | Yes | High |
| Negative review spans | `frontend_adapter.py:70`, `:76` | `negative_style_profile[*].top_spans` | Code path in `POST /context` | Yes `/context.evidence.negatives[].spans` | Yes | High |
| Context grounded flag | `frontend_adapter.py:214` | `ContextPackage.metadata.grounded=True` for selected hotel | Code path | Not returned directly in adapter response; only internal package | No | Medium |
| Source URL / provenance | `frontend_adapter.py:160`, `:167`; `lexical_search/service.py:139` | From `knowledge_objects.provenance.source_url` or OpenSearch `_source.source_url` | Code path | Yes in `GET /search`; yes in `POST /search` citations/source docs; not full in `/context` | Partial | High |
| Hotel metadata for display | `frontend_adapter.py:108`; `lexical_search/service.py:125` | Location, category, amenities, ranking_info, price_level, best_for | Code path | Yes in `POST /search.results[].metadata`; also raw in `GET /search` | Yes | High |
| KE ontology concepts per hotel | `ke_labels.py:72`; `pipeline.py:199`; `context_package.py:74` | From `knowledge_objects.json` | Code path | Yes in raw `/hybrid_search.top_hotels[].metadata.ontology_concepts`; context package chunk metadata currently loses it in `to_dict` | Partial | Medium |
| Strong feel concepts | `ke_labels.py:39`, `:73` | Computed from `semantic_profile` with `FEEL_MIN=0.6` | Code path | Not directly exposed | No | Medium |
| Nearby landmarks | `ke_labels.py:75`; `concept_index.py:40` | From KE labels used in concept index | Code path | Not directly exposed in API output unless in raw metadata | Partial/No | Medium |
| Metadata location concept | `ke_labels.py:76`; `concept_index.py:43` | From `semantic_metadata.location` | Code path | Not directly exposed except via intent/result metadata | Partial | Medium |
| Metadata enrichment range filters | `metadata_pipeline.py:38`, `:51` | Offline enrichment creates star/review/price filters | Asset/code path for enrichment, not search request | Exposed indirectly via KE labels/result metadata | Partial | Medium |
| Price tier reconciliation reason | `metadata_pipeline.py:73` | Offline note from `infer_price_tier` | Not in search runtime | Not exposed | No | Medium |
| ABSA raw review spans | `absa.py`, `knowledge_engineering/enrichment/review_evidence/*.json` | Offline ABSA evidence files | Asset/code path; not live in search path except aggregated profiles | Only selected negative spans through `/context`; raw full evidence not exposed | Partial | Medium |
| Prometheus request counters/latency/errors | `api/main.py:28`, `:39`, `:45`, `:108` | API middleware/manual metrics in endpoints | Code path | Yes `/metrics`, not JSON UI API | Partial | Medium |

## 4. Important Non-Signals / Not Runtime-Exposed

These items exist in code or assets but should not be presented as live explainability unless backend changes expose them or runtime confirms them.

| Item | Evidence | Current Status |
| --- | --- | --- |
| Query expansion actually changing retrieval | `knowledge_engineering/common/build_expansion.py`; no call found in `retrieval/hybrid_search/pipeline.py` | Asset/generated offline, not found in live search path |
| Per-step candidate counts: before/after hard filter/concept lookup/intersection | `run_hybrid_search` computes `cw`, `sw`, `candidates`, but only returns final `n_candidates` | Needs backend response change for full funnel |
| Exact matched surface form for every synonym concept | `_lookup_concepts` returns only concept set | Needs parser trace enhancement |
| Reranker mode: cross-encoder vs fallback density | `pipeline.py` decides via `USE_RERANKER`; `neural_rerank.py` falls back silently | Needs API trace field |
| Business score component breakdown | `business_rerank` computes components locally but only stores final `business_score` and `text_signal_norm` | Needs backend to return `review_component`, `price_fit`, `concept_match`, etc. |
| Raw BM25/vector result lists inside `/hybrid_search` | `run_hybrid_search` local variables `bm25_results`, `vector_results` are not returned | Needs backend response change |
| Context token budget | `context/token_budget/README.md` only; no runtime code found in inspected path | Not implemented as runtime signal |
| Citation builder module | `context/citation_builder/README.md` only; citations currently come from `ContextPackage.citation_index` and adapter IDs | No dedicated runtime citation builder found |

## 5. Tier Ranking By UI Value

### Tier A: Must Show

These signals are high-value and can explain the system without backend changes, mostly through `GET /hybrid_search`, `GET /search`, and `POST /context`.

| Signal | Why It Matters | Current Access |
| --- | --- | --- |
| Parsed intent and concept groups | Explains what the system understood from the query | `/hybrid_search.intent` |
| Implicit intent evidence | Shows why a purpose was inferred from phrases like "trẻ nhỏ" | `/hybrid_search.intent.implicit` |
| Candidate count | Shows narrowing from query understanding to retrieval candidate pool | `/hybrid_search.n_candidates` |
| Fused count | Shows how many candidate documents entered ranking/fusion | `/hybrid_search.n_fused` |
| BM25 baseline score/results | Enables "BM25 only vs hybrid" comparison | `GET /search` |
| BM25 rank and vector rank | Explains whether a hotel was retrieved lexically, semantically, or both | `/hybrid_search.top_hotels[]` if fields present |
| RRF score | Explains fusion contribution | `/hybrid_search.top_hotels[].rrf_score` |
| Rerank score | Explains text relevance after reranking | `/hybrid_search.top_hotels[].rerank_score` |
| Business score | Explains final ranking after business/metadata logic | `/hybrid_search.top_hotels[].business_score` |
| Final score | Explains final order | `/hybrid_search.top_hotels[].final_score` |
| Matched chunks | Shows evidence density per hotel | `/hybrid_search.top_hotels[].matched_chunks` |
| Context chunks and citation index | Shows what is fed to LLM and cited | `/hybrid_search.context_package.chunks[]` |
| LLM prompt | Shows final consumption package | `/hybrid_search.prompt` |
| ABSA positives/negatives | Shows review-grounded strengths and limitations | `POST /context.evidence` |

### Tier B: Useful

These are valuable but either partially exposed or require frontend derivation.

| Signal | Why Useful | Current Access |
| --- | --- | --- |
| Hard concepts vs feel concepts | Separates filter-like signals from boost-like signals | `/hybrid_search.intent` |
| City/range filters | Shows structured constraints | `/hybrid_search.intent.city`, `.range` |
| Hotel ontology concepts | Lets UI compare query concepts to hotel concepts | Raw `top_hotels[].metadata.ontology_concepts` if present |
| Text signal normalized | Helps explain business score | `/hybrid_search.top_hotels[].text_signal_norm` |
| Profile boost | Shows style/aspect profile influence | `/hybrid_search.top_hotels[].profile_boost` when applicable |
| Source URL | Supports provenance | `GET /search`, `POST /search` citations/source documents |
| API latency/took_ms | Shows operational status | `GET /search.took_ms`, `/metrics` |
| Optional generated answer | Demo value, but depends on LLM provider | `/hybrid_search?answer=true` |

### Tier C: Hidden / Debug

These should be hidden behind reviewer/debug mode because they are noisy or not fully exposed.

| Signal | Reason |
| --- | --- |
| Full raw `top_hotels` JSON | Useful for audit, too technical for mentor main flow |
| Full prompt text | Useful for RAG inspection, large for normal UI |
| Prometheus metrics | Operational, not directly explainability |
| Concept IDF scores | Important internally but not exposed |
| Match count per hotel | Important internally but not exposed |
| Relation expansion graph | Strong demo value but currently not runtime-applied in search path |
| Reranker mode/fallback | Important debug detail, not exposed |
| Raw ABSA evidence files | Too large; use aggregated positives/negatives first |

## 6. What Current Backend Can Explain Without Changes

The most impressive explainable search UI Hieu can build without backend changes is:

```text
Explainable Hybrid Search Console

Query
-> /hybrid_search
   -> intent/concepts/implicit evidence
   -> candidate and fused counts
   -> top_hotels with ranking fields
   -> context package chunks and citation indexes
   -> LLM prompt

Parallel baseline:
-> /search
   -> BM25-only result list, score, took_ms, total_hits

On hotel selection:
-> /context
   -> selected-hotel grounded ABSA positives/negatives
   -> llm_context
   -> citation/source/context IDs
```

This can answer:

1. "Hệ thống hiểu query thế nào?"
   - Use `/hybrid_search.intent`: concepts, hard/feel/purpose/location/landmark groups, implicit evidence.

2. "Vì sao khách sạn này được lấy ra?"
   - Use `top_hotels[].bm25_rank`, `vector_rank`, `rrf_score`, `matched_chunks`, `context_package.chunks[]`.

3. "Vì sao khách sạn này đứng cao?"
   - Use `final_score`, `business_score`, `rerank_score`, `text_signal_norm`, `profile_boost`, `metadata.ke_review_score`, `matched_chunks`.

4. "BM25 thuần khác gì hybrid?"
   - Call `GET /search` and `GET /hybrid_search` for the same query, compare order and score fields.

5. "Bằng chứng review/citation ở đâu?"
   - Use `POST /context` for selected hotel: `evidence.positives`, `evidence.negatives`, `llm_context`, `context_chunks`.

## 7. Current Backend Limits For Explainability

Without backend changes, frontend should avoid overclaiming these:

1. Do not claim runtime ontology expansion improved ranking.
   - Reason: `ontology/query_expansion.yaml` exists, but no call was found in `run_hybrid_search`.

2. Do not claim exact per-factor score breakdown for business ranking.
   - Reason: `business_rerank` computes components but only stores final `business_score` plus `text_signal_norm`.

3. Do not claim exact hard-filter reduction counts.
   - Reason: `sw`, `cw`, and intersection sizes are local variables and not returned.

4. Do not claim cross-encoder reranker was used unless backend exposes mode or env is known.
   - Reason: `neural_rerank` falls back to keyword density if model loading fails.

5. Do not claim source-level citation builder is implemented as a separate runtime component.
   - Reason: `context/citation_builder` contains README only; current citation signal is `citation_index` and adapter IDs.

## 8. Recommended No-Backend-Change Display Strategy

Use three current endpoints:

| UI Data Need | Endpoint | Why |
| --- | --- | --- |
| Query understanding and ranking trace | `GET /hybrid_search?q=...&top_n=10&answer=false` | Richest explainability payload currently available |
| BM25 baseline comparison | `GET /search?q=...` | Shows pure lexical retrieval score/order |
| Selected hotel evidence | `POST /context` with `{result_id, query}` | Shows grounded ABSA positive/negative evidence and LLM context |

Minimum frontend transformations:

| Backend Field | Frontend Explanation |
| --- | --- |
| `intent.concepts` | "Detected ontology concepts" |
| `intent.implicit` | "Inferred from phrase" |
| `n_candidates` | "Hotels considered after candidate generation" |
| `n_fused` | "Candidate docs entering fusion/ranking" |
| `top_hotels[].bm25_rank` | "Lexical retrieval rank" |
| `top_hotels[].vector_rank` | "Vector retrieval rank" |
| `top_hotels[].rrf_score` | "Hybrid fusion score" |
| `top_hotels[].rerank_score` | "Rerank relevance score" |
| `top_hotels[].business_score` | "Business/metadata score" |
| `top_hotels[].final_score` | "Final ranking score" |
| `top_hotels[].matched_chunks` | "Evidence density" |
| `context_package.chunks[]` | "LLM context and citation source" |
| `/context.evidence.positives` | "Review-backed strengths" |
| `/context.evidence.negatives` | "Review-backed limitations" |

## 9. Final Answer

With current backend, the most impressive explainable search UI that Hieu can build without backend changes is a **read-only Explainable Hybrid Search Console** backed by:

- `GET /hybrid_search` as the main trace source.
- `GET /search` as the BM25 baseline.
- `POST /context` as selected-hotel evidence and LLM-context source.

It should focus on:

1. Query understanding: intent, concepts, implicit evidence.
2. Retrieval trace: candidate count, fused count, BM25 rank, vector rank, RRF score.
3. Ranking explanation: rerank score, business score, final score, matched chunks.
4. Evidence: context chunks, citation index, ABSA positives/negatives.
5. BM25 vs hybrid comparison: result order and scores.

This is feasible without backend changes if frontend consumes raw `/hybrid_search` instead of relying only on flattened `POST /search`.

