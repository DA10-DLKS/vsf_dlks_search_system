"""Sprint 2 pipeline: khử trùng lặp cleaned documents (near-duplicate).

Luồng:
    data/cleaned/*.json  ──▶  MinHash + LSH  ──▶  bỏ trùng  ──▶  data/cleaned/ (in-place)
                                                       │
                                                       └─▶  data/dedup_groups.json
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

from ingestion.deduplication.minhash import DuplicateGroup, find_duplicates, dedup_documents

DEFAULT_INPUT_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_OUTPUT_DIR: Path = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_GROUPS_PATH: Path = _PROJECT_ROOT / "data" / "dedup_groups.json"


def read_docs(input_dir: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for fpath in sorted(input_dir.glob("*.json")):
        with open(fpath, encoding="utf-8") as f:
            docs.append(json.load(f))
    return docs


def write_docs(docs: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Xoá file cũ trước khi ghi đè
    for fpath in output_dir.glob("*.json"):
        fpath.unlink()
    paths: list[Path] = []
    for doc in docs:
        doc_id = doc.get("id") or doc.get("hotel_id", "unknown")
        fname = f"hotel_{doc_id}.json"
        fpath = output_dir / fname
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        paths.append(fpath)
    return paths


def find_duplicate_groups(
    docs: list[dict[str, Any]],
    *,
    text_field: str = "embedding_text",
    id_field: str = "hotel_id",
) -> list[DuplicateGroup]:
    """Trả về danh sách DuplicateGroup."""
    id_map: dict[str, dict] = {}
    for doc in docs:
        doc_id = str(doc.get(id_field) or doc.get("id") or "")
        if not doc_id:
            continue
        text = doc.get(text_field) or doc.get("description", "") or ""
        id_map[doc_id] = doc

    items = list(id_map.items())
    return find_duplicates(
        [(did, doc.get(text_field) or doc.get("description", "") or "") for did, doc in items],
    )


def write_groups(
    groups: Iterable[DuplicateGroup],
    output_path: Path = DEFAULT_GROUPS_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(g) for g in groups]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_path


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path | None = None,
    *,
    groups_path: Path = DEFAULT_GROUPS_PATH,
) -> dict[str, int]:
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    docs = read_docs(input_dir)
    total = len(docs)

    groups = find_duplicate_groups(docs)
    write_groups(groups, groups_path)

    # Remove duplicates (keep first per group)
    to_remove: set[str] = set()
    for g in groups:
        for doc_id in g.document_ids[1:]:
            to_remove.add(doc_id)

    kept = [d for d in docs if str(d.get("hotel_id") or d.get("id")) not in to_remove]
    write_docs(kept, output_dir)

    return {
        "total": total,
        "kept": len(kept),
        "removed": len(to_remove),
        "groups": len(groups),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Deduplicate cleaned hotel documents")
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--groups-path", type=str, default=str(DEFAULT_GROUPS_PATH))
    args = parser.parse_args()
    summary = run(
        Path(args.input_dir),
        output_dir=Path(args.output_dir),
        groups_path=Path(args.groups_path),
    )
    print(f"Total: {summary['total']}, Kept: {summary['kept']}, "
          f"Removed: {summary['removed']}, Groups: {summary['groups']}")


if __name__ == "__main__":
    main()
