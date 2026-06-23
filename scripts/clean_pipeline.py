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
from ingestion.cleaning.text_normalizer import normalize_text
from ingestion.cleaning.html_stripper import strip_html
from ingestion.cleaning.occupancy_imputer import impute_max_occupancy
from ingestion.cleaning.price_mocker import mock_room_prices
from ingestion.cleaning.name_normalizer import normalize_hotel_name
from ingestion.cleaning.nearby_filter import filter_nearby_places
from ingestion.cleaning.brand_normalizer import extract_brand

DEFAULT_INPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_OUTPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"
_REVIEWS_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "raw" / "reviews"

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


def _clean_room(room: dict[str, Any], hotel: dict[str, Any]) -> dict[str, Any]:
    cr = dict(room)
    for fk in ("name", "bed_type", "room_view"):
        if fk in cr and isinstance(cr[fk], str):
            cr[fk] = _clean_str(cr[fk])
    if "room_amenities" in cr and isinstance(cr["room_amenities"], list):
        cr["room_amenities"] = normalize_amenities(cr["room_amenities"])
    cr["max_occupancy"] = impute_max_occupancy(cr)
    prices = mock_room_prices(cr, hotel)
    cr["price_per_night"] = prices["price_per_night"]
    cr["original_price"] = prices["original_price"]
    if "price" in cr:
        del cr["price"]
    return cr


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
                        cleaned_comments.append(nc)
                    else:
                        cleaned_comments.append(c)
                cleaned[key]["sample_comments"] = cleaned_comments

        # name — chuẩn hóa tên KS (bỏ ngoặc EN + đuôi marketing). Gắn name + name_original +
        # name_alt (DA09 #1). Giữ gốc để audit + alias search; KHÔNG vứt dữ liệu.
        elif key == "name" and isinstance(val, str):
            nm = normalize_hotel_name(val)
            cleaned["name"] = nm["name"]
            cleaned["name_original"] = nm["name_original"]
            if nm["name_alt"]:
                cleaned["name_alt"] = nm["name_alt"]
            # brand (chuỗi KS) trích từ name + name_alt -> field filter. None nếu không thuộc brand
            # đã biết. Query "khách sạn thuộc Vinpearl" lọc theo field này. (DA09: query brand.)
            brand = extract_brand(nm["name"], nm["name_alt"])
            if brand:
                cleaned["brand"] = brand

        # nearby_places — loại điểm quá xa theo loại (DA09 #2). Sân bay/ga ngoại lệ (xa hợp lệ).
        elif key == "nearby_places" and isinstance(val, list):
            cleaned[key] = filter_nearby_places(val)

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
                    cr = _clean_room(room, doc)
                    cleaned[key].append(cr)
                else:
                    cleaned[key].append(room)

        # room_grid → clean nested rooms too (duplicate from raw)
        elif key == "room_grid" and isinstance(val, dict):
            cleaned[key] = dict(val)
            grid_rooms = cleaned[key].get("rooms")
            if isinstance(grid_rooms, list):
                cleaned[key]["rooms"] = [_clean_room(r, doc) if isinstance(r, dict) else r for r in grid_rooms]
            # also pass through cheapest_price, etc.

        # Strings that aren't HTML (just normalize, skip strip_html)
        elif isinstance(val, str):
            cleaned[key] = normalize_text(val)

        # Everything else: pass through
        else:
            cleaned[key] = val

    return cleaned


def _merge_reviews_into_doc(doc: dict) -> dict:
    """Inject review crawl data into doc.reviews_detail.sample_comments.

    Dedup key: (reviewer_name, date) — existing comments from hotel detail
    crawl don't have review_id, so fallback to name+date.
    """
    hotel_id = doc.get("id") or doc.get("hotel_id")
    if hotel_id is None:
        return doc

    review_path = _REVIEWS_DIR / f"hotel_{hotel_id}_reviews.json"
    if not review_path.exists():
        return doc

    with open(review_path, encoding="utf-8") as f:
        review_data = json.load(f)

    new_reviews = review_data.get("reviews", [])
    if not new_reviews:
        return doc

    seen_by_id: set = set()
    seen_by_fallback: set = set()
    for r in new_reviews:
        rid = r.get("review_id")
        if rid is not None:
            seen_by_id.add(rid)
        seen_by_fallback.add((r.get("reviewer_name"), r.get("date")))

    existing = doc.get("reviews_detail", {}).get("sample_comments", [])
    kept = []
    for c in existing:
        rid = c.get("review_id")
        if rid is not None and rid in seen_by_id:
            continue
        if (c.get("reviewer_name"), c.get("date")) in seen_by_fallback:
            continue
        kept.append(c)

    merged = kept + new_reviews

    if "reviews_detail" not in doc:
        doc["reviews_detail"] = {}
    doc["reviews_detail"]["sample_comments"] = merged
    return doc


def read_raw(input_dir: Path = DEFAULT_INPUT_DIR) -> Iterable[dict[str, Any]]:
    json_files = sorted(input_dir.rglob("*.json"))
    for fpath in json_files:
        # Skip aggregated files (non-hotel)
        if fpath.name in ("hotels_detail.json", "hotels_list.json", "failed.json"):
            continue
        # Skip raw review files (loaded on-demand via _merge_reviews_into_doc)
        if fpath.parent.name == "reviews" or fpath.name.endswith("_reviews.json"):
            continue
        with open(fpath, encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            print(f"WARN: skipping non-dict file {fpath.name} ({type(doc).__name__})")
            continue
        yield _merge_reviews_into_doc(doc)


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
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for idx, doc in enumerate(read_raw(input_dir), 1):
        doc_id = doc.get("id") or doc.get("hotel_id", "unknown")
        import time
        t0 = time.time()
        cleaned = clean_document(doc)
        elapsed = time.time() - t0
        fname = f"hotel_{doc_id}.json"
        fpath = output_dir / fname
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        paths.append(fpath)
        n_reviews = len(cleaned.get("reviews_detail", {}).get("sample_comments", []))
        print(f"[{idx}] hotel_{doc_id}: {elapsed:.0f}s - {n_reviews} reviews", flush=True)
    print(f"Cleaned {len(paths)} documents")
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
