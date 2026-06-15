# Technical Onboarding

Generated date: 2026-06-15  
Audience: ChatGPT Plus, AI Engineer, or new engineer taking over DA10/Frontend work.

## Repository Structure

Important top-level modules:

| Path | Purpose | Current Status |
| ---- | ------- | -------------- |
| `api/` | FastAPI platform service layer | Real baseline `/search` exists; target routers not registered |
| `crawler/` | Agoda crawler/browser/parser pipeline | Code exists |
| `data/` | Raw, cleaned, processed, quarantine data | 520 raw hotels, 520 cleaned hotels, 518 review files |
| `ingestion/` | Cleaning, translation, deduplication helpers | Code exists |
| `knowledge_engineering/` | Chunking and common ontology/query helpers | Chunking code exists |
| `indexing/` | BM25, embedding, vector/metadata index modules | BM25 indexer and embedding model code exist |
| `retrieval/` | Query processing, lexical/vector/hybrid/filtering/reranking modules | Mostly skeleton/design docs |
| `context/` | Context selection/aggregation/citation/compression/token budget | Mostly skeleton |
| `ontology/` | Ontology YAML, synonym dictionary, query expansion | Assets exist |
| `evaluation/` | Retrieval/RAG evaluation folders | Skeleton; real harness not implemented |
| `frontend/` | Hieu frontend demo/display layer | Standalone demos and React-ready components exist |
| `docs/` | Architecture, evaluation, audit, planning docs | Many docs, some planned state differs from code |
| `docs/docs_NDHieu/` | Hieu-specific handover/task/status/architecture docs | Main frontend handover source |

## Search Flow

Current implemented backend flow:

```text
User Query
-> FastAPI GET /search?q=<query>
-> OpenSearch index travel_bm25
-> multi_match over name^2, description, city, address, amenities
-> ranked hotel results
```

Current response shape from `api/main.py`:

```json
{
  "query": "user query",
  "results": [
    {
      "id": 123,
      "name": "Hotel name",
      "accommodation_type": "Khách sạn",
      "star_rating": 5.0,
      "review_score": 9.0,
      "address": "...",
      "city": "...",
      "description": "...",
      "score": 12.34
    }
  ],
  "took_ms": 123,
  "total_hits": 10
}
```

Important mismatch:

- Current code: `GET /search?q=<query>`.
- Older docs: `POST /search`.
- Kien proposal/frontend v2 mock: `POST /api/v1/search`.

For real backend work, prioritize `api/main.py` unless the team formally changes the API contract.

## Planned RAG Flow

Target RAG flow:

```text
User Query
-> Search API
-> Retrieval
-> Context API
-> LLM-ready Context Package
```

More detailed target:

```text
query
-> parse intent / filters
-> BM25 + vector retrieval
-> hybrid ranking / reranking
-> selected hotel/document/chunks
-> Context API
-> context_text + chunks + citations + metadata + token_info
```

Current reality:

- Chunking code exists in `knowledge_engineering/chunking/`.
- Embedding model code exists in `indexing/embedding/`.
- Qdrant service exists in `docker-compose.yml`.
- `context/` modules are mostly placeholders.
- `data/processed` has no chunk output.
- No backend Context API route is registered.

## Frontend Flow

### `frontend/search_ui.html`

Stable standalone old demo.

- Runs directly in browser.
- Uses embedded mock data.
- Demonstrates:
  - User Query
  - Top-K Results
  - Metadata
  - Citation
  - Source Documents
  - Context Chunks
  - LLM Consumption Preview

### `frontend/search_ui_v2.html`

Standalone v2 demo for Kien schema v1 and real BM25 mode.

Modes:

- `MOCK_SCHEMA_V1`: embedded mock Search -> Context flow.
- `REAL_BM25`: calls `GET http://127.0.0.1:8000/search?q=<query>`.

Important:

- In `REAL_BM25` mode, only real search results are available.
- Real Context API is not implemented yet, so citations/chunks/LLM context are disabled or shown as unavailable.

### React-ready components

Location:

```text
frontend/src/components/
frontend/src/dashboard/
frontend/src/api/api_client.js
frontend/src/config/config.js
frontend/src/types/searchTypes.js
```

Current status:

- Components exist.
- `SearchInterface.jsx` uses `searchV2()`.
- `ResultCard.jsx` is expected to call `getContextV2()` on expansion.
- `MetadataCard`, `CitationList`, `ContextPreview` render normalized context/search data.
- No React/Vite runtime exists.

### `api_client.js`

Supports:

- Old mock API via `mock_api_responses.json`.
- Kien schema v1 mock via `mock_api_responses_v2.json`.
- Normalizers:
  - `normalizeSearchResponse`
  - `normalizeSearchResult`
  - `normalizeContextResponse`
  - `normalizeApiError`
- New functions:
  - `searchV2(query, options)`
  - `getContextV2({ hotel_id, query, query_id, options })`

Important mismatch:

- For non-mock mode, `searchV2()` calls `POST /api/v1/search`.
- Real backend currently exposes `GET /search`.
- `search_ui_v2.html` already handles the real GET endpoint separately.

## Backend Flow

### `api/main.py`

Implemented endpoints:

- `GET /health`
- `GET /metrics`
- `GET /search?q=<query>`

`GET /search`:

- Connects to OpenSearch URL from `OPENSEARCH_URL`, default `http://localhost:9200`.
- Uses index name from `BM25_INDEX`, default `travel_bm25`.
- Runs OpenSearch `multi_match`.
- Returns real BM25 search results.

Not registered:

- `POST /api/v1/search`
- `POST /api/v1/context`
- `Knowledge API`

### Indexing

Important files:

- `indexing/bm25_index/index_mapping.json`
- `indexing/bm25_index/index_bm25.py`

Flow:

```text
data/cleaned/*.json
-> index_bm25.py
-> OpenSearch index travel_bm25
```

### Retrieval

Folders exist:

- `retrieval/lexical_search`
- `retrieval/vector_search`
- `retrieval/hybrid_search`
- `retrieval/filtering`
- `retrieval/reranking`
- `retrieval/query_processing`

Current code status:

- Mostly README/init placeholders and design docs.
- Real search baseline is directly in `api/main.py`.

### Context

Folders exist:

- `context/selection`
- `context/aggregation`
- `context/ordering`
- `context/compression`
- `context/citation_builder`
- `context/token_budget`

Current code status:

- Mostly placeholders.
- No real Context API endpoint yet.

## Data Flow

Current data flow:

```text
data/raw/hotels
-> cleaning scripts / ingestion
-> data/cleaned
-> indexing/bm25_index/index_bm25.py
-> OpenSearch
-> FastAPI GET /search
```

Known counts:

- `data/raw/hotels`: 520 files.
- `data/raw/reviews`: 518 files.
- `data/cleaned`: 520 files.
- `data/processed`: only `.gitkeep`.

Data quality summary from `docs/DATASET_QUALITY_AUDIT_REPORT.md`:

- Audit scope: first 100 cleaned records.
- Score: 82/100, Good.
- Good for BM25 v1 and mentor demo.
- Not production-ready due to schema drift, location hierarchy issue, ontology mapping gap and missing RAG processed chunks.

## Important Decisions

1. DA10 is the knowledge/retrieval platform, not the DA09 chatbot.
2. DA09 consumes DA10 APIs; DA09 should not access data sources directly.
3. Hieu frontend is a DA10 display/demo layer, not a chatbot.
4. Kien owns API schema/evaluation calculation; Hieu displays outputs.
5. Current real backend search is `GET /search`.
6. Kien target schema is `POST /api/v1/search` and `POST /api/v1/context`.
7. Standalone HTML demos are used because React/Vite runtime is not set up.
8. Mock evaluation metrics must always be labeled mock/demo.
9. Frontend should not calculate official evaluation metrics.
10. Code reality should override older docs when they disagree.

## Technical Debt

- No `api_contract.yaml`.
- `docs/08_api_contract.md`, `frontend/README.md`, Kien schema proposal and `api/main.py` describe different API shapes.
- React-ready components exist without a runnable React/Vite project.
- `data/processed` lacks chunks.
- `scripts/run_eval.py` is not implemented.
- Context API is missing.
- Retrieval modules are mostly skeletons.
- Ontology assets are not fully mapped into cleaned records.
- `province` field quality is weak according to data audit.
- Some docs/mock text shows mojibake in terminal output and should be checked before mentor presentation.

## Known Risks

1. Frontend/backend API drift.
2. Mock demos being mistaken for real API outputs.
3. Real search works only if OpenSearch index is built and running.
4. Context/citation UI cannot be real until Context API exists.
5. Evaluation dashboard is mock-only until Kien provides real output.
6. Vector/Qdrant pipeline may look present because Docker/config exists, but integration is not verified.
7. Production readiness may be overstated if using docs only; inspect code before claims.

