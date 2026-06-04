"""Đo chất lượng dữ liệu (Layer 2 — validation / quality).

Module này tính các metric mà Hiếu chịu trách nhiệm:
- Missing Rate < 5%      (tỷ lệ trường bắt buộc bị thiếu/rỗng)
- Duplicate Rate < 2%    (tỷ lệ tài liệu trùng lặp, dùng kết quả từ deduplication/)

Output: dict metric + (tuỳ chọn) ghi báo cáo Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from ingestion.validation.schema_validator import (
    ACTIVITY_REQUIRED_FIELDS,
    HOTEL_REQUIRED_ALIASES,
    HOTEL_REQUIRED_FIELDS,
    NEARBY_PLACE_REQUIRED_FIELDS,
    ROOM_REQUIRED_FIELDS,
)

# Required fields theo DA09 relational_schema.md
REQUIRED_FIELDS_HOTEL: list[str] = HOTEL_REQUIRED_FIELDS  # ["id", "name", "source_url"]
REQUIRED_FIELDS_ROOM: list[str] = ROOM_REQUIRED_FIELDS
REQUIRED_FIELDS_NEARBY_PLACE: list[str] = NEARBY_PLACE_REQUIRED_FIELDS
REQUIRED_FIELDS_ACTIVITY: list[str] = ACTIVITY_REQUIRED_FIELDS

# Ngưỡng mục tiêu cam kết với team (Sprint 1 plan).
MISSING_RATE_TARGET: float = 0.05
DUPLICATE_RATE_TARGET: float = 0.02


@dataclass
class QualityReport:
    """Báo cáo chất lượng cho 1 batch tài liệu."""

    total_documents: int
    missing_rate: float
    duplicate_rate: float
    missing_by_field: dict[str, int] = field(default_factory=dict)
    duplicate_group_count: int = 0
    passed_missing: bool = False
    passed_duplicate: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "missing_rate": self.missing_rate,
            "duplicate_rate": self.duplicate_rate,
            "missing_by_field": self.missing_by_field,
            "duplicate_group_count": self.duplicate_group_count,
            "passed_missing": self.passed_missing,
            "passed_duplicate": self.passed_duplicate,
            "notes": self.notes,
        }


def _field_present(obj: Mapping[str, Any], field: str, aliases: dict[str, list[str]] | None = None) -> bool:
    """Check if field (or its alias) is present and non-empty."""
    candidates = list(aliases.get(field, [field])) if aliases else [field]
    for c in candidates:
        val = obj.get(c)
        if val is not None and (not isinstance(val, str) or val.strip() != ""):
            return True
    return False


def compute_missing_rate(
    docs: Iterable[Mapping[str, Any]],
    required_fields: Sequence[str] | None = None,
) -> tuple[float, dict[str, int]]:
    """Tính Missing Rate cho hotel documents.

    Dùng alias mapping (id ↔ hotel_id) cho hotel-level fields.
    Sub-document FK hotel_id được coi là implicit nếu hotel cha có id.

    Returns:
        (missing_rate, missing_count_by_field)
    """
    if required_fields is None:
        required_fields = REQUIRED_FIELDS_HOTEL

    total_checks = 0
    missing_count = 0
    missing_by_field: dict[str, int] = {}

    def _check(
        obj: Mapping[str, Any],
        fields: Sequence[str],
        prefix: str = "",
        *,
        aliases: dict[str, list[str]] | None = None,
    ) -> None:
        nonlocal total_checks, missing_count
        for field in fields:
            full_name = f"{prefix}.{field}" if prefix else field
            total_checks += 1
            if not _field_present(obj, field, aliases):
                missing_count += 1
                missing_by_field[full_name] = missing_by_field.get(full_name, 0) + 1

    for doc in docs:
        _check(doc, required_fields, aliases=HOTEL_REQUIRED_ALIASES)

        parent_id = doc.get("id") or doc.get("hotel_id")

        # Check sub-documents (FK hotel_id implicit nếu parent có ID)
        for key, sub_fields in [
            ("rooms", REQUIRED_FIELDS_ROOM),
            ("nearby_places", REQUIRED_FIELDS_NEARBY_PLACE),
            ("activities", REQUIRED_FIELDS_ACTIVITY),
        ]:
            items = doc.get(key)
            if items and isinstance(items, list):
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        # Skip hotel_id check if implicit
                        filtered = [
                            f for f in sub_fields
                            if not (f == "hotel_id" and parent_id is not None)
                        ]
                        _check(item, filtered, prefix=f"{key}[{i}]")

    if total_checks == 0:
        return 0.0, {}

    rate = missing_count / total_checks
    return rate, missing_by_field


def compute_duplicate_rate(
    docs: Iterable[Mapping[str, Any]] | int,
    duplicate_group_ids: Iterable[Iterable[str]],
) -> tuple[float, int]:
    """Tính Duplicate Rate từ kết quả của deduplication pipeline.

    Returns:
        (duplicate_rate, num_groups) — duplicate_rate = duplicate_docs / total_docs
    """
    num_groups = 0
    duplicate_docs = 0
    for group in duplicate_group_ids:
        group_list = list(group)
        if len(group_list) >= 2:
            num_groups += 1
            duplicate_docs += len(group_list) - 1  # keep 1 per group

    total = len(list(docs)) if isinstance(docs, (list, tuple)) else 0
    if total == 0:
        return 0.0, num_groups

    rate = duplicate_docs / total
    return rate, num_groups


def build_report(
    docs: Sequence[Mapping[str, Any]],
    *,
    required_fields: Sequence[str] | None = None,
    duplicate_group_ids: Iterable[Iterable[str]] = (),
) -> QualityReport:
    """Tính đầy đủ QualityReport cho 1 batch."""
    if required_fields is None:
        required_fields = REQUIRED_FIELDS_HOTEL

    missing_rate, missing_by_field = compute_missing_rate(docs, required_fields)
    duplicate_rate, dup_group_count = compute_duplicate_rate(docs, duplicate_group_ids)

    notes_parts: list[str] = []
    if missing_rate > MISSING_RATE_TARGET:
        notes_parts.append(
            f"Missing rate {missing_rate:.1%} exceeds target {MISSING_RATE_TARGET:.1%}"
        )
    if duplicate_rate > DUPLICATE_RATE_TARGET:
        notes_parts.append(
            f"Duplicate rate {duplicate_rate:.1%} exceeds target {DUPLICATE_RATE_TARGET:.1%}"
        )

    return QualityReport(
        total_documents=len(docs),
        missing_rate=missing_rate,
        duplicate_rate=duplicate_rate,
        missing_by_field=missing_by_field,
        duplicate_group_count=dup_group_count,
        passed_missing=missing_rate <= MISSING_RATE_TARGET,
        passed_duplicate=duplicate_rate <= DUPLICATE_RATE_TARGET,
        notes="; ".join(notes_parts),
    )


def render_markdown(report: QualityReport) -> str:
    """Render QualityReport thành chuỗi Markdown (để ghi vào .md)."""
    lines: list[str] = []
    lines.append("# Data Quality Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"| Metric | Value | Target | Pass |")
    lines.append(f"|---|---|---|---|")
    lines.append(
        f"| **Total documents** | {report.total_documents} | – | – |"
    )
    lines.append(
        f"| **Missing rate** | {report.missing_rate:.1%} | < {MISSING_RATE_TARGET:.1%} | "
        f"{'✅' if report.passed_missing else '❌'} |"
    )
    lines.append(
        f"| **Duplicate rate** | {report.duplicate_rate:.1%} | < {DUPLICATE_RATE_TARGET:.1%} | "
        f"{'✅' if report.passed_duplicate else '❌'} |"
    )
    lines.append(f"| **Duplicate groups** | {report.duplicate_group_count} | – | – |")
    lines.append("")

    if report.missing_by_field:
        lines.append("## Missing by field")
        lines.append("")
        lines.append("| Field | Count |")
        lines.append("|---|---|")
        for field, count in sorted(
            report.missing_by_field.items(), key=lambda x: -x[1]
        ):
            lines.append(f"| {field} | {count} |")
        lines.append("")

    if report.notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(report.notes)
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "MISSING_RATE_TARGET",
    "DUPLICATE_RATE_TARGET",
    "QualityReport",
    "compute_missing_rate",
    "compute_duplicate_rate",
    "build_report",
    "render_markdown",
]
