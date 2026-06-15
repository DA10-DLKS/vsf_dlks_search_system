# Project Master Context

Generated date: 2026-06-15  
Owner focus: Nguyen Duy Hieu - Frontend Demo Tool / DA10 Display Layer  
Rule used for this document: when current docs and code disagree, this document follows the current code and explicitly notes the difference.

## Project Goal

### Mục tiêu cuối cùng

DA10 is the Knowledge Platform & Retrieval Infrastructure for the OTA AI Search Platform. It should ingest hotel/travel data, clean and enrich it, index it into searchable/retrievable stores, and expose reusable Search / Context / Knowledge services for DA09 and other AI applications.

The target end-to-end flow is:

```text
raw travel data
-> cleaned/validated data
-> chunking + metadata enrichment
-> BM25/vector indexing
-> retrieval/ranking
-> Context API with citations
-> DA09 chatbot/copilot or DA10 demo display
```

### MVP

The current practical MVP is:

```text
Cleaned hotel data
-> OpenSearch BM25 index
-> FastAPI GET /search?q=<query>
-> standalone frontend demo
```

The MVP currently focuses on search over real cleaned hotel data, plus frontend mock demos for the planned Search -> Context flow.

### Long-term vision

Long-term, DA10 should provide:

- Search API for ranked OTA hotel/accommodation results.
- Context API for chunk-level context packages, citations and sources.
- Knowledge API for document/metadata lookup.
- Hybrid retrieval using BM25 + vector search + filtering + reranking.
- Evaluation outputs for retrieval/RAG quality.
- A DA10 display/demo layer that can show exactly what DA09 will consume.

## Team Responsibilities

### Nguyen Duy Hieu

Role: Frontend Demo Tool / DA10 Display Layer.

Owns:

- Standalone Search/RAG demos.
- Search result display.
- Metadata display.
- Citation/source/context display.
- LLM consumption preview.
- Evaluation dashboard display layer.
- Frontend state handling: loading, empty, error, missing context/citation fallback.
- React-ready display components.
- Frontend documentation, demo scenarios and mentor-facing display flow.

Does not own:

- Backend Search API implementation.
- Context API implementation.
- Retrieval/ranking algorithms.
- Embedding pipeline.
- Evaluation metric calculation.
- Data cleaning.
- DA09 chatbot response generation.

### Vu Duc Kien

Based on existing docs and schema proposal, Kien owns API & Evaluation scope:

- Proposed Search API schema: `POST /api/v1/search`.
- Proposed Context API schema: `POST /api/v1/context`.
- Evaluation output shape and metrics.
- Metric calculation ownership.

Important boundary: Hieu displays evaluation values; Kien calculates them.

### Other roles found in docs/code

The repo contains ownership references for backend/data/retrieval/knowledge work, but not all roles are consistently mapped in code. Existing docs mention:

- DA10 backend/API ownership around API & Evaluation.
- Knowledge engineering and ontology work under `knowledge_engineering/` and `ontology/`.
- Retrieval design under `retrieval/`.
- Data cleaning and ingestion under `ingestion/`, `crawler/`, `scripts/`.

If a new engineer needs owner-level clarity, use `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md` and confirm with the team.

## Architecture Summary

### Data Layer

Current code/data:

- `data/raw/hotels`: 520 raw hotel files.
- `data/raw/reviews`: 518 review files.
- `data/cleaned`: 520 cleaned hotel files.
- `data/quarantine`: quarantined/foreign/invalid data from cleanup work.
- `contracts/data_schema.json`: documented data schema.
- `db/models.py` and `migrations/`: PostgreSQL model/migration layer exists.

Current caveat:

- `data/processed` only contains `.gitkeep`; no processed RAG chunk export exists yet.

### Search Layer

Implemented:

- `indexing/bm25_index/index_mapping.json`
- `indexing/bm25_index/index_bm25.py`
- `api/main.py` implements `GET /search?q=<query>` using OpenSearch multi-match over:
  - `name^2`
  - `description`
  - `city`
  - `address`
  - `amenities`

Code reality:

- Current real backend Search API is `GET /search?q=<query>`.
- Several docs/plans mention `POST /search` or `POST /api/v1/search`; those are planned/target schemas, not the current implemented FastAPI endpoint.

### Retrieval Layer

Current state:

- `retrieval/` contains package skeletons and design docs.
- `retrieval/lexical_search`, `vector_search`, `hybrid_search`, `filtering`, `reranking`, `query_processing` exist mostly as README/init placeholders.
- Search baseline is implemented directly in `api/main.py`, not through a full retrieval service layer.

### Context Layer

Current state:

- `context/` has submodules for selection, aggregation, ordering, compression, citation_builder and token_budget.
- These are currently placeholders with README/init files.
- No real Context API route is registered in `api/main.py`.
- Frontend mock demos can display context chunks/citations, but those are mock/demo values.

### Frontend Layer

Implemented:

- `frontend/search_ui.html`: stable old standalone mock Search/RAG demo.
- `frontend/search_ui_v2.html`: standalone Kien schema v1 demo, plus real backend `REAL_BM25` mode that calls `GET http://127.0.0.1:8000/search?q=<query>`.
- `frontend/evaluation_dashboard.html`: standalone mock/demo evaluation dashboard.
- `frontend/src/api/api_client.js`: old mock support, Kien v1 mock support, normalizers, `searchV2()` and `getContextV2()`.
- `frontend/src/components/*.jsx`: React-ready components.
- `frontend/src/dashboard/EvaluationDashboard.jsx`: React-ready display component.

Not implemented:

- No `package.json`.
- No Vite/React runtime setup.
- React components are not directly runnable in the repo today.

### Evaluation Layer

Current state:

- `frontend/mock_evaluation_results.json` exists and is clearly mock/demo.
- `frontend/evaluation_dashboard.html` displays mock metrics.
- `evaluation/` contains folder skeletons for test queries, relevance labels, retrieval metrics and RAG evaluation.
- `scripts/run_eval.py` exists but raises `NotImplementedError`.

Important boundary:

- Hieu displays evaluation outputs.
- Kien/API & Evaluation owns metric calculation.

## Current Reality

| Area | Implemented | Partial | Planned / Missing |
| ---- | ----------- | ------- | ----------------- |
| Data | 520 raw hotel files, 520 cleaned hotel files, 518 review files | Data quality report for first 100 records exists | Production validation gate and final processed dataset governance |
| Ontology | `ontology/*.yaml`, synonyms, amenity/location/style/purpose assets | Cleaned records not mapped to concept IDs | Full ontology mapping output in cleaned/indexed data |
| OpenSearch | Docker service, BM25 mapping, BM25 indexing script, FastAPI search client | Need index runtime verification after environment startup | Production search tuning, Vietnamese analyzer, hybrid routing |
| Qdrant | Docker service exists | Embedding model code exists | Vector index population and API integration not verified |
| Search API | `GET /search?q=<query>` implemented in `api/main.py` | Target `POST /api/v1/search` exists in docs/mock/frontend normalizer only | Final API contract and backend implementation for Kien schema v1 |
| Context API | Mock frontend context display exists | Context module directories exist | Real backend Context API not implemented/registered |
| Frontend | Standalone search demos and evaluation dashboard exist | React-ready components exist without runtime | Decide React/Vite or continue standalone demos |
| Dashboard | Standalone evaluation dashboard exists | React `EvaluationDashboard.jsx` exists | Real evaluation output integration |

## Current Progress

This is an engineering estimate based on current repo files, not a formal project tracker.

| Area | Estimated Progress | Basis |
| ---- | ------------------ | ----- |
| Data collection/cleaned hotel dataset | 80% | 520 raw + 520 cleaned hotels, quarantine exists, but schema/location quality issues remain |
| Data quality/governance | 55% | Audit report exists; validation scripts exist; production gate not confirmed |
| Ontology | 55% | Ontology assets exist; concept mapping into records is not complete |
| BM25/OpenSearch search | 65% | Mapping, indexer and real `GET /search` endpoint exist; runtime/index verification still needed |
| Vector/Qdrant retrieval | 30% | Docker and embedding model code exist; vector index integration not verified |
| Context/RAG backend | 20% | Chunking code exists; Context API and processed chunks missing |
| Frontend display/demo | 75% | Standalone demos, v2 demo, evaluation dashboard and React-ready components exist |
| Evaluation | 25% | Mock dashboard exists; `scripts/run_eval.py` not implemented |
| Overall DA10 MVP | 55% | BM25 MVP and demos exist, but real Context API/RAG/evaluation are incomplete |

Frontend-specific progress from `HIEU_TASK_BOARD.md`:

- Sprint 1: 94%
- Sprint 2: 50%
- Sprint 3: 33%
- Total frontend roadmap: 60%

## Current Blockers

1. Final API contract is missing.
   - `api_contract.yaml` is not present.
   - Kien schema proposal exists as Markdown, but backend code does not implement it yet.

2. Context API is not implemented in backend.
   - `api/main.py` registers `/health`, `/metrics`, `/search` only.

3. `GET /search` and planned frontend APIs differ.
   - Real backend: `GET /search?q=<query>`.
   - Planned schema/mock v2: `POST /api/v1/search` and `POST /api/v1/context`.

4. React/Vite runtime is missing.
   - No root `package.json`.
   - No `frontend/package.json`.

5. RAG processed data is missing.
   - `data/processed` contains only `.gitkeep`.
   - No persisted chunk/citation/context artifacts.

6. Evaluation is mock-only.
   - `scripts/run_eval.py` raises `NotImplementedError`.
   - `frontend/mock_evaluation_results.json` is demo data only.

7. Location/schema quality issues remain.
   - `docs/DATASET_QUALITY_AUDIT_REPORT.md` notes schema drift and location hierarchy issues.

## Next Recommended Tasks

1. Verify OpenSearch + FastAPI runtime:
   - Start services.
   - Build/index `data/cleaned`.
   - Confirm `GET /search?q=<query>` returns real results.

2. Decide API contract direction:
   - Keep baseline `GET /search` for MVP, or implement Kien's `POST /api/v1/search`.
   - Do not let frontend and backend drift silently.

3. Build or expose Context API:
   - Use existing chunking code as input.
   - Define `chunk_id`, provenance and citation payload.

4. Generate processed chunks:
   - Use `knowledge_engineering/chunking`.
   - Persist chunk outputs under `data/processed` or DB/vector store.

5. Align frontend real mode:
   - `search_ui_v2.html` already supports `REAL_BM25`.
   - React `api_client.js` still assumes POST endpoints for non-mock mode; update only after team decides contract.

6. Implement evaluation harness or get Kien's output:
   - Replace mock metrics with real evaluation report when available.

7. Update task board after mentor/API decisions.

## Read First Files

Read these files first before taking over:

1. `README.md`
2. `task.md`
3. `api/main.py`
4. `docker-compose.yml`
5. `indexing/bm25_index/index_mapping.json`
6. `indexing/bm25_index/index_bm25.py`
7. `knowledge_engineering/chunking/strategies.py`
8. `indexing/embedding/models.py`
9. `contracts/data_schema.json`
10. `VuDucKien_api_schema_proposal.md`
11. `docs/08_api_contract.md`
12. `docs/DATASET_QUALITY_AUDIT_REPORT.md`
13. `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md`
14. `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
15. `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
16. `docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md`
17. `frontend/search_ui_v2.html`
18. `frontend/src/api/api_client.js`
19. `frontend/src/components/SearchInterface.jsx`
20. `frontend/evaluation_dashboard.html`

