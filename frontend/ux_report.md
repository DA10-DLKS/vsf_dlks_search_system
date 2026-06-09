# UX Report

## UX Goals

- Make the AI Search/RAG flow visible without requiring backend knowledge.
- Keep the demo readable on laptop and projector screens.
- Help mentors inspect why a result was returned.
- Show graceful behavior when data is missing.

## Laptop/Projector Layout Notes

- The standalone HTML uses a max-width desktop layout for readability.
- The RAG flow strip appears near the top as a persistent mental model.
- Result cards use two-column traceability sections on desktop.
- On smaller screens, the layout collapses to one column.

## Loading/Error/Empty State Review

- Loading state appears after submit before mock response rendering.
- Empty state appears when the query does not match mock demo queries.
- Error state can be triggered in `search_ui.html` by submitting a query containing `error`.
- React components include reusable `LoadingState`, `ErrorState`, and `EmptyState`.

## Citation/Context Readability Review

- Citations show label, citation id, chunk id, and quote.
- Source documents show title, type, and path.
- Context chunks show chunk id, source document id, rank, and text.
- Missing citation/context uses fallback text instead of blank UI.

## Known UX Limitations

- The standalone HTML embeds mock data instead of loading the JSON file directly, so it can run from local file without CORS issues.
- React modules are implemented, but the repo does not yet include Vite or a package.json.
- Filtering and result detail pages are not implemented.
- Real latency and metrics are not connected to backend telemetry yet.

## Next Iteration Suggestions

- Add Vite React app setup when the team is ready for full frontend integration.
- Add filters for location, category, price level, and amenities.
- Add a selected-result detail panel for deeper context inspection.
- Add real metrics from evaluation and observability modules.
- Add visual highlighting between citation, source document, and context chunk.
