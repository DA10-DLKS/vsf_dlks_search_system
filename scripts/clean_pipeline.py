"""Sprint 2 pipeline: clean raw documents và ghi ra data/cleaned/.

Luồng:
    data/raw/*.json  ──▶  strip HTML  ──▶  normalize text  ──▶  data/cleaned/*.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

# Ensure project root is on path
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ingestion.cleaning.html_stripper import strip_html
from ingestion.cleaning.text_normalizer import normalize_text
from ingestion.cleaning.amenity_normalizer import normalize_amenities, normalize_amenities_batch
from ingestion.cleaning.translator import translate_to_vi

DEFAULT_INPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_OUTPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"

TEXT_FIELDS_TO_CLEAN: list[str] = [
    "description",
    "description_short",
    "embedding_text",
    "address",
]

NESTED_TEXT_FIELDS: dict[str, list[str]] = {
    "secondary": ["description_full", "hotel_policy"],
    "faq": ["question", "answer"],
    "activities": ["title", "description"],
    "useful_info": None,  # all str values
}


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str) and not val.strip():
        return None
    if isinstance(val, str):
        cleaned = strip_html(val).text
        cleaned = normalize_text(cleaned)
        return cleaned
    return str(val)


def clean_document(doc: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for key, val in doc.items():
        # Top-level text fields
        if key in TEXT_FIELDS_TO_CLEAN and isinstance(val, str):
            cleaned[key] = _clean_str(val)

        # Nested text fields (dict)
        elif key in NESTED_TEXT_FIELDS and isinstance(val, dict):
            cleaned[key] = {}
            fields = NESTED_TEXT_FIELDS[key]
            if fields:
                for sub_key, sub_val in val.items():
                    if sub_key in fields and isinstance(sub_val, str):
                        cleaned[key][sub_key] = _clean_str(sub_val)
                    else:
                        cleaned[key][sub_key] = sub_val
            else:
                # Clean all string values in the dict
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, str):
                        cleaned[key][sub_key] = _clean_str(sub_val)
                    else:
                        cleaned[key][sub_key] = sub_val

        # faq list
        elif key == "faq" and isinstance(val, list):
            cleaned[key] = []
            for item in val:
                if isinstance(item, dict):
                    new_item = {}
                    for fk, fv in item.items():
                        if fk in ("question", "answer") and isinstance(fv, str):
                            new_item[fk] = _clean_str(fv)
                        else:
                            new_item[fk] = fv
                    cleaned[key].append(new_item)
                else:
                    cleaned[key].append(item)

        # activities list
        elif key == "activities" and isinstance(val, list):
            cleaned[key] = []
            for item in val:
                if isinstance(item, dict):
                    new_item = {}
                    for fk, fv in item.items():
                        if fk in ("title", "description") and isinstance(fv, str):
                            new_item[fk] = _clean_str(fv)
                        else:
                            new_item[fk] = fv
                    cleaned[key].append(new_item)
                else:
                    cleaned[key].append(item)

        # reviews_detail → clean nested strings + sample_comments
        elif key == "reviews_detail" and isinstance(val, dict):
            cleaned[key] = {}
            for sub_key, sub_val in val.items():
                if isinstance(sub_val, str):
                    cleaned[key][sub_key] = _clean_str(sub_val)
                else:
                    cleaned[key][sub_key] = sub_val
            comments = val.get("sample_comments")
            if isinstance(comments, list):
                cleaned_comments = []
                for c in comments:
                    if isinstance(c, dict):
                        nc = dict(c)
                        for fk in ("text", "title", "positives", "negatives", "response"):
                            if fk in nc and isinstance(nc[fk], str):
                                nc[fk] = _clean_str(nc[fk])
                                nc[fk] = translate_to_vi(nc[fk])
                        cleaned_comments.append(nc)
                    else:
                        cleaned_comments.append(c)
                cleaned[key]["sample_comments"] = cleaned_comments

        # amenities — normalize + merge near-duplicates
        elif key == "amenities" and isinstance(val, list):
            cleaned[key] = normalize_amenities(val)

        # amenities_general / _leisure / _dining — subsets chưa được normalize
        elif key in ("amenities_general", "amenities_leisure", "amenities_dining") and isinstance(val, list):
            cleaned[key] = normalize_amenities(val)

        # amenity_groups — normalize each group
        elif key == "amenity_groups" and isinstance(val, dict):
            cleaned[key] = {}
            for group_name, items in val.items():
                if isinstance(items, list):
                    cleaned[key][group_name] = normalize_amenities(items)
                else:
                    cleaned[key][group_name] = items

        # rooms[] → clean room_amenities descriptions etc
        elif key == "rooms" and isinstance(val, list):
            cleaned[key] = []
            for room in val:
                if isinstance(room, dict):
                    cr = dict(room)
                    for fk in ("name", "bed_type", "room_view"):
                        if fk in cr and isinstance(cr[fk], str):
                            cr[fk] = _clean_str(cr[fk])
                    if "room_amenities" in cr and isinstance(cr["room_amenities"], list):
                        cr["room_amenities"] = normalize_amenities(cr["room_amenities"])
                    cleaned[key].append(cr)
                else:
                    cleaned[key].append(room)

        # Strings that aren't HTML (just normalize, skip strip_html)
        elif isinstance(val, str):
            cleaned[key] = normalize_text(val)

        # Everything else: pass through
        else:
            cleaned[key] = val

    return cleaned


def read_raw(input_dir: Path = DEFAULT_INPUT_DIR) -> Iterable[dict[str, Any]]:
    json_files = sorted(input_dir.rglob("*.json"))
    for fpath in json_files:
        # Skip aggregated files (non-hotel)
        if fpath.name in ("hotels_detail.json", "hotels_list.json", "failed.json"):
            continue
        with open(fpath, encoding="utf-8") as f:
            yield json.load(f)


def write_cleaned(
    docs: Iterable[dict[str, Any]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for doc in docs:
        doc_id = doc.get("id") or doc.get("hotel_id", "unknown")
        fname = f"hotel_{doc_id}_cleaned.json"
        fpath = output_dir / fname
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        paths.append(fpath)
    return paths


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    paths = []
    for doc in read_raw(input_dir):
        cleaned = clean_document(doc)
        doc_id = cleaned.get("id") or cleaned.get("hotel_id", "unknown")
        fname = f"hotel_{doc_id}.json"
        fpath = output_dir / fname
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        paths.append(fpath)
    return paths


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Clean raw hotel documents")
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = run(Path(args.input_dir), Path(args.output_dir))
    print(f"Cleaned {len(paths)} documents → {args.output_dir}")


if __name__ == "__main__":
    main()
