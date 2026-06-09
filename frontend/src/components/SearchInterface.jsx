import { useState } from "react";
import { search } from "../api/api_client";
import EmptyState from "./EmptyState";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import ResultList from "./ResultList";

const defaultQuery = "Tôi muốn resort yên tĩnh gần biển cho gia đình";

export default function SearchInterface() {
  const [query, setQuery] = useState(defaultQuery);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runSearch() {
    setLoading(true);
    setError(null);

    try {
      const data = await search(query);
      setResponse(data);
    } catch (apiError) {
      setError(apiError);
      setResponse(null);
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
      {!loading && !error && response ? <ResultList results={response.results} /> : null}
      {!loading && !error && !response ? (
        <EmptyState message="Submit a demo query to inspect ranked results, citations, sources, and context chunks." />
      ) : null}
    </main>
  );
}
