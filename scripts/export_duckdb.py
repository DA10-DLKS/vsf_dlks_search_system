"""Export cleaned hotel JSON → DuckDB single file.

Usage:
    python scripts/export_duckdb.py
    python scripts/export_duckdb.py --output data/da10.duckdb
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import duckdb

DEFAULT_CLEANED_DIR = _PROJECT_ROOT / "data" / "cleaned"
DEFAULT_OUTPUT = _PROJECT_ROOT / "data" / "da10.duckdb"


def _safe_list(val: list | None) -> list:
    return val if isinstance(val, list) else []


def _build_amenity_groups(doc: dict) -> str | None:
    groups = {}
    raw = doc.get("amenity_groups")
    if raw:
        groups["groups"] = raw
    for field in ("amenities_general", "amenities_leisure", "amenities_dining"):
        val = doc.get(field)
        if val:
            groups[field.replace("amenities_", "")] = val
    return json.dumps(groups, ensure_ascii=False) if groups else None


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
        s = s.replace("₫", "").replace("$", "").replace(",", "").strip()
        s = s.replace(".", "")  # remove thousands separator dots
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


def run(
    cleaned_dir: Path = DEFAULT_CLEANED_DIR,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, int]:
    hotel_files = sorted(cleaned_dir.glob("hotel_*.json"))
    if not hotel_files:
        print(f"No hotel files found in {cleaned_dir}")
        return {"hotels": 0, "rooms": 0, "nearby_places": 0, "activities": 0}

    hotels_rows: list[tuple] = []
    rooms_rows: list[tuple] = []
    nearby_rows: list[tuple] = []
    activity_rows: list[tuple] = []

    for fp in hotel_files:
        with open(fp) as f:
            doc = json.load(f)

        hid = doc.get("hotel_id") or doc.get("id")

        hotels_rows.append((
            hid,
            doc.get("name"),
            doc.get("accommodation_type"),
            doc.get("star_rating"),
            bool(doc.get("is_luxury", False)),
            doc.get("review_score"),
            doc.get("review_count", 0),
            doc.get("address"),
            doc.get("city") or doc.get("province"),
            doc.get("latitude"),
            doc.get("longitude"),
            doc.get("description"),
            _safe_list(doc.get("amenities")),
            _build_amenity_groups(doc),
            json.dumps(doc.get("useful_info"), ensure_ascii=False)
            if doc.get("useful_info") else None,
            _extract_policy_notes(doc),
            _safe_list(doc.get("suitable_for")),
            json.dumps(doc.get("reviews_detail"), ensure_ascii=False)
            if doc.get("reviews_detail") else None,
            _safe_list(doc.get("image_urls")),
            doc.get("source_url"),
            doc.get("crawled_at"),
            _safe_list(doc.get("amenities_general")),
            _safe_list(doc.get("amenities_leisure")),
            _safe_list(doc.get("amenities_dining")),
        ))

        # Rooms
        for room in doc.get("rooms", []):
            rooms_rows.append((
                hid,
                room.get("room_type_id"),
                room.get("name"),
                _clean_price(room.get("price")),
                room.get("room_size"),
                room.get("max_occupancy"),
                room.get("bed_type"),
                room.get("room_view"),
                _safe_list(room.get("room_amenities")),
                _safe_list(room.get("images")),
                room.get("review_score"),
            ))

        # Nearby places
        for np in doc.get("nearby_places", []):
            nearby_rows.append((
                hid,
                np.get("name"),
                np.get("type"),
                np.get("distance_km"),
            ))

        # Activities
        for act in doc.get("activities", []):
            activity_rows.append((
                hid,
                act.get("title"),
                act.get("description"),
                _extract_price_amount(act.get("price")) or _clean_price(act.get("price_amount")),
                act.get("review_score"),
                act.get("activity_id"),
            ))

    # ── Write DuckDB ──
    output.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(output))

    conn.execute("DROP TABLE IF EXISTS hotels")
    conn.execute("""
        CREATE TABLE hotels (
            id              INTEGER,
            name            VARCHAR,
            accommodation_type VARCHAR,
            star_rating     FLOAT,
            is_luxury       BOOLEAN,
            review_score    FLOAT,
            review_count    INTEGER,
            address         VARCHAR,
            city            VARCHAR,
            latitude        DOUBLE,
            longitude       DOUBLE,
            description     VARCHAR,
            amenities       VARCHAR[],
            amenity_groups  JSON,
            useful_info     JSON,
            policy_notes    VARCHAR[],
            suitable_for    VARCHAR[],
            reviews_detail  JSON,
            images              VARCHAR[],
            source_url          VARCHAR,
            crawled_at          VARCHAR,
            amenities_general   VARCHAR[],
            amenities_leisure   VARCHAR[],
            amenities_dining    VARCHAR[]
        )
    """)
    conn.executemany(
        "INSERT INTO hotels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        hotels_rows,
    )

    conn.execute("DROP TABLE IF EXISTS rooms")
    conn.execute("""
        CREATE TABLE rooms (
            hotel_id        INTEGER,
            room_type_id    INTEGER,
            name            VARCHAR,
            price           FLOAT,
            room_size       VARCHAR,
            max_occupancy   INTEGER,
            bed_type        VARCHAR,
            room_view       VARCHAR,
            room_amenities  VARCHAR[],
            images          VARCHAR[],
            review_score    FLOAT
        )
    """)
    conn.executemany(
        "INSERT INTO rooms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rooms_rows,
    )

    conn.execute("DROP TABLE IF EXISTS nearby_places")
    conn.execute("""
        CREATE TABLE nearby_places (
            hotel_id        INTEGER,
            name            VARCHAR,
            type            VARCHAR,
            distance_km     FLOAT
        )
    """)
    conn.executemany(
        "INSERT INTO nearby_places VALUES (?, ?, ?, ?)",
        nearby_rows,
    )

    conn.execute("DROP TABLE IF EXISTS activities")
    conn.execute("""
        CREATE TABLE activities (
            hotel_id        INTEGER,
            title           VARCHAR,
            description     VARCHAR,
            price_amount    FLOAT,
            review_score    FLOAT,
            activity_id     INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?)",
        activity_rows,
    )

    conn.close()

    summary = {
        "hotels": len(hotels_rows),
        "rooms": len(rooms_rows),
        "nearby_places": len(nearby_rows),
        "activities": len(activity_rows),
    }
    print(f"Exported {output} — {summary}")
    return summary


def _parse_args(argv: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="Export cleaned hotels to DuckDB")
    parser.add_argument("--cleaned-dir", type=str, default=str(DEFAULT_CLEANED_DIR))
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    run(Path(args.cleaned_dir), Path(args.output))


if __name__ == "__main__":
    main()
