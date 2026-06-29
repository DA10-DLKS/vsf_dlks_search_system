export default function ErrorState({ error, onRetry }) {
  const message =
    typeof error === "string"
      ? error
      : error?.user_message || error?.message || "Something went wrong.";

  return (
    <div className="state state-error" role="alert">
      <strong>API error</strong>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
