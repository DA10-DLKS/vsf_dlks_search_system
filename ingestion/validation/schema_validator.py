"""Kiểm định tài liệu theo data_schema.json (Layer 2 — validation).

Module này wrap pydantic để validate từng dict document theo schema do
DA09 cung cấp (contracts/data_schema.json) — xem cleaning_rules.md và
validation_rules.md để biết rule cụ thể.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

# TODO(hieudm): Load schema từ contracts/data_schema.json (CONTRACT với DA09)
# và sinh pydantic model tự động (vd: pydantic.json_schema / datamodel-code-generator).
# TODO(hieudm): Tách bạch "schema lỗi nghiêm trọng" (drop doc) và
# "schema lỗi nhẹ" (giữ doc, fill default) — xem validation_rules.md.

DEFAULT_SCHEMA_PATH: Path = Path(__file__).resolve().parents[3] / "contracts" / "data_schema.json"


@dataclass
class ValidationIssue:
    """Một vấn đề phát hiện được khi validate 1 tài liệu."""

    field: str
    code: str
    message: str
    severity: str  # "error" | "warning"


@dataclass
class ValidationResult:
    """Kết quả validate 1 tài liệu."""

    document_id: str
    is_valid: bool
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def load_schema(path: Path | str = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    """Đọc JSON schema từ file. Cache lại để dùng nhiều lần."""
    # TODO(hieudm): implement (json.load + cache)
    raise NotImplementedError("load_schema not implemented")


def build_pydantic_model(schema: dict[str, Any]):
    """Tạo pydantic model từ JSON schema (dùng cho validation runtime)."""
    # TODO(hieudm): implement
    raise NotImplementedError("build_pydantic_model not implemented")


def validate_document(doc: Mapping[str, Any]) -> ValidationResult:
    """Validate 1 document theo schema + rule đã định nghĩa trong validation_rules.md."""
    # TODO(hieudm): implement
    raise NotImplementedError("validate_document not implemented")


def validate_batch(docs: Iterable[Mapping[str, Any]]) -> list[ValidationResult]:
    """Validate một batch document, trả về danh sách ValidationResult."""
    # TODO(hieudm): implement (cân nhắc song song hóa với multiprocessing)
    raise NotImplementedError("validate_batch not implemented")


def filter_valid(
    docs: Iterable[Mapping[str, Any]],
    *,
    drop_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Tiện ích: chỉ giữ lại các document hợp lệ (hoặc cảnh báo)."""
    # TODO(hieudm): implement dựa trên validate_batch
    raise NotImplementedError("filter_valid not implemented")


__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "ValidationIssue",
    "ValidationResult",
    "load_schema",
    "build_pydantic_model",
    "validate_document",
    "validate_batch",
    "filter_valid",
]
