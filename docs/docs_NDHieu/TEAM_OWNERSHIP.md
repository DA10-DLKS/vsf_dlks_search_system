# Team Ownership

Generated date: 2026-06-15

Confidence levels:

- High: explicitly stated in repo docs/code.
- Medium: stated in team dependency docs but not confirmed by code ownership.
- Low: inferred from folder/document names only.

## Ownership Matrix

| Person / Role | Area | Confidence | Evidence |
| ------------- | ---- | ---------- | -------- |
| Nguyen Duy Hieu | Frontend Demo Tool / DA10 Display Layer | High | `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md:5-33`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:93-130` |
| Nguyen Duy Hieu | Search/RAG display, metadata, citation, source, context chunk and evaluation display | High | `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:95-110`, `docs/docs_NDHieu/HIEU_TASK_BOARD.md:51-74` |
| Vu Duc Kien | API & Evaluation / metric calculation | High | `frontend/evaluation_dashboard.html:278`, `frontend/evaluation_dashboard.html:345-348`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:146-183` |
| Vu Duc Kien | Proposed Search API and Context API schema | High | `VuDucKien_api_schema_proposal.md:1-29`, `VuDucKien_api_schema_proposal.md:313` |
| Do Minh Hieu | Data quality / cleaning docs | Medium | `docs/Do Minh Hieu/data_quality_report.md`, `docs/Do Minh Hieu/cleaning_rules.md`, `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md:74-105` |
| Truong Anh Long | Metadata / ontology dependency inputs | Medium | `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md:130-138` |
| Nguyen Ngoc Khanh Duy | Chunk/context structure dependency | Medium | `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md:140-173` |
| Le Hoang Dat | Search infrastructure/OpenSearch dependency | Medium | `docs/Le Hoang Dat/opensearch_index_run_guide.md`, `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md:179-208` |
| Nguyen Anh Tai | Retrieval/ranking dependency | Medium | `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md:210-246` |

## Hieu Scope Boundary

Hieu owns display and demo UX, including standalone HTML demos and React-ready frontend components. Evidence: `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:93-110`, `docs/docs_NDHieu/HIEU_TASK_BOARD.md:51-74`.

Hieu does not own backend API implementation, search infrastructure, retrieval/ranking algorithms, evaluation metric calculation, or DA09 chatbot response generation. Evidence: `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:112-130`.

## Kien Scope Boundary

Kien owns API & Evaluation outputs/calculation according to frontend architecture and dashboard docs. Evidence: `frontend/evaluation_dashboard.html:278`, `frontend/evaluation_dashboard.html:345-348`, `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md:146-183`.

Kien's proposed schema defines `POST /api/v1/search` and `POST /api/v1/context`, but implementation is not verified in `api/main.py`. Evidence: `VuDucKien_api_schema_proposal.md:29`, `VuDucKien_api_schema_proposal.md:313`, `api/main.py:113-117`.

## Ownership Not Verified

Production owner of current `api/main.py` is not verified from repository.

Production owner of `indexing/bm25_index/index_bm25.py` is not verified from repository.

Production owner of `knowledge_engineering/chunking/strategies.py` is not verified from repository.

Production owner of Docker/infrastructure is not verified from repository.

