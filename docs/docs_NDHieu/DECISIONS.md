# Decisions

## Decision 1: Create a Standalone HTML Demo

Decision:

- Implemented `frontend/search_ui.html` as a browser-ready demo.

Reason:

- The repository does not currently include Vite, React, or `package.json`.
- The frontend owner needs a demo that can run immediately without dependency installation.

Tradeoffs:

- The standalone HTML duplicates some mock data instead of importing `mock_api_responses.json`.
- It is less maintainable than a full React app, but much easier to run for mentor review.

Future considerations:

- Replace standalone demo with a Vite React app once the team is ready to add frontend tooling.
- Keep `search_ui.html` as a lightweight fallback demo if useful.

## Decision 2: Implement React Components Without Adding Build Tooling

Decision:

- Created React-ready components under `frontend/src/`.
- Did not add Vite, npm dependencies, or package scripts.

Reason:

- The user asked to prefer React + Vite only if the repo already supports it.
- The repo currently has no frontend build setup.

Tradeoffs:

- Components are not executable in the repo yet.
- The code is ready for future integration but needs a Vite entry point.

Future considerations:

- Add `package.json`, Vite, React dependencies, and app entry files when approved by the team.
- Wire `Dashboard.jsx` as the main page.

## Decision 3: Use a Config Layer for Mock vs Real API

Decision:

- Added `frontend/src/config/config.js` with `API_BASE_URL`, `USE_MOCK_API`, `SEARCH_ENDPOINT`, and `CONTEXT_ENDPOINT`.

Reason:

- The frontend needs to switch between mock data and backend APIs without changing component code.

Tradeoffs:

- Current config is static JavaScript, not environment-variable based.
- This is simpler for the demo but less flexible for production.

Future considerations:

- Convert config to use Vite environment variables such as `import.meta.env.VITE_API_BASE_URL`.
- Add separate dev/staging/prod config once deployment exists.

## Decision 4: Normalize API Responses in `api_client.js`

Decision:

- Added normalizers for search response, context response, and API errors.

Reason:

- The backend API contract is not final.
- UI components should consume a stable frontend shape.

Tradeoffs:

- Normalizers may need updates once real API schemas are finalized.
- Some fields may be simplified compared to final backend objects.

Future considerations:

- Align `searchTypes.js` with official `api_contract.yaml`.
- Add runtime validation if API shape becomes complex.

## Decision 5: Keep State Management Local

Decision:

- `SearchInterface.jsx` uses local state for query, loading, error, and response.

Reason:

- The demo is small and does not require global state.

Tradeoffs:

- If filters, selected result, context caching, or multi-page navigation are added, local state may become insufficient.

Future considerations:

- Add a lightweight store only when shared state becomes necessary.

## Decision 6: Make Citation and Context First-Class UI Sections

Decision:

- Added dedicated `CitationList.jsx` and `ContextPreview.jsx`.

Reason:

- The frontend must demonstrate RAG traceability, not only search ranking.

Tradeoffs:

- Result cards are denser than a normal search UI.
- The density is acceptable because the target is a mentor/demo workflow.

Future considerations:

- Add expand/collapse and highlighting between result snippets, citations, source documents, and chunks.
- Add a detail view for deep traceability inspection.

## Decision 7: Use Framework-Neutral E2E Checklist

Decision:

- Added `frontend/tests/e2e_test.js` as a documented checklist instead of executable Playwright/Cypress tests.

Reason:

- The repo has no test runner or frontend package setup.

Tradeoffs:

- Tests cannot be executed automatically yet.

Future considerations:

- Convert the checklist to Playwright tests after Vite and package scripts are added.
