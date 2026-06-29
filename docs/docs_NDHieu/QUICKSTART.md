# Quickstart

Generated date: 2026-06-15

## Prerequisites

Python is required because backend, crawler, ingestion, indexing and tests are Python-based. Evidence: `requirements.txt:2-44`.

Docker Compose is needed to start Postgres, Qdrant, OpenSearch and API services as declared in `docker-compose.yml`. Evidence: `docker-compose.yml:1-48`.

Playwright Chromium is needed for crawler browser automation. Evidence: `crawler/README.md:134`, `requirements.txt:16`.

Node/npm is **not currently required** for the checked-in frontend demos because standalone HTML demos run directly in a browser. Evidence: `frontend/README.md:14-24`.

React/Vite runtime is not present. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

## Environment Variables

Copy `.env.example` to `.env` as recommended by README. Evidence: `README.md:47`.

Important variables:

| Variable | Purpose | Evidence |
| -------- | ------- | -------- |
| `DATABASE_URL` | Postgres connection | `.env.example:6` |
| `QDRANT_URL` | Qdrant service URL | `.env.example:13` |
| `QDRANT_COLLECTION` | Qdrant collection name | `.env.example:14` |
| `OPENSEARCH_URL` | OpenSearch URL | `.env.example:17`, `api/main.py:17` |
| `BM25_INDEX` | OpenSearch BM25 index name | `.env.example:21`, `api/main.py:18` |
| `CLEANED_DATA_DIR` | Cleaned data directory for indexing | `.env.example:22`, `indexing/bm25_index/index_bm25.py:7` |

## Installation Steps

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

Evidence: `README.md:48`, `requirements.txt:2-44`.

2. Install Playwright Chromium if crawling:

```bash
python -m playwright install chromium
```

Evidence: `crawler/README.md:134`.

3. Start infrastructure:

```bash
docker compose up -d
```

Evidence: `README.md:49`, `docker-compose.yml:1-48`.

## Commands To Run Backend

Run FastAPI directly:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Evidence: `Dockerfile:17`.

Or run via Docker Compose:

```bash
docker compose up -d api opensearch postgres qdrant
```

Evidence: `docker-compose.yml:1-48`.

## Commands To Test

Run all tests:

```bash
pytest
```

Evidence: `requirements.txt:44`, `tests/test_api.py:1-11`, `tests/test_chunking.py:1-58`.

Test API health manually:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Evidence: `api/main.py:47-49`, `tests/test_api.py:10-11`.

Test real search manually after OpenSearch index exists:

```bash
curl "http://127.0.0.1:8000/search?q=resort%20Nha%20Trang"
```

Evidence: `api/main.py:58-106`.

## Commands To Rebuild Indexes

The generic `scripts/run_index.py` is not implemented. Do not rely on it. Evidence: `scripts/run_index.py:1-5`.

Use the BM25 indexer directly after creating the OpenSearch index with the agreed mapping:

```bash
python indexing/bm25_index/index_bm25.py
```

Evidence: `indexing/bm25_index/index_bm25.py:139-154`.

The script expects:

- `OPENSEARCH_URL`, default `http://localhost:9200`.
- `BM25_INDEX`, default `travel_bm25`.
- `CLEANED_DATA_DIR`, default `data/cleaned`.

Evidence: `indexing/bm25_index/index_bm25.py:4-7`.

Important: the script exits if the index does not already exist. Evidence: `indexing/bm25_index/index_bm25.py:139-142`.

## Commands To Start Frontend

Open old standalone demo:

```text
frontend/search_ui.html
```

Evidence: `frontend/README.md:14-16`.

Open v2 standalone demo:

```text
frontend/search_ui_v2.html
```

Evidence: `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:434-435`.

For v2 real BM25 mode:

1. Start OpenSearch and FastAPI.
2. Ensure BM25 index is populated.
3. Open `frontend/search_ui_v2.html`.
4. Select `REAL_BM25`.
5. Search.

Evidence: `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:823`, `frontend/search_ui_v2.html:974`.

React frontend cannot be started from current repo because Vite/React project config is not present. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

