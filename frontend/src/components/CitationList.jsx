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
          return (
            <li key={citation.id}>
              <strong>{citation.label || citation.id}</strong>
              <span>Chunk: {citation.chunk_id || "Unknown chunk"}</span>
              <span>Source: {source?.title || citation.source_document_id || "Source document unavailable"}</span>
              {citation.quote ? <p>{citation.quote}</p> : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
