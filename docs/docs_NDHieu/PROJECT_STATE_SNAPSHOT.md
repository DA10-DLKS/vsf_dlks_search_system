# Project State Snapshot

Generated date: 2026-06-15

## What Is Currently Working

FastAPI app exists and implements `GET /health`, `GET /metrics`, and `GET /search`. Evidence: `api/main.py:44-58`.

`GET /search` executes an OpenSearch BM25-style `multi_match` query and returns ranked hotel result fields. Evidence: `api/main.py:58-106`.

OpenSearch infrastructure is declared in Docker Compose. Evidence: `docker-compose.yml:31-38`.

BM25 index mapping and indexing code exist. Evidence: `indexing/bm25_index/index_mapping.json`, `indexing/bm25_index/index_bm25.py:44-55`, `indexing/bm25_index/index_bm25.py:110-154`.

The crawler entry point supports Agoda URL and keyword crawl modes. Evidence: `crawler/main.py:1-12`, `crawler/main.py:287-293`, `crawler/README.md:12-17`.

Ingestion runner describes and invokes clean, dedup, validate and translate steps. Evidence: `scripts/run_ingest.py:1-14`, `scripts/run_ingest.py:31-36`, `scripts/run_ingest.py:152-175`.

Chunking functions exist for hotel, review and CMS documents. Evidence: `knowledge_engineering/chunking/__init__.py:2-10`, `knowledge_engineering/chunking/strategies.py:143-283`, `tests/test_chunking.py:1-58`.

Embedding model registry exists with BAAI/bge-m3 as production default and hash embeddings for offline tests. Evidence: `indexing/embedding/models.py:3-4`, `indexing/embedding/models.py:15-32`, `indexing/embedding/models.py:53`, `indexing/embedding/registry.py:11-14`.

Standalone frontend demos exist for search and evaluation. Evidence: `frontend/README.md:14-16`, `frontend/search_ui_v2.html:422`, `frontend/evaluation_dashboard.html:267-278`.

React-ready frontend modules exist but are not a runnable app. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`.

## What Partially Works

Frontend API client supports mock and planned v2 API normalizers, but its non-mock mode calls POST endpoints that do not match current backend `GET /search`. Evidence: `frontend/src/api/api_client.js:252-365`, `api/main.py:58`, `frontend/search_ui_v2.html:974`.

Search UI v2 can call real BM25 backend, but real Context API is unavailable. Evidence: `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:807`, `frontend/search_ui_v2.html:861-869`.

Ontology assets exist, but mapping into cleaned records is not verified from repository. Evidence: `ontology/core/amenity.yaml`, `ontology/synonym_dictionary.yaml`, `ontology/query_expansion.yaml`; concept mapping into cleaned records: Not verified from repository.

Vector search stack is partially present through Qdrant service and embedding code, but actual vector index population/runtime search is not verified from repository. Evidence: `docker-compose.yml:24-28`, `indexing/embedding/models.py:15-32`; runtime vector integration: Not verified from repository.

Evaluation display exists as mock/demo, but evaluation calculation is not implemented. Evidence: `frontend/mock_evaluation_results.json:1-41`, `frontend/evaluation_dashboard.html:345-348`, `scripts/run_eval.py:5`.

## What Is Not Implemented

Backend `POST /api/v1/search` is proposed/planned, not implemented in `api/main.py`. Evidence: `VuDucKien_api_schema_proposal.md:29`, `api/main.py:58`, `api/main.py:113-117`.

Backend `POST /api/v1/context` is proposed/planned, not implemented in `api/main.py`. Evidence: `VuDucKien_api_schema_proposal.md:313`, `api/main.py:113-117`.

Knowledge API routes are not registered. Evidence: `api/main.py:113-117`, `docs/08_api_contract.md:14-15`.

The generic indexing pipeline script is not implemented. Evidence: `scripts/run_index.py:1-5`.

The evaluation harness is not implemented. Evidence: `scripts/run_eval.py:1-5`.

Retrieval and context tests are placeholders. Evidence: `tests/test_retrieval.py:1-5`, `tests/test_context.py:1-5`.

React/Vite runtime is not present. Evidence: `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:94-98`, `frontend/README.md:18-24`.

`api_contract.yaml` is not found in current repo status docs. Evidence: `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:80-84`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:346`.

## Known Blockers

API contract mismatch blocks clean frontend/backend integration. Evidence: current code `api/main.py:58`; planned schema `VuDucKien_api_schema_proposal.md:29`, `VuDucKien_api_schema_proposal.md:313`; frontend real mode docs `frontend/README.md:50-64`.

Context API is missing, blocking real citation/context display. Evidence: `api/main.py:113-117`, `frontend/search_ui_v2.html:861-869`.

React runtime decision blocks running React-ready components as an app. Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_TASK_BOARD.md:65-66`.

Real evaluation output is missing, blocking production evaluation dashboard. Evidence: `scripts/run_eval.py:5`, `frontend/mock_evaluation_results.json:4-6`, `frontend/mock_evaluation_results.json:41`.

Processed RAG artifacts are not verified from repository. Evidence: `data/processed/.gitkeep`; no generated chunk files found in `data/processed`.

## Technical Debt

Multiple API shapes exist across docs/code: current `GET /search`, older `POST /search`, and proposed `POST /api/v1/search`. Evidence: `api/main.py:58`, `docs/08_api_contract.md:5-12`, `VuDucKien_api_schema_proposal.md:29`, `frontend/README.md:61-64`.

The repo contains planned skeleton directories for retrieval/context/evaluation with little runtime implementation. Evidence: `retrieval/*/README.md`, `context/*/README.md`, `evaluation/*/README.md`, `tests/test_retrieval.py:1-5`, `tests/test_context.py:1-5`.

The root docs previously generated under `docs/docs_NDHieu/` may be untracked in git status. Evidence: `git status --short` output showed `?? docs/docs_NDHieu/...`; exact persistence depends on git workflow.

## Open Questions

Should the team keep current `GET /search` as MVP or implement Kien's `POST /api/v1/search` immediately? Evidence: `api/main.py:58`, `VuDucKien_api_schema_proposal.md:29`.

What is the final Context API response shape and source of chunks? Evidence: `VuDucKien_api_schema_proposal.md:313-383`; backend implementation not present in `api/main.py:113-117`.

Will evaluation be delivered as JSON report or API endpoint? Evidence: frontend mock expects JSON values `frontend/mock_evaluation_results.json:1-41`; real evaluation harness not implemented `scripts/run_eval.py:5`.

Should React/Vite be added, or should standalone HTML remain the demo path? Evidence: `frontend/README.md:18-24`, `docs/docs_NDHieu/HIEU_TASK_BOARD.md:65`.

