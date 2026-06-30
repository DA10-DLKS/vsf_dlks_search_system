# Hieu Current Frontend Status

Generated date: 2026-06-11

Owner: Nguyen Duy Hieu

## 1. Role and Scope

Nguyen Duy Hieu owns the Frontend Demo Tool / DA10 Display Layer for the OTA AI Search Platform.

Hieu's frontend scope is to display outputs produced by DA10 APIs and mock equivalents:

- Search/RAG result display.
- Top-K result list.
- Metadata display.
- Citation display.
- Source document display.
- Context chunk display.
- LLM consumption preview.
- Evaluation output display when evaluation outputs are provided.

Hieu does not own:

- Backend API implementation.
- Retrieval algorithms.
- Ranking algorithms.
- Embedding.
- Chunking logic.
- Data cleaning.
- Metric calculation.
- DA09 chatbot response generation.

Evaluation metrics, when shown, must be treated as outputs from Vu Duc Kien's API & Evaluation layer. The frontend may render those metrics but must not calculate or claim ownership of them.

## 2. Current Repository State

Important frontend files found:

- `frontend/search_ui.html`
- `frontend/search_ui_v2.html`
- `frontend/mock_api_responses.json`
- `frontend/mock_api_responses_v2.json`
- `frontend/README.md`
- `frontend/frontend_design.md`
- `frontend/dashboard_design.md`
- `frontend/demo_scenarios.md`
- `frontend/ux_report.md`
- `frontend/src/api/api_client.js`
- `frontend/src/config/config.js`
- `frontend/src/types/searchTypes.js`
- `frontend/src/components/SearchInterface.jsx`
- `frontend/src/components/ResultList.jsx`
- `frontend/src/components/ResultCard.jsx`
- `frontend/src/components/MetadataCard.jsx`
- `frontend/src/components/CitationList.jsx`
- `frontend/src/components/ContextPreview.jsx`
- `frontend/src/components/LoadingState.jsx`
- `frontend/src/components/ErrorState.jsx`
- `frontend/src/components/EmptyState.jsx`
- `frontend/src/dashboard/Dashboard.jsx`
- `frontend/src/dashboard/EvaluationDashboard.jsx`
- `frontend/tests/e2e_test.js`
- `frontend/evaluation_dashboard.html`
- `frontend/mock_evaluation_results.json`
- `frontend/evaluation_dashboard_design.md`

Important docs found:

- `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
- `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
- `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md`
- `docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md`
- `docs/docs_NDHieu/PROJECT_STATE.md`
- `docs/docs_NDHieu/architecture.md`
- `docs/docs_NDHieu/DECISIONS.md`
- `AI_REVIEW_SUMMARY.md`

Files expected by earlier planning but not found in current workspace:

- `docs/PROJECT_STRUCTURE.md`
- `docs/PROJECT_STRUCTURE.json`
- `api_contract.yaml`
- `package.json`
- `frontend/package.json`
- `MENTOR_QA.md`
- `MOCK_DATA_EXPLAINED.md`

Standalone HTML demos:

- Search/RAG standalone demo exists: `frontend/search_ui.html`.
- Search/RAG standalone v2 demo for Kien schema v1 exists: `frontend/search_ui_v2.html`.
- Evaluation Dashboard standalone demo exists: `frontend/evaluation_dashboard.html`.

React/Vite runtime:

- No root `package.json` found.
- No `frontend/package.json` found.
- React-ready components exist under `frontend/src/`, but there is no confirmed React/Vite runtime in the current repository state.

API contract and backend integration:

- `api_contract.yaml` was not found.
- `frontend/src/config/config.js` exists and defines mock/real API switching values.
- `frontend/src/api/api_client.js` supports old mock mode, real API mode and Kien schema v1 mock mode through `searchV2()` and `getContextV2()`.
- React-ready components now follow the Kien schema v1 Search -> Context flow:
  - `SearchInterface` -> `searchV2()`
  - `ResultCard` -> `getContextV2()`
  - `MetadataCard` / `CitationList` / `ContextPreview`
- Real backend integration has not been verified in the current workspace.

Mock data status:

- `frontend/mock_api_responses.json` exists.
- It contains 3 demo search queries.
- Each query currently has 2 results.
- It contains 3 context records under `context_api.contexts_by_result_id`.
- `frontend/mock_api_responses_v2.json` exists.
- It follows Kien API schema v1 for mock `POST /api/v1/search` and `POST /api/v1/context` responses.
- The standalone `frontend/search_ui.html` still uses old embedded mock data and remains the stable old demo.
- The standalone `frontend/search_ui_v2.html` demonstrates the new Kien schema v1 Search -> Context split with embedded mock v2 data.

Encoding/readability note:

- Some frontend markdown/mock files show mojibake in console output, for example Vietnamese text appearing as `TÃ´i` instead of `Tôi`.
- This should be reviewed before mentor-facing presentation because demo query readability matters.

## 3. Completed Deliverables

### Search/RAG Demo

Completed or present:

- `frontend/search_ui.html` exists and runs as a standalone browser file.
- `frontend/search_ui_v2.html` exists and runs as a standalone browser file for Kien API schema v1.
- The standalone demo includes the core RAG display flow:
  - User Query
  - Top-K Results
  - Metadata
  - Citation
  - Source Documents
  - Context Chunks
  - LLM Consumption Preview
- It includes loading, empty and error state behavior.
- It includes fallback handling for missing citation/source/context in at least one mock result.
- The v2 standalone demo includes:
  - Search API mock response metadata: `query_id`, `total_found`, `returned`, `latency_ms`, `parsed_intent`.
  - Top-K HotelCard result cards.
  - Per-hotel Context API mock loading by `hotel_id`.
  - Metadata detail, citations, context chunks, token info, context latency and LLM-ready context preview.
  - NO_RESULTS mock error display and no-chunks context fallback.

### Evaluation Dashboard Demo

Restored/recreated in the current workspace:

- `frontend/evaluation_dashboard.html`
- `frontend/mock_evaluation_results.json`
- `frontend/evaluation_dashboard_design.md`
- `frontend/src/dashboard/EvaluationDashboard.jsx`

Current status:

- The standalone Evaluation Dashboard is presentable as a browser-runnable mock/demo artifact.
- It clearly labels metrics as MOCK / DEMO.
- It states the ownership boundary: Kien calculates, Hieu displays.
- It embeds mock evaluation data directly in the HTML so it can run from the local filesystem.
- It does not calculate official Recall/MRR/NDCG values in the frontend.

Remaining limitation:

- It is not connected to Kien's real evaluation output yet.

### Architecture/Planning Docs

Completed or present:

- `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
- `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
- `docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md`
- `frontend/frontend_design.md`
- `frontend/dashboard_design.md`
- `frontend/demo_scenarios.md`
- `frontend/ux_report.md`

Current task board estimates:

- Sprint 1: 94%
- Sprint 2: 44%
- Sprint 3: 33%
- Total frontend roadmap: 59%

### Mock Data

Completed or present:

- `frontend/mock_api_responses.json` exists.
- It mocks Search API and Context API style data.
- It includes metadata, citations, source documents and context chunks.
- `frontend/mock_api_responses_v2.json` exists.
- It follows Kien schema v1 for Search API `POST /api/v1/search` and Context API `POST /api/v1/context`.
- `frontend/search_ui_v2.html` embeds a presentable Kien schema v1 mock dataset for direct browser demo.

Gaps:

- Mock data may not match final backend contract because `api_contract.yaml` is missing.
- `search_ui.html` still uses old embedded mock data by design.
- `search_ui_v2.html` and `mock_api_responses_v2.json` should be kept aligned if mock v2 changes.
- Some mock/demo text appears to have encoding issues and should be reviewed.

### React-ready Components

Completed or present:

- `SearchInterface.jsx`
- `ResultList.jsx`
- `ResultCard.jsx`
- `MetadataCard.jsx`
- `CitationList.jsx`
- `ContextPreview.jsx`
- `LoadingState.jsx`
- `ErrorState.jsx`
- `EmptyState.jsx`
- `Dashboard.jsx`
- `EvaluationDashboard.jsx`
- `api_client.js`
- `config.js`
- `searchTypes.js`

Current schema status:

- `api_client.js` exposes `searchV2()` and `getContextV2()` for Kien API schema v1.
- `SearchInterface.jsx` now calls `searchV2()` and stores `query_id`, results, loading and error state.
- `ResultList.jsx` passes `query` and `query_id` to each result card.
- `ResultCard.jsx` renders normalized Search result fields and loads Context API data per `hotel_id` on expand.
- `MetadataCard.jsx`, `CitationList.jsx` and `ContextPreview.jsx` consume normalized context package data.
- The intended flow is:

```text
SearchInterface -> searchV2 -> ResultCard -> getContextV2 -> Metadata/Citation/Context display
```

Limitations:

- These are React-ready source files, not a runnable React app yet.
- No Vite/React package setup was found.
- `frontend/tests/e2e_test.js` is currently a framework-neutral checklist, not an executable automated test suite.
- The standalone `frontend/search_ui.html` remains on the old embedded mock flow and is intentionally unchanged.

## 4. Presentable Demos

### `frontend/search_ui.html`

How to open:

- Open `frontend/search_ui.html` directly in a browser.
- No npm, Vite, React or backend is required.

What it demonstrates:

- User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption Preview.
- Loading state.
- Empty state.
- Error state by submitting a query containing `error`.
- Missing citation/context fallback behavior.

Mock data:

- Uses embedded mock data inside the HTML file.
- Also has separate mock API data in `frontend/mock_api_responses.json`, but the HTML demo has its own embedded data.

Limitations:

- It does not call the real backend.
- Embedded HTML mock data can drift from `frontend/mock_api_responses.json`.
- It does not yet use `frontend/mock_api_responses_v2.json` or the Kien schema v1 Search -> Context split.
- Some Vietnamese text may need encoding/readability review before mentor demo.

### `frontend/search_ui_v2.html`

How to open:

- Open `frontend/search_ui_v2.html` directly in a browser.
- No npm, Vite, React, backend or fetch is required.

What it demonstrates:

- Kien API schema v1 Search -> Context split:
  - User Query
  - Search API mock response
  - Top-K HotelCard results
  - Select/expand hotel by `hotel_id`
  - Context API mock response
  - Metadata detail, citations, context chunks, token info and LLM-ready context preview
- Query-level metadata such as `query_id`, `total_found`, `returned`, `latency_ms` and `parsed_intent`.
- Context loading state, missing context fallback, no-chunks fallback and NO_RESULTS mock error.

Mock data:

- Uses embedded mock v2 data copied from the Kien schema v1 mock shape.
- The source mock reference is `frontend/mock_api_responses_v2.json`.

Limitations:

- It does not call the real backend.
- It does not replace `frontend/search_ui.html`.
- Embedded mock data can drift from `frontend/mock_api_responses_v2.json` if not kept in sync.

### `frontend/evaluation_dashboard.html`

Current status:

- Present in current workspace.

How to open:

- Open `frontend/evaluation_dashboard.html` directly in a browser.
- No backend, npm, Vite or React runtime is required.

What it should demonstrate:

- Evaluation metrics as display-only outputs.
- Clear MOCK / DEMO labeling.
- Query-level evaluation rows.
- Explanation that Kien calculates metrics and Hieu displays them.
- Summary cards.
- Retrieval metrics.
- Context and citation metrics.
- API latency.
- Golden Dataset Coverage.

Mock data:

- Uses embedded mock evaluation data inside `frontend/evaluation_dashboard.html`.
- The same mock/demo dataset is also stored in `frontend/mock_evaluation_results.json`.

Limitations:

- It does not use real evaluation output from Kien yet.
- Embedded HTML data can drift from `frontend/mock_evaluation_results.json` if not kept in sync.
- `frontend/src/dashboard/EvaluationDashboard.jsx` is React-ready only and cannot run until the team adds a React/Vite runtime.

## 5. Current Dependencies / Blockers

| Dependency / Blocker | Current Status | Impact |
| --- | --- | --- |
| `api_contract.yaml` | Not found | Frontend cannot reliably align real API response shape. |
| Search API | Not verified | `api_client.js` has real API mode, but endpoint integration is untested. |
| Context API | Not verified | Context package shape is still based on mock assumptions. |
| Evaluation output from Kien | Not found | Evaluation dashboard uses mock/demo values until real output is provided. |
| React/Vite runtime decision | Not made in repo | React-ready components cannot be run as an app yet. |
| Real API integration | Pending | Current working demo is mock/standalone only. |
| Encoding/readability review | Needed | Mentor-facing Vietnamese text may display incorrectly in some files. |

## 6. Risks

- Mock data may drift from the final real API contract.
- Standalone HTML embedded mock data and `mock_api_responses.json` may diverge.
- Standalone `search_ui.html` old mock and `search_ui_v2.html` Kien schema v1 mock should be treated as separate demos unless explicitly consolidated.
- React components exist but may not run without a React/Vite runtime.
- Evaluation metrics are mock/demo only until Kien provides real evaluation output.
- Evaluation dashboard is restored as mock/demo, but real evaluation output integration is still blocked.
- Architecture docs may drift if the canonical version under `docs/docs_NDHieu/` is not used consistently.
- Some Vietnamese text appears mojibake in frontend files and should be reviewed before mentor-facing demos.

## 7. Recommended Next Actions

1. Verify `frontend/search_ui.html` in a browser on the actual demo laptop/projector.
2. Open `frontend/evaluation_dashboard.html` in a browser and verify it on the actual demo laptop/projector.
3. Verify `frontend/search_ui_v2.html` in a browser on the actual demo laptop/projector.
4. Decide whether to add React/Vite runtime after the standalone v2 demo is accepted.
5. Ask Kien for final `/search`, `/context` and evaluation output shape.
6. Align `frontend/mock_api_responses.json`, `frontend/mock_api_responses_v2.json`, `search_ui.html` and `search_ui_v2.html` mock data with the real API contract when available.
7. Review and fix Vietnamese text encoding in mentor-facing frontend files if needed.
8. Update `docs/docs_NDHieu/HIEU_TASK_BOARD.md` after mentor/team feedback.

## 8. What To Send Back To ChatGPT

Send these files back to ChatGPT:

- `docs/docs_NDHieu/HIEU_CURRENT_STATUS.md`
- `docs/docs_NDHieu/HIEU_TASK_BOARD.md`
- `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
- `docs/PROJECT_STRUCTURE.md` if it exists or is regenerated later
- `AI_REVIEW_SUMMARY.md` if changed

Suggested context note:

- Mention that `frontend/evaluation_dashboard.html`, `frontend/mock_evaluation_results.json`, `frontend/evaluation_dashboard_design.md` and `frontend/src/dashboard/EvaluationDashboard.jsx` have been restored/recreated as mock/demo display-layer artifacts.
- Mention that `frontend/search_ui.html`, `frontend/search_ui_v2.html` and `frontend/evaluation_dashboard.html` are presentable standalone demos.
- Mention that React-ready components are updated for Kien API schema v1, but they are not runnable until React/Vite runtime is added.
