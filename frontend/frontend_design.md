# Frontend Design

## Architecture

The frontend is a demo-oriented React component set plus a standalone HTML prototype.

Primary goals:

- Show the complete AI Search/RAG flow.
- Make result traceability visible.
- Keep mock mode available while backend APIs are incomplete.
- Allow easy switch to real backend APIs.

Core flow:

```text
User Query -> Search API -> Top-K Results -> Metadata -> Citations -> Source Documents -> Context API -> Context Chunks -> LLM Consumption
```

## Folder Structure

```text
frontend/
├── search_ui.html
├── mock_api_responses.json
├── src/
│   ├── api/api_client.js
│   ├── config/config.js
│   ├── types/searchTypes.js
│   ├── components/
│   └── dashboard/Dashboard.jsx
└── tests/e2e_test.js
```

## Routes and Views

Planned views:

- `/`: dashboard and search demo.
- `/search`: focused search interface if the team later separates dashboard and search.
- `/result/:id`: optional detail page for a selected result.

The standalone `search_ui.html` combines dashboard and search into one page for fast demo use.

## Component Breakdown

- `Dashboard.jsx`: page shell, RAG traceability strip, metric targets, and embedded search.
- `SearchInterface.jsx`: query input, submit behavior, API state.
- `ResultList.jsx`: renders multiple `ResultCard` components.
- `ResultCard.jsx`: displays ranked result content and traceability sections.
- `MetadataCard.jsx`: structured hotel metadata and ranking explanation.
- `CitationList.jsx`: citations connected to source documents and chunks.
- `ContextPreview.jsx`: retrieved chunks prepared for LLM context.
- `LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx`: reusable UI states.

## API Flow

Mock mode:

```text
SearchInterface -> api_client.search -> mock_api_responses.json -> normalized SearchResponse
```

Real API mode:

```text
SearchInterface -> api_client.search -> POST /search -> normalized SearchResponse
ResultCard/Context action -> api_client.getContext -> POST /context -> normalized context package
```

`api_client.js` reads `USE_MOCK_API` and `API_BASE_URL` from `src/config/config.js`.

## State Management

Local React state is sufficient for the demo:

- `query`
- `response`
- `loading`
- `error`

Large global state is intentionally avoided. If the final product grows, the team can add a small store for selected result, filters, and context package cache.

## RAG Display Flow

Each result card must show:

1. Result title, snippet, and score.
2. Metadata: location, category, amenities, ranking info.
3. Citations: citation id, source document id, chunk id, quote.
4. Source documents: title, type, path or URL.
5. Context chunks: chunk id, source document reference, retrieved text.
6. LLM consumption preview: context text that would be sent downstream.
