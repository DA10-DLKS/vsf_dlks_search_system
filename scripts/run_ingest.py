"""Entry point: clean → dedup → validate → translate (Layer 2).

Usage:
    python scripts/run_ingest.py                      # full pipeline
    python scripts/run_ingest.py --skip-clean         # skip cleaning
    python scripts/run_ingest.py --skip-translate     # skip translation

Steps:
    1/4  Cleaning       - strip HTML, normalize text, amenities, impute, mock
    2/4  Deduplication  - MinHash + LSH near-duplicate removal
    3/4  Validation     - schema + quality checks, quarantine
    4/4  Translation    - Google Translate non-Vietnamese texts
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.clean_pipeline import run as run_clean
from scripts.dedup_pipeline import run as run_dedup
from scripts.validation_pipeline import run as run_validate
from scripts.post_translate import run as run_translate

DEFAULT_RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"
DEFAULT_CLEANED_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_GROUPS_PATH: Path = _PROJECT_ROOT / "data" / "dedup_groups.json"
DEFAULT_REPORT_PATH: Path = _PROJECT_ROOT / "docs" / "data_quality_report.md"
DEFAULT_QUARANTINE_DIR: Path = _PROJECT_ROOT / "data" / "quarantine"


def _step_log(step: int, total: int, name: str) -> None:
    print(f"\n=== Step {step}/{total}: {name} ===", flush=True)


def _elapsed(t_start: float) -> str:
    s = time.time() - t_start
    if s >= 60:
        return f"{s / 60:.1f}m"
    return f"{s:.0f}s"


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    cleaned_dir: Path = DEFAULT_CLEANED_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    skip_clean: bool = False,
    skip_dedup: bool = False,
    skip_validate: bool = False,
    skip_translate: bool = False,
    translate_workers: int = 6,
) -> dict[str, object]:
    summary: dict[str, object] = {}
    t_total = time.time()

    # ── Step 1/4: Cleaning ──
    _step_log(1, 4, "Cleaning")
    if not skip_clean:
        t0 = time.time()
        cleaned = run_clean(raw_dir, cleaned_dir)
        summary["cleaned"] = len(cleaned)
        print(f"  Done in {_elapsed(t0)} -> {len(cleaned)} documents", flush=True)
    else:
        summary["cleaned"] = 0
        print("  Skipped", flush=True)

    # ── Step 2/4: Deduplication ──
    _step_log(2, 4, "Deduplication")
    if not skip_dedup:
        t0 = time.time()
        dedup_result = run_dedup(
            cleaned_dir,
            output_dir=cleaned_dir,
            groups_path=DEFAULT_GROUPS_PATH,
        )
        for k, v in dedup_result.items():
            summary[f"dedup_{k}"] = v
        print(f"  Done in {_elapsed(t0)} -> kept {dedup_result.get('kept', 0)} / {dedup_result.get('total', 0)}", flush=True)
    else:
        for k in ("total", "kept", "removed", "groups"):
            summary[f"dedup_{k}"] = 0
        print("  Skipped", flush=True)

    # ── Step 3/4: Validation ──
    _step_log(3, 4, "Validation")
    if not skip_validate:
        t0 = time.time()
        validate_result = run_validate(
            cleaned_dir,
            report_path=report_path,
            quarantine_dir=DEFAULT_QUARANTINE_DIR,
            groups_path=DEFAULT_GROUPS_PATH,
        )
        summary["valid"] = validate_result.get("valid", 0)
        summary["invalid"] = validate_result.get("invalid", 0)
        summary["passed_missing"] = validate_result.get("passed_missing", False)
        summary["passed_duplicate"] = validate_result.get("passed_duplicate", False)
        valid = validate_result.get("valid", 0)
        invalid = validate_result.get("invalid", 0)
        missing_ok = "✅" if validate_result.get("passed_missing") else "❌"
        dup_ok = "✅" if validate_result.get("passed_duplicate") else "❌"
        print(f"  Done in {_elapsed(t0)} -> {valid} valid, {invalid} invalid", flush=True)
        print(f"  Missing rate: {missing_ok} | Duplicate rate: {dup_ok}", flush=True)
    else:
        summary["valid"] = 0
        summary["invalid"] = 0
        summary["passed_missing"] = False
        summary["passed_duplicate"] = False
        print("  Skipped", flush=True)

    # ── Step 4/4: Translation ──
    _step_log(4, 4, "Translation")
    if not skip_translate:
        t0 = time.time()
        trans_result = run_translate(cleaned_dir, workers=translate_workers)
        summary["unique_texts"] = trans_result.get("unique_texts", 0)
        summary["changes"] = trans_result.get("changes", 0)
        summary["translation_s"] = trans_result.get("translation_s", 0)
        print(f"  Done in {_elapsed(t0)} -> {trans_result.get('changes', 0)} changes applied", flush=True)
    else:
        summary["unique_texts"] = 0
        summary["changes"] = 0
        print("  Skipped", flush=True)

    summary["total_s"] = round(time.time() - t_total, 1)
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingestion pipeline: clean + dedup + validate + translate"
    )
    parser.add_argument("--raw-dir", type=str, default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--cleaned-dir", type=str, default=str(DEFAULT_CLEANED_DIR))
    parser.add_argument("--report", type=str, default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--skip-clean", action="store_true", help="Skip cleaning step")
    parser.add_argument("--skip-dedup", action="store_true", help="Skip dedup step")
    parser.add_argument("--skip-validate", action="store_true", help="Skip validation step")
    parser.add_argument("--skip-translate", action="store_true", help="Skip translation step")
    parser.add_argument("--translate-workers", type=int, default=6, help="Workers for translation (default 6)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    t0 = time.time()
    try:
        summary = run(
            raw_dir=Path(args.raw_dir),
            cleaned_dir=Path(args.cleaned_dir),
            report_path=Path(args.report),
            skip_clean=args.skip_clean,
            skip_dedup=args.skip_dedup,
            skip_validate=args.skip_validate,
            skip_translate=args.skip_translate,
            translate_workers=args.translate_workers,
        )
        elapsed = time.time() - t0
        print(f"\n=== Ingestion Pipeline Complete ({elapsed:.0f}s) ===", flush=True)
        for k, v in summary.items():
            print(f"  {k}: {v}", flush=True)
    except KeyboardInterrupt:
        print("\n\n=== Pipeline interrupted by user ===", flush=True)


if __name__ == "__main__":
    main()
