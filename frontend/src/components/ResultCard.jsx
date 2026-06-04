import CitationList from "./CitationList";
import ContextPreview from "./ContextPreview";
import MetadataCard from "./MetadataCard";

export default function ResultCard({ result }) {
  return (
    <article className="result-card">
      <header>
        <div>
          <h3>{result.title}</h3>
          <p>{result.snippet}</p>
        </div>
        <span className="score">{Number(result.score || 0).toFixed(2)}</span>
      </header>

      <MetadataCard metadata={result.metadata} score={result.score} />

      <section className="source-documents">
        <h4>Source Documents</h4>
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

      <CitationList citations={result.citations} sourceDocuments={result.source_documents} />
      <ContextPreview contextChunks={result.context_chunks} />
    </article>
  );
}
