"""Kiểm định tài liệu theo data_schema.json (Layer 2 — validation).

Schema chính thức từ DA09: docs/relational_schema.md (PostgreSQL).
Ánh xạ 4 bảng: hotels, rooms, nearby_places, activities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

# Hotel required fields (NOT NULL trong relational_schema.md)
# Data thật (Agoda) dùng hotel_id thay vì id → chấp nhận cả 2.
HOTEL_REQUIRED_ALIASES: dict[str, list[str]] = {
    "id": ["id", "hotel_id"],
}
HOTEL_REQUIRED_FIELDS: list[str] = ["id", "name", "source_url"]

# Sub-document required fields — hotel_id là FK implicit (lấy từ parent)
ROOM_REQUIRED_FIELDS: list[str] = ["hotel_id", "name"]
NEARBY_PLACE_REQUIRED_FIELDS: list[str] = ["hotel_id", "name"]
ACTIVITY_REQUIRED_FIELDS: list[str] = ["hotel_id", "title"]

# All required fields for missing rate calculation
ALL_REQUIRED_FIELDS: list[str] = (
    HOTEL_REQUIRED_FIELDS
    + [f"rooms.{f}" for f in ROOM_REQUIRED_FIELDS]
    + [f"nearby_places.{f}" for f in NEARBY_PLACE_REQUIRED_FIELDS]
    + [f"activities.{f}" for f in ACTIVITY_REQUIRED_FIELDS]
)

DEFAULT_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "contracts" / "data_schema.json"
)

# Numeric ranges from relational_schema
NUMERIC_RANGES: dict[str, tuple[float | None, float | None]] = {
    "star_rating": (1.0, 5.0),
    "review_score": (0, 10),
    "latitude": (-90, 90),
    "longitude": (-180, 180),
    "distance_km": (0, None),
    "price": (0, None),
    "price_amount": (0, None),
    "max_occupancy": (1, None),
}


@dataclass
class ValidationIssue:
    field: str
    code: str
    message: str
    severity: str  # "error" | "warning"


@dataclass
class ValidationResult:
    document_id: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def load_schema(path: Path | str = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_required_fields(
    doc: Mapping[str, Any],
    required: list[str],
    prefix: str = "",
    *,
    aliases: dict[str, list[str]] | None = None,
) -> list[ValidationIssue]:
    """Check required fields với optional alias mapping (vd: id ↔ hotel_id)."""
    issues: list[ValidationIssue] = []
    for field in required:
        full_name = f"{prefix}.{field}" if prefix else field
        candidates = [field]
        if aliases and field in aliases:
            candidates = aliases[field]

        # Check if any alias exists with a non-None value
        found = False
        for c in candidates:
            val = doc.get(c)
            if val is not None and (not isinstance(val, str) or val.strip() != ""):
                found = True
                break

        if not found:
            # Report using primary field name
            issues.append(
                ValidationIssue(
                    field=full_name,
                    code="missing_required",
                    message=f"Missing required field '{full_name}' (aliases: {candidates})",
                    severity="error",
                )
            )
    return issues


def _check_numeric_range(
    doc: Mapping[str, Any],
    field: str,
    min_val: float | None,
    max_val: float | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if field not in doc or doc[field] is None:
        return issues
    val = doc[field]
    if not isinstance(val, (int, float)):
        issues.append(
            ValidationIssue(
                field=field,
                code="wrong_type",
                message=f"Field '{field}' expected numeric, got {type(val).__name__}",
                severity="warning",
            )
        )
        return issues
    if min_val is not None and val < min_val:
        issues.append(
            ValidationIssue(
                field=field,
                code="out_of_range",
                message=f"Field '{field}'={val} < min {min_val}",
                severity="warning",
            )
        )
    if max_val is not None and val > max_val:
        issues.append(
            ValidationIssue(
                field=field,
                code="out_of_range",
                message=f"Field '{field}'={val} > max {max_val}",
                severity="warning",
            )
        )
    return issues


def _check_sub_documents(
    doc: Mapping[str, Any],
    key: str,
    required: list[str],
    label: str,
    *,
    parent_id_field: str = "hotel_id",
) -> list[ValidationIssue]:
    """Check sub-document required fields.

    FK hotel_id trong sub-document là implicit (lấy từ hotel cha).
    Nếu sub-doc thiếu hotel_id nhưng hotel cha có id/hotel_id → OK.
    """
    issues: list[ValidationIssue] = []
    items = doc.get(key)
    if items is None or not isinstance(items, list):
        return issues

    # Get parent ID to fill implicit FK
    parent_id = doc.get("id") or doc.get("hotel_id")

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(
                ValidationIssue(
                    field=f"{key}[{i}]",
                    code="wrong_type",
                    message=f"{label}[{i}] expected object, got {type(item).__name__}",
                    severity="error",
                )
            )
            continue

        # Skip hotel_id check if implicit (parent has ID, sub-doc in context)
        filtered_required = [
            f for f in required if not (f == parent_id_field and parent_id is not None)
        ]
        issues.extend(_check_required_fields(item, filtered_required, prefix=f"{key}[{i}]"))

    return issues


def validate_document(doc: Mapping[str, Any]) -> ValidationResult:
    doc_id = str(doc.get("id") or doc.get("hotel_id", "unknown"))
    issues: list[ValidationIssue] = []

    # 1. Hotel required fields (with alias id ↔ hotel_id)
    issues.extend(_check_required_fields(
        doc, HOTEL_REQUIRED_FIELDS, aliases=HOTEL_REQUIRED_ALIASES,
    ))

    # 2. Sub-document required fields (FK hotel_id implicit từ parent)
    issues.extend(_check_sub_documents(doc, "rooms", ROOM_REQUIRED_FIELDS, "Room"))
    issues.extend(
        _check_sub_documents(doc, "nearby_places", NEARBY_PLACE_REQUIRED_FIELDS, "NearbyPlace")
    )
    issues.extend(_check_sub_documents(doc, "activities", ACTIVITY_REQUIRED_FIELDS, "Activity"))

    # 3. Numeric range checks (hotel level)
    for field, (lo, hi) in NUMERIC_RANGES.items():
        if field in doc:
            issues.extend(_check_numeric_range(doc, field, lo, hi))

    # 4. Type checks cho array fields (chỉ warning cho item type)
    string_array_fields = {"amenities", "policyNotes", "suitable_for"}
    for field in string_array_fields:
        val = doc.get(field)
        if val is not None and isinstance(val, list):
            for i, item in enumerate(val):
                if not isinstance(item, str):
                    issues.append(
                        ValidationIssue(
                            field=f"{field}[{i}]",
                            code="wrong_item_type",
                            message=f"{field}[{i}] expected str, got {type(item).__name__}",
                            severity="warning",
                        )
                    )

    # images có thể là list[str] hoặc list[dict{url,...}] → chấp nhận cả 2
    images = doc.get("images")
    if images is not None and isinstance(images, list) and len(images) > 0:
        first_item = images[0]
        if not isinstance(first_item, (str, dict)):
            issues.append(
                ValidationIssue(
                    field="images[0]",
                    code="wrong_item_type",
                    message=f"images[0] expected str or dict, got {type(first_item).__name__}",
                    severity="warning",
                )
            )

    object_fields = ["useful_info", "reviews_detail"]
    for field in object_fields:
        val = doc.get(field)
        if val is not None and not isinstance(val, dict):
            issues.append(
                ValidationIssue(
                    field=field,
                    code="wrong_type",
                    message=f"{field} expected object (JSONB), got {type(val).__name__}",
                    severity="warning",
                )
            )

    # 5. Format checks
    crawled_at = doc.get("crawled_at")
    if crawled_at is not None and isinstance(crawled_at, str):
        if not (crawled_at.endswith("Z") or "T" in crawled_at):
            issues.append(
                ValidationIssue(
                    field="crawled_at",
                    code="bad_format",
                    message=f"crawled_at does not look like ISO 8601: {crawled_at}",
                    severity="warning",
                )
            )

    return ValidationResult(
        document_id=doc_id,
        is_valid=len([i for i in issues if i.severity == "error"]) == 0,
        issues=issues,
    )


def validate_batch(docs: Iterable[Mapping[str, Any]]) -> list[ValidationResult]:
    return [validate_document(doc) for doc in docs]


def filter_valid(
    docs: Iterable[Mapping[str, Any]],
    *,
    drop_on_error: bool = True,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for doc in docs:
        result = validate_document(doc)
        if drop_on_error and not result.is_valid:
            continue
        results.append(dict(doc))
    return results


__all__ = [
    "HOTEL_REQUIRED_FIELDS",
    "ROOM_REQUIRED_FIELDS",
    "NEARBY_PLACE_REQUIRED_FIELDS",
    "ACTIVITY_REQUIRED_FIELDS",
    "ALL_REQUIRED_FIELDS",
    "NUMERIC_RANGES",
    "DEFAULT_SCHEMA_PATH",
    "ValidationIssue",
    "ValidationResult",
    "load_schema",
    "validate_document",
    "validate_batch",
    "filter_valid",
]
