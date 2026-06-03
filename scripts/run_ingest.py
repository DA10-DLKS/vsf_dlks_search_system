"""Entry point: clean / validate / dedup raw data (Layer 2).

Compose 3 pipeline con:
    clean_pipeline  →  validation_pipeline  →  dedup_pipeline

Đầu vào mặc định:  data/raw/
Đầu ra:             data/cleaned/, data_quality_report.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

# TODO(hieudm): Import các pipeline thật khi đã implement:
# from scripts.clean_pipeline import run as run_clean
# from scripts.validation_pipeline import run as run_validate
# from scripts.dedup_pipeline import run as run_dedup

DEFAULT_RAW_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_CLEANED_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"
DEFAULT_REPORT_PATH: Path = Path(__file__).resolve().parents[1] / "data_quality_report.md"


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    cleaned_dir: Path = DEFAULT_CLEANED_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    skip_clean: bool = False,
    skip_validate: bool = False,
    skip_dedup: bool = False,
) -> dict[str, int]:
    """Chạy full ingestion pipeline. Trả về summary counters."""
    # TODO(hieudm): orchestrate 3 bước
    #   1. run_clean(raw_dir, cleaned_dir)  nếu không skip_clean
    #   2. run_validate(cleaned_dir, report_path=...)  nếu không skip_validate
    #   3. run_dedup(cleaned_dir)  nếu không skip_dedup
    raise NotImplementedError("run_ingest.run not implemented")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI: --raw-dir, --cleaned-dir, --report, --skip-*."""
    # TODO(hieudm): implement argparse
    raise NotImplementedError("_parse_args not implemented")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    summary = run(
        raw_dir=args.raw_dir,
        cleaned_dir=args.cleaned_dir,
        report_path=args.report,
        skip_clean=args.skip_clean,
        skip_validate=args.skip_validate,
        skip_dedup=args.skip_dedup,
    )
    # TODO(hieudm): log summary bằng structlog (đã có requirements.txt:34)
    raise NotImplementedError("run_ingest.main not implemented")


if __name__ == "__main__":
    main()
