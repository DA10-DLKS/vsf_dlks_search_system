"""Generate amenity frequency table across all cleaned hotels."""

import json
import glob
import csv
import sys
import os
from collections import Counter

AMENITY_FIELDS = ["amenities", "amenities_general", "amenities_leisure", "amenities_dining"]


def run(input_dir: str = "data/cleaned", output: str = "docs/amenity_frequency.tsv") -> None:
    hotels = sorted(glob.glob(os.path.join(input_dir, "hotel_*.json")))
    if not hotels:
        print(f"No hotel files found in {input_dir}")
        sys.exit(1)

    total_hotels = len(hotels)
    occ_counter: Counter[str] = Counter()
    hotel_counter: Counter[str] = Counter()
    room_count = 0

    for fp in hotels:
        with open(fp) as f:
            doc = json.load(f)
        seen_in_hotel: set[str] = set()
        for field in AMENITY_FIELDS:
            for a in doc.get(field, []):
                occ_counter[a] += 1
                seen_in_hotel.add(a)
        for room in doc.get("rooms", []):
            room_count += 1
            for a in room.get("room_amenities", []):
                occ_counter[a] += 1
                seen_in_hotel.add(a)
        for a in seen_in_hotel:
            hotel_counter[a] += 1

    sorted_items = sorted(
        hotel_counter.items(), key=lambda x: (-x[1], -occ_counter[x[0]], x[0])
    )

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["amenity", "hotels", "occurrences", "pct_hotels"])
        for name, hotel_cnt in sorted_items:
            pct = round(hotel_cnt / total_hotels * 100, 1)
            writer.writerow([name, hotel_cnt, occ_counter[name], f"{pct}%"])

    print(f"Wrote {len(sorted_items)} amenities to {output}")
    print(f"  Hotels: {total_hotels}, Rooms: {room_count}")
    print(f"  Unique amenities: {len(sorted_items)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build amenity frequency table")
    parser.add_argument("--input-dir", default="data/cleaned")
    parser.add_argument("--output", default="docs/amenity_frequency.tsv")
    args = parser.parse_args()
    run(args.input_dir, args.output)
