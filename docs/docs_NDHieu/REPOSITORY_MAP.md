# Repository Map

Generated date: 2026-06-15

Large data leaves are summarized by count to keep the handover readable. File counts are based on filesystem scan.

## Directory Tree

```text
vsf_dlks_search_system/
├── api/
│   ├── main.py
│   ├── app/
│   ├── routes/
│   └── schemas/
├── config/
│   ├── dev.yaml
│   ├── logging.yaml
│   └── prod.yaml
├── context/
│   ├── aggregation/
│   ├── citation_builder/
│   ├── compression/
│   ├── ordering/
│   ├── selection/
│   └── token_budget/
├── contracts/
│   └── data_schema.json
├── crawler/
│   ├── main.py
│   ├── browser.py
│   ├── pipelines.py
│   ├── validate.py
│   ├── configs/
│   ├── parsers/
│   └── spiders/
├── data/
│   ├── raw/
│   │   ├── hotels/   (520 files)
│   │   └── reviews/  (518 files)
│   ├── cleaned/      (520 files)
│   ├── processed/    (.gitkeep only)
│   ├── quarantine/
│   └── samples/
├── db/
│   └── models.py
├── docs/
│   ├── 01_problem_scope.md ... 11_sprint_plan.md
│   ├── 08_api_contract.md
│   ├── 09_evaluation.md
│   ├── docs_NDHieu/
│   └── reports/
├── evaluation/
│   ├── rag_eval/
│   ├── relevance_labels/
│   ├── reports/
│   ├── retrieval_metrics/
│   └── test_queries/
├── frontend/
│   ├── search_ui.html
│   ├── search_ui_v2.html
│   ├── evaluation_dashboard.html
│   ├── mock_api_responses.json
│   ├── mock_api_responses_v2.json
│   ├── mock_evaluation_results.json
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── config/
│   │   ├── dashboard/
│   │   └── types/
│   └── tests/
├── indexing/
│   ├── bm25_index/
│   ├── embedding/
│   ├── metadata_index/
│   └── vector_index/
├── ingestion/
│   ├── cleaning/
│   ├── connectors/
│   └── deduplication/
├── knowledge_engineering/
│   ├── chunking/
│   ├── common/
│   └── metadata_extraction/
├── migrations/
├── observability/
├── ontology/
│   ├── core/
│   └── candidate/
├── retrieval/
│   ├── filtering/
│   ├── hybrid_search/
│   ├── lexical_search/
│   ├── query_processing/
│   ├── reranking/
│   ├── sprint_task/
│   └── vector_search/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
└── task.md
```

Evidence: filesystem scan; key module descriptions from `README.md:15-21`.

## Purpose Of Major Folders

| Folder | Purpose | Evidence |
| ------ | ------- | -------- |
| `api/` | Platform service API layer | `README.md:21`, `api/main.py:44-58` |
| `crawler/` | Crawl hotel data by URL or keyword | `crawler/main.py:1-12`, `crawler/README.md:12-17` |
| `data/` | Raw, cleaned, processed and quarantine data | `README.md:15`, filesystem scan |
| `ingestion/` | Cleaning/dedup/validation/translation pipeline | `scripts/run_ingest.py:1-14` |
| `knowledge_engineering/` | Chunking and knowledge utilities | `knowledge_engineering/chunking/strategies.py:143-283` |
| `indexing/` | BM25, embedding, vector/metadata indexing | `README.md:18`, `indexing/bm25_index/index_bm25.py:44-154` |
| `retrieval/` | Retrieval design/runtime placeholder modules | `README.md:19`, `retrieval/*/README.md` |
| `context/` | Context construction placeholder modules | `README.md:20`, `context/*/README.md` |
| `ontology/` | Ontology, synonyms, query expansion | `ontology/core/amenity.yaml`, `ontology/query_expansion.yaml` |
| `evaluation/` | Retrieval/RAG evaluation skeleton | `docs/09_evaluation.md:1-13`, `scripts/run_eval.py:1-5` |
| `frontend/` | Hieu frontend demo/display layer | `frontend/README.md:1-16`, `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:9-33` |
| `tests/` | Pytest tests | `tests/test_api.py:1-11`, `tests/test_chunking.py:1-58` |

## Important Files

| File | Why Important | Evidence |
| ---- | ------------- | -------- |
| `api/main.py` | Current backend API entry point | `api/main.py:44-58` |
| `docker-compose.yml` | Declares API/Postgres/Qdrant/OpenSearch services | `docker-compose.yml:1-48` |
| `Dockerfile` | API container startup command | `Dockerfile:10-17` |
| `requirements.txt` | Python dependencies | `requirements.txt:2-44` |
| `contracts/data_schema.json` | Data contract for hotel/room/nearby/activity | `contracts/data_schema.json:5-13`, `contracts/data_schema.json:83-121` |
| `indexing/bm25_index/index_bm25.py` | Cleaned data -> OpenSearch indexer | `indexing/bm25_index/index_bm25.py:44-154` |
| `indexing/bm25_index/index_mapping.json` | OpenSearch mapping | `indexing/bm25_index/index_mapping.json` |
| `knowledge_engineering/chunking/strategies.py` | Chunking logic | `knowledge_engineering/chunking/strategies.py:24-106`, `knowledge_engineering/chunking/strategies.py:143-283` |
| `frontend/search_ui_v2.html` | Standalone v2 demo with real BM25 mode | `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:974` |
| `frontend/src/api/api_client.js` | Frontend API normalizer/client | `frontend/src/api/api_client.js:252-365` |
| `scripts/run_ingest.py` | Ingestion pipeline runner | `scripts/run_ingest.py:1-14`, `scripts/run_ingest.py:152-175` |
| `scripts/run_eval.py` | Evaluation runner placeholder | `scripts/run_eval.py:1-5` |
| `VuDucKien_api_schema_proposal.md` | Proposed Search/Context API schema | `VuDucKien_api_schema_proposal.md:29`, `VuDucKien_api_schema_proposal.md:313` |

## Entry Points

| Entry Point | Command / Use | Evidence |
| ----------- | ------------- | -------- |
| API app | `uvicorn api.main:app --host 0.0.0.0 --port 8000` | `Dockerfile:17` |
| Health test | `GET /health` | `api/main.py:47-49`, `tests/test_api.py:10-11` |
| Search API | `GET /search?q=<query>` | `api/main.py:58-106` |
| Crawler | `python -m crawler.main ...` | `crawler/main.py:287-293`, `crawler/README.md:12-17` |
| Ingestion | `python scripts/run_ingest.py` | `scripts/run_ingest.py:4-6`, `scripts/run_ingest.py:152-175` |
| BM25 indexer | `python indexing/bm25_index/index_bm25.py` | `indexing/bm25_index/index_bm25.py:139-154` |
| Frontend old demo | Open `frontend/search_ui.html` in browser | `frontend/README.md:14-16` |
| Frontend v2 demo | Open `frontend/search_ui_v2.html` in browser | `frontend/search_ui_v2.html:422`, `frontend/search_ui_v2.html:434-435` |

## Startup Scripts

| Script | Status | Evidence |
| ------ | ------ | -------- |
| `scripts/run_ingest.py` | Implemented runner | `scripts/run_ingest.py:1-14`, `scripts/run_ingest.py:152-175` |
| `scripts/run_index.py` | Placeholder, not implemented | `scripts/run_index.py:1-5` |
| `scripts/run_eval.py` | Placeholder, not implemented | `scripts/run_eval.py:1-5` |
| `scripts/run_crawl.py` | Wrapper around crawler main | `scripts/run_crawl.py:4-9` |
| `scripts/run_crawl_reviews.py` | Review crawl runner | `scripts/run_crawl_reviews.py:9-16`, `scripts/run_crawl_reviews.py:113-186` |
| `scripts/validation_pipeline.py` | Validation pipeline entry exists | `scripts/validation_pipeline.py:137-160` |

