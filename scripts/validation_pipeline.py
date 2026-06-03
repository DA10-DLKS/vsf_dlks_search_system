"""Validate cleaned documents, sinh data quality report, quarantine invalid docs.

Luồng:
    data/cleaned/*.json
        ──▶  schema_validator.validate_document()
        ├── valid   ──▶  quality_checks.build_report()  ──▶  data_quality_report.md
        └── invalid ──▶  data/quarantine/*.json (kèm lý do)
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ingestion.validation.schema_validator import (
    ValidationResult,
    validate_document,
)
from ingestion.validation.quality_checks import (
    QualityReport,
    build_report,
    render_markdown,
)

DEFAULT_INPUT_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_QUARANTINE_DIR: Path = _PROJECT_ROOT / "data" / "quarantine"
DEFAULT_REPORT_PATH: Path = _PROJECT_ROOT / "docs" / "data_quality_report.md"
DEFAULT_GROUPS_PATH: Path = _PROJECT_ROOT / "data" / "dedup_groups.json"


def _read_docs(input_dir: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for fpath in sorted(input_dir.glob("*.json")):
        with open(fpath, encoding="utf-8") as f:
            docs.append(json.load(f))
    return docs


def _read_dedup_groups(groups_path: Path) -> list[list[str]]:
    if not groups_path.exists():
        return []
    with open(groups_path, encoding="utf-8") as f:
        data = json.load(f)
    return [g.get("document_ids", []) for g in data]


def validate_docs(
    docs: Iterable[dict[str, Any]],
    *,
    drop_invalid: bool = True,
) -> tuple[list[dict[str, Any]], list[ValidationResult]]:
    valid_docs: list[dict[str, Any]] = []
    invalid_results: list[ValidationResult] = []

    for doc in docs:
        result = validate_document(doc)
        if result.is_valid:
            valid_docs.append(doc)
        else:
            invalid_results.append(result)

    return valid_docs, invalid_results


def write_quarantine(
    invalid_results: Iterable[ValidationResult],
    output_dir: Path = DEFAULT_QUARANTINE_DIR,
) -> list[Path]:
    """Ghi document lỗi + lý do vào quarantine."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for result in invalid_results:
        issues = asdict(result) if hasattr(result, "__dataclass_fields__") else result
        payload = {
            "document_id": result.document_id,
            "is_valid": result.is_valid,
            "issues": [asdict(i) for i in result.issues],
        }
        fpath = output_dir / f"quarantine_{result.document_id}.json"
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        paths.append(fpath)

    return paths


def write_report(
    report_md: str,
    output_path: Path = DEFAULT_REPORT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    return output_path


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    quarantine_dir: Path = DEFAULT_QUARANTINE_DIR,
    groups_path: Path = DEFAULT_GROUPS_PATH,
    drop_invalid: bool = True,
) -> dict[str, Any]:
    docs = _read_docs(input_dir)
    valid_docs, invalid_results = validate_docs(docs, drop_invalid=drop_invalid)

    quarantine_paths: list[Path] = []
    if invalid_results and drop_invalid:
        quarantine_paths = write_quarantine(invalid_results, quarantine_dir)

    dedup_group_ids = _read_dedup_groups(groups_path)
    report = build_report(valid_docs, duplicate_group_ids=dedup_group_ids)
    report_md = render_markdown(report)
    write_report(report_md, report_path)

    return {
        "total": len(docs),
        "valid": len(valid_docs),
        "invalid": len(invalid_results),
        "quarantine_files": len(quarantine_paths),
        "report_path": str(report_path),
        "passed_missing": report.passed_missing,
        "passed_duplicate": report.passed_duplicate,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Validate cleaned hotel documents")
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--report", type=str, default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--quarantine-dir", type=str, default=str(DEFAULT_QUARANTINE_DIR))
    parser.add_argument("--keep-invalid", action="store_true", help="Don't quarantine invalid docs")
    args = parser.parse_args()

    summary = run(
        Path(args.input_dir),
        report_path=Path(args.report),
        quarantine_dir=Path(args.quarantine_dir),
        drop_invalid=not args.keep_invalid,
    )
    print(f"Total: {summary['total']}, Valid: {summary['valid']}, "
          f"Invalid: {summary['invalid']}, Quarantined: {summary['quarantine_files']}")
    print(f"Report: {summary['report_path']}")
    print(f"  Missing rate target: {'Pass ✅' if summary['passed_missing'] else 'Fail ❌'}")
    print(f"  Duplicate rate target: {'Pass ✅' if summary['passed_duplicate'] else 'Fail ❌'}")


if __name__ == "__main__":
    main()
