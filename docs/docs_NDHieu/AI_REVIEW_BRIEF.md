# AI Review Brief

Generated date: 2026-06-15  
Audience: mentor, AI reviewer, or ChatGPT Plus reviewing the project without opening the full repo.

## Project Goal

DA10 is the Knowledge Platform & Retrieval Infrastructure for the OTA AI Search Platform. It should provide reusable Search / Context / Knowledge services for DA09 chatbot/copilot and other AI applications.

Nguyen Duy Hieu owns the Frontend Demo Tool / DA10 Display Layer. Hieu's frontend shows DA10 outputs:

```text
User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption Preview
```

## Current Status

The repo currently has:

- 520 cleaned hotel records.
- OpenSearch BM25 mapping and indexing script.
- FastAPI baseline `GET /search?q=<query>`.
- Standalone frontend Search/RAG demos.
- Standalone Search UI v2 with mock Kien schema and real BM25 mode.
- Mock Evaluation Dashboard.
- React-ready components, but no React/Vite runtime.
- Ontology YAML assets.
- Chunking and embedding code.

Main backend gap:

- Real Context API is not implemented.

Main frontend gap:

- React components are not runnable until runtime is added.

Main contract gap:

- Current backend uses `GET /search`; planned schema uses `POST /api/v1/search` and `POST /api/v1/context`.

## Completed Deliverables

### Frontend

- `frontend/search_ui.html`
- `frontend/search_ui_v2.html`
- `frontend/evaluation_dashboard.html`
- `frontend/src/api/api_client.js`
- `frontend/src/components/*.jsx`
- `frontend/src/dashboard/EvaluationDashboard.jsx`
- `frontend/mock_api_responses.json`
- `frontend/mock_api_responses_v2.json`
- `frontend/mock_evaluation_results.json`

### Backend/Search/Data

- `api/main.py` with `/health`, `/metrics`, `/search`.
- `indexing/bm25_index/index_mapping.json`.
- `indexing/bm25_index/index_bm25.py`.
- `data/cleaned` with 520 hotel JSON files.
- `data/raw/hotels` with 520 hotel files.
- `data/raw/reviews` with 518 review files.

### Docs

- `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
- `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
- `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md`
- `docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md`
- `docs/DATASET_QUALITY_AUDIT_REPORT.md`

## Pending Deliverables

- Final `api_contract.yaml`.
- Backend implementation of `POST /api/v1/search` if Kien schema is accepted.
- Backend implementation of `POST /api/v1/context`.
- Processed chunks with stable `chunk_id`.
- Chunk-level citation/provenance payload.
- Vector/Qdrant indexing integration.
- Real evaluation report or Evaluation API output.
- React/Vite runtime if the team wants a runnable React app.
- Production validation pipeline for data/index/API.

## Known Issues

1. API contract mismatch:
   - Code: `GET /search?q=<query>`.
   - Planned schema: `POST /api/v1/search`.

2. Context API missing:
   - Frontend mock can show citations/chunks.
   - Backend cannot currently provide real context package.

3. Evaluation is mock-only:
   - `frontend/mock_evaluation_results.json` is demo data.
   - `scripts/run_eval.py` is not implemented.

4. React runtime missing:
   - Components exist, but no `package.json`.

5. RAG processed data missing:
   - `data/processed` contains only `.gitkeep`.

6. Data quality issues:
   - `docs/DATASET_QUALITY_AUDIT_REPORT.md` scores first 100 records at 82/100.
   - Schema drift and location hierarchy issues remain.

7. Some docs show planned architecture that is ahead of code.
   - Reviewers should inspect code before judging implementation status.

## Questions For Mentor

1. Should Sprint MVP prioritize real BM25 search demo or full planned Search -> Context API?
2. Is standalone HTML acceptable for demo, or must React/Vite be added?
3. Should Hieu continue as display-only frontend, or should frontend also own demo API adapters?
4. What is the minimum acceptable Context API output for mentor review?
5. Should ontology mapping be visible in frontend demo, or only backend/indexing?
6. Is first-100 data audit enough for review, or should the full 520 records be re-audited?

## Questions For Kien

1. Is `POST /api/v1/search` the final Search API contract?
2. Should backend keep `GET /search` as baseline while adding v1 POST endpoint?
3. What is the final Context API response shape?
4. Is Context API called per `hotel_id`, per result, or batch?
5. Will Search API return `query_id` for every successful request?
6. What fields are guaranteed in HotelCard?
7. What is the final error shape?
8. When will real evaluation output be available?
9. Will evaluation be a JSON report file or API endpoint?
10. Which metrics should Hieu display: Recall@10, MRR@10, NDCG@10, citation coverage, context quality, latency?

## Recommended Review Areas

Review these areas first:

1. `api/main.py`
   - Confirm real backend search behavior.

2. `frontend/search_ui_v2.html`
   - Check mock schema mode and real BM25 mode.

3. `frontend/src/api/api_client.js`
   - Check old mock, v2 mock and planned real API assumptions.

4. `docs/DATASET_QUALITY_AUDIT_REPORT.md`
   - Check data quality findings and limits.

5. `indexing/bm25_index/index_bm25.py`
   - Confirm cleaned data -> OpenSearch indexing.

6. `knowledge_engineering/chunking/strategies.py`
   - Confirm chunking code readiness.

7. `scripts/run_eval.py`
   - Confirm evaluation is not implemented.

8. `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
   - Confirm Hieu's progress and blockers.

9. `VuDucKien_api_schema_proposal.md`
   - Compare planned API schema with current backend code.

10. `frontend/evaluation_dashboard.html`
    - Confirm mock metrics are clearly labeled.

