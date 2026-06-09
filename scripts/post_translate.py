"""Post-processing: translate non-Vietnamese texts via translator.py.

Usage:
    python scripts/post_translate.py [--cleaned-dir data/cleaned] [--workers 6]
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ingestion.cleaning.translator import translate_texts, REVIEW_TEXT_FIELDS

DEFAULT_CLEANED_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"


def _collect_refs(doc: dict, fp: Path) -> list[tuple[Path, list, str]]:
    refs: list[tuple[Path, list, str]] = []

    for ai, act in enumerate(doc.get("activities") or []):
        if not isinstance(act, dict):
            continue
        for fk in ("title", "description"):
            txt = act.get(fk)
            if isinstance(txt, str) and txt.strip():
                refs.append((fp, ["activities", ai, fk], txt.strip()))

    for ci, c in enumerate(doc.get("reviews_detail", {}).get("sample_comments") or []):
        if not isinstance(c, dict):
            continue
        for fk in REVIEW_TEXT_FIELDS:
            txt = c.get(fk)
            if isinstance(txt, str) and txt.strip():
                refs.append((fp, ["reviews_detail", "sample_comments", ci, fk], txt.strip()))

    return refs


def _set_by_path(doc: dict, path: list, value: str) -> None:
    obj = doc
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def run(cleaned_dir: Path = DEFAULT_CLEANED_DIR, workers: int = 6) -> dict:
    t0 = time.time()
    files = sorted(cleaned_dir.glob("hotel_*.json"))
    if not files:
        return {"files": 0, "texts_translated": 0, "elapsed": 0}

    # ── Phase 1: collect refs + texts ──
    print(f"Phase 1: scanning {len(files)} files...", flush=True)
    all_refs: list[tuple[Path, list, str]] = []
    text_set: set[str] = set()

    for fp in files:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        refs = _collect_refs(doc, fp)
        all_refs.extend(refs)
        for _, _, txt in refs:
            text_set.add(txt)

    n_total = len(all_refs)
    n_unique = len(text_set)
    print(f"  refs={n_total}, unique texts={n_unique}", flush=True)

    if not text_set:
        print("Nothing to translate.", flush=True)
        return {"files": len(files), "texts_translated": 0, "elapsed": 0}

    # ── Phase 2: translate via translator.py ──
    print(f"Phase 2: translating {n_unique} unique texts (workers={workers})...", flush=True)
    t1 = time.time()
    translated = translate_texts(list(text_set), workers=workers)
    t2 = time.time()
    print(f"  Translation done in {t2-t1:.0f}s", flush=True)

    # Build translation map
    trans_map: dict[str, str] = {}
    for orig, trans in zip(text_set, translated):
        if orig != trans:
            trans_map[orig] = trans

    # ── Phase 3: apply to files ──
    print(f"Phase 3: applying {len(trans_map)} changes to {len(files)} files...", flush=True)
    file_changes: dict[Path, list[tuple[list, str]]] = {}
    for fp, path, orig in all_refs:
        new_val = trans_map.get(orig)
        if new_val is not None:
            file_changes.setdefault(fp, []).append((path, new_val))

    def _apply(fp: Path, changes: list[tuple[list, str]]) -> int:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        for path, val in changes:
            _set_by_path(doc, path, val)
        fp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(changes)

    applied = 0
    if file_changes:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in as_completed({pool.submit(_apply, fp, ch): fp for fp, ch in file_changes.items()}):
                applied += future.result()

    t3 = time.time()
    return {
        "files": len(files),
        "unique_texts": n_unique,
        "changes": applied,
        "translation_s": round(t2 - t1, 1),
        "apply_s": round(t3 - t2, 1),
        "elapsed": round(t3 - t0, 1),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Translate non-VN texts in cleaned files")
    parser.add_argument("--cleaned-dir", type=str, default=str(DEFAULT_CLEANED_DIR))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    print(f"Post-translate: dir={args.cleaned_dir}, workers={args.workers}")
    result = run(Path(args.cleaned_dir), workers=args.workers)
    print(f"\n=== Done ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
