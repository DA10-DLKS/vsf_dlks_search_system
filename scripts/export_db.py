"""Export cleaned hotel JSON → PostgreSQL.

Usage:
    python scripts/export_db.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from db import SessionLocal, create_tables

DEFAULT_CLEANED_DIR = _PROJECT_ROOT / "data" / "cleaned"


def _safe_list(val: list | None) -> list:
    return val if isinstance(val, list) else []


def _build_amenity_groups(doc: dict) -> dict | None:
    groups = {}
    raw = doc.get("amenity_groups")
    if raw:
        groups["groups"] = raw
    for field in ("amenities_general", "amenities_leisure", "amenities_dining"):
        val = doc.get(field)
        if val:
            groups[field.replace("amenities_", "")] = val
    return groups if groups else None


def _extract_policy_notes(doc: dict) -> list[str]:
    notes = doc.get("policyNotes")
    if notes:
        return notes if isinstance(notes, list) else []
    secondary = doc.get("secondary") or {}
    policy = secondary.get("hotel_policy") or {}
    return policy.get("policyNotes", []) if isinstance(policy, dict) else []


def _clean_price(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        s = s.replace("\u20ab", "").replace("$", "").replace(",", "").strip()
        s = s.replace(".", "")
        try:
            return float(s)
        except (ValueError, TypeError):
            return None
    return None


def _extract_price_amount(price_field) -> float | None:
    if price_field is None:
        return None
    if isinstance(price_field, (int, float)):
        return float(price_field)
    if isinstance(price_field, dict):
        try:
            return float(
                price_field["display"]["perBook"]["total"]["allInclusive"][
                    "chargeTotal"
                ]
            )
        except (KeyError, TypeError, ValueError):
            pass
    return None


def _parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def run(cleaned_dir: Path = DEFAULT_CLEANED_DIR) -> dict[str, int]:
    hotel_files = sorted(cleaned_dir.glob("hotel_*.json"))
    if not hotel_files:
        print(f"No hotel files found in {cleaned_dir}")
        return {"hotels": 0, "rooms": 0, "nearby_places": 0, "activities": 0}

    from db.models import Activity, Hotel, NearbyPlace, Room

    create_tables()

    hotels: list[dict] = []
    rooms: list[dict] = []
    nearby_places: list[dict] = []
    activities: list[dict] = []

    for fp in hotel_files:
        with open(fp) as f:
            doc = json.load(f)

        hid = doc.get("hotel_id") or doc.get("id")

        hotels.append({
            "id": hid,
            "name": doc.get("name"),
            "accommodation_type": doc.get("accommodation_type"),
            "star_rating": doc.get("star_rating"),
            "is_luxury": bool(doc.get("is_luxury", False)),
            "review_score": doc.get("review_score"),
            "review_count": doc.get("review_count", 0),
            "address": doc.get("address"),
            "city": doc.get("city") or doc.get("province"),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
            "description": doc.get("description"),
            "amenities": _safe_list(doc.get("amenities")),
            "amenity_groups": _build_amenity_groups(doc),
            "useful_info": doc.get("useful_info"),
            "policy_notes": _extract_policy_notes(doc),
            "suitable_for": _safe_list(doc.get("suitable_for")),
            "reviews_detail": doc.get("reviews_detail"),
            "images": _safe_list(doc.get("image_urls")),
            "source_url": doc.get("source_url"),
            "crawled_at": _parse_datetime(doc.get("crawled_at")),
            "amenities_general": _safe_list(doc.get("amenities_general")),
            "amenities_leisure": _safe_list(doc.get("amenities_leisure")),
            "amenities_dining": _safe_list(doc.get("amenities_dining")),
        })

        seen_room = set()
        for room in doc.get("rooms", []):
            key = (hid, room.get("room_type_id"))
            if key not in seen_room:
                seen_room.add(key)
                rooms.append({
                "hotel_id": hid,
                "room_type_id": room.get("room_type_id"),
                "name": room.get("name"),
                "price": _clean_price(room.get("price")),
                "room_size": room.get("room_size"),
                "max_occupancy": room.get("max_occupancy"),
                "bed_type": room.get("bed_type"),
                "room_view": room.get("room_view"),
                "room_amenities": _safe_list(room.get("room_amenities")),
                "images": _safe_list(room.get("images")),
                "review_score": room.get("review_score"),
            })

        seen_np = set()
        for np in doc.get("nearby_places", []):
            key = (hid, np.get("name"))
            if key not in seen_np:
                seen_np.add(key)
                nearby_places.append({
                    "hotel_id": hid,
                    "name": np.get("name"),
                    "type": np.get("type"),
                    "distance_km": np.get("distance_km"),
                })

        seen_act = set()
        for act in doc.get("activities", []):
            key = (hid, act.get("title"))
            if key not in seen_act:
                seen_act.add(key)
                activities.append({
                "hotel_id": hid,
                "title": act.get("title"),
                "description": act.get("description"),
                "price_amount": _extract_price_amount(act.get("price"))
                or _clean_price(act.get("price_amount")),
                "review_score": act.get("review_score"),
                "activity_id": act.get("activity_id"),
            })

    # ── Write PostgreSQL ──
    session = SessionLocal()
    try:
        session.query(Activity).delete()
        session.query(NearbyPlace).delete()
        session.query(Room).delete()
        session.query(Hotel).delete()
        session.commit()

        session.execute(Hotel.__table__.insert(), hotels)
        if rooms:
            session.execute(Room.__table__.insert(), rooms)
        if nearby_places:
            session.execute(NearbyPlace.__table__.insert(), nearby_places)
        if activities:
            session.execute(Activity.__table__.insert(), activities)
        session.commit()
    finally:
        session.close()

    summary = {
        "hotels": len(hotels),
        "rooms": len(rooms),
        "nearby_places": len(nearby_places),
        "activities": len(activities),
    }
    print(f"Exported {DEFAULT_CLEANED_DIR} → PostgreSQL — {summary}")
    return summary


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Export cleaned hotels to PostgreSQL")
    parser.add_argument("--cleaned-dir", type=str, default=str(DEFAULT_CLEANED_DIR))
    args = parser.parse_args(argv)
    run(Path(args.cleaned_dir))


if __name__ == "__main__":
    main()
