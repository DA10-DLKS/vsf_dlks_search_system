import EmptyState from "./EmptyState";
import ResultCard from "./ResultCard";

export default function ResultList({ results = [] }) {
  if (!results.length) {
    return <EmptyState />;
  }

  return (
    <section className="result-list">
      {results.map((result) => (
        <ResultCard key={result.id} result={result} />
      ))}
    </section>
  );
}
