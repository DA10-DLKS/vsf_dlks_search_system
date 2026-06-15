# Project State Snapshot

Generated date: 2026-06-15  
Purpose: one-page operational snapshot for handover and AI review.

## Completed

### Frontend

- `frontend/search_ui.html` exists as standalone mock Search/RAG demo.
- `frontend/search_ui_v2.html` exists as standalone v2 demo.
- `frontend/search_ui_v2.html` supports:
  - `MOCK_SCHEMA_V1`
  - `REAL_BM25`
  - real `GET http://127.0.0.1:8000/search?q=<query>`
- `frontend/evaluation_dashboard.html` exists as standalone mock/demo evaluation dashboard.
- React-ready components exist under `frontend/src/components`.
- `frontend/src/api/api_client.js` supports old mock and Kien schema v1 mock normalization.

### Backend

- `api/main.py` implements FastAPI app.
- Implemented endpoints:
  - `GET /health`
  - `GET /metrics`
  - `GET /search?q=<query>`
- `/search` uses OpenSearch BM25 multi-match.

### Search

- OpenSearch service exists in `docker-compose.yml`.
- BM25 mapping exists: `indexing/bm25_index/index_mapping.json`.
- BM25 indexing script exists: `indexing/bm25_index/index_bm25.py`.

### Data

- `data/raw/hotels`: 520 files.
- `data/raw/reviews`: 518 files.
- `data/cleaned`: 520 files.
- `data/quarantine` exists for removed/problematic records.
- Data quality audit exists: `docs/DATASET_QUALITY_AUDIT_REPORT.md`.

### Ontology

- Ontology YAML assets exist under `ontology/`.
- Synonym and query expansion files exist.
- Location/amenity/purpose/style/object type assets exist.

### Dashboard

- Standalone evaluation dashboard exists.
- React-ready `EvaluationDashboard.jsx` exists.
- Mock evaluation data exists in `frontend/mock_evaluation_results.json`.

## Partial

### Frontend

- React components are implemented but not runnable because there is no React/Vite runtime.
- `api_client.js` real mode does not match current backend `GET /search`; it targets planned POST endpoints.
- `search_ui_v2.html` is the current bridge to real backend search.

### Backend

- FastAPI app exists but only baseline search route is implemented.
- API route folders exist but are not registered.
- Kien schema proposal exists but is not implemented in backend.

### Search

- BM25 search code exists.
- OpenSearch must be running and indexed before real search works.
- Hybrid search/reranking are not implemented as runtime services.

### Context

- Context package folders exist.
- Frontend mock context display exists.
- Backend Context API is not implemented.

### Data

- Cleaned data exists.
- `data/processed` has no real processed chunk export.
- Data quality audit only re-scored the first 100 cleaned records in the latest report.

### Ontology

- Ontology assets exist.
- Cleaned records are not confirmed to contain ontology concept IDs.

### Infrastructure

- Docker Compose includes API, Postgres, Qdrant, OpenSearch and OpenSearch Dashboards.
- Runtime status was not verified as part of this handover document.

## Blocked

### Frontend

- Real Context API integration is blocked by missing backend Context API.
- React smoke testing is blocked until React/Vite setup decision.
- Final dashboard with real evaluation data is blocked by real evaluation output.

### Backend

- `POST /api/v1/search` and `POST /api/v1/context` are blocked until implementation and final contract.
- Knowledge API is planned but not implemented.

### Search

- Real demo depends on OpenSearch index being created and populated.
- Hybrid/vector/rerank search is blocked by incomplete retrieval runtime integration.

### Context

- Context API is blocked by missing processed chunks, retrieval selection and citation builder integration.

### Dashboard

- Evaluation dashboard remains mock/demo until Kien provides real evaluation report/API output.

### Data

- RAG readiness is blocked by missing processed chunks and chunk-level provenance.

### Ontology

- Ontology readiness is blocked by missing concept mapping into cleaned/indexed records.

### Infrastructure

- API/frontend integration is blocked by contract mismatch:
  - current backend: `GET /search`
  - target schema: `POST /api/v1/search`, `POST /api/v1/context`

## Current Next Task

Recommended immediate task:

```text
Start OpenSearch + FastAPI, build/index cleaned data, then verify frontend/search_ui_v2.html REAL_BM25 mode against GET /search.
```

After that:

1. Decide whether the team keeps `GET /search` for MVP or implements Kien's `POST /api/v1/search`.
2. Generate processed chunks from cleaned hotel data.
3. Define and implement real Context API.

## Do Not Repeat Work

Do not recreate these from scratch unless intentionally replacing them:

- `frontend/search_ui.html`
- `frontend/search_ui_v2.html`
- `frontend/evaluation_dashboard.html`
- `frontend/mock_api_responses.json`
- `frontend/mock_api_responses_v2.json`
- `frontend/mock_evaluation_results.json`
- `frontend/src/api/api_client.js`
- `frontend/src/components/*.jsx`
- `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
- `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
- `docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md`
- `docs/DATASET_QUALITY_AUDIT_REPORT.md`

## Recent Decisions

- Use standalone HTML demos because React/Vite runtime is not set up.
- Keep `frontend/search_ui.html` unchanged as stable old mock demo.
- Add `frontend/search_ui_v2.html` for Kien schema v1 and real BM25 mode.
- Clearly label mock evaluation dashboard values as MOCK / DEMO.
- Hieu owns display layer only; Kien owns evaluation calculation.
- Current data audit report is based on the first 100 cleaned records, not all 520.

## Code Reality vs Existing Docs

| Topic | Existing Docs May Say | Current Code Reality |
| ----- | --------------------- | -------------------- |
| Search API | `POST /search` or `POST /api/v1/search` | `GET /search?q=<query>` in `api/main.py` |
| Context API | `POST /context` or `POST /api/v1/context` | Not implemented/registered |
| React frontend | Components ready | No `package.json`, no Vite runtime |
| Evaluation | `scripts/run_eval.py` command documented | `scripts/run_eval.py` raises `NotImplementedError` |
| Processed RAG data | Planned chunks/context | `data/processed` only has `.gitkeep` |

