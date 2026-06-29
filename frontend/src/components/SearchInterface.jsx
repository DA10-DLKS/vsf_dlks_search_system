import { useState } from "react";
import { searchV2 } from "../api/api_client";
import EmptyState from "./EmptyState";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import ResultList from "./ResultList";

const defaultQuery = "Tôi muốn resort yên tĩnh gần biển cho gia đình";

export default function SearchInterface() {
  const [query, setQuery] = useState(defaultQuery);
  const [queryId, setQueryId] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function runSearch() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await searchV2(trimmedQuery, {
        top_k: 10,
        page: 0,
        include_debug: false
      });
      setQueryId(data.query_id || "");
      setResults(data.results || []);
    } catch (apiError) {
      setError(apiError);
      setQueryId("");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await runSearch();
  }

  return (
    <main className="search-interface">
      <form onSubmit={handleSubmit} className="search-form">
        <label htmlFor="search-query">User Query</label>
        <div>
          <input
            id="search-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Describe the OTA experience you need"
          />
          <button type="submit" disabled={loading || !query.trim()}>
            Search
          </button>
        </div>
      </form>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState error={error} onRetry={runSearch} /> : null}
      {!loading && !error && hasSearched ? (
        <ResultList results={results} query={query.trim()} query_id={queryId} />
      ) : null}
      {!loading && !error && !hasSearched ? (
        <EmptyState message="Submit a demo query to inspect ranked results, citations, sources, and context chunks." />
      ) : null}
    </main>
  );
}
