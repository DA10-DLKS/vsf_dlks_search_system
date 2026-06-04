import SearchInterface from "../components/SearchInterface";

export default function Dashboard() {
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>OTA AI Search Demo</h1>
          <p>User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption</p>
        </div>
      </header>

      <section className="traceability-strip" aria-label="RAG flow">
        {["Query", "Top-K", "Metadata", "Citation", "Sources", "Context", "LLM"].map((step) => (
          <span key={step}>{step}</span>
        ))}
      </section>

      <section className="metrics-grid">
        <article>
          <strong>Recall@10</strong>
          <span>Target >= 0.80</span>
        </article>
        <article>
          <strong>MRR</strong>
          <span>Target >= 0.70</span>
        </article>
        <article>
          <strong>NDCG</strong>
          <span>Target >= 0.75</span>
        </article>
        <article>
          <strong>P95 latency</strong>
          <span>Target < 500ms</span>
        </article>
      </section>

      <SearchInterface />
    </div>
  );
}
