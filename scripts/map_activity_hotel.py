"""Map crawled activities -> nearest hotel by Haversine distance.

Usage:
    python scripts/map_activity_hotel.py                                # map all activities -> nearest hotel
    python scripts/map_activity_hotel.py --max-distance 30              # chỉ map trong bán kính 30km
    python scripts/map_activity_hotel.py --output data/enriched/        # output dir
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

ACTIVITIES_DIR = _PROJECT_ROOT / "data" / "raw" / "activities"
HOTELS_DIR = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "raw" / "activities"
MAX_DISTANCE_KM = 50.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_hotels(hotels_dir: Path) -> list[dict]:
    hotels = []
    for fp in sorted(hotels_dir.glob("hotel_*.json")):
        with open(fp) as f:
            doc = json.load(f)
        lat = doc.get("latitude")
        lng = doc.get("longitude")
        if lat is not None and lng is not None:
            hotels.append({
                "id": doc.get("hotel_id") or doc.get("id"),
                "name": doc.get("name", ""),
                "latitude": lat,
                "longitude": lng,
            })
    return hotels


def load_activities(activities_dir: Path) -> list[dict]:
    activities = []
    for fp in sorted(activities_dir.glob("*.json")):
        if fp.name.startswith("_"):
            continue
        with open(fp) as f:
            data = json.load(f)
        for act in data.get("activities", []):
            if act.get("latitude") is not None and act.get("longitude") is not None:
                activities.append(act)
    return activities


def nearest_hotel(act_lat: float, act_lng: float,
                  hotels: list[dict]) -> tuple[int | None, float | None]:
    best_id = None
    best_dist = float("inf")
    for h in hotels:
        dist = haversine_km(act_lat, act_lng, h["latitude"], h["longitude"])
        if dist < best_dist:
            best_dist = dist
            best_id = h["id"]
    if best_dist <= MAX_DISTANCE_KM:
        return best_id, round(best_dist, 2)
    return None, None


def run(hotels_dir: Path = HOTELS_DIR,
        activities_dir: Path = ACTIVITIES_DIR,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        max_distance: float = MAX_DISTANCE_KM) -> dict[str, int]:
    global MAX_DISTANCE_KM
    MAX_DISTANCE_KM = max_distance

    print("Loading hotels...")
    hotels = load_hotels(hotels_dir)
    print(f"  {len(hotels)} hotels (with lat/lng)")

    print("Loading activities...")
    all_activities = load_activities(activities_dir)
    print(f"  {len(all_activities)} activities (with lat/lng)")

    if not hotels or not all_activities:
        print("[!] No hotels or activities to map")
        return {"hotels": len(hotels), "activities": len(all_activities),
                "mapped": 0, "unmapped": 0}

    mapped = 0
    unmapped = 0
    matched = []

    for act in all_activities:
        h_id, dist = nearest_hotel(
            act["latitude"], act["longitude"], hotels)
        act["hotel_id"] = h_id
        act["distance_to_hotel_km"] = dist
        if h_id is not None:
            mapped += 1
            matched.append(act)
        else:
            unmapped += 1

    # Save individual province files with hotel_id enriched
    # Group activities back by province
    by_province: dict[str, list[dict]] = {}
    for act in all_activities:
        slug = act.get("province_slug", "unknown")
        by_province.setdefault(slug, []).append(act)

    for slug, acts in by_province.items():
        province_info = acts[0]
        out = {
            "province": province_info.get("province"),
            "province_slug": slug,
            "region": province_info.get("region"),
            "mapped_at": datetime.now(timezone.utc).isoformat(),
            "activity_count": len(acts),
            "activities": acts,
        }
        out_path = output_dir / f"{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    # Write summary
    summary = {
        "hotels": len(hotels),
        "activities_total": len(all_activities),
        "mapped": mapped,
        "unmapped": unmapped,
        "max_distance_km": max_distance,
    }
    summary_path = activities_dir / "_mapping_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Show distance distribution
    if matched:
        distances = [a["distance_to_hotel_km"] for a in matched if a["distance_to_hotel_km"] is not None]
        if distances:
            print(f"\nDistance distribution (km):")
            print(f"  min: {min(distances):.2f}")
            print(f"  avg: {sum(distances) / len(distances):.2f}")
            print(f"  max: {max(distances):.2f}")
            print(f"  median: {sorted(distances)[len(distances)//2]:.2f}")

    print(f"\nSummary:")
    print(f"  Total activities: {len(all_activities)}")
    print(f"  Mapped to hotel:  {mapped}")
    print(f"  Unmapped (> {max_distance}km): {unmapped}")

    return summary


def _parse_args(argv: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Map activities to nearest hotel")
    parser.add_argument("--max-distance", type=float, default=MAX_DISTANCE_KM,
                        help=f"Max distance in km (default: {MAX_DISTANCE_KM})")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help="Output directory for enriched files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    run(max_distance=args.max_distance,
        output_dir=Path(args.output))


if __name__ == "__main__":
    main()
