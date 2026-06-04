from __future__ import annotations

import re
from typing import Any

BED_CAPACITY: dict[str, int] = {
    "đơn": 1,
    "semi-double": 1,
    "đôi": 2,
    "lớn": 2,
    "đôi lớn": 2,
    "siêu lớn": 2,
    "king": 2,
    "queen": 2,
    "tầng": 2,
    "sofa giường": 1,
    "sofa": 1,
}

_BED_CAPACITY_KEYS = sorted(BED_CAPACITY, key=len, reverse=True)
_BED_PATTERN = re.compile(r"(\d+)\s+giường\s+(.+)")


def _bed_type_capacity(bed_text: str) -> int:
    m = _BED_PATTERN.search(bed_text)
    if not m:
        return 2
    count = int(m.group(1))
    desc = m.group(2).strip().lower()
    for key in _BED_CAPACITY_KEYS:
        if key in desc:
            return count * BED_CAPACITY[key]
    return 2


def _parse_bed_text(text: str) -> int:
    text = text.strip().lower()

    or_parts = re.split(r"\s*(?:/|\s+hoặc\s+)\s*", text)
    and_parts = re.split(r"\s*(?:và|,)\s*", or_parts[0])

    total = sum(_bed_type_capacity(p.strip()) for p in and_parts if p.strip())

    if len(or_parts) > 1:
        alt_total = sum(
            _bed_type_capacity(p.strip())
            for p in re.split(r"\s*(?:và|,)\s*", or_parts[1])
            if p.strip()
        )
        total = max(total, alt_total)

    return total


def impute_max_occupancy(room: dict[str, Any]) -> int:
    mo = room.get("max_occupancy")
    if mo is not None and isinstance(mo, (int, float)) and mo > 0:
        return int(mo)

    mo_text = room.get("max_occupancy_text")
    if mo_text:
        m = re.search(r"(\d+)", str(mo_text))
        if m:
            val = int(m.group(1))
            if val > 0:
                return val

    bed_types = room.get("bed_types") or []
    if bed_types and isinstance(bed_types, list) and len(bed_types) > 0:
        combined = ", ".join(str(b) for b in bed_types if b)
        if combined.strip():
            try:
                return _parse_bed_text(combined)
            except (ValueError, TypeError):
                pass

    bt = room.get("bed_type")
    if bt and isinstance(bt, str) and bt.strip():
        try:
            return _parse_bed_text(bt)
        except (ValueError, TypeError):
            pass

    return 2
