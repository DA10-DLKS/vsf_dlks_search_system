# Team Dependency Map

Project: DA10 - OTA AI Search Platform
Scope: Sprint dependency view for team coordination and Nguyen Duy Hieu's Frontend Demo Tool

## Overall Project Flow

```text
DA09 Contracts
-> Data Quality
-> Knowledge Engineering
-> Chunking & Embedding
-> Search Infrastructure
-> Retrieval & Ranking
-> API & Evaluation
-> Frontend Demo Tool
```

Practical interpretation:

- DA09 provides upstream contracts and expected integration requirements.
- Data Quality prepares valid source data.
- Knowledge Engineering defines taxonomy, ontology and metadata.
- Chunking & Embedding turns cleaned knowledge into retrievable units.
- Search Infrastructure provides BM25/vector infrastructure.
- Retrieval & Ranking implements hybrid search and ranking logic.
- API & Evaluation exposes Search API, Context API and evaluation signals.
- Frontend Demo Tool visualizes the end-to-end Search/RAG flow for mentor/demo review.

## Team Members

### Nguyen Duy Hieu

Role:

- Frontend Demo Tool

Inputs:

- `api_contract.yaml`
- `golden_queries.json`
- Search API response shape
- Context API response shape
- Evaluation/demo expectations
- Metadata/citation/context format

Outputs:

- Frontend architecture
- Search UI
- Dashboard design
- Mock API responses
- Demo scenarios
- Frontend React-ready components
- Standalone HTML demo
- UX report
- E2E checklist

Dependencies:

- Depends on Vu Duc Kien for API contract, Search API, Context API and mock API server.
- Depends on Nguyen Anh Tai for retrieval/ranking behavior and result scoring explanation.
- Depends on Truong Anh Long for metadata schema, ontology and taxonomy.
- Depends on Nguyen Ngoc Khanh Duy for chunk/context structure.
- Depends on Le Hoang Dat for search infrastructure readiness.
- Depends on DA09 for upstream contracts and expected API consumption.

Who depends on them:

- Mentor/demo review depends on the frontend demo.
- API & Evaluation can use frontend feedback to validate response usability.
- Team depends on frontend to demonstrate the integrated Search/RAG flow.

### Do Minh Hieu

Role:

- Data Quality

Inputs:

- Raw OTA/tourism data
- DA09 data expectations
- Schema requirements

Outputs:

- `data_schema.json`
- `cleaning_rules.md`
- `validation_rules.md`
- `mock_documents_v1.json`
- Cleaning pipeline
- Validation pipeline
- Deduplication pipeline

Dependencies:

- Depends on DA09 data contracts and source data expectations.

Who depends on them:

- Knowledge Engineering depends on clean/valid documents.
- Chunking & Embedding depends on reliable text/data.
- Search Infrastructure and Retrieval depend on data quality for meaningful indexes.
- Frontend depends indirectly through result quality.

### Truong Anh Long

Role:

- Knowledge Engineering

Inputs:

- Cleaned/validated data
- Data schema
- Domain requirements for OTA/tourism

Outputs:

- `taxonomy.yaml`
- `ontology.yaml`
- `metadata_schema.yaml`
- `metadata_pipeline.py`
- `ontology_mapper.py`
- `knowledge_objects.json`

Dependencies:

- Depends on Do Minh Hieu for data schema and clean data.
- Depends on DA09/domain requirements for ontology direction.

Who depends on them:

- Chunking & Embedding depends on metadata and knowledge objects.
- Retrieval & Ranking depends on ontology and synonym/metadata signals.
- API & Evaluation depends on metadata schema.
- Frontend depends on metadata fields for `MetadataCard`, result traceability and dashboard display.

### Nguyen Ngoc Khanh Duy

Role:

- Chunking & Embedding

Inputs:

- Clean documents
- Metadata schema
- Taxonomy/ontology
- Chunking requirements

Outputs:

- `chunking_report.md`
- `embedding_report.md`
- `chunk_service.py`
- `embedding_service.py`
- Final chunk service
- Final embedding service
- `embeddings/`

Dependencies:

- Depends on Data Quality for clean source documents.
- Depends on Knowledge Engineering for metadata and ontology.

Who depends on them:

- Search Infrastructure depends on embeddings and chunks for vector index.
- Retrieval & Ranking depends on chunk granularity and embedding quality.
- API & Evaluation depends on context chunks.
- Frontend depends on chunk IDs, chunk text and context packages for `ContextPreview`.

### Le Hoang Dat

Role:

- Search Infrastructure

Inputs:

- Clean data
- Metadata schema
- Embeddings
- Chunk outputs
- Search architecture requirements

Outputs:

- `docker-compose.yml`
- Elasticsearch setup
- Qdrant setup
- Search architecture
- `index_mapping.json`
- `search_service.py`
- `vector_search.py`
- `baseline_latency_report.md`

Dependencies:

- Depends on Data Quality, Knowledge Engineering and Chunking & Embedding.

Who depends on them:

- Retrieval & Ranking depends on BM25/vector search availability.
- API & Evaluation depends on stable search services.
- Frontend depends indirectly on infrastructure through Search API availability and latency.

### Nguyen Anh Tai

Role:

- Retrieval & Ranking

Inputs:

- BM25 search
- Vector search
- Index mappings
- Ontology/synonyms
- Golden queries
- Evaluation metrics targets

Outputs:

- `retrieval_design.md`
- `ranking_design.md`
- `metrics_targets.md`
- `baseline_benchmark.md`
- `query_processor.py`
- `hybrid_search.py`
- `reranker.py`
- `walking_skeleton_demo.ipynb`

Dependencies:

- Depends on Search Infrastructure for BM25/vector search.
- Depends on Knowledge Engineering for query expansion and metadata signals.
- Depends on Chunking & Embedding for vector quality.
- Depends on API/Evaluation or team for golden queries and labels.

Who depends on them:

- API & Evaluation depends on retrieval/ranking modules to expose Search API.
- Frontend depends on ranked Top-K results, scores and ranking explanations.
- Mentor demo depends on convincing hybrid search behavior.

### Vu Duc Kien

Role:

- API & Evaluation

Inputs:

- Retrieval/ranking modules
- Context chunks
- Metadata schema
- Golden queries
- Evaluation metrics targets
- Monitoring/logging requirements

Outputs:

- `api_contract.yaml`
- `evaluation_plan.md`
- `monitoring_plan.md`
- `mock_api_server.py`
- `api_server.py`
- `logger.py`
- `monitor.py`
- `integration_test.py`
- Search API
- Context API

Dependencies:

- Depends on Retrieval & Ranking for search behavior.
- Depends on Chunking & Embedding for context chunks.
- Depends on Knowledge Engineering for metadata schema.
- Depends on Search Infrastructure for search services.

Who depends on them:

- Frontend depends directly on API contract, mock API server, Search API and Context API.
- Evaluation/reporting depends on integration tests and metrics.
- Final integrated demo depends on stable APIs.

## Dependency Table

| Member | Needs From | Output To |
| ------ | ---------- | --------- |
| Nguyen Duy Hieu | Vu Duc Kien, Nguyen Anh Tai, Truong Anh Long, Nguyen Ngoc Khanh Duy, DA09 | Mentor/demo, API feedback, final frontend demo |
| Do Minh Hieu | DA09 contracts, raw data | Truong Anh Long, Nguyen Ngoc Khanh Duy, Le Hoang Dat |
| Truong Anh Long | Do Minh Hieu, DA09/domain requirements | Nguyen Ngoc Khanh Duy, Nguyen Anh Tai, Vu Duc Kien, Nguyen Duy Hieu |
| Nguyen Ngoc Khanh Duy | Do Minh Hieu, Truong Anh Long | Le Hoang Dat, Nguyen Anh Tai, Vu Duc Kien, Nguyen Duy Hieu |
| Le Hoang Dat | Do Minh Hieu, Truong Anh Long, Nguyen Ngoc Khanh Duy | Nguyen Anh Tai, Vu Duc Kien |
| Nguyen Anh Tai | Le Hoang Dat, Truong Anh Long, Nguyen Ngoc Khanh Duy, golden queries | Vu Duc Kien, Nguyen Duy Hieu |
| Vu Duc Kien | Nguyen Anh Tai, Nguyen Ngoc Khanh Duy, Truong Anh Long, Le Hoang Dat | Nguyen Duy Hieu, final integration, evaluation report |

## Critical Path Items

### API Contract

Why critical:

- Defines how frontend calls Search API and Context API.
- Defines response shape for results, metadata, citations, source documents and context chunks.

Impact:

- Blocks frontend real API integration.
- Blocks reliable E2E testing.

Primary owner:

- Vu Duc Kien

### Golden Queries

Why critical:

- Define expected demo/evaluation queries.
- Anchor retrieval benchmarking and frontend demo scenarios.

Impact:

- Affects mock data, demo scenarios, evaluation dataset and mentor presentation.

Primary owner:

- Team-level dependency, likely API & Evaluation plus Retrieval & Ranking.

### Search API

Why critical:

- Provides Top-K results to frontend.

Impact:

- Blocks moving frontend from mock mode to real backend mode.

Primary owner:

- Vu Duc Kien, with input from Nguyen Anh Tai and Le Hoang Dat.

### Context API

Why critical:

- Provides context package, citations and source references for LLM consumption.

Impact:

- Blocks full RAG traceability in real API mode.

Primary owner:

- Vu Duc Kien, with input from Nguyen Ngoc Khanh Duy and Truong Anh Long.

### Hybrid Search

Why critical:

- Produces meaningful ranked results combining lexical/vector signals.

Impact:

- Affects Top-K quality and score/ranking explanation in frontend.

Primary owner:

- Nguyen Anh Tai, with infrastructure from Le Hoang Dat.

### Evaluation Dataset

Why critical:

- Provides labels/golden answers for Recall@10, MRR, NDCG and demo confidence.

Impact:

- Blocks evidence-based evaluation of search quality.
- Limits how confidently frontend can explain ranking quality.

Primary owner:

- Vu Duc Kien, with team input.

## Impact On Nguyen Duy Hieu

### Tasks Hiếu Can Do Independently

- Maintain `frontend/search_ui.html` standalone demo.
- Improve visual layout and responsiveness for mentor demo.
- Maintain `frontend/mock_api_responses.json`.
- Maintain `frontend/demo_scenarios.md`.
- Maintain `MENTOR_QA.md` and `MOCK_DATA_EXPLAINED.md`.
- Update `frontend/ux_report.md` after mentor feedback.
- Improve fallback UI for missing citation/context/source documents.
- Prepare speaking notes and final demo script.
- Check consistency between mock JSON and HTML embedded mock data.

### Tasks That Require Kiên

Kiên owns API & Evaluation, so Hiếu needs Kiên for:

- Final `api_contract.yaml`.
- Search API request/response shape.
- Context API request/response shape.
- Mock API server behavior.
- API error shape.
- Integration test expectations.
- Evaluation metrics and demo acceptance criteria.

### Tasks That Require DA09

Hiếu needs DA09-related contracts for:

- Expected API consumption behavior.
- Contract shape that DA10 must expose.
- Any required response format for downstream LLM consumption.
- Demo expectations if DA09 is the consumer of Search API/Context API.

### Tasks Blocked By Backend

- Real API mode verification in `api_client.js`.
- Search API integration.
- Context API integration.
- E2E tests against real backend.
- Final dashboard using live data.
- Real latency/error handling review.
- Real citation/context traceability validation.

## Sprint 2 Readiness Checklist

| Item | Status | Owner/Dependency | Notes |
| ---- | ------ | ---------------- | ----- |
| API contract available? | Not ready | Vu Duc Kien | `docs/08_api_contract.md` still indicates schema TODO; `api_contract.yaml` not confirmed. |
| Mock API server available? | Not ready | Vu Duc Kien | Frontend currently uses local mock data, not a server. |
| Search API available? | Not ready | Vu Duc Kien, Nguyen Anh Tai, Le Hoang Dat | Needed for real mode and integration tests. |
| Context API available? | Not ready | Vu Duc Kien, Nguyen Ngoc Khanh Duy | Needed for real RAG context and citations. |
| React/Vite decision made? | Not ready | Team/mentor | Repo currently has no frontend runtime setup. |

## Risk Analysis

### High Risk

- API contract is not finalized.
- Backend Search API and Context API may not be ready for Sprint 2 integration.
- React/Vite setup decision is unresolved, so React components cannot be runtime-tested.
- Hybrid search quality may not be ready, leaving frontend dependent on mock data longer.

### Medium Risk

- Golden queries and evaluation dataset may change, requiring mock data/demo scenario updates.
- Metadata schema changes may require frontend component updates.
- Context chunk format may change, affecting `ContextPreview` and citation display.
- Mock scores are hardcoded and need clear explanation during mentor review.

### Low Risk

- Standalone HTML demo is already available for mentor review.
- Frontend can continue with mock mode while backend matures.
- Documentation and mentor preparation materials already exist.
- UI fallback states for missing citation/context/source are already represented.

## Summary For Nguyen Duy Hieu

- Hiếu can continue improving demo usability, documentation and mentor presentation independently.
- Hiếu's Sprint 2 implementation depends most heavily on Kiên's API contract and API availability.
- The biggest technical unblocker is a stable Search API and Context API contract.
- Until backend is ready, the standalone HTML demo and mock API data should remain the primary demo path.
