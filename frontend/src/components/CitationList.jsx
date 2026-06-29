export default function CitationList({ citations = [], sourceDocuments = [] }) {
  if (!citations.length) {
    return (
      <section className="citation-list">
        <h4>Citations</h4>
        <p className="fallback">No citation available.</p>
      </section>
    );
  }

  const sourceMap = new Map(sourceDocuments.map((doc) => [doc.id, doc]));

  return (
    <section className="citation-list">
      <h4>Citations</h4>
      <ul>
        {citations.map((citation) => {
          const source = sourceMap.get(citation.source_document_id);
          const sourceTable = citation.metadata?.source_table;
          const sourceColumn = citation.metadata?.source_column;
          const relevanceScore =
            citation.relevance_score !== undefined
              ? Number(citation.relevance_score).toFixed(2)
              : null;

          return (
            <li key={citation.id || citation.citation_id}>
              <strong>{citation.citation_id || citation.id}</strong>
              <span>Chunk: {citation.chunk_id || "Unknown chunk"}</span>
              <span>Type: {citation.source_type || citation.label || "Unknown source type"}</span>
              <span>
                Source:{" "}
                {source?.title ||
                  [sourceTable, sourceColumn].filter(Boolean).join(".") ||
                  citation.source_document_id ||
                  "Source unavailable"}
              </span>
              {relevanceScore ? <span>Relevance: {relevanceScore}</span> : null}
              {citation.text_snippet || citation.quote ? (
                <p>{citation.text_snippet || citation.quote}</p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
