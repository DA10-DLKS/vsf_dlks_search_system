import { useState } from "react";

export default function ContextPreview({ contextChunks = [] }) {
  const [expanded, setExpanded] = useState(false);

  if (!contextChunks.length) {
    return (
      <section className="context-preview">
        <h4>Context Chunks</h4>
        <p className="fallback">No context preview available.</p>
      </section>
    );
  }

  const visibleChunks = expanded ? contextChunks : contextChunks.slice(0, 1);

  return (
    <section className="context-preview">
      <div className="section-header">
        <h4>Context Chunks</h4>
        {contextChunks.length > 1 ? (
          <button type="button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Collapse" : `Show all ${contextChunks.length}`}
          </button>
        ) : null}
      </div>
      <ol>
        {visibleChunks.map((chunk) => (
          <li key={chunk.id}>
            <span>#{chunk.rank} {chunk.id}</span>
            <p>{chunk.text || "No context text available."}</p>
            <small>Source: {chunk.source_document_id || "Source document unavailable"}</small>
          </li>
        ))}
      </ol>
    </section>
  );
}
