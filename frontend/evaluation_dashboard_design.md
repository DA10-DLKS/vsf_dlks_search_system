# Evaluation Dashboard Design

Owner: Nguyen Duy Hieu

## Purpose

The Evaluation Dashboard is a DA10 display-layer artifact. It helps mentors and teammates review Search API and Context API quality signals without requiring a running backend or React/Vite app.

The dashboard is intentionally presentation-focused:

- Show evaluation outputs clearly.
- Explain traceability between golden queries, returned hotels and pass/fail status.
- Make mock/demo status explicit.
- Keep the ownership boundary clear: Kien calculates, Hieu displays.

## Scope Boundary

Hieu owns:

- Dashboard layout.
- Metric card display.
- Query-level table display.
- MOCK / DEMO labeling.
- Empty data fallback.
- Browser-runnable standalone demo.

Hieu does not own:

- Evaluation metric calculation.
- Recall/MRR/NDCG formulas.
- Search ranking algorithm.
- Retrieval algorithm.
- Context quality scoring.
- Backend Evaluation API.

Vu Duc Kien owns the Evaluation Engine and metric calculation. The frontend consumes evaluation output only.

## Dashboard Sections

1. Header
   - Title: Evaluation Dashboard - MOCK / DEMO.
   - Ownership boundary note: Kien calculates, Hieu displays.

2. Data Provenance
   - Source of current values.
   - Last updated date.
   - Mock/demo warning.

3. Summary Cards
   - Total queries.
   - Tested queries.
   - Passed queries.
   - Failed queries.

4. Retrieval Metrics
   - Recall@10.
   - MRR@10.
   - NDCG@10.
   - Hit@5.
   - Hit@10.
   - Zero Result Rate.

5. Context & Citation Metrics
   - Chunk Recall.
   - Citation Coverage.
   - Context Quality.

6. API Latency
   - p95 Search Latency.
   - p95 Context Latency.

7. Golden Dataset Coverage
   - Covered query count.
   - Total golden query count.
   - Coverage rate.
   - Coverage note.

8. Query-level Evaluation Table
   - Query ID.
   - Query.
   - Business category.
   - Expected hotel IDs.
   - Returned hotel IDs.
   - Relevant found.
   - Status.
   - Notes.

## Data Flow

Current Sprint demo:

```text
frontend/mock_evaluation_results.json
-> embedded mock object in frontend/evaluation_dashboard.html
-> metric cards and query-level table
```

React-ready future path:

```text
frontend/mock_evaluation_results.json
-> frontend/src/dashboard/EvaluationDashboard.jsx
-> React/Vite app if the team adds runtime
```

Real integration future path:

```text
Kien Evaluation Engine
-> evaluation_report.json or Evaluation API output
-> frontend normalizer/display layer
-> Evaluation Dashboard
```

## Mock vs Real Rule

Current values are MOCK / DEMO only.

Rules:

- Do not present current metrics as real evaluation results.
- Do not calculate official metrics in frontend.
- Keep every metric visibly labeled MOCK / DEMO.
- Replace mock values only when Kien provides official evaluation output.
- When the real output shape changes, update:
  - `frontend/evaluation_dashboard.html`
  - `frontend/mock_evaluation_results.json`
  - `frontend/src/dashboard/EvaluationDashboard.jsx`
  - `docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md`
  - `docs/docs_NDHieu/HIEU_TASK_BOARD.md`

## How To Open Standalone HTML

Open this file directly in a browser:

```text
frontend/evaluation_dashboard.html
```

No backend, npm, Vite or React runtime is required.

## Difference Between Standalone And React-ready Dashboard

Standalone dashboard:

- Path: `frontend/evaluation_dashboard.html`
- Pure HTML/CSS/JS.
- Embeds mock data directly.
- Best for Sprint review and mentor demo.

React-ready dashboard:

- Path: `frontend/src/dashboard/EvaluationDashboard.jsx`
- Imports `frontend/mock_evaluation_results.json`.
- Not runnable until the team adds React/Vite runtime.
- Intended for future app integration.

## Future Integration With Kien Output

Expected future input from Kien:

- `evaluation_report.json`, or
- `mock_evaluation_results.json` updated with official schema, or
- Evaluation API response.

Expected fields may include:

- Recall@10.
- MRR@10.
- NDCG@10.
- Hit@5.
- Hit@10.
- Zero result rate.
- Chunk recall.
- Citation coverage.
- Context quality.
- p95 search latency.
- p95 context latency.
- Query-level pass/fail rows.

## Risks And Dependencies

Risks:

- Mock metrics may drift from Kien's final evaluation schema.
- HTML-embedded mock data can drift from `frontend/mock_evaluation_results.json`.
- Without React/Vite, `EvaluationDashboard.jsx` cannot be presented directly.
- Metric definitions may change after the Evaluation Engine is finalized.

Dependencies:

- Kien's evaluation output shape.
- Golden query dataset.
- Search API availability.
- Context API availability.
- Team decision on React/Vite runtime.
