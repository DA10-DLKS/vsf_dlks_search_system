"""Entry point: clean → dedup → validate → PostgreSQL (Layer 2).

Luồng:
    data/raw/    ──▶  clean   ──▶  data/cleaned/
    data/cleaned/ ──▶  dedup   ──▶  data/cleaned/ (in-place) + data/dedup_groups.json
    data/cleaned/ ──▶  validate ──▶  data_quality_report.md (+ quarantine nếu có lỗi)
    data/cleaned/ ──▶  db      ──▶  PostgreSQL

Đầu ra cuối: data/cleaned/*.json, data_quality_report.md, PostgreSQL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.clean_pipeline import run as run_clean
from scripts.dedup_pipeline import run as run_dedup
from scripts.validation_pipeline import run as run_validate
from scripts.export_db import run as run_db

DEFAULT_RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"
DEFAULT_CLEANED_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_GROUPS_PATH: Path = _PROJECT_ROOT / "data" / "dedup_groups.json"
DEFAULT_REPORT_PATH: Path = _PROJECT_ROOT / "docs" / "data_quality_report.md"
DEFAULT_QUARANTINE_DIR: Path = _PROJECT_ROOT / "data" / "quarantine"


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    cleaned_dir: Path = DEFAULT_CLEANED_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    skip_clean: bool = False,
    skip_dedup: bool = False,
    skip_validate: bool = False,
    skip_db: bool = False,
) -> dict[str, int | str | bool]:
    summary: dict[str, int | str | bool] = {}

    if not skip_clean:
        cleaned = run_clean(raw_dir, cleaned_dir)
        summary["cleaned"] = len(cleaned)
    else:
        summary["cleaned"] = summary.get("total", 0)

    if not skip_dedup:
        dedup_result = run_dedup(
            cleaned_dir,
            output_dir=cleaned_dir,
            groups_path=DEFAULT_GROUPS_PATH,
        )
        summary.update(dedup_result)
    else:
        summary.update({"total": 0, "kept": 0, "removed": 0, "groups": 0})

    if not skip_validate:
        validate_result = run_validate(
            cleaned_dir,
            report_path=report_path,
            quarantine_dir=DEFAULT_QUARANTINE_DIR,
            groups_path=DEFAULT_GROUPS_PATH,
        )
        summary["validated"] = validate_result.get("valid", 0)
        summary["invalid"] = validate_result.get("invalid", 0)
        summary["passed_missing"] = validate_result.get("passed_missing", False)
        summary["passed_duplicate"] = validate_result.get("passed_duplicate", False)
    else:
        summary["validated"] = 0
        summary["passed_missing"] = False
        summary["passed_duplicate"] = False

    if not skip_db:
        db_result = run_db(cleaned_dir)
        summary["db_hotels"] = db_result.get("hotels", 0)
        summary["db_rooms"] = db_result.get("rooms", 0)
        summary["db_nearby"] = db_result.get("nearby_places", 0)
        summary["db_activities"] = db_result.get("activities", 0)

    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Full ingestion pipeline: clean → dedup → validate → PostgreSQL"
    )
    parser.add_argument("--raw-dir", type=str, default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--cleaned-dir", type=str, default=str(DEFAULT_CLEANED_DIR))
    parser.add_argument("--report", type=str, default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-dedup", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--skip-db", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    summary = run(
        raw_dir=Path(args.raw_dir),
        cleaned_dir=Path(args.cleaned_dir),
        report_path=Path(args.report),
        skip_clean=args.skip_clean,
        skip_dedup=args.skip_dedup,
        skip_validate=args.skip_validate,
        skip_db=args.skip_db,
    )
    print("=== Ingestion Pipeline Complete ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
