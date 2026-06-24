"""hotel_data.py — Full hotel detail from local cache (replaces OTA API).

Loads hotel_detail_cache.json lazily (lru_cache) and provides typed helpers
for room-level filtering (price, room_view). This removes dependency on
the external OTA (Supabase) API entirely.

Usage:
    from knowledge_engineering.common.hotel_data import get_hotel, get_rooms
    hotel = get_hotel(1032041)
    rooms = get_rooms(1032041)
    matching = filter_rooms(1032041, max_price=2000000, view="thành phố")
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

HOTEL_CACHE_PATH = os.getenv(
    "HOTEL_CACHE_PATH",
    "data/hotel_detail_cache.json",
)


@lru_cache(maxsize=1)
def load_hotel_cache(path: str = HOTEL_CACHE_PATH) -> dict[str, dict]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_id(hotel_id: Any) -> str:
    if isinstance(hotel_id, str):
        return hotel_id
    return str(int(hotel_id))


def get_hotel(hotel_id: Any) -> dict | None:
    """Full hotel detail for the frontend schema. None if not found."""
    return load_hotel_cache().get(_resolve_id(hotel_id))


def get_hotel_ids() -> list[int]:
    return [int(k) for k in load_hotel_cache()]


def get_rooms(hotel_id: Any) -> list[dict]:
    """All rooms for a hotel. Empty list if hotel not found or no rooms."""
    hotel = get_hotel(hotel_id)
    if hotel is None:
        return []
    return hotel.get("rooms") or []


def price_range_hotel(hotel_id: Any) -> tuple[int | None, int | None]:
    """(min_price, max_price) among rooms for this hotel. (None, None) if no data."""
    prices = [
        r.get("price_per_night") for r in get_rooms(hotel_id)
        if r.get("price_per_night") is not None
    ]
    if not prices:
        return None, None
    return min(prices), max(prices)


def hotel_min_price(hotel_id: Any) -> int | None:
    return price_range_hotel(hotel_id)[0]


def hotel_max_price(hotel_id: Any) -> int | None:
    return price_range_hotel(hotel_id)[1]


def room_views_for_hotel(hotel_id: Any) -> list[str]:
    """Unique room view types available."""
    views: set[str] = set()
    for r in get_rooms(hotel_id):
        v = r.get("room_view")
        if v:
            views.add(str(v).lower())
    return sorted(views)


def filter_rooms(
    hotel_id: Any,
    *,
    max_price: int | None = None,
    min_price: int | None = None,
    view: str | None = None,
) -> list[dict]:
    """Return rooms matching all given criteria. No filter = all rooms."""
    rooms = get_rooms(hotel_id)
    result: list[dict] = []

    # Pre-process view filter
    view_lower = view.lower().strip() if view else None

    for r in rooms:
        price = r.get("price_per_night")
        rv = r.get("room_view")

        if min_price is not None and (price is None or price < min_price):
            continue
        if max_price is not None and (price is None or price > max_price):
            continue
        if view_lower and (not rv or view_lower not in rv.lower()):
            continue

        result.append(r)

    return result


def available_views(cache: dict[str, dict] | None = None) -> set[str]:
    """All unique room_view values across all hotels (for frontend filter options)."""
    if cache is None:
        cache = load_hotel_cache()
    views: set[str] = set()
    for entry in cache.values():
        for r in entry.get("rooms") or []:
            v = r.get("room_view")
            if v:
                views.add(str(v).strip())
    return views
