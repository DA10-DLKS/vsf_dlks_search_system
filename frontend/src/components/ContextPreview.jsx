import { useState } from "react";

export default function ContextPreview({ contextPackage = null, contextChunks = [] }) {
  const [expanded, setExpanded] = useState(false);
  const chunks = contextPackage?.chunks?.length ? contextPackage.chunks : contextChunks || [];
  const contextText = contextPackage?.context_text || "";
  const tokenInfo = contextPackage?.token_info;

  if (!chunks.length && !contextText) {
    return (
      <section className="context-preview">
        <h4>Context Chunks</h4>
        <p className="fallback">No context preview available.</p>
      </section>
    );
  }

  const visibleChunks = expanded ? chunks : chunks.slice(0, 1);

  return (
    <section className="context-preview">
      <div className="section-header">
        <h4>LLM-ready Context</h4>
        {chunks.length > 1 ? (
          <button type="button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Collapse chunks" : `Show all ${chunks.length} chunks`}
          </button>
        ) : null}
      </div>
      {contextText ? <p className="llm-context">{contextText}</p> : null}
      {tokenInfo ? (
        <small>
          Tokens: {tokenInfo.total_tokens ?? "N/A"} total
          {tokenInfo.model_used_for_count ? ` - ${tokenInfo.model_used_for_count}` : ""}
        </small>
      ) : null}
      {chunks.length ? (
        <ol>
          {visibleChunks.map((chunk) => {
            const rerankerScore = chunk.scores?.reranker_score;
            return (
              <li key={chunk.id || chunk.chunk_id}>
                <span>{chunk.chunk_id || chunk.id}</span>
                <p>{chunk.text || "No context text available."}</p>
                <small>
                  Type: {chunk.source_type || "Unknown"}
                  {rerankerScore !== undefined
                    ? ` - Reranker: ${Number(rerankerScore).toFixed(2)}`
                    : ""}
                </small>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="fallback">No detailed chunks available.</p>
      )}
    </section>
  );
}
