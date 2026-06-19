import { useState } from "react";

export default function MetadataCard({ metadata = {}, contextMetadata = null, score }) {
  const [expanded, setExpanded] = useState(false);
  const detail = contextMetadata || {};
  const mergedMetadata = {
    ...metadata,
    ...detail,
    amenities: detail.amenities || metadata.amenities || metadata.amenities_top || [],
    suitable_for: detail.suitable_for || metadata.suitable_for || metadata.best_for || [],
    category: metadata.category || detail.accommodation_type || metadata.accommodation_type,
    location: metadata.location || detail.city || metadata.city || detail.address || metadata.address
  };
  const amenities = mergedMetadata.amenities || [];
  const suitableFor = mergedMetadata.suitable_for || [];
  const priceFrom = mergedMetadata.price_from;

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
          <dt>City</dt>
          <dd>{mergedMetadata.city || mergedMetadata.location || "Unknown city"}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{mergedMetadata.accommodation_type || mergedMetadata.category || "Unknown type"}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{Number(score || 0).toFixed(2)}</dd>
        </div>
      </dl>
      {expanded ? (
        <div className="metadata-expanded">
          <p>
            <strong>Address:</strong> {mergedMetadata.address || "Unknown address"}
          </p>
          <p>
            <strong>Star rating:</strong> {mergedMetadata.star_rating ?? "Unknown"}
          </p>
          <p>
            <strong>Review score:</strong> {mergedMetadata.review_score ?? "Unknown"}
            {mergedMetadata.review_count ? ` (${mergedMetadata.review_count} reviews)` : ""}
          </p>
          <p>
            <strong>Price from:</strong>{" "}
            {priceFrom ? `${Number(priceFrom).toLocaleString("vi-VN")} VND` : "Unknown"}
          </p>
          <p>
            <strong>Amenities:</strong> {amenities.length ? amenities.join(", ") : "No amenities listed"}
          </p>
          <p>
            <strong>Suitable for:</strong>{" "}
            {suitableFor.length ? suitableFor.join(", ") : "No audience tags listed"}
          </p>
          <p>
            <strong>Ranking:</strong>{" "}
            {mergedMetadata.ranking_info || "No ranking information available"}
          </p>
        </div>
      ) : null}
    </section>
  );
}
