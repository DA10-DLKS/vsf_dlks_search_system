# Project Master Context

Generated date: 2026-06-15

## Evidence Policy

This document uses only repository evidence. If a feature is mentioned in documentation but not implemented in code, it is labeled as planned or proposed. If something cannot be verified from repository files, it is labeled **Not verified from repository**.

## Business Objective

The project builds DA10, a Knowledge & Retrieval Platform for travel/OTA hotel search. DA10 is scoped as the layer that ingests travel data, enriches/indexes it, and exposes reusable Search / Context / Knowledge APIs for DA09 and other AI systems. Evidence: `README.md:1-8`, `README.md:15-21`.

The current practical business objective is to make hotel/accommodation data searchable and demonstrable through API and frontend demo layers. Evidence: `api/main.py:58-106`, `frontend/search_ui_v2.html:422`, `frontend/README.md:14-16`.

## End Users

Primary downstream consumer is DA09 Travel AI Search & Recommendation Copilot / chatbot layer. Evidence: `README.md:3-8`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:59-65`.

Demo/review users include mentor/team reviewers who inspect the DA10 output through Nguyen Duy Hieu's Frontend Demo Tool. Evidence: `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:12-24`, `docs/docs_NDHieu/HIEU_TASK_BOARD.md:52`.

Production end-user UI is not in DA10 scope according to the root README. Evidence: `README.md:7-8`.

## Problem Being Solved

The project solves the platform-side retrieval problem: collect real travel/hotel data, clean it, index it, retrieve ranked candidates, and eventually build LLM-ready context with citations. Evidence: `README.md:15-21`, `README.md:31-39`.

The current implemented search problem is BM25 hotel search over OpenSearch. Evidence: `api/main.py:58-80`, `indexing/bm25_index/index_bm25.py:44-55`, `indexing/bm25_index/index_bm25.py:110-133`.

The planned RAG problem is context construction with citations and metadata for LLM consumption. Evidence: `README.md:31-39`, `docs/08_api_contract.md:9-12`.

## High-Level Architecture

### Current Reality

```text
data/raw + data/cleaned
-> indexing/bm25_index/index_bm25.py
-> OpenSearch index travel_bm25
-> FastAPI GET /search?q=<query>
-> frontend/search_ui_v2.html REAL_BM25 mode
```

Evidence: `indexing/bm25_index/index_bm25.py:6-7`, `indexing/bm25_index/index_bm25.py:44-55`, `indexing/bm25_index/index_bm25.py:110-154`, `api/main.py:17-21`, `api/main.py:58-106`, `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:823`, `frontend/search_ui_v2.html:974`.

### Proposed Architecture

```text
crawl
-> clean
-> chunk
-> embed
-> BM25/vector/metadata indexes
-> hybrid retrieval + rerank
-> Context API with citations
-> DA09 or frontend display
```

Evidence: `README.md:31`, `README.md:38-39`, `docs/08_api_contract.md:5-12`, `VuDucKien_api_schema_proposal.md:29`, `VuDucKien_api_schema_proposal.md:313`.

## Main Workflows

### Data Workflow

Raw hotel data is stored under `data/raw`; cleaned hotel data is stored under `data/cleaned`; the ingestion runner describes clean, dedup, validate and translate steps. Evidence: `scripts/run_ingest.py:1-14`, `scripts/run_ingest.py:31-36`.

Repository filesystem scan found 520 raw hotel files, 518 raw review files and 520 cleaned hotel files. Evidence: filesystem scan of `data/raw/hotels`, `data/raw/reviews`, `data/cleaned`.

### Search Workflow

The current API exposes `GET /search`; it builds an OpenSearch `multi_match` query over `name^2`, `description`, `city`, `address` and `amenities`. Evidence: `api/main.py:58-80`.

The current response includes `query`, `results`, `took_ms` and `total_hits`; each result includes fields such as `id`, `name`, `accommodation_type`, `star_rating`, `review_score`, `address`, `city`, `description` and `score`. Evidence: `api/main.py:82-106`.

### Frontend Workflow

The old standalone demo is `frontend/search_ui.html` and requires no build step. Evidence: `frontend/README.md:14-16`.

The v2 standalone demo has `MOCK_SCHEMA_V1` and `REAL_BM25` modes; real mode calls local FastAPI `GET /search`. Evidence: `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:434-435`, `frontend/search_ui_v2.html:823`, `frontend/search_ui_v2.html:974`.

React-ready components exist, but the repo does not include a Vite/React project configuration. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

## System Boundaries

DA10 owns knowledge/retrieval infrastructure and is the only layer allowed to access knowledge repositories according to project documentation. Evidence: `README.md:3-8`.

DA10 does not own end-user chatbot conversation UI, recommendation conversation behavior, or DA09 response generation. Evidence: `README.md:7-8`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:80-84`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:112-126`.

Nguyen Duy Hieu owns display/demo frontend scope, not backend retrieval/ranking/evaluation calculation. Evidence: `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:9-33`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:93-130`.

Vu Duc Kien is documented as owner of API & Evaluation outputs/calculation in frontend/evaluation context. Evidence: `frontend/evaluation_dashboard.html:278`, `frontend/evaluation_dashboard.html:345-348`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:146-183`.

## Dependencies On External Systems

OpenSearch is required by current real search. Evidence: `api/main.py:10`, `api/main.py:17-21`, `docker-compose.yml:31-38`.

PostgreSQL is defined in Docker Compose and SQLAlchemy models/migrations exist. Evidence: `docker-compose.yml:13-22`, `db/models.py:12-75`, `migrations/versions/53b4d4b91081_create_initial_tables.py`.

Qdrant is defined in Docker Compose and qdrant-client is in requirements, but vector indexing/runtime integration is not verified from repository. Evidence: `docker-compose.yml:24-28`, `requirements.txt:31`.

Sentence Transformers are required for production embedding model code. Evidence: `requirements.txt:27`, `indexing/embedding/models.py:3-4`, `indexing/embedding/models.py:15-32`.

Playwright/Scrapy are crawler dependencies. Evidence: `requirements.txt:12-16`, `crawler/README.md:12-17`, `crawler/README.md:134`.

