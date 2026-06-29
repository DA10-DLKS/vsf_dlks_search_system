# API Schema Impact For Hieu Frontend

Generated date: 2026-06-10

Owner: Nguyen Duy Hieu

Input schema: `VuDucKien_api_schema_proposal.md`

## Summary

Kien's new API schema proposal defines two DA10 retrieval APIs for frontend consumption:

- Search API: `POST /api/v1/search`
- Context API: `POST /api/v1/context`

The Search API receives a natural-language query and returns ranked `HotelCard` results. This should become the source of truth for Top-K result cards in Hieu's Frontend Demo Tool.

The Context API receives a selected `hotel_id`, the original `query`, and optional `query_id`. It returns a context package containing:

- `context_text`
- `chunks`
- `citations`
- detailed hotel `metadata`
- optional `token_info`
- `latency_ms`

This is an important schema shift for the frontend:

- Current mock data puts `citations`, `source_documents` and `context_chunks` directly inside each search result.
- Kien's new schema separates search result display from detailed context retrieval.
- Frontend should normalize API responses into stable UI-facing shapes instead of rendering raw backend fields directly.

## Old Mock Shape vs New API Shape

| UI Concept | Old Mock Field | New Search API Field | New Context API Field | Frontend Action |
| --- | --- | --- | --- | --- |
| result id | `result.id` like `hotel_805030` | `HotelCard.hotel_id` | `ContextResponse.hotel_id` | Normalize to string `id`; preserve raw numeric `hotel_id` for Context API request. |
| title/name | `result.title` | `HotelCard.name` | `metadata.name` / `hotel_name` | Map Search `name` to normalized `title`; Context can enrich detailed title if needed. |
| snippet/description | `result.snippet` | `HotelCard.description` | `metadata.description`, `context_text` | Use Search `description` for card snippet; use Context `context_text` for LLM preview. |
| score | `result.score` | `ranking.final_score` or `ranking.relevance_score` | `chunks[].scores.reranker_score`, `citations[].relevance_score` | Normalize `score = ranking.final_score`; chunk/citation scores stay in context detail. |
| ranking | `metadata.ranking_info` text | `ranking.rank`, `ranking.final_score`, `ranking.relevance_score` | `chunks[].scores` | Add normalized `rank`; render numeric rank/score instead of assuming prose ranking info. |
| metadata | `result.metadata` with `location`, `category`, `amenities`, `price_level`, `best_for` | HotelCard fields: `address`, `city`, `star_rating`, `review_score`, `price_from`, `amenities_top`, `suitable_for`, `nearby_places` | `metadata` full HotelMetadata including rooms, activities, images, useful_info | Search card should show compact metadata; expanded view can be hydrated by Context metadata. |
| citations | `result.citations[]` | Not expected directly from Search API | `citations[]` with `citation_id`, `chunk_id`, `source_type`, `text_snippet`, `relevance_score`, `metadata` | Do not require citations in Search response. Load/show after Context API call. |
| source documents | `result.source_documents[]` | `source_url` only | `citations[].metadata.source_table`, `metadata.source_url`, chunk payload source table/column | Replace document list with source provenance based on source URL, source table, source column and chunk metadata. |
| context chunks | `result.context_chunks[]` | Not expected directly from Search API | `chunks[]` with `chunk_id`, `text`, `source_type`, `scores`, `payload` | ContextPreview should consume Context API chunks, not Search results. |
| LLM consumption preview | Built from `result.context_chunks[].text` | Not provided by Search API | `context_text` | LLM preview should display normalized `context_text` from Context API. |
| latency | Not available in old mock | `SearchResponse.latency_ms` | `ContextResponse.latency_ms` | Add optional latency display for debug/demo. Do not block UI if missing. |
| parsed intent | Not available in old mock | `parsed_intent` | Not applicable | Display optionally in debug/dev UI, not required for mentor-facing card. |
| error state | Mock error triggered in HTML or `normalizeApiError` generic object | Error schema `{ error: { code, message, user_message, query_id, details } }` | Same shared error schema | Update error normalizer to prefer `user_message`, preserve `code` and `query_id`. |

## Search API Frontend Impact

The Search API should drive Top-K Results.

New endpoint:

```text
POST /api/v1/search
```

Important response fields for frontend:

- `query_id`
- `query`
- `total_found`
- `returned`
- `page`
- `latency_ms`
- `results: HotelCard[]`
- `parsed_intent`
- optional `debug_info`

Frontend impact:

- Result cards should use `HotelCard`.
- `HotelCard.hotel_id` replaces current mock `result.id` as backend identifier.
- `HotelCard.name` replaces current mock `result.title`.
- `HotelCard.description` replaces current mock `result.snippet`.
- `HotelCard.ranking.final_score` should become the primary displayed score.
- `HotelCard.ranking.rank` should become the displayed rank.
- `HotelCard.thumbnail_url`, `image_count`, `source_url`, `price_from`, `review_score`, `review_count`, `star_rating`, `nearby_places` can improve result card richness later.

Important behavior change:

- Citation and chunks should not be expected directly from Search API.
- The Search API returns ranked hotel candidates, not the full RAG context package.
- `parsed_intent` can be displayed optionally in a debug/dev panel to show how DA10 understood the query.

Request impact:

- Current `api_client.search(query, filters)` can evolve into:

```js
search(query, {
  filters,
  top_k,
  page,
  include_debug
})
```

Future UI support:

- `top_k`
- `page`
- city filter
- star rating range
- price range
- accommodation type filter
- amenities filter
- suitable_for filter
- review score filter
- luxury toggle
- optional geo search

For the current demo, these can remain optional and defaulted.

## Context API Frontend Impact

The Context API should be called after a user selects or expands a hotel result.

New endpoint:

```text
POST /api/v1/context
```

Request needs:

- `hotel_id`
- `query`
- optional `query_id`
- optional `options.max_context_tokens`
- optional `options.include_chunks`
- optional `options.include_metadata`
- optional `options.include_token_info`

Context response drives:

- `ContextPreview`
- `CitationList`
- `MetadataCard` detailed view
- LLM Consumption Preview
- optional token info display
- optional context latency display

Important response fields:

- `hotel_id`
- `hotel_name`
- `query_id`
- `context_text`
- `chunks[]`
- `citations[]`
- `metadata`
- optional `token_info`
- `latency_ms`

Frontend behavior impact:

- Result cards can initially render compact Search API data.
- On expand/select, frontend should call Context API with the selected `hotel_id`.
- While waiting, show `LoadingState` inside the expanded card/detail panel.
- On Context API failure, show `ErrorState` scoped to context loading.
- If `include_chunks=false`, Context API may return empty `chunks`; UI should show context text and a fallback for chunks.
- If citations are empty, show a clear fallback rather than treating it as a fatal error.

## Required Frontend Changes

Implementation status after the latest frontend update:

- `api_client.js` now supports Kien schema v1 through `searchV2()` and `getContextV2()`.
- `searchTypes.js` documents old mock compatibility, raw Kien schema shapes and normalized frontend shapes.
- React-ready components under `frontend/src/components/` now follow the new Search -> Context flow.
- `frontend/search_ui.html` has not been modified and still uses the old embedded mock demo.
- React/Vite runtime is still not set up, so these React-ready components are prepared but not runnable as an app yet.

Current required updates by file:

| File | Required Updates |
| --- | --- |
| `frontend/src/api/api_client.js` | DONE for mock v2 normalization. Still needs real backend verification when API is available. |
| `frontend/src/types/searchTypes.js` | DONE for documentation of raw Kien schema and normalized frontend shapes. |
| `frontend/mock_api_responses_v2.json` | DONE as separate Kien-schema-compatible mock data. Old `mock_api_responses.json` remains for standalone demo compatibility. |
| `frontend/search_ui.html` | NOT UPDATED. It intentionally remains stable on the old embedded mock until the team chooses standalone v2 HTML or React/Vite runtime. |
| `frontend/src/components/SearchInterface.jsx` | DONE for React-ready v2 flow. It calls `searchV2()`, stores `query_id`, results, loading and error state. |
| `frontend/src/components/ResultCard.jsx` | DONE for React-ready v2 flow. It renders normalized Search result fields and calls `getContextV2()` per `hotel_id` on expand. |
| `frontend/src/components/MetadataCard.jsx` | DONE for compact Search metadata plus detailed Context metadata fallback. |
| `frontend/src/components/CitationList.jsx` | DONE for normalized Context API citations with graceful missing citation fallback. |
| `frontend/src/components/ContextPreview.jsx` | DONE for normalized `context_text`, chunks and token info with empty chunk fallback. |

## React-ready Components Updated For Kien Schema v1

The React-ready component flow now matches Kien's Search API and Context API split:

```text
SearchInterface
-> searchV2(query)
-> ResultList
-> ResultCard
-> getContextV2({ hotel_id, query, query_id })
-> MetadataCard / CitationList / ContextPreview
```

What changed conceptually:

- Search results are rendered from normalized `HotelCard` data.
- Citations and chunks are no longer assumed to exist in Search results.
- Context data is loaded only when a result card is expanded/selected.
- `query_id` from Search API is preserved and passed into Context API.
- Context loading and Context API errors are scoped inside the result card.

Important warnings:

- These components are React-ready only. They are not runnable until React/Vite runtime is added.
- The standalone `frontend/search_ui.html` still uses old embedded mock data.
- Real backend behavior is not verified yet.

## Standalone Search UI v2 Demo Created

Created file:

```text
frontend/search_ui_v2.html
```

Purpose:

- Provide a browser-runnable demo for Kien API schema v1 without adding React/Vite runtime.
- Demonstrate the new Search API and Context API separation for mentor/team review.
- Keep the old stable `frontend/search_ui.html` unchanged.

What it demonstrates:

```text
User Query
-> Search API mock response
-> Top-K HotelCard results
-> Load Context Package by hotel_id
-> Context API mock response
-> Metadata detail / Citations / Context Chunks / LLM-ready Context Preview
```

Data source:

- Uses embedded mock v2 data shaped after `frontend/mock_api_responses_v2.json`.
- All data is labeled MOCK / DEMO.
- It does not call the real backend.
- It does not replace `frontend/search_ui.html`.

UI states covered:

- Initial help/empty state.
- Search loading simulation.
- NO_RESULTS mock error display.
- Context loading simulation.
- Missing context fallback.
- No-chunks Context API fallback through the `805030_no_chunks` mock case.

Maintenance note:

- If `frontend/mock_api_responses_v2.json` changes, the embedded mock data inside `frontend/search_ui_v2.html` should be reviewed to prevent drift.
- When React/Vite runtime is added later, this standalone file can remain as a mentor/demo artifact or be marked legacy.

## Proposed Normalization Layer

Frontend components should consume normalized shapes, not raw API responses.

### NormalizedSearchResult

```js
{
  id: string,
  hotel_id: number | string,
  title: string,
  snippet: string,
  score: number,
  rank: number,
  metadata: {
    address?: string,
    city?: string,
    location?: string,
    accommodation_type?: string,
    category?: string,
    star_rating?: number,
    review_score?: number,
    review_count?: number,
    price_from?: number,
    amenities?: string[],
    suitable_for?: string[],
    nearby_places?: Array<{
      name: string,
      type: string,
      distance_km: number
    }>
  },
  image: {
    thumbnail_url?: string,
    image_count?: number
  },
  source_url?: string,
  query_id?: string,
  latency_ms?: number,
  raw: object
}
```

### NormalizedContextPackage

```js
{
  result_id: string,
  hotel_id: number | string,
  query_id?: string,
  context_text: string,
  chunks: Array<{
    id: string,
    chunk_id: string,
    text: string,
    source_type?: string,
    rank?: number,
    scores?: {
      bm25_rank?: number,
      vector_rank?: number,
      rrf_score?: number,
      reranker_score?: number
    },
    payload?: object
  }>,
  citations: Array<{
    id: string,
    citation_id: string,
    chunk_id: string,
    source_type?: string,
    text_snippet?: string,
    relevance_score?: number,
    metadata?: object
  }>,
  metadata: object,
  token_info?: {
    context_text_tokens?: number,
    metadata_tokens?: number,
    total_tokens?: number,
    model_used_for_count?: string
  },
  latency_ms?: number,
  raw: object
}
```

Why normalize:

- UI stays stable even if backend field names evolve.
- Standalone mock, React mock and real API can share one display model.
- Components remain simple and do not need to know whether data came from old mock, Kien schema mock or real backend.
- Future DA09/LLM preview can consume `context_text` consistently.

## Compatibility Plan

### Phase 1: Keep Sprint demo stable

- Keep `frontend/search_ui.html` working with the old embedded mock shape.
- Do not break the current mentor-ready Search/RAG standalone demo.
- Create a new Kien-schema-compatible mock section or separate mock file.
- Document mapping and review questions with Kien before changing runtime behavior.

### Phase 2: Update React-ready API layer

- Status: DONE for mock v2 and React-ready component preparation.

Completed:

- Updated `api_client.js` normalizers:
  - `normalizeSearchResponse`
  - `normalizeSearchResult`
  - `normalizeContextResponse`
  - `normalizeApiError`
- Updated `searchTypes.js` with Kien schema and normalized frontend shapes.
- Updated React-ready components to consume normalized shapes.
- Keep `USE_MOCK_API` mode available for demos without backend.

### Phase 3: Update standalone demo flow

- Update `frontend/search_ui.html` to demonstrate:

```text
User Query
-> Search API / mock Search response
-> Top-K HotelCard results
-> Select or expand hotel
-> Context API / mock Context response
-> ContextPreview + CitationList + Metadata detail + LLM Consumption Preview
```

- Add a context loading state at the result-card/detail level.
- Add fallback for:
  - no context chunks
  - no citations
  - Context API error
  - missing `query_id`
  - missing `latency_ms`

## Questions For Kien

1. Is Context API called per hotel, or will there be a batch context endpoint for multiple hotel IDs?
2. Can Search API include a lightweight context preview, or should frontend always call Context API for any citation/context display?
3. What is the final error shape? Is `{ error: { code, message, user_message, query_id, details } }` final for both APIs?
4. Are field names final, especially `hotel_id`, `name`, `description`, `ranking.final_score`, `parsed_intent`, `context_text`, `chunks`, `citations`, and `metadata`?
5. Does Search API return `query_id` for all successful requests?
6. Will Context API return empty `chunks: []` or omit `chunks` when `include_chunks=false`?
7. Is `latency_ms` always returned for both Search API and Context API, including error responses?
8. Should frontend pass `include_metadata=true` by default when opening a hotel detail view?
9. Are `source_url` and citation `metadata.source_table/source_column` enough to replace the old `source_documents[]` UI?
10. Should frontend display `parsed_intent` to mentors, or keep it hidden in a dev/debug panel?

## Key Breaking Changes

- Endpoint paths change from planned `/search` and `/context` to `/api/v1/search` and `/api/v1/context`.
- Search result ID changes from string `id` to numeric `hotel_id`.
- Search result title changes from `title` to `name`.
- Search result snippet changes from `snippet` to `description`.
- Score moves from top-level `score` to `ranking.final_score`.
- Rank is explicit as `ranking.rank`.
- Search response includes `query_id`, `latency_ms`, `parsed_intent`, `total_found`, `returned`, `page`.
- Citations and chunks move out of Search result and into Context API response.
- Source documents are no longer an explicit `source_documents[]` shape; frontend must derive source provenance from `source_url`, citations and chunk payload metadata.
- Error schema becomes structured under `error`.

## Recommended Next Implementation Task

The next frontend decision is:

```text
Verify standalone Search UI v2 demo, then decide whether React/Vite runtime is still needed.
```

Recommended next implementation order:

1. Verify `frontend/search_ui_v2.html` on the actual demo laptop/projector.
2. Ask Kien for final `/api/v1/search`, `/api/v1/context` and error response shape.
3. Decide whether React/Vite runtime is still needed after standalone v2 demo review.
4. If React/Vite is chosen, add runtime setup and smoke test the updated React-ready components.
5. Verify real backend integration when the API is available.

## Mock API v2 Created

Created file:

```text
frontend/mock_api_responses_v2.json
```

This file follows Kien's proposed API schema:

- Search API endpoint: `POST /api/v1/search`
- Context API endpoint: `POST /api/v1/context`
- Schema version: `kien_api_schema_v1`

Current contents:

- 3 Search API mock requests.
- 3 Search API mock responses.
- 6 total `HotelCard` search results.
- Context API mock responses for selected hotel IDs.
- A no-chunks Context API example where `include_chunks=false` returns `chunks: []`.
- Error mocks for:
  - `INVALID_REQUEST`
  - `NO_RESULTS`
  - `HOTEL_NOT_FOUND`
  - `RETRIEVAL_TIMEOUT`
  - `INTERNAL_ERROR`

Frontend interpretation:

- Search API drives Top-K hotel cards.
- Search results contain HotelCard fields such as `hotel_id`, `name`, `description`, `ranking.final_score`, `ranking.rank`, `amenities_top`, `nearby_places` and `source_url`.
- Context API drives citations, chunks, detailed metadata and LLM preview.
- Context responses contain `context_text`, `chunks`, `citations`, `metadata`, `token_info` and `latency_ms`.

Important rule:

- `frontend/mock_api_responses_v2.json` is still mock/demo data.
- It is not real backend output.
- It should be used to update normalizers and UI mapping before the real backend is available.
- `frontend/search_ui.html` and `frontend/src/api/api_client.js` have not been changed yet.
