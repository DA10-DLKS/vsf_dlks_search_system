# Architecture

## Current Frontend Architecture

The current frontend is split into two layers:

1. Standalone demo:
   - `frontend/search_ui.html`
   - Runs directly in a browser.
   - Contains embedded mock data for immediate demo use.
   - Uses inline CSS and JavaScript only, with no external runtime dependency.
   - Includes Top-K heading, metadata, citations, source documents, context chunks, and LLM consumption preview.

2. React-ready modules:
   - `frontend/src/`
   - Contains API client, config, data shape comments, reusable components, and dashboard component.
   - Not currently wired to a Vite/React runtime because the repository has no `package.json`.

The frontend demonstrates this RAG/Search flow:

```text
User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption
```

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
│   ├── api/
│   │   └── api_client.js
│   ├── config/
│   │   └── config.js
│   ├── types/
│   │   └── searchTypes.js
│   ├── components/
│   │   ├── SearchInterface.jsx
│   │   ├── ResultList.jsx
│   │   ├── ResultCard.jsx
│   │   ├── MetadataCard.jsx
│   │   ├── CitationList.jsx
│   │   ├── ContextPreview.jsx
│   │   ├── LoadingState.jsx
│   │   ├── ErrorState.jsx
│   │   └── EmptyState.jsx
│   └── dashboard/
│       └── Dashboard.jsx
└── tests/
    └── e2e_test.js
```

## Component Hierarchy

```text
Dashboard
└── SearchInterface
    ├── LoadingState
    ├── ErrorState
    ├── EmptyState
    └── ResultList
        └── ResultCard
            ├── MetadataCard
            ├── CitationList
            └── ContextPreview
```

Standalone HTML mirrors the same conceptual hierarchy in a single file.

Standalone HTML render sections:

```text
Search form
-> Loading/empty/error state
-> Top-K Results
-> Result card
   -> Metadata details
   -> Citations
   -> Source Documents
   -> Context Chunks with expand/collapse
   -> LLM Consumption Preview
```

## API Flow

Search flow:

```text
SearchInterface
-> api_client.search(query, filters)
-> Search API or mock data
-> normalizeSearchResponse()
-> ResultList
-> ResultCard
```

Context flow:

```text
Result/context request
-> api_client.getContext(resultId)
-> Context API or mock data
-> normalizeContextResponse()
-> ContextPreview / LLM consumption preview
```

## State Management Flow

Current React state is local to `SearchInterface.jsx`:

```text
query
loading
error
response
```

State transitions:

```text
Initial
-> user enters query
-> submit
-> loading=true
-> search() resolves
-> response set
-> loading=false
-> render ResultList
```

Error state:

```text
submit
-> loading=true
-> search() throws
-> error set
-> response cleared
-> loading=false
-> render ErrorState
```

Empty state:

```text
submit
-> response.results is empty
-> render EmptyState
```

## Mock API Flow

Config:

```js
USE_MOCK_API: true
```

Flow:

```text
api_client.search()
-> read frontend/mock_api_responses.json
-> find exact query match
-> return normalized SearchResponse
```

If there is no exact mock query match, the API client returns an empty normalized response.

The standalone HTML also uses exact query matching for the three mentor demo queries. Any unmatched query shows the empty state. Any query containing `error` shows the error state for demo review.

Context mock flow:

```text
api_client.getContext(resultId)
-> read context_api.contexts_by_result_id[resultId]
-> return normalized context response
```

If no context exists for a result, empty citations, source documents, and context chunks are returned.

Fallback behavior in the standalone HTML:

- Missing citations: `No citation available.`
- Missing source documents: `Source document unavailable.`
- Missing context chunks: `No context preview available.`
- Missing LLM context package: `No context package available for LLM consumption.`

Latest standalone demo check:

- The HTML file has no external runtime dependency.
- The three approved demo queries render the required RAG sections.
- Empty, error, and missing citation/context/source fallbacks are covered by the standalone script.

## Real API Integration Points

Config file:

```text
frontend/src/config/config.js
```

Switch:

```js
USE_MOCK_API: false
```

Search endpoint:

```text
POST {API_BASE_URL}/search
```

Context endpoint:

```text
POST {API_BASE_URL}/context
```

Integration work still needed:

- Confirm final request body for `/search`.
- Confirm final request body for `/context`.
- Confirm response fields for metadata, citations, source documents, and context chunks.
- Update normalizers if backend field names differ from the current frontend shape.
