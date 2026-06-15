# Technical Onboarding

Generated date: 2026-06-15

## Tech Stack

Backend API uses FastAPI and Uvicorn. Evidence: `requirements.txt:2-3`, `api/main.py:9`, `api/main.py:44`, `Dockerfile:17`.

Search uses OpenSearch Python client and OpenSearch Docker service. Evidence: `requirements.txt:32`, `api/main.py:10`, `api/main.py:17-21`, `docker-compose.yml:31-38`.

Crawler stack includes Scrapy, BeautifulSoup, lxml, httpx and Playwright. Evidence: `requirements.txt:12-16`, `crawler/README.md:12-17`, `crawler/README.md:134`.

Data/DB stack includes pandas, SQLAlchemy, Alembic and psycopg2-binary. Evidence: `requirements.txt:19-24`, `db/models.py:3-8`, `migrations/versions/53b4d4b91081_create_initial_tables.py`.

Embedding stack includes sentence-transformers and BAAI/bge-m3 default model. Evidence: `requirements.txt:27`, `indexing/embedding/models.py:3-4`, `indexing/embedding/models.py:15-32`.

Vector infrastructure includes Qdrant Docker service and qdrant-client dependency, but runtime vector search is not verified from repository. Evidence: `docker-compose.yml:24-28`, `requirements.txt:31`.

Frontend uses standalone HTML/CSS/JS demos plus React-ready JSX modules. Evidence: `frontend/README.md:14-24`, `frontend/search_ui_v2.html:422`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

Testing uses pytest and FastAPI TestClient for health route. Evidence: `requirements.txt:44`, `tests/test_api.py:1-11`.

## Programming Languages

Python is used for backend, crawler, ingestion, indexing, chunking, embedding, scripts and tests. Evidence: `api/main.py`, `crawler/main.py`, `scripts/run_ingest.py`, `indexing/bm25_index/index_bm25.py`, `knowledge_engineering/chunking/strategies.py`.

JavaScript/JSX is used for frontend modules. Evidence: `frontend/src/api/api_client.js`, `frontend/src/components/SearchInterface.jsx`, `frontend/src/dashboard/EvaluationDashboard.jsx`.

HTML/CSS/JS are used for standalone demos. Evidence: `frontend/search_ui.html`, `frontend/search_ui_v2.html`, `frontend/evaluation_dashboard.html`.

YAML is used for ontology/config assets. Evidence: `ontology/*.yaml`, `config/dev.yaml`, `config/prod.yaml`.

JSON is used for data, mock responses and schema. Evidence: `data/cleaned/*.json`, `frontend/mock_api_responses_v2.json`, `contracts/data_schema.json`.

## Frameworks

FastAPI app is created in `api/main.py`. Evidence: `api/main.py:9`, `api/main.py:44`.

OpenSearch is used for BM25 baseline. Evidence: `api/main.py:10`, `api/main.py:17-21`, `indexing/bm25_index/index_mapping.json`.

SQLAlchemy models define hotels, rooms, nearby places and activities. Evidence: `db/models.py:12-75`.

React components exist but no React/Vite runtime exists. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

## Infrastructure

Docker Compose defines services: `api`, `postgres`, `qdrant`, `opensearch`, `opensearch-dashboard`. Evidence: `docker-compose.yml:1-48`.

The API container exposes port 8000. Evidence: `docker-compose.yml:2-5`, `Dockerfile:15-17`.

Postgres maps port 5432. Evidence: `docker-compose.yml:13-20`.

Qdrant maps port 6333. Evidence: `docker-compose.yml:24-28`.

OpenSearch maps port 9200 and Dashboards maps 5601. Evidence: `docker-compose.yml:31-48`.

Environment variables include `DATABASE_URL`, `QDRANT_URL`, `QDRANT_COLLECTION`, `OPENSEARCH_URL`, `BM25_INDEX`, and `CLEANED_DATA_DIR`. Evidence: `.env.example:6-22`.

## Services

### Current Runtime Service

FastAPI service in `api/main.py` is the current API entry point. Evidence: `api/main.py:44-58`.

### Current Search Service

The current search service is a direct endpoint inside `api/main.py`, not a separate retrieval package service. Evidence: `api/main.py:58-106`; retrieval package runtime integration not verified from repository.

### Planned Services

Search API, Context API and Knowledge API are described as platform services. Evidence: `README.md:5`, `docs/08_api_contract.md:5-15`.

Kien proposal specifies `POST /api/v1/search` and `POST /api/v1/context`. Evidence: `VuDucKien_api_schema_proposal.md:29`, `VuDucKien_api_schema_proposal.md:313`.

These planned services are not registered in current FastAPI code. Evidence: `api/main.py:113-117`.

## How Components Communicate

Current real search communication:

```text
Browser or client
-> GET /search?q=<query>
-> FastAPI api/main.py
-> OpenSearch client
-> OpenSearch index travel_bm25
-> JSON response
```

Evidence: `api/main.py:17-21`, `api/main.py:58-106`.

Current frontend real BM25 communication:

```text
frontend/search_ui_v2.html REAL_BM25 mode
-> fetch("http://127.0.0.1:8000/search?q=...")
-> normalized UI result cards
```

Evidence: `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:823`, `frontend/search_ui_v2.html:974`.

Current frontend mock v2 communication:

```text
frontend/search_ui_v2.html MOCK_SCHEMA_V1 mode
-> embedded mock Search API data
-> button loads embedded mock Context API data by hotel_id
```

Evidence: `frontend/search_ui_v2.html:415`, `frontend/search_ui_v2.html:461`, `frontend/search_ui_v2.html:622`, `frontend/search_ui_v2.html:893-924`.

React-ready communication:

```text
SearchInterface.jsx
-> api_client.searchV2()
-> ResultCard.jsx
-> api_client.getContextV2()
```

Evidence: `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:231-239`, `frontend/src/api/api_client.js:305-365`.

