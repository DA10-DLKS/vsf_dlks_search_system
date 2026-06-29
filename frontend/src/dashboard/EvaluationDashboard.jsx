import mockEvaluationResults from "../../mock_evaluation_results.json";

function formatPercent(value) {
  if (typeof value !== "number") return "N/A";
  return `${Math.round(value * 100)}%`;
}

function formatValue(value, type = "number") {
  if (value === undefined || value === null || value === "") return "N/A";
  if (type === "percent") return formatPercent(value);
  if (type === "latency") return `${value} ms`;
  return value;
}

function MetricCard({ label, value, type }) {
  return (
    <article className="evaluation-metric-card">
      <span className="evaluation-label">{label}</span>
      <strong>{formatValue(value, type)}</strong>
      <small>MOCK / DEMO</small>
    </article>
  );
}

function MetricSection({ title, metrics }) {
  return (
    <section className="evaluation-section">
      <h2>{title}</h2>
      <div className="evaluation-grid">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            type={metric.type}
          />
        ))}
      </div>
    </section>
  );
}

export default function EvaluationDashboard({ data = mockEvaluationResults }) {
  const summary = data?.summary || {};
  const retrieval = data?.retrieval_metrics || {};
  const contextCitation = data?.context_citation_metrics || {};
  const latency = data?.latency_metrics || {};
  const coverage = data?.golden_dataset_coverage || {};
  const rows = Array.isArray(data?.query_results) ? data.query_results : [];

  if (!data || !rows.length) {
    return (
      <section className="evaluation-empty-state">
        <h1>Evaluation Dashboard - MOCK / DEMO</h1>
        <p>No evaluation data is available.</p>
      </section>
    );
  }

  return (
    <main className="evaluation-dashboard">
      <header className="evaluation-header">
        <div>
          <p className="evaluation-kicker">DA10 Display Layer</p>
          <h1>Evaluation Dashboard - MOCK / DEMO</h1>
          <p>Kien calculates evaluation metrics. Hieu displays the outputs.</p>
        </div>
        <strong className="evaluation-badge">MOCK / DEMO</strong>
      </header>

      <section className="evaluation-section">
        <h2>Data Provenance</h2>
        <p>{data.data_provenance?.source}</p>
        <p>Status: {data.data_provenance?.status}</p>
        <p>Last updated: {data.data_provenance?.last_updated}</p>
      </section>

      <MetricSection
        title="Summary"
        metrics={[
          { label: "Total Queries", value: summary.total_queries },
          { label: "Tested Queries", value: summary.tested_queries },
          { label: "Passed Queries", value: summary.passed_queries },
          { label: "Failed Queries", value: summary.failed_queries }
        ]}
      />

      <MetricSection
        title="Retrieval Metrics"
        metrics={[
          { label: "Recall@10", value: retrieval.recall_at_10, type: "percent" },
          { label: "MRR@10", value: retrieval.mrr_at_10, type: "percent" },
          { label: "NDCG@10", value: retrieval.ndcg_at_10, type: "percent" },
          { label: "Hit@5", value: retrieval.hit_at_5, type: "percent" },
          { label: "Hit@10", value: retrieval.hit_at_10, type: "percent" },
          { label: "Zero Result Rate", value: retrieval.zero_result_rate, type: "percent" }
        ]}
      />

      <MetricSection
        title="Context & Citation Metrics"
        metrics={[
          { label: "Chunk Recall", value: contextCitation.chunk_recall, type: "percent" },
          { label: "Citation Coverage", value: contextCitation.citation_coverage, type: "percent" },
          { label: "Context Quality", value: contextCitation.context_quality, type: "percent" }
        ]}
      />

      <MetricSection
        title="API Latency"
        metrics={[
          { label: "p95 Search Latency", value: latency.p95_search_latency_ms, type: "latency" },
          { label: "p95 Context Latency", value: latency.p95_context_latency_ms, type: "latency" }
        ]}
      />

      <section className="evaluation-section">
        <h2>Golden Dataset Coverage</h2>
        <p>
          {coverage.covered_queries} / {coverage.total_golden_queries} queries covered (
          {formatPercent(coverage.coverage_rate)})
        </p>
        <p>{coverage.note}</p>
      </section>

      <section className="evaluation-section">
        <h2>Query-level Evaluation</h2>
        <table className="evaluation-table">
          <thead>
            <tr>
              <th>Query ID</th>
              <th>Query</th>
              <th>Category</th>
              <th>Expected</th>
              <th>Returned</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.query_id} className={row.status === "PASS" ? "pass" : "fail"}>
                <td>{row.query_id}</td>
                <td>{row.query}</td>
                <td>{row.business_category}</td>
                <td>{row.expected_hotel_ids.join(", ")}</td>
                <td>{row.returned_hotel_ids.join(", ")}</td>
                <td>{row.status} - MOCK / DEMO</td>
                <td>{row.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
