"""Kiểm định schema & chất lượng (Layer 2 — validation)."""

from ingestion.validation.quality_checks import (
    DUPLICATE_RATE_TARGET,
    MISSING_RATE_TARGET,
    QualityReport,
    build_report,
    compute_duplicate_rate,
    compute_missing_rate,
    render_markdown,
)
from ingestion.validation.schema_validator import (
    DEFAULT_SCHEMA_PATH,
    ValidationIssue,
    ValidationResult,
    build_pydantic_model,
    filter_valid,
    load_schema,
    validate_batch,
    validate_document,
)

__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "ValidationIssue",
    "ValidationResult",
    "build_pydantic_model",
    "filter_valid",
    "load_schema",
    "validate_batch",
    "validate_document",
    "DUPLICATE_RATE_TARGET",
    "MISSING_RATE_TARGET",
    "QualityReport",
    "build_report",
    "compute_duplicate_rate",
    "compute_missing_rate",
    "render_markdown",
]
