# OTA AI Search Frontend Demo

Owner: Nguyen Duy Hieu  
Role: Frontend Demo Tool

This frontend demonstrates the AI Search/RAG flow:

```text
User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption
```

## Run the Standalone HTML Demo

Open `frontend/search_ui.html` directly in a browser.

No build step is required. The HTML file includes embedded mock data and can be used for mentor review immediately.

## Run the React Frontend

This repository does not currently include a Vite or React project configuration. The React files under `frontend/src/` are implemented as reusable modules and are ready to be moved into a Vite app.

If the team adds Vite later:

```bash
cd frontend
npm install
npm run dev
```

The expected app entry should render `src/dashboard/Dashboard.jsx`.

## Mock API Mode

Mock data is stored in:

```text
frontend/mock_api_responses.json
```

The React API client reads:

```text
frontend/src/config/config.js
```

When `USE_MOCK_API` is `true`, `api_client.js` returns data from `mock_api_responses.json`.

## Switch to Real API Mode

Edit `frontend/src/config/config.js`:

```js
export const config = {
  API_BASE_URL: "http://localhost:8000",
  USE_MOCK_API: false,
  SEARCH_ENDPOINT: "/search",
  CONTEXT_ENDPOINT: "/context"
};
```

When `USE_MOCK_API` is `false`, `api_client.js` calls:

- `POST {API_BASE_URL}/search`
- `POST {API_BASE_URL}/context`

## Demo Queries

Use these three queries:

1. `Tôi muốn resort yên tĩnh gần biển cho gia đình`
2. `Khách sạn phù hợp cho chuyến công tác ở trung tâm`
3. `Địa điểm nghỉ dưỡng có tiện ích cho trẻ em`

For error state review in `search_ui.html`, submit a query containing `error`.

For empty state review, submit any query that is not in the mock data.

## Folder Structure

```text
frontend/
├── README.md
├── frontend_design.md
├── dashboard_design.md
├── mock_api_responses.json
├── demo_scenarios.md
├── ux_report.md
├── search_ui.html
├── src/
│   ├── api/api_client.js
│   ├── config/config.js
│   ├── types/searchTypes.js
│   ├── components/
│   └── dashboard/Dashboard.jsx
└── tests/e2e_test.js
```

## Main Components

- `SearchInterface.jsx`: controls query input, submit, loading, error, and empty states.
- `ResultList.jsx`: renders ranked search results.
- `ResultCard.jsx`: displays title, snippet, score, metadata, citations, sources, and context.
- `MetadataCard.jsx`: displays location, category, amenities, score, and ranking information.
- `CitationList.jsx`: displays citations and handles missing citations.
- `ContextPreview.jsx`: displays context chunks and handles missing context.
- `LoadingState.jsx`: reusable loading UI.
- `ErrorState.jsx`: reusable API error UI.
- `EmptyState.jsx`: reusable no-results UI.
- `Dashboard.jsx`: shows the demo overview, metrics targets, and RAG traceability flow.

## Troubleshooting

- If no results appear, use one of the exact demo queries.
- If real API mode fails, check `API_BASE_URL`, backend availability, and endpoint paths.
- If citations or context are missing, the UI should show fallback messages instead of breaking.
- If React imports fail, add a Vite/React setup or move these modules into the team's frontend app.
