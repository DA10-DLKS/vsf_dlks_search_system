"""Sprint 2 pipeline: validate cleaned documents theo data_schema.json.

Luồng:
    data/cleaned/*.json  ──▶  schema_validator  ──▶  drop / warn  ──▶  data/cleaned/ (in-place)
                                                                       hoặc data/quarantine/

Output kèm: `quality_report_mock.md` (Sprint 2) / `data_quality_report.md` (Sprint 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

# TODO(hieudm): Import module thật khi đã implement:
# from ingestion.validation.schema_validator import validate_batch, filter_valid
# from ingestion.validation.quality_checks import build_report, render_markdown

DEFAULT_INPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"
DEFAULT_QUARANTINE_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "quarantine"
DEFAULT_REPORT_PATH: Path = Path(__file__).resolve().parents[1] / "quality_report_mock.md"


def validate_docs(
    docs: Iterable[dict[str, Any]],
    *,
    drop_invalid: bool = True,
) -> tuple[list[dict[str, Any]], list[Any]]:
    """Validate batch, trả về (docs_hợp_lệ, danh_sách_ValidationResult_lỗi)."""
    # TODO(hieudm): implement dựa trên schema_validator
    raise NotImplementedError("validate_docs not implemented")


def write_quarantine(
    invalid_results: Iterable[Any],
    output_dir: Path = DEFAULT_QUARANTINE_DIR,
) -> list[Path]:
    """Ghi các document lỗi + lý do vào quarantine để debug."""
    # TODO(hieudm): implement
    raise NotImplementedError("write_quarantine not implemented")


def write_report(
    report_md: str,
    output_path: Path = DEFAULT_REPORT_PATH,
) -> Path:
    """Ghi báo cáo chất lượng ra .md."""
    # TODO(hieudm): implement
    raise NotImplementedError("write_report not implemented")


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Entry point: validate + sinh báo cáo. Trả về summary."""
    # TODO(hieudm): orchestrate (validate_docs → build_report → write_report)
    raise NotImplementedError("validation_pipeline.run not implemented")


def main() -> None:
    # TODO(hieudm): parse CLI args + gọi run()
    raise NotImplementedError("validation_pipeline.main not implemented")


if __name__ == "__main__":
    main()
