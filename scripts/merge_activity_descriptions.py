"""Merge filled activity descriptions from CSV into cleaned hotel files."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent

CLEANED_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
CSV_PATH: Path = _PROJECT_ROOT / "data" / "fill_description.txt"


def _merge_text(cut: str, fill: str) -> str:
    if not fill:
        return ""
    fill = fill.strip()
    if fill.startswith("...") or fill.startswith("…"):
        fill = fill[3:].lstrip(",.;: ")
    max_olap = min(len(cut), len(fill))
    for olap in range(max_olap, 0, -1):
        if cut[-olap:] == fill[:olap]:
            return cut + fill[olap:]
    return cut + " " + fill


def run() -> dict:
    # ── Read CSV ──
    rows: list[dict] = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # Build map: activity_id -> filled_description
    fill_map: dict[int, str] = {}
    for row in rows:
        try:
            aid = int(float(row["activity_id"]))
        except (ValueError, TypeError):
            continue
        fill = (row.get("description_fill") or "").strip()
        cut = (row.get("description_cut") or "").strip()
        if fill:
            fill_map[aid] = _merge_text(cut, fill)
        else:
            fill_map[aid] = ""

        # Also handle alt_activity_ids
        alt = (row.get("alt_activity_ids") or "").strip()
        if alt:
            for aid_str in alt.split(","):
                aid_str = aid_str.strip()
                if aid_str:
                    try:
                        alt_aid = int(float(aid_str))
                        fill_map[alt_aid] = fill_map[aid]
                    except (ValueError, TypeError):
                        pass

    # ── Apply to cleaned files ──
    files = sorted(CLEANED_DIR.glob("hotel_*.json"))
    applied = 0
    skipped = 0
    not_found = set(fill_map.keys())

    for fp in files:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        changed = False
        for act in doc.get("activities") or []:
            aid = act.get("activity_id")
            if aid in fill_map:
                new_desc = fill_map[aid]
                act["description"] = new_desc
                if aid in not_found:
                    not_found.remove(aid)
                changed = True
                applied += 1
        if changed:
            fp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            skipped += 1

    return {
        "total_rows": len(rows),
        "mapped_ids": len(fill_map),
        "applied": applied,
        "files_updated": len(files) - skipped,
        "files_skipped": skipped,
        "not_found": list(not_found),
    }


def main() -> None:
    t0 = time.time()
    result = run()
    elapsed = time.time() - t0
    print(f"=== Merge complete ({elapsed:.0f}s) ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
