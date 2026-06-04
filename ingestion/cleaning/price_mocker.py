from __future__ import annotations

import hashlib
import re
from typing import Any

STAR_PRICE_TABLE: dict[int, tuple[int, int, int]] = {
    5: (2_000_000, 3_500_000, 5_000_000),
    4: (1_200_000, 2_100_000, 3_000_000),
    3: (600_000, 1_050_000, 1_500_000),
    2: (300_000, 550_000, 800_000),
    1: (200_000, 350_000, 500_000),
}

BRAND_FACTORS: dict[str, float] = {
    "vinpearl": 1.2,
    "meliá": 1.2,
    "melia": 1.2,
    "muong thanh": 0.9,
}

ROOM_TYPE_FACTORS: dict[str, float] = {
    "penthouse": 2.0,
    "suite": 1.8,
    "villa": 1.6,
    "studio": 1.4,
    "deluxe": 1.3,
    "executive": 1.3,
    "premier": 1.2,
    "superior": 1.0,
    "standard": 0.9,
    "family": 1.1,
}

CITY_FACTORS: dict[str, float] = {
    "phú quốc": 1.3,
    "nha trang": 1.3,
    "hạ long": 1.3,
    "đà nẵng": 1.1,
    "hội an": 1.1,
    "sầm sơn": 1.1,
    "phan thiết": 1.1,
    "đà lạt": 1.1,
}


def _star_rating(hotel: dict[str, Any]) -> int:
    sr = hotel.get("star_rating") or 3
    return int(round(float(sr)))


def _base_price(star: int) -> tuple[int, int, int]:
    return STAR_PRICE_TABLE.get(star, STAR_PRICE_TABLE[3])


def _brand_factor(name: str | None) -> float:
    if not name:
        return 1.0
    lower = name.lower()
    for brand, factor in BRAND_FACTORS.items():
        if brand in lower:
            return factor
    return 0.8


def _room_type_factor(room_name: str | None) -> float:
    if not room_name:
        return 1.0
    lower = room_name.lower()
    for rtype, factor in ROOM_TYPE_FACTORS.items():
        if rtype in lower:
            return factor
    return 1.0


def _city_factor(city: str | None) -> float:
    if not city:
        return 1.0
    lower = city.lower().strip()
    for key, factor in CITY_FACTORS.items():
        if key in lower:
            return factor
    return 1.0


def _size_factor(room: dict[str, Any]) -> float:
    sqm = room.get("size_sqm")
    if sqm and isinstance(sqm, (int, float)):
        return max(0.5, min(2.0, sqm / 30))

    size_str = room.get("room_size")
    if size_str and isinstance(size_str, str):
        m = re.search(r"(\d+)", size_str.replace(",", "."))
        if m:
            val = float(m.group(1))
            return max(0.5, min(2.0, val / 30))

    return 1.0


def _deterministic_discount(hotel_id: int, room_type_id: int | None) -> float:
    key = f"{hotel_id}_{room_type_id or 0}"
    h = hashlib.md5(key.encode()).hexdigest()
    val = int(h[:8], 16)
    return 1.2 + (val % 6000) / 10000


def _round_price(val: float) -> int:
    return int(round(val / 10_000) * 10_000)


def mock_room_prices(
    room: dict[str, Any],
    hotel: dict[str, Any],
) -> dict[str, int | None]:
    hotel_id = hotel.get("id") or hotel.get("hotel_id") or 0
    if not hotel_id:
        return {"price_per_night": None, "original_price": None}

    if not isinstance(hotel_id, int):
        hotel_id = int(hashlib.md5(str(hotel_id).encode()).hexdigest()[:8], 16)

    star = _star_rating(hotel)
    price_min, price_mid, price_max = _base_price(star)

    base = price_mid
    base *= _brand_factor(hotel.get("name"))
    base *= _room_type_factor(room.get("name"))
    base *= _city_factor(hotel.get("city") or hotel.get("province"))
    base *= _size_factor(room)

    base = max(float(price_min), min(float(price_max), base))

    ppn = _round_price(base)

    discount = _deterministic_discount(hotel_id, room.get("room_type_id"))
    orig = _round_price(ppn * discount)

    return {"price_per_night": ppn, "original_price": orig}
