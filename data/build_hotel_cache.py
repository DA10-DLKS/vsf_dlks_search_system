"""build_hotel_cache.py — Build hotel_detail_cache.json from cleaned hotel files.

Extracts only fields needed by the frontend schema (HotelMetadata) to produce a
~9MB single-file cache instead of shipping 161MB of 520 individual cleaned files.

Usage:
    python data/build_hotel_cache.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

CLEANED_DIR = os.path.join(os.path.dirname(__file__), "cleaned")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "hotel_detail_cache.json")

# Fields to keep for frontend HotelMetadata
HOTEL_FIELDS = {
    "hotel_id", "name", "name_original", "name_alt", "brand",
    "accommodation_type", "star_rating", "is_luxury",
    "review_score", "review_count",
    "address", "city", "province", "district", "latitude", "longitude",
    "description",
    "check_in_from", "check_out_until",
    "number_of_rooms", "number_of_floors", "year_built",
    "source_url", "suitable_for",
}

# Room fields to keep (trimmed — no room image URLs)
ROOM_FIELDS = {
    "room_type_id", "name", "name_en", "room_size", "size_sqm",
    "max_occupancy", "bed_type", "room_view", "is_sold_out",
    "facilities", "room_amenities",
    "review_score", "price_per_night", "original_price",
}

MAX_ROOMS = 5
MAX_IMAGES = 5
MAX_NEARBY = 5
MAX_ACTIVITIES = 5
MAX_DESC_LEN = 500


def build_cache() -> dict:
    cache: dict[str, dict] = {}
    pattern = os.path.join(CLEANED_DIR, "hotel_*.json")
    files = sorted(glob.glob(pattern))
    print(f"Processing {len(files)} hotel files...", file=sys.stderr)

    for path in files:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)

        key = str(raw.get("hotel_id"))
        if not key:
            continue

        entry = {k: raw[k] for k in HOTEL_FIELDS if k in raw}

        # Trim rooms
        rooms = raw.get("rooms") or []
        # Sort rooms by price ascending so price_from/min/max are correct
        rooms_sorted = sorted(
            rooms,
            key=lambda r: r.get("price_per_night") or 0,
        )
        entry["rooms"] = []
        for r in rooms_sorted[:MAX_ROOMS]:
            sr = {k: r[k] for k in ROOM_FIELDS if k in r}
            entry["rooms"].append(sr)

        # Add price_from for sorting / display
        prices = [r.get("price_per_night") for r in entry["rooms"] if r.get("price_per_night")]
        entry["price_from"] = min(prices) if prices else None

        # Trim images
        images = raw.get("images") or raw.get("image_urls") or []
        entry["images"] = images[:MAX_IMAGES]

        # Trim nearby_places
        nearby = raw.get("nearby_places") or []
        entry["nearby_places"] = nearby[:MAX_NEARBY]

        # Trim activities
        activities = raw.get("activities") or []
        entry["activities"] = activities[:MAX_ACTIVITIES]

        # Trim description
        desc = entry.get("description") or ""
        if len(desc) > MAX_DESC_LEN:
            entry["description"] = desc[:MAX_DESC_LEN]

        # Useful info (check-in/out policies)
        entry["useful_info"] = raw.get("useful_info")
        # Amenities (from cleaned — already a list of strings)
        entry["amenities"] = raw.get("amenities") or []
        # Reviews detail (keep only rating breakdown, trim full text)
        rd = raw.get("reviews_detail")
        if isinstance(rd, dict):
            entry["reviews_detail"] = {
                k: v for k, v in rd.items()
                if isinstance(v, (int, float, dict))
            }

        cache[key] = entry

    return cache


def main():
    cache = build_cache()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=None, separators=(",", ":"))
    size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"Done: {OUTPUT_PATH} ({len(cache)} hotels, {size_mb:.1f}MB)", file=sys.stderr)


if __name__ == "__main__":
    main()
