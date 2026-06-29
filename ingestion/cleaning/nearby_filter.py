"""nearby_filter.py — Lọc nearby_places quá xa (Layer 2 cleaning). Feedback DA09 (#2).

VẤN ĐỀ: Agoda liệt kê "địa điểm gần" gồm cả nơi cách HÀNG CHỤC–TRĂM km. Khảo sát 520 hotel:
  - Phần lớn loại (siêu thị/quán/bãi biển/công viên...): median ~0.5-0.9 km, p90 ~2-5 km.
  - Sân bay: median 124 km, max 265 km — Agoda liệt kê sân bay GẦN NHẤT bất kể xa.

QUYẾT ĐỊNH (2026-06-21): NGƯỠNG DUY NHẤT 15km cho MỌI loại. "Gần" phải là "gần" thật —
một sân bay cách 200km thì gắn `near` là VÔ NGHĨA (query "gần sân bay" sẽ trả hotel cách 200km).
KHÔNG ngoại lệ theo loại nữa (bản trước nới sân bay 200km/ga 60km là SAI: mâu thuẫn khái niệm
nearby — VN dài 1600km, 200km không thể gọi là gần). 15km = đi taxi ~20-30 phút, vẫn là "tiện".

Vượt ngưỡng -> loại khỏi nearby_places. Bản ghi thiếu distance_km -> GIỮ (không đủ căn cứ loại).
KHÔNG đụng thứ tự / field khác.

LƯU Ý ĐỒNG BỘ: nearby_places là NGUỒN sinh quan hệ `near` (build_relations) + nearby_landmarks
(build_objects). Lọc Ở ĐÂY (clean) là gốc -> các tầng sau tự sạch theo. Xem [[lmk-pipeline-rebuild-chain]].
"""

from __future__ import annotations

# Ngưỡng "gần" DUY NHẤT (km) — áp cho MỌI loại địa điểm. Vượt -> không còn là nearby, loại.
MAX_NEARBY_KM = 15.0


def filter_nearby_places(places: list[dict] | None) -> list[dict]:
    """Trả list nearby_places đã loại điểm xa hơn MAX_NEARBY_KM. Bản ghi thiếu distance_km
    -> GIỮ (không đủ căn cứ loại). Không sửa thứ tự / field khác."""
    if not places:
        return places or []
    out = []
    for p in places:
        if not isinstance(p, dict):
            out.append(p)
            continue
        km = p.get("distance_km")
        if not isinstance(km, (int, float)):
            out.append(p)            # không có khoảng cách -> giữ
            continue
        if km <= MAX_NEARBY_KM:
            out.append(p)
    return out


def filter_stats(places: list[dict] | None) -> tuple[int, int]:
    """(giữ, loại) — cho log/kiểm tra, không sửa data."""
    if not places:
        return (0, 0)
    kept = filter_nearby_places(places)
    return (len(kept), len(places) - len(kept))


__all__ = ["filter_nearby_places", "filter_stats"]
