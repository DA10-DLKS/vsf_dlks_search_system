export default function EmptyState({ message = "No matching OTA results were found." }) {
  return (
    <div className="state state-empty">
      <strong>No results</strong>
      <p>{message}</p>
    </div>
  );
}
