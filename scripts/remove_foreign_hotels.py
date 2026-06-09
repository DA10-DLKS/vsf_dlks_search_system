"""Remove non-Vietnam hotels from the active OTA dataset.

Default mode is dry-run. Use --quarantine to move files out of active data
folders while keeping a recoverable copy. Use --delete only when permanent
removal is explicitly desired.
"""

from __future__ import annotations

import argparse
import json
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
RAW_HOTELS_DIR = PROJECT_ROOT / "data" / "raw" / "hotels"
RAW_REVIEWS_DIR = PROJECT_ROOT / "data" / "raw" / "reviews"
RAW_DETAIL_FILE = PROJECT_ROOT / "data" / "raw" / "hotels_detail.json"
RAW_LIST_FILE = PROJECT_ROOT / "data" / "raw" / "hotels_list.json"
QUARANTINE_ROOT = PROJECT_ROOT / "data" / "quarantine"

ALLOWED_COUNTRIES = {"viet nam", "vietnam", "vn"}


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.replace("_", " ").replace("-", " ").split())


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def hotel_id_from_name(path: Path) -> int | None:
    stem = path.stem
    if not stem.startswith("hotel_"):
        return None
    raw = stem.split("_", 2)[1]
    try:
        return int(raw)
    except ValueError:
        return None


def is_vietnam(record: dict[str, Any]) -> bool:
    country = record.get("country")
    if country is None and isinstance(record.get("address"), dict):
        country = record["address"].get("country")
    return norm_text(country) in ALLOWED_COUNTRIES


def collect_foreign_ids() -> tuple[set[int], dict[str, int], list[dict[str, Any]]]:
    foreign_ids: set[int] = set()
    country_counts: dict[str, int] = {}
    samples: list[dict[str, Any]] = []

    for source_dir in (CLEANED_DIR, RAW_HOTELS_DIR):
        for path in source_dir.glob("*.json"):
            record = read_json(path, {})
            if not isinstance(record, dict):
                continue
            hid = record.get("hotel_id") or hotel_id_from_name(path)
            if hid is None:
                continue
            country = record.get("country")
            if country is None and isinstance(record.get("address"), dict):
                country = record["address"].get("country")
            country_key = str(country or "missing")
            if not is_vietnam(record):
                foreign_ids.add(int(hid))
                country_counts[country_key] = country_counts.get(country_key, 0) + 1
                if len(samples) < 30:
                    samples.append({
                        "hotel_id": int(hid),
                        "name": record.get("name"),
                        "country": country_key,
                        "file": str(path.relative_to(PROJECT_ROOT)),
                    })
    return foreign_ids, country_counts, samples


def related_files(hotel_ids: set[int]) -> list[Path]:
    files: list[Path] = []
    for hid in hotel_ids:
        files.extend(CLEANED_DIR.glob(f"hotel_{hid}.json"))
        files.extend(RAW_HOTELS_DIR.glob(f"hotel_{hid}_*.json"))
        files.extend(RAW_HOTELS_DIR.glob(f"hotel_{hid}.json"))
        files.extend(RAW_REVIEWS_DIR.glob(f"hotel_{hid}_reviews.json"))
    return sorted({p for p in files if p.exists()})


def move_or_delete(paths: list[Path], mode: str, quarantine_dir: Path | None) -> int:
    changed = 0
    for path in paths:
        if not path.exists():
            continue
        if mode == "delete":
            path.unlink()
        elif mode == "quarantine":
            assert quarantine_dir is not None
            target = quarantine_dir / path.relative_to(PROJECT_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
        changed += 1
    return changed


def filter_json_list(path: Path, foreign_ids: set[int], mode: str, quarantine_dir: Path | None) -> int:
    data = read_json(path, [])
    if not isinstance(data, list):
        return 0
    kept = []
    removed = []
    for item in data:
        if isinstance(item, dict) and item.get("hotel_id") in foreign_ids:
            removed.append(item)
        else:
            kept.append(item)
    if not removed or mode == "dry-run":
        return len(removed)
    if mode == "quarantine" and quarantine_dir is not None:
        backup = quarantine_dir / path.relative_to(PROJECT_ROOT)
        write_json(backup, data)
    write_json(path, kept)
    return len(removed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove non-Vietnam hotels from active dataset.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--quarantine", action="store_true", help="Move foreign files to data/quarantine.")
    action.add_argument("--delete", action="store_true", help="Permanently delete foreign files.")
    parser.add_argument("--report", default=None, help="Optional report JSON path.")
    args = parser.parse_args()

    mode = "delete" if args.delete else "quarantine" if args.quarantine else "dry-run"
    foreign_ids, country_counts, samples = collect_foreign_ids()
    files = related_files(foreign_ids)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    quarantine_dir = QUARANTINE_ROOT / f"foreign_hotels_{timestamp}" if mode == "quarantine" else None

    detail_removed = filter_json_list(RAW_DETAIL_FILE, foreign_ids, mode, quarantine_dir)
    list_removed = filter_json_list(RAW_LIST_FILE, foreign_ids, mode, quarantine_dir)
    file_changed = 0 if mode == "dry-run" else move_or_delete(files, mode, quarantine_dir)

    report = {
        "mode": mode,
        "foreign_hotel_count": len(foreign_ids),
        "related_file_count": len(files),
        "files_changed": file_changed,
        "hotels_detail_removed": detail_removed,
        "hotels_list_removed": list_removed,
        "country_counts_from_sources": dict(sorted(country_counts.items())),
        "sample_removed_hotels": samples,
        "quarantine_dir": str(quarantine_dir.relative_to(PROJECT_ROOT)) if quarantine_dir else None,
    }

    report_path = Path(args.report) if args.report else QUARANTINE_ROOT / f"foreign_hotels_report_{timestamp}.json"
    if mode != "dry-run" or args.report:
        write_json(PROJECT_ROOT / report_path if not report_path.is_absolute() else report_path, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
