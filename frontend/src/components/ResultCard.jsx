import { useState } from "react";
import { getContextV2 } from "../api/api_client";
import CitationList from "./CitationList";
import ContextPreview from "./ContextPreview";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import MetadataCard from "./MetadataCard";

export default function ResultCard({ result, query = "", query_id = "" }) {
  const [expanded, setExpanded] = useState(false);
  const [contextPackage, setContextPackage] = useState(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState(null);

  const score = Number(result.score || 0);
  const rank = result.rank ? `#${result.rank}` : "Unranked";
  const thumbnailUrl = result.image?.thumbnail_url;
  const sourceUrl = result.source_url || result.metadata?.source_url;
  const canLoadContext = Boolean(result.hotel_id);

  async function loadContext() {
    if (contextPackage || contextLoading || !canLoadContext) return;

    setContextLoading(true);
    setContextError(null);

    try {
      const context = await getContextV2({
        hotel_id: result.hotel_id,
        query,
        query_id: query_id || result.query_id,
        options: {
          include_chunks: true,
          include_metadata: true,
          include_token_info: true
        }
      });
      setContextPackage(context);
    } catch (error) {
      setContextError(error);
    } finally {
      setContextLoading(false);
    }
  }

  async function toggleExpanded() {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);

    if (nextExpanded) {
      await loadContext();
    }
  }

  return (
    <article className="result-card">
      <header>
        {thumbnailUrl ? (
          <img className="result-thumbnail" src={thumbnailUrl} alt="" loading="lazy" />
        ) : null}
        <div>
          <h3>{result.title || "Untitled hotel"}</h3>
          <p>{result.snippet || "No description available."}</p>
          <small>
            Rank {rank}
            {result.latency_ms ? ` - Search latency ${result.latency_ms}ms` : ""}
          </small>
        </div>
        <span className="score">{score.toFixed(2)}</span>
      </header>

      <MetadataCard
        metadata={result.metadata}
        contextMetadata={contextPackage?.metadata}
        score={result.score}
      />

      <section className="source-documents">
        <h4>Source</h4>
        {sourceUrl ? (
          <a href={sourceUrl} target="_blank" rel="noreferrer">
            {sourceUrl}
          </a>
        ) : (
          <p className="fallback">Source URL unavailable.</p>
        )}
      </section>

      <button type="button" onClick={toggleExpanded} disabled={contextLoading || !canLoadContext}>
        {!canLoadContext
          ? "Context unavailable"
          : expanded
            ? "Collapse context"
            : "Load context package"}
      </button>

      {expanded ? (
        <section className="context-package">
          {contextLoading ? <LoadingState message="Loading context package..." /> : null}
          {contextError ? <ErrorState error={contextError} onRetry={loadContext} /> : null}
          {!contextLoading && !contextError ? (
            <>
              <CitationList
                citations={contextPackage?.citations || result.citations}
                sourceDocuments={result.source_documents}
              />
              <ContextPreview contextPackage={contextPackage} contextChunks={result.context_chunks} />
            </>
          ) : null}
        </section>
      ) : null}

      {!expanded && result.source_documents ? (
        <section className="source-documents">
          <h4>Legacy Source Documents</h4>
          {result.source_documents?.length ? (
            <ul>
              {result.source_documents.map((document) => (
                <li key={document.id}>
                  <strong>{document.title || document.id}</strong>
                  <span>{document.type || "document"}</span>
                  <small>{document.path || document.url || "Source document unavailable"}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="fallback">Source document unavailable.</p>
          )}
        </section>
      ) : null}
    </article>
  );
}
