import EmptyState from "./EmptyState";
import ResultCard from "./ResultCard";

export default function ResultList({ results = [], query = "", query_id = "" }) {
  if (!results.length) {
    return <EmptyState />;
  }

  return (
    <section className="result-list">
      {results.map((result) => (
        <ResultCard key={result.id} result={result} query={query} query_id={query_id} />
      ))}
    </section>
  );
}
