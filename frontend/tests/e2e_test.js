/**
 * Minimal E2E test checklist for the OTA AI Search frontend.
 *
 * This file is intentionally framework-neutral because the repository does not
 * currently include Playwright, Cypress, Vite, or a package.json.
 *
 * Recommended future command after adding Playwright:
 *   npx playwright test frontend/tests/e2e_test.js
 */

export const e2eChecklist = [
  {
    name: "input query",
    steps: [
      "Open frontend/search_ui.html",
      "Find the search input",
      "Enter: Tôi muốn resort yên tĩnh gần biển cho gia đình"
    ],
    expected: "The input accepts the full Vietnamese query."
  },
  {
    name: "submit search",
    steps: ["Click Search"],
    expected: "Loading state appears, then ranked results render."
  },
  {
    name: "render result list",
    steps: ["Inspect Top-K results"],
    expected: "At least one ResultCard appears with title, snippet, and score."
  },
  {
    name: "render metadata",
    steps: ["Inspect a result card"],
    expected: "Location, category, amenities, score, and ranking info are visible."
  },
  {
    name: "render citation",
    steps: ["Inspect Citations section"],
    expected: "Citation id, chunk id, source reference, and quote are visible when available."
  },
  {
    name: "render context preview",
    steps: ["Inspect Context Chunks section"],
    expected: "Context chunk id, source document id, rank, and text are visible when available."
  },
  {
    name: "empty state",
    steps: ["Submit a query not present in mock data"],
    expected: "Empty state appears without breaking layout."
  },
  {
    name: "error state",
    steps: ["Submit a query containing the word error"],
    expected: "Error state appears without breaking layout."
  }
];
