"""Sinh mock documents theo data_schema.json thật (DA09 relational_schema.md).

Mỗi document sinh ra khớp với 4 bảng: hotels, rooms, nearby_places, activities.
Dùng để phát triển & test pipeline ingestion.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT: Path = (
    Path(__file__).resolve().parents[1] / "data" / "samples" / "mock_documents_v1.json"
)
DEFAULT_NUM_DOCS: int = 200
RANDOM_SEED: int = 42

_random = random.Random(RANDOM_SEED)

ACCOMMODATION_TYPES = ["Hotel", "Resort", "Villa", "Homestay", "Biệt thự"]
PROPERTY_TYPES = ["Hotel", "Resort"]
CITIES = [
    "Nha Trang", "Đà Nẵng", "Hà Nội", "TP. Hồ Chí Minh", "Phú Quốc",
    "Hội An", "Đà Lạt", "Hạ Long", "Huế", "Vũng Tàu",
]
PROVINCES = [
    "Khánh Hòa", "Đà Nẵng", "Hà Nội", "TP. Hồ Chí Minh", "Kiên Giang",
    "Quảng Nam", "Lâm Đồng", "Quảng Ninh", "Thừa Thiên Huế", "Bà Rịa - Vũng Tàu",
]
AMENITIES_POOL = [
    "Hồ bơi", "WiFi miễn phí", "Bãi biển riêng", "Phòng tập gym",
    "Nhà hàng", "Bar", "Xông hơi", "Spa", "Dịch vụ phòng 24/7",
    "Chỗ đậu xe", "Xe đưa đón sân bay", "Trung tâm thương mại",
    "Dịch vụ giặt ủi", "Lễ tân 24/7", "Tour du lịch",
]
SUITABLE_FOR_POOL = [
    "Cặp đôi", "Gia đình có trẻ nhỏ", "Khách đi công tác",
    "Nhóm du khách", "Khách du lịch một mình", "Người cao tuổi",
]
BED_TYPES = ["1 giường đôi", "2 giường đơn", "1 giường đôi + 1 giường đơn", "1 giường king"]
ROOM_VIEWS = ["Hướng Biển", "Hướng Vườn", "Hướng Hồ bơi", "Hướng Thành phố", "Hướng Núi"]
ACTIVITY_TYPES = [
    "Vé vào cổng", "Tour tham quan", "Trải nghiệm ẩm thực",
    "Massage & Spa", "Lặn biển", "Chèo thuyền",
]


def _generate_hotel(doc_id: int) -> dict[str, Any]:
    name = f"Khách sạn Mẫu {doc_id}"
    city = _random.choice(CITIES)

    doc: dict[str, Any] = {
        "id": doc_id,
        "name": name,
        "accommodation_type": _random.choice(ACCOMMODATION_TYPES),
        "star_rating": round(_random.uniform(2.0, 5.0) * 2) / 2,
        "is_luxury": _random.random() < 0.3,
        "review_score": round(_random.uniform(6.0, 10.0), 1),
        "review_count": _random.randint(50, 10000),
        "address": f"Số {_random.randint(1, 999)} Đường {_random.choice(['Nguyễn Huệ', 'Trần Hưng Đạo', 'Lê Lợi', 'Hùng Vương'])}, {city}",
        "city": city,
        "latitude": round(_random.uniform(10.0, 22.0), 6),
        "longitude": round(_random.uniform(103.0, 110.0), 6),
        "description": f"{name} là khách sạn {'sang trọng' if _random.random() < 0.5 else 'ấm cúng'} tọa lạc tại {city}. "
        f"Cung cấp dịch vụ chất lượng cao với đội ngũ nhân viên chuyên nghiệp. "
        f"Phù hợp cho {'kỳ nghỉ gia đình' if _random.random() < 0.5 else 'chuyến công tác'}.",
        "amenities": _random.sample(
            AMENITIES_POOL, _random.randint(5, len(AMENITIES_POOL))
        ),
        "useful_info": {
            "Nhận phòng từ": "14:00",
            "Trả phòng đến": "12:00",
            "Khoảng cách từ trung tâm thành phố": f"{_random.randint(1, 15)}km",
        },
        "policyNotes": [
            "Không hút thuốc trong phòng",
            "Không mang theo thú cưng",
        ],
        "suitable_for": _random.sample(
            SUITABLE_FOR_POOL, _random.randint(2, 4)
        ),
        "reviews_detail": {
            "score": round(_random.uniform(6.0, 10.0), 1),
            "score_text": "Tuyệt vời",
            "review_count": _random.randint(50, 10000),
            "grades": [
                {"name": "Độ sạch sẽ", "score": round(_random.uniform(7.0, 10.0), 1)},
                {"name": "Dịch vụ", "score": round(_random.uniform(7.0, 10.0), 1)},
            ],
        },
        "images": [
            f"https://example.com/hotel_{doc_id}_img_{i}.jpg"
            for i in range(_random.randint(3, 10))
        ],
        "source_url": f"https://www.example.com/hotel/{doc_id}/{name.lower().replace(' ', '-')}",
        "crawled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return doc


def _generate_rooms(doc_id: int) -> list[dict[str, Any]]:
    num_rooms = _random.randint(3, 8)
    rooms: list[dict[str, Any]] = []
    for i in range(num_rooms):
        rooms.append({
            "hotel_id": doc_id,
            "room_type_id": doc_id * 100 + i,
            "name": _random.choice([
                "Phòng Deluxe", "Phòng Suite", "Phòng Superior",
                "Phòng Executive", "Phòng Family", "Phòng Twin",
            ]),
            "price": round(_random.uniform(500000, 5000000), -3),
            "room_size": f"{_random.randint(25, 80)} m²",
            "max_occupancy": _random.randint(2, 6),
            "bed_type": _random.choice(BED_TYPES),
            "room_view": _random.choice(ROOM_VIEWS),
            "room_amenities": _random.sample(
                ["WiFi", "TV", "Điều hòa", "Minibar", "Bồn tắm", "Ban công"],
                _random.randint(2, 5),
            ),
            "images": [
                f"https://example.com/hotel_{doc_id}_room_{i}_{j}.jpg"
                for j in range(_random.randint(1, 4))
            ],
            "review_score": round(_random.uniform(7.0, 10.0), 1),
        })
    return rooms


def _generate_nearby_places(doc_id: int) -> list[dict[str, Any]]:
    num_places = _random.randint(3, 7)
    places: list[dict[str, Any]] = []
    for i in range(num_places):
        places.append({
            "hotel_id": doc_id,
            "name": _random.choice([
                "VinWonders", "Bãi biển trung tâm", "Chợ đêm",
                "Khu phố cổ", "Khu mua sắm", "Công viên giải trí",
                "Nhà hàng hải sản", "Cảng du thuyền",
            ]),
            "type": _random.choice([
                "Khu vui chơi", "Bãi biển", "Khu mua sắm",
                "Địa danh", "Nhà hàng", "Giải trí",
            ]),
            "distance_km": round(_random.uniform(0.1, 10.0), 1),
        })
    return places


def _generate_activities(doc_id: int) -> list[dict[str, Any]]:
    num_activities = _random.randint(1, 4)
    acts: list[dict[str, Any]] = []
    for i in range(num_activities):
        acts.append({
            "hotel_id": doc_id,
            "title": _random.choice(ACTIVITY_TYPES) + f" {doc_id}.{i}",
            "description": f"Hoạt động thú vị dành cho du khách tại điểm đến.",
            "price_amount": round(_random.uniform(100000, 3000000), -3),
            "review_score": round(_random.uniform(7.0, 10.0), 1),
        })
    return acts


def _generate_invalid_doc(doc_id: int) -> dict[str, Any]:
    """Sinh 1 document cố tình vi phạm schema — thiếu field, sai type."""
    doc = _generate_hotel(doc_id)
    violation = _random.choice([
        "missing_id",
        "missing_name",
        "missing_source_url",
        "empty_name",
        "bad_star_rating",
        "bad_review_score",
    ])
    if violation == "missing_id":
        del doc["id"]
    elif violation == "missing_name":
        del doc["name"]
    elif violation == "missing_source_url":
        del doc["source_url"]
    elif violation == "empty_name":
        doc["name"] = ""
    elif violation == "bad_star_rating":
        doc["star_rating"] = 6.0  # vượt max 5.0
    elif violation == "bad_review_score":
        doc["review_score"] = 11.0  # vượt max 10
    return doc


def generate_mock_documents(
    n: int = DEFAULT_NUM_DOCS,
    *,
    invalid_ratio: float = 0.1,
    seed: int = RANDOM_SEED,
) -> list[dict[str, Any]]:
    """Sinh `n` mock document (hợp lệ + không hợp lệ)."""
    global _random
    _random = random.Random(seed)

    docs: list[dict[str, Any]] = []
    num_invalid = int(n * invalid_ratio)

    for i in range(n):
        doc_id = i + 1
        is_invalid = i < num_invalid

        if is_invalid:
            doc = _generate_invalid_doc(doc_id)
        else:
            doc = _generate_hotel(doc_id)
            doc["rooms"] = _generate_rooms(doc_id)
            doc["nearby_places"] = _generate_nearby_places(doc_id)
            doc["activities"] = _generate_activities(doc_id)

        docs.append(doc)

    _random.shuffle(docs)
    return docs


def write_mock_documents(
    output_path: Path | str = DEFAULT_OUTPUT,
    n: int = DEFAULT_NUM_DOCS,
    **kwargs,
) -> Path:
    """Generate + ghi ra file JSON, trả về path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    docs = generate_mock_documents(n, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    return path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate mock hotel documents")
    parser.add_argument("--n", type=int, default=DEFAULT_NUM_DOCS, help="Number of documents")
    parser.add_argument("--invalid-ratio", type=float, default=0.1, help="Ratio of invalid docs")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output path")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    args = parser.parse_args()
    path = write_mock_documents(
        args.output,
        n=args.n,
        invalid_ratio=args.invalid_ratio,
        seed=args.seed,
    )
    print(f"Generated {args.n} mock documents → {path}")


if __name__ == "__main__":
    main()
