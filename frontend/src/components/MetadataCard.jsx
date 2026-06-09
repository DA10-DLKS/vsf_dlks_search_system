import { useState } from "react";

export default function MetadataCard({ metadata = {}, score }) {
  const [expanded, setExpanded] = useState(false);
  const amenities = metadata.amenities || [];
  const bestFor = metadata.best_for || [];

  return (
    <section className="metadata-card">
      <div className="section-header">
        <h4>Metadata</h4>
        <button type="button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      <dl>
        <div>
          <dt>Location</dt>
          <dd>{metadata.location || "Unknown location"}</dd>
        </div>
        <div>
          <dt>Category</dt>
          <dd>{metadata.category || "Unknown category"}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{Number(score || 0).toFixed(2)}</dd>
        </div>
      </dl>
      {expanded ? (
        <div className="metadata-expanded">
          <p>
            <strong>Ranking:</strong> {metadata.ranking_info || "No ranking information available"}
          </p>
          <p>
            <strong>Price level:</strong> {metadata.price_level || "Unknown"}
          </p>
          <p>
            <strong>Amenities:</strong> {amenities.length ? amenities.join(", ") : "No amenities listed"}
          </p>
          <p>
            <strong>Best for:</strong> {bestFor.length ? bestFor.join(", ") : "No audience tags listed"}
          </p>
        </div>
      ) : null}
    </section>
  );
}
