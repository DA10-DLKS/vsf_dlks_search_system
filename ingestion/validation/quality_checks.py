"""Đo chất lượng dữ liệu (Layer 2 — validation / quality).

Module này tính các metric mà Hiếu chịu trách nhiệm:
- Missing Rate < 5%      (tỷ lệ trường bắt buộc bị thiếu/rỗng)
- Duplicate Rate < 2%    (tỷ lệ tài liệu trùng lặp, dùng kết quả từ deduplication/)

Output: dict metric + (tuỳ chọn) ghi báo cáo Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

# TODO(hieudm): Mapping required_fields theo từng doc_type — định nghĩa trong
# contracts/data_schema.json hoặc 1 file config riêng.
# TODO(hieudm): Missing Rate nên tính theo (số field bị thiếu) / (tổng field bắt buộc)
# chứ không phải theo document để chính xác hơn.


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


def compute_missing_rate(
    docs: Iterable[Mapping[str, Any]],
    required_fields: Sequence[str],
) -> tuple[float, dict[str, int]]:
    """Tính Missing Rate và đếm số lần thiếu theo từng field.

    Returns:
        (missing_rate, missing_count_by_field)
    """
    # TODO(hieudm): implement
    raise NotImplementedError("compute_missing_rate not implemented")


def compute_duplicate_rate(
    docs: Iterable[Mapping[str, Any]],
    duplicate_group_ids: Iterable[Iterable[str]],
) -> tuple[float, int]:
    """Tính Duplicate Rate từ kết quả của deduplication pipeline.

    Returns:
        (duplicate_rate, num_groups)
    """
    # TODO(hieudm): implement
    raise NotImplementedError("compute_duplicate_rate not implemented")


def build_report(
    docs: Sequence[Mapping[str, Any]],
    *,
    required_fields: Sequence[str],
    duplicate_group_ids: Iterable[Iterable[str]] = (),
) -> QualityReport:
    """Tính đầy đủ QualityReport cho 1 batch."""
    # TODO(hieudm): implement (gọi compute_missing_rate + compute_duplicate_rate)
    raise NotImplementedError("build_report not implemented")


def render_markdown(report: QualityReport) -> str:
    """Render QualityReport thành chuỗi Markdown (để ghi vào .md)."""
    # TODO(hieudm): implement
    raise NotImplementedError("render_markdown not implemented")


__all__ = [
    "MISSING_RATE_TARGET",
    "DUPLICATE_RATE_TARGET",
    "QualityReport",
    "compute_missing_rate",
    "compute_duplicate_rate",
    "build_report",
    "render_markdown",
]
