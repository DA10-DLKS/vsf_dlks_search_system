# DA10 → DA09 Handoff: Hotel Metadata Schema v1.0

## 1. Mục tiêu

Tài liệu này định nghĩa cách DA10 chuyển dữ liệu crawl khách sạn thô thành các lớp metadata có cấu trúc để DA09 sử dụng cho:

* Keyword Search
* Semantic Search
* Hybrid Search
* Metadata Filtering
* Faceted Search
* RAG Question Answering
* Recommendation
* Ranking
* Explainability

Nguyên tắc quan trọng:

> Metadata không phải là bê nguyên toàn bộ JSON crawl.
> Metadata là tập thông tin có cấu trúc, có ích trực tiếp cho search, filter, ranking, QA và recommendation.

---

## 2. Phân biệt Raw Data và Metadata

### 2.1 Raw Data

Raw data là dữ liệu crawl nguyên bản từ nguồn như Agoda.

Ví dụ:

```json
{
  "hotel_id": 805030,
  "name": "Vinpearl Resort & Spa Nha Trang Bay",
  "description": "...",
  "amenities": [...],
  "rooms": [...],
  "reviews_detail": {...},
  "nearby_places": [...]
}
```

Raw data nên được lưu lại để trace/debug, nhưng không phải field nào cũng đưa vào metadata.

---

### 2.2 Metadata

Metadata là bản chuẩn hóa/enrich từ raw data.

Ví dụ:

```json
{
  "hotel_id": 805030,
  "city": "Nha Trang",
  "star_rating": 5,
  "private_beach": true,
  "pool": true,
  "family_friendly": true,
  "nearby_places": [
    {"place_id": "LMK_VINWONDERS_NHA_TRANG", "category": "theme_park", "distance_km": 0.86}
  ]
}
```

DA09 có thể dùng trực tiếp cho filter, ranking và retrieval.

---

## 3. Metadata Final Structure

Metadata được tách thành 10 layer:

```text
1. Core Metadata
2. Policy & Operation Metadata
3. Search / Filter Metadata
4. Room Metadata
5. Nearby / Geo Metadata
6. Review & Reputation Metadata
7. Image / Media Metadata
8. Semantic Metadata
9. Evidence & Traceability Metadata
10. Data Quality & Ownership Metadata
```

---

# Layer 1 — Core Metadata

## Mục đích

Dùng cho định danh, hiển thị cơ bản, filter cơ bản và fact QA.

## Nguồn từ crawl

* `hotel_id`
* `name`
* `property_type`
* `accommodation_type`
* `star_rating`
* `review_score`
* `review_count`
* `address`
* `area`
* `city`
* `country`
* `postal_code`
* `latitude`
* `longitude`
* `description`
* `gold_circle_award_year`

## Schema

```json
{
  "core_metadata": {
    "hotel_id": "integer",
    "name": "string",
    "brand": "string | null",
    "chain": "string | null",

    "property_type": "string",
    "accommodation_type": "string",
    "entity_type": "hotel | resort | villa | apartment | homestay | other",

    "star_rating": "number | null",
    "review_score": "number | null",
    "review_count": "integer | null",

    "gold_circle_award_year": "string | null",

    "address": "string | null",
    "area": "string | null",
    "district": "string | null",
    "city": "string | null",
    "province": "string | null",
    "country": "string | null",
    "postal_code": "string | null",

    "latitude": "number | null",
    "longitude": "number | null",

    "description_short": "string | null",
    "description_full": "string | null"
  }
}
```

## Example

```json
{
  "core_metadata": {
    "hotel_id": 805030,
    "name": "Vinpearl Resort & Spa Nha Trang Bay",
    "brand": "Vinpearl",
    "chain": "Vinpearl",

    "property_type": "Hotel",
    "accommodation_type": "Resort",
    "entity_type": "resort",

    "star_rating": 5.0,
    "review_score": 8.8,
    "review_count": 10862,

    "gold_circle_award_year": "2025",

    "address": "Hòn Tre, Hòn Tre, Nha Trang, Việt Nam",
    "area": "Hòn Tre",
    "district": "Hòn Tre",
    "city": "Nha Trang",
    "province": "Nha Trang",
    "country": "Việt Nam",
    "postal_code": "650000",

    "latitude": 12.22537612915039,
    "longitude": 109.23710632324219,

    "description_short": "Resort 5 sao tại Hòn Tre, Nha Trang, có bãi biển riêng, spa, hồ bơi và nhiều tiện ích nghỉ dưỡng.",
    "description_full": "Full cleaned hotel description here..."
  }
}
```

---

# Layer 2 — Policy & Operation Metadata

## Mục đích

Dùng để trả lời các câu hỏi fact phổ biến:

* Check-in mấy giờ?
* Check-out mấy giờ?
* Có đưa đón sân bay không?
* Phí đưa đón sân bay bao nhiêu?
* Có bao nhiêu phòng?
* Có bao nhiêu tầng?
* Có bao nhiêu nhà hàng?
* Có bao nhiêu quán bar?
* Lễ tân mở đến mấy giờ?

## Nguồn từ crawl

* `check_in_from`
* `check_out_until`
* `year_built`
* `number_of_floors`
* `number_of_rooms`
* `useful_info`

## Schema

```json
{
  "policy_operation_metadata": {
    "check_in_from": "string | null",
    "check_out_until": "string | null",
    "reception_open_until": "string | null",

    "year_built": "integer | null",
    "last_renovated_year": "integer | null",

    "number_of_rooms": "integer | null",
    "number_of_floors": "integer | null",
    "number_of_restaurants": "integer | null",
    "number_of_bars": "integer | null",

    "city_center_distance_km": "number | null",
    "airport_travel_time_minutes": "integer | null",

    "airport_transfer_available": "boolean | null",
    "airport_transfer_fee_vnd": "integer | null",

    "parking_available": "boolean | null",
    "daily_parking_fee_vnd": "integer | null"
  }
}
```

## Example

```json
{
  "policy_operation_metadata": {
    "check_in_from": "15:00",
    "check_out_until": "12:00",
    "reception_open_until": "23:59",

    "year_built": 2015,
    "last_renovated_year": 2016,

    "number_of_rooms": 651,
    "number_of_floors": 11,
    "number_of_restaurants": 5,
    "number_of_bars": 2,

    "city_center_distance_km": 6.5,
    "airport_travel_time_minutes": 40,

    "airport_transfer_available": true,
    "airport_transfer_fee_vnd": 1700000,

    "parking_available": true,
    "daily_parking_fee_vnd": 0
  }
}
```

---

# Layer 3 — Search / Filter Metadata

## Mục đích

Dùng cho DA09 filter/facet/search.

Ví dụ user hỏi:

* Tìm resort có bãi biển riêng
* Tìm khách sạn có hồ bơi
* Tìm resort có kids club
* Tìm khách sạn có spa
* Tìm resort có đưa đón sân bay
* Tìm khách sạn phù hợp gia đình

## Nguồn từ crawl

* `amenities`
* `amenity_groups`
* `amenities_general`
* `amenities_leisure`
* `amenities_dining`
* `location_tags`
* `highlights`

## Schema

```json
{
  "search_filter_metadata": {
    "beach_private_beach": "boolean",
    "beachfront": "boolean",

    "pool": "boolean",
    "outdoor_pool": "boolean",
    "indoor_pool": "boolean",
    "kids_pool": "boolean",
    "private_pool_available": "boolean",

    "spa": "boolean",
    "sauna": "boolean",
    "steam_room": "boolean",
    "massage": "boolean",
    "gym": "boolean",
    "yoga_room": "boolean",

    "restaurant": "boolean",
    "bar": "boolean",
    "breakfast": "boolean",
    "buffet_breakfast": "boolean",
    "room_service": "boolean",

    "kids_club": "boolean",
    "children_facilities": "boolean",
    "playground": "boolean",
    "family_friendly": "boolean",

    "airport_transfer": "boolean",
    "free_parking": "boolean",
    "on_site_parking": "boolean",
    "ev_charging_station": "boolean",

    "meeting_facilities": "boolean",
    "event_facilities": "boolean",
    "business_facilities": "boolean",

    "golf_on_site": "boolean",
    "golf_nearby": "boolean",
    "tennis_court": "boolean",
    "water_sport_equipment": "boolean",

    "wheelchair_accessible": "boolean",
    "non_smoking_rooms": "boolean",
    "smoking_area": "boolean",
    "fully_non_smoking_property": "boolean",

    "languages": ["string"]
  }
}
```

## Example

```json
{
  "search_filter_metadata": {
    "beach_private_beach": true,
    "beachfront": true,

    "pool": true,
    "outdoor_pool": true,
    "indoor_pool": false,
    "kids_pool": true,
    "private_pool_available": true,

    "spa": true,
    "sauna": true,
    "steam_room": true,
    "massage": true,
    "gym": true,
    "yoga_room": true,

    "restaurant": true,
    "bar": true,
    "breakfast": true,
    "buffet_breakfast": true,
    "room_service": true,

    "kids_club": true,
    "children_facilities": true,
    "playground": true,
    "family_friendly": true,

    "airport_transfer": true,
    "free_parking": true,
    "on_site_parking": true,
    "ev_charging_station": true,

    "meeting_facilities": true,
    "event_facilities": true,
    "business_facilities": true,

    "golf_on_site": true,
    "golf_nearby": true,
    "tennis_court": true,
    "water_sport_equipment": true,

    "wheelchair_accessible": true,
    "non_smoking_rooms": true,
    "smoking_area": true,
    "fully_non_smoking_property": true,

    "languages": ["vi", "en"]
  }
}
```

---

# Layer 4 — Room Metadata

## Mục đích

Dùng cho room-level search và QA.

Ví dụ user hỏi:

* Có phòng hướng biển không?
* Có villa hồ bơi riêng không?
* Có phòng 2 giường đơn không?
* Phòng lớn nhất bao nhiêu m²?
* Có villa 3 phòng ngủ không?
* Có phòng gia đình không?

## Nguồn từ crawl

* `room_grid`
* `rooms`
* `room_type_id`
* `name`
* `name_en`
* `size_sqm`
* `bed_type`
* `room_view`
* `facilities`
* `room_amenities`
* `review_score`

## Schema

```json
{
  "room_metadata": {
    "room_count": "integer",
    "is_sold_out": "boolean",
    "cheapest_price": "number | null",

    "has_deluxe_room": "boolean",
    "has_villa": "boolean",
    "has_duplex_villa": "boolean",
    "has_two_bedroom_villa": "boolean",
    "has_three_bedroom_villa": "boolean",
    "has_four_bedroom_villa": "boolean",

    "has_private_pool_villa": "boolean",
    "has_beachfront_villa": "boolean",

    "has_ocean_view_room": "boolean",
    "has_beach_view_room": "boolean",
    "has_mountain_view_room": "boolean",
    "has_garden_view_room": "boolean",
    "has_pool_view_room": "boolean",

    "min_room_size_sqm": "number | null",
    "max_room_size_sqm": "number | null",

    "king_bed_available": "boolean",
    "twin_bed_available": "boolean",
    "multi_bedroom_available": "boolean",

    "room_types": [
      {
        "room_type_id": "integer",
        "name_vi": "string",
        "name_en": "string | null",
        "size_sqm": "number | null",
        "room_view": "string | null",
        "bed_type": "string | null",
        "is_sold_out": "boolean",
        "private_pool": "boolean",
        "beachfront": "boolean",
        "ocean_view": "boolean",
        "review_score": "number | null"
      }
    ]
  }
}
```

## Example

```json
{
  "room_metadata": {
    "room_count": 10,
    "is_sold_out": false,
    "cheapest_price": null,

    "has_deluxe_room": true,
    "has_villa": true,
    "has_duplex_villa": true,
    "has_two_bedroom_villa": true,
    "has_three_bedroom_villa": true,
    "has_four_bedroom_villa": true,

    "has_private_pool_villa": true,
    "has_beachfront_villa": true,

    "has_ocean_view_room": true,
    "has_beach_view_room": true,
    "has_mountain_view_room": true,
    "has_garden_view_room": true,
    "has_pool_view_room": true,

    "min_room_size_sqm": 45,
    "max_room_size_sqm": 290,

    "king_bed_available": true,
    "twin_bed_available": true,
    "multi_bedroom_available": true,

    "room_types": [
      {
        "room_type_id": 15009536,
        "name_vi": "Villa cạnh bãi biển 2 phòng ngủ có hồ bơi riêng",
        "name_en": "2-Bedroom Beachfront Villa with Private Pool",
        "size_sqm": 240,
        "room_view": "beachfront",
        "bed_type": "1 giường lớn / 2 giường đơn",
        "is_sold_out": false,
        "private_pool": true,
        "beachfront": true,
        "ocean_view": false,
        "review_score": 9.166
      }
    ]
  }
}
```

---

# Layer 5 — Nearby / Geo Metadata

## Mục đích

Dùng cho local search, travel planning và QA.

Ví dụ user hỏi:

* Gần VinWonders không?
* Cách biển bao xa?
* Gần sân golf không?
* Gần bệnh viện không?
* Gần điểm tham quan nào?

## Nguồn từ crawl

* `nearby_places`
* nearby image captions
* location tags
* useful info distance

## Schema

> **Mô hình category + distance (KHÔNG dùng field `near_*` boolean).** Thay vì sinh field cố định
> cho từng loại/landmark (`near_beach`, `near_vinwonders`...) — vốn không scale khi thêm điểm mới —
> dùng MỘT list `nearby_places[]`. DA09 tự suy "gần biển" / "gần VinWonders" bằng cách lọc list theo
> `category` và/hoặc `place_id` + ngưỡng `distance_km`. Thêm landmark = thêm 1 phần tử, **0 field mới**.
>
> `place_id` = concept_id `LMK_*` của ontology (`ontology/core/location.yaml`) khi điểm khớp một
> landmark Core; `null` nếu chưa có concept (vẫn giữ `name` + `category` để filter theo loại).

```json
{
  "nearby_geo_metadata": {
    "nearby_places": [
      {
        "place_id": "string | null",
        "name": "string",
        "category": "theme_park | beach | golf | airport | hospital | museum | historical_site | shopping | park | restaurant | transport | other",
        "type_raw": "string",
        "distance_km": "number | null"
      }
    ]
  }
}
```

> **Cách DA09 dùng (thay cho near_* boolean cũ):**
> - "gần biển" → `any(p.category == "beach" and p.distance_km <= R)`
> - "gần VinWonders" → `any(p.place_id == "LMK_VINWONDERS_NHA_TRANG" and p.distance_km <= R)`
> - "điểm tham quan gần nhất theo loại" → `min(distance_km for p if p.category == X)`

## Example

```json
{
  "nearby_geo_metadata": {
    "nearby_places": [
      {
        "place_id": null,
        "name": "VinWonders Nha Trang",
        "category": "theme_park",
        "type_raw": "Công Viên Giải Trí",
        "distance_km": 0.86
      },
      {
        "place_id": "LMK_VINWONDERS_NHA_TRANG",
        "name": "VinWonders Nha Trang",
        "category": "theme_park",
        "type_raw": "Công Viên Giải Trí",
        "distance_km": 0.86
      },
      {
        "place_id": null,
        "name": "Sân golf Vinpearl",
        "category": "golf",
        "type_raw": "Sân Gôn",
        "distance_km": 2.7
      },
      {
        "place_id": "LMK_DINH_BAO_DAI",
        "name": "Dinh Bảo Đại",
        "category": "historical_site",
        "type_raw": "Đài Kỷ Niệm và Di Tích Lịch Sử",
        "distance_km": 2.78
      },
      {
        "place_id": "LMK_VIEN_HAI_DUONG_HOC",
        "name": "Viện Hải Dương Học",
        "category": "museum",
        "type_raw": "Viện Bảo Tàng và Phòng Trưng Bày Nghệ Thuật",
        "distance_km": 3.11
      },
      {
        "place_id": null,
        "name": "Bệnh viện Quân Y 87",
        "category": "hospital",
        "type_raw": "Bệnh Viện và Cơ Sở Y Tế",
        "distance_km": 3.09
      },
      {
        "place_id": null,
        "name": "Biển Nha Trang",
        "category": "beach",
        "type_raw": "Bãi Biển",
        "distance_km": 3.4
      }
    ]
  }
}
```

> `place_id` dùng concept_id `LMK_*` khi khớp landmark Core của ontology (đồng bộ với quan hệ `near`
> sinh ở `relations_near.generated.yaml`); `null` khi điểm chưa có concept (vẫn filter được theo
> `category`). Một điểm có thể xuất hiện 2 bản (có/không `place_id`) nếu nguồn ghi tên khác nhau —
> dedup theo `place_id` ưu tiên khoảng cách nhỏ nhất (xem `build_relations.py`).

---

# Layer 6 — Review & Reputation Metadata

## Mục đích

Dùng cho ranking, explainability và recommendation.

Ví dụ user hỏi:

* Khách đánh giá khách sạn này thế nào?
* Điểm dịch vụ bao nhiêu?
* Có sạch không?
* Có đáng tiền không?
* Phù hợp gia đình không?
* Nhược điểm thường gặp là gì?

## Nguồn từ crawl

* `reviews_detail`
* `rating_overall`
* `rating_count`
* `rating_breakdown`
* `reviews_detail.tags`
* `reviews_detail.demographics`
* `word_cloud`
* `sample_comments`

## Schema

```json
{
  "review_reputation_metadata": {
    "overall_score": "number | null",
    "score_text": "string | null",
    "review_count": "integer | null",
    "comments_count": "integer | null",

    "rating_breakdown": {
      "service": "number | null",
      "cleanliness": "number | null",
      "room_comfort_quality": "number | null",
      "facilities": "number | null",
      "value_for_money": "number | null",
      "location": "number | null",
      "food_dining": "number | null"
    },

    "review_topics": [
      {
        "topic_raw": "string",
        "topic_normalized": "string",
        "mentioned": "integer",
        "positive_pct": "number | null"
      }
    ],

    "positive_strength_topics": ["string"],
    "possible_pain_points": [
      {
        "topic": "string",
        "reason": "string",
        "positive_pct": "number | null"
      }
    ],

    "guest_demographics": [
      {
        "guest_type_raw": "string",
        "guest_type_normalized": "string",
        "count": "integer",
        "score": "number | null"
      }
    ],

    "word_cloud": [
      {
        "word": "string",
        "count": "integer"
      }
    ]
  }
}
```

## Example

```json
{
  "review_reputation_metadata": {
    "overall_score": 8.8,
    "score_text": "Tuyệt vời",
    "review_count": 10862,
    "comments_count": 4570,

    "rating_breakdown": {
      "service": 9.1,
      "cleanliness": 9.0,
      "room_comfort_quality": 9.0,
      "facilities": 8.9,
      "value_for_money": 8.9,
      "location": 8.6,
      "food_dining": 8.3
    },

    "review_topics": [
      {
        "topic_raw": "Dịch vụ",
        "topic_normalized": "service",
        "mentioned": 305,
        "positive_pct": 68
      },
      {
        "topic_raw": "Bể bơi",
        "topic_normalized": "pool",
        "mentioned": 217,
        "positive_pct": 83
      },
      {
        "topic_raw": "Gia đình",
        "topic_normalized": "family",
        "mentioned": 112,
        "positive_pct": 95
      }
    ],

    "positive_strength_topics": [
      "pool",
      "beach",
      "family",
      "room_view",
      "kids_facilities",
      "room_size",
      "atmosphere"
    ],

    "possible_pain_points": [
      {
        "topic": "check_in",
        "reason": "positive_pct thấp",
        "positive_pct": 30
      },
      {
        "topic": "transportation",
        "reason": "positive_pct thấp",
        "positive_pct": 28
      },
      {
        "topic": "check_out",
        "reason": "positive_pct thấp",
        "positive_pct": 35
      }
    ],

    "guest_demographics": [
      {
        "guest_type_raw": "Gia đình có trẻ nhỏ",
        "guest_type_normalized": "family_with_kids",
        "count": 3085,
        "score": 8.8
      },
      {
        "guest_type_raw": "Cặp đôi",
        "guest_type_normalized": "couple",
        "count": 1927,
        "score": 9.0
      },
      {
        "guest_type_raw": "Nhóm du khách",
        "guest_type_normalized": "group",
        "count": 1635,
        "score": 9.1
      }
    ],

    "word_cloud": [
      {
        "word": "come back",
        "count": 17
      },
      {
        "word": "swimming pool",
        "count": 15
      },
      {
        "word": "theme park",
        "count": 9
      }
    ]
  }
}
```

---

# Layer 7 — Image / Media Metadata

## Mục đích

Dùng cho UI, visual retrieval và recommendation có ảnh.

Ví dụ user hỏi:

* Cho tôi xem ảnh phòng
* Có ảnh hồ bơi không?
* Có ảnh nhà hàng không?
* Có ảnh bãi biển không?
* Khách sạn này có nhiều ảnh không?

## Nguồn từ crawl

* `image_count`
* `image_urls`
* `images`
* `images[].caption`
* `images[].category`

## Schema

```json
{
  "image_media_metadata": {
    "image_count": "integer",
    "has_room_images": "boolean",
    "has_pool_images": "boolean",
    "has_restaurant_images": "boolean",
    "has_spa_images": "boolean",
    "has_beach_images": "boolean",
    "has_kids_area_images": "boolean",
    "has_nearby_place_images": "boolean",

    "image_categories": ["string"],

    "representative_images": [
      {
        "url": "string",
        "caption": "string | null",
        "category": "hotel | room | facilities | dining | nearby_places | other"
      }
    ]
  }
}
```

## Example

```json
{
  "image_media_metadata": {
    "image_count": 159,
    "has_room_images": true,
    "has_pool_images": true,
    "has_restaurant_images": true,
    "has_spa_images": true,
    "has_beach_images": true,
    "has_kids_area_images": true,
    "has_nearby_place_images": true,

    "image_categories": [
      "hotel",
      "room",
      "facilities",
      "dining",
      "nearby_places"
    ],

    "representative_images": [
      {
        "url": "https://example.com/image1.jpg",
        "caption": "Ngoại cảnh khách sạn",
        "category": "hotel"
      },
      {
        "url": "https://example.com/image2.jpg",
        "caption": "Bể bơi ngoài trời",
        "category": "facilities"
      },
      {
        "url": "https://example.com/image3.jpg",
        "caption": "Phòng nghỉ",
        "category": "room"
      }
    ]
  }
}
```

---

# Layer 8 — Semantic Metadata

## Mục đích

Đây là output của ontology/enrichment, không phải raw crawl.

Dùng cho semantic search và recommendation.

Ví dụ user hỏi:

* Tôi muốn đi với người yêu
* Tôi muốn resort cho gia đình
* Tôi muốn nghỉ dưỡng biển
* Tôi muốn nơi thư giãn
* Tôi muốn gần khu vui chơi cho trẻ em
* Tôi muốn villa riêng tư

## Schema

```json
{
  "semantic_metadata": {
    "travel_style": ["string"],
    "guest_type": ["string"],
    "location_type": ["string"],
    "experience_tags": ["string"],
    "room_experience": ["string"],
    "atmosphere": ["string"]
  }
}
```

## Controlled values = concept_id (ontology v2)

> **Đồng bộ với DA10 ontology (concepts_v2):** controlled values của Layer 8 dùng **concept_id**
> trung tính từ `ontology/core/*.yaml` (NGUỒN SỰ THẬT DUY NHẤT), không phải chuỗi phẳng. Mỗi key
> Layer 8 ánh xạ tới một facet. Một số ý niệm cũ chưa phải concept Core → đánh dấu rõ
> (candidate / quan hệ near / room attribute).

```yaml
# travel_style  <- facet style + price_tier (phong cách + phân khúc)
travel_style:
  - STYLE_LUXURY          # luxury (cảm nhận); phân khúc giá -> PRICE_LUXURY
  - PURPOSE_FAMILY        # family
  - PURPOSE_ROMANTIC      # romantic
  - PURPOSE_WELLNESS      # wellness
  - PURPOSE_BUSINESS      # business
  - SETTING_COASTAL       # beach_holiday (kèm query_expansion -> AMEN_BEACHFRONT)
  - OBJ_RESORT            # resort_vacation
  - PRICE_BUDGET          # budget

# guest_type  <- facet purpose
guest_type:
  - PURPOSE_FAMILY        # family_with_kids, family_with_teens
  - PURPOSE_ROMANTIC      # couple
  - PURPOSE_SOLO          # solo
  - PURPOSE_GROUP         # group_travelers
  - PURPOSE_BUSINESS      # business_traveler
  # senior_traveler -> CHƯA có concept Core; candidate_queue (chờ duyệt)

# location_type  <- facet setting/amenity + quan hệ near
location_type:
  - AMEN_BEACHFRONT       # beachfront
  - SETTING_ISLAND        # island
  - SETTING_CITY_CENTER   # city_center
  - SETTING_COASTAL       # near_beach
  - SETTING_NATURE        # nature_escape
  - AMEN_GOLF             # near_golf (presence golf) — "gần golf" dùng quan hệ near
  # near_theme_park -> KHÔNG phải concept; biểu diễn bằng quan hệ near tới LMK_* (ontology.yaml)

# experience_tags  <- tổ hợp purpose/setting/amenity
experience_tags:
  - PURPOSE_FAMILY        # family_vacation
  - SETTING_COASTAL       # beach_holiday
  - PURPOSE_WELLNESS      # wellness_retreat
  - AMEN_GOLF             # golf_trip
  - PURPOSE_ROMANTIC      # romantic_getaway
  - STYLE_LUXURY          # luxury_escape
  # theme_park_trip -> quan hệ near tới LMK_* (amusement_park); workcation -> candidate_queue

# room_experience  <- amenity room-level + room_metadata (Layer 4) attribute
room_experience:
  - AMEN_PRIVATE_POOL     # private_pool_villa (+ OBJ_VILLA)
  - AMEN_BEACHFRONT       # beachfront_villa  (+ OBJ_VILLA)
  - AMEN_SEA_VIEW         # ocean_view_room
  # large_room / family_room / multi_bedroom_villa -> ATTRIBUTE phòng (room_metadata Layer 4),
  # KHÔNG phải semantic concept. Filter qua room_metadata.min/max_room_size_sqm, has_*_villa.

# atmosphere  <- facet style
atmosphere:
  - STYLE_RELAXING        # relaxing
  - STYLE_QUIET           # quiet, peaceful
  - STYLE_LIVELY          # lively
  # private -> CHƯA có concept Core; candidate_queue (chờ duyệt)
```

## Example

```json
{
  "semantic_metadata": {
    "travel_style": [
      "STYLE_LUXURY",
      "PURPOSE_FAMILY",
      "PURPOSE_WELLNESS",
      "SETTING_COASTAL",
      "OBJ_RESORT"
    ],

    "guest_type": [
      "PURPOSE_FAMILY",
      "PURPOSE_ROMANTIC",
      "PURPOSE_GROUP"
    ],

    "location_type": [
      "AMEN_BEACHFRONT",
      "SETTING_ISLAND",
      "AMEN_GOLF",
      "SETTING_COASTAL"
    ],

    "experience_tags": [
      "PURPOSE_FAMILY",
      "SETTING_COASTAL",
      "PURPOSE_WELLNESS",
      "AMEN_GOLF",
      "PURPOSE_ROMANTIC"
    ],

    "room_experience": [
      "AMEN_PRIVATE_POOL",
      "AMEN_BEACHFRONT",
      "AMEN_SEA_VIEW"
    ],

    "atmosphere": [
      "STYLE_RELAXING",
      "STYLE_QUIET"
    ],

    "_note": "near_theme_park (acc near LMK_VINWONDERS_*) biểu diễn ở Layer 5 nearby_geo + ontology near, không ở đây"
  }
}
```

---

# Layer 9 — Evidence & Traceability Metadata

## Mục đích

Layer này cực kỳ quan trọng để tránh việc semantic tag bị xem là “AI tự bịa”.

Mỗi semantic label nên có:

* confidence
* evidence_fields
* rule_source hoặc model_source
* note nếu bằng chứng yếu

## Schema

```json
{
  "evidence_traceability_metadata": {
    "semantic_evidence": {
      "concept_name": {
        "confidence": "number",
        "evidence_fields": ["string"],
        "evidence_values": ["string"],
        "method": "rule | llm | hybrid | human_verified",
        "note": "string | null"
      }
    },

    "source_trace": {
      "raw_fields_used": ["string"],
      "enrichment_version": "string",
      "ontology_version": "string",
      "processed_at": "datetime"
    }
  }
}
```

## Example

```json
{
  "evidence_traceability_metadata": {
    "semantic_evidence": {
      "PURPOSE_FAMILY": {
        "confidence": 0.95,
        "evidence_fields": [
          "search_filter_metadata.kids_club",
          "search_filter_metadata.kids_pool",
          "reviews_detail.tags.Gia đình",
          "reviews_detail.demographics.family_with_kids_count"
        ],
        "evidence_values": [
          "CLB trẻ em",
          "Bể bơi trẻ em",
          "Gia đình positive_pct=95",
          "Gia đình có trẻ nhỏ count=3085"
        ],
        "method": "hybrid",
        "note": null
      },

      "PURPOSE_WELLNESS": {
        "confidence": 0.9,
        "evidence_fields": [
          "search_filter_metadata.spa",
          "search_filter_metadata.sauna",
          "search_filter_metadata.massage",
          "search_filter_metadata.gym"
        ],
        "evidence_values": [
          "Spa",
          "Xông khô",
          "Mát-xa",
          "Phòng tập"
        ],
        "method": "rule",
        "note": null
      },

      "SETTING_COASTAL": {
        "confidence": 0.95,
        "evidence_fields": [
          "search_filter_metadata.beach_private_beach",
          "location_tags.Bãi biển",
          "reviews_detail.tags.Bãi biển"
        ],
        "evidence_values": [
          "Bãi biển riêng",
          "Bãi biển",
          "Bãi biển positive_pct=88"
        ],
        "method": "hybrid",
        "note": "beach_holiday cũ -> SETTING_COASTAL (+ query_expansion AMEN_BEACHFRONT)."
      },

      "PURPOSE_ROMANTIC": {
        "confidence": 0.72,
        "evidence_fields": [
          "reviews_detail.demographics.couple_score",
          "room_metadata.has_private_pool_villa",
          "search_filter_metadata.beachfront"
        ],
        "evidence_values": [
          "Cặp đôi score=9.0",
          "Private pool villa available",
          "Beachfront/private beach"
        ],
        "method": "hybrid",
        "note": "Không có direct review tag romantic, nên confidence không nên quá cao."
      },

      "STYLE_QUIET": {
        "confidence": 0.55,
        "evidence_fields": [
          "core_metadata.description_full",
          "core_metadata.area",
          "search_filter_metadata"
        ],
        "evidence_values": [
          "Description mentions peaceful/relaxing atmosphere",
          "Hòn Tre island location",
          "Vườn"
        ],
        "method": "llm",
        "note": "Bằng chứng yếu. Cần review mining sâu hơn trước khi dùng làm hard filter."
      }
    },

    "source_trace": {
      "raw_fields_used": [
        "amenities",
        "amenity_groups",
        "amenities_general",
        "amenities_leisure",
        "amenities_dining",
        "useful_info",
        "nearby_places",
        "reviews_detail.tags",
        "reviews_detail.demographics",
        "rooms",
        "images"
      ],
      "enrichment_version": "hotel_enrichment_v1.0",
      "ontology_version": "concepts_v2.0.0",
      "processed_at": "2026-06-03T00:00:00+07:00"
    }
  }
}
```

---

# Layer 10 — Data Quality & Ownership Metadata

## Mục đích

Layer này giúp DA09 biết field nào đáng tin, field nào thiếu, field nào là suy luận.

## Schema

```json
{
  "data_quality_ownership_metadata": {
    "field_quality": {
      "field_name": {
        "status": "available | missing | inferred | partial | uncertain",
        "source": "crawl | rule | llm | human",
        "confidence": "number"
      }
    },

    "missing_fields": ["string"],
    "nullable_fields": ["string"],

    "da10_owned_fields": ["string"],
    "da09_consumed_fields": ["string"],
    "requires_da09_confirmation": ["string"]
  }
}
```

## Example

```json
{
  "data_quality_ownership_metadata": {
    "field_quality": {
      "check_in_from": {
        "status": "available",
        "source": "crawl",
        "confidence": 1.0
      },
      "number_of_rooms": {
        "status": "available",
        "source": "crawl",
        "confidence": 1.0
      },
      "STYLE_QUIET": {
        "status": "inferred",
        "source": "llm",
        "confidence": 0.55
      },
      "PURPOSE_ROMANTIC": {
        "status": "inferred",
        "source": "hybrid",
        "confidence": 0.72
      },
      "cheapest_price": {
        "status": "missing",
        "source": "crawl",
        "confidence": 0.0
      }
    },

    "missing_fields": [
      "cheapest_price",
      "max_occupancy",
      "some_room_prices"
    ],

    "nullable_fields": [
      "cheapest_price",
      "max_occupancy",
      "room_price",
      "review_score_per_some_room_types"
    ],

    "da10_owned_fields": [
      "core_metadata",
      "policy_operation_metadata",
      "search_filter_metadata",
      "room_metadata",
      "nearby_geo_metadata",
      "review_reputation_metadata",
      "image_media_metadata",
      "semantic_metadata",
      "evidence_traceability_metadata",
      "data_quality_ownership_metadata"
    ],

    "da09_consumed_fields": [
      "core_metadata",
      "search_filter_metadata",
      "room_metadata",
      "nearby_geo_metadata",
      "review_reputation_metadata",
      "semantic_metadata",
      "evidence_traceability_metadata"
    ],

    "requires_da09_confirmation": [
      "which fields are hard filters",
      "which fields are ranking features",
      "which semantic labels are allowed in retrieval",
      "minimum confidence threshold for semantic filter"
    ]
  }
}
```

---

# 4. Field Usage Recommendation for DA09

## 4.1 Hard Filter Fields

Các field có thể dùng làm filter cứng vì đến trực tiếp từ crawl hoặc rule rõ ràng:

```yaml
hard_filter_fields:
  - city
  - area
  - star_rating
  - property_type
  - accommodation_type
  - review_score
  - private_beach
  - pool
  - kids_club
  - spa
  - airport_transfer
  - free_parking
  - golf_on_site
  - has_villa
  - has_private_pool_villa
  - has_ocean_view_room
  - check_in_from
  - check_out_until
  # "gần X" KHÔNG dùng field near_* boolean — filter qua nearby_places[] (category + distance):
  - nearby_places.category        # vd category == "beach" / "theme_park" / "golf"
  - nearby_places.place_id        # vd place_id == "LMK_VINWONDERS_NHA_TRANG"
  - nearby_places.distance_km     # kèm ngưỡng, vd distance_km <= 5
```

> **Đã bỏ field `near_*` boolean (near_vinwonders, near_theme_park...):** chúng là anti-pattern —
> mỗi loại/landmark mới phải thêm 1 field → schema phình, không scale. Thay bằng mô hình
> **category + distance** của Layer 5 (`nearby_places[]`). DA09 filter "gần X":
> - theo loại: `any(p.category == "beach" and p.distance_km <= R)`
> - theo landmark cụ thể: `any(p.place_id == "LMK_VINWONDERS_NHA_TRANG" and p.distance_km <= R)`
>
> Thêm landmark/loại mới = thêm phần tử trong data, **0 field schema mới**. (Sẽ thống nhất với DA09 ở buổi chốt contract.)

---

## 4.2 Soft Filter / Boost Fields

Các field nên dùng để boost ranking, không nên dùng làm hard filter ngay:

```yaml
# concept ngữ nghĩa -> dùng concept_id (ontology v2); score/pct -> attribute số (giữ field name)
soft_boost_fields:
  # semantic concept (boost theo điểm match concept vs hotel semantic_profile)
  - PURPOSE_FAMILY        # family
  - PURPOSE_ROMANTIC      # romantic
  - PURPOSE_WELLNESS      # wellness
  - STYLE_LUXURY          # luxury
  - STYLE_RELAXING        # relaxing
  - STYLE_QUIET           # quiet
  # attribute số từ review (không phải concept) — boost trực tiếp
  - rating_breakdown.value_for_money
  - rating_breakdown.service
  - rating_breakdown.cleanliness
  - family_review_positive_pct
  - couple_score
```

---

## 4.3 Fields Không Nên Dùng Làm Filter Cứng

```yaml
# concept SOFT (fact_type=soft trong ontology) — suy luận, không filter cứng
avoid_hard_filter_fields:
  - STYLE_QUIET           # quiet, peaceful
  - PURPOSE_ROMANTIC      # romantic
  - STYLE_LUXURY          # luxury (cảm nhận); khác PRICE_LUXURY (phân khúc, suy từ star -> filter được)
```

Lý do:

* Đây là semantic inference (ontology `fact_type: soft`).
* Một số concept không có bằng chứng trực tiếp từ raw crawl (đến từ review/LLM).
* Nên dùng confidence threshold hoặc ranking boost.
* Quy tắc chung: concept `fact_type: hard` (amenity/location/object_type) -> filter cứng OK;
  concept `fact_type: soft` (style/purpose trải nghiệm) -> chỉ boost.

---

# 5. Gợi ý Query Mapping

## Query 1

User:

```text
Tôi muốn khách sạn gần VinWonders cho gia đình có trẻ nhỏ
```

Mapping:

```json
{
  "hard_filters": {
    "near": {"to": "LMK_VINWONDERS_NHA_TRANG", "distance_km_max": 5},
    "PURPOSE_FAMILY": true
  },
  "boost": {
    "AMEN_KIDS_CLUB": true,
    "AMEN_KIDS_POOL": true,
    "family_positive_pct": "high"
  }
}
```

> Lưu ý: "gần VinWonders" filter qua **quan hệ `near`** trỏ `LMK_*` + ngưỡng khoảng cách (xem §4.1
> ghi chú), KHÔNG dùng field `near_vinwonders`. `PURPOSE_FAMILY` là concept (fact_type soft) —
> ở đây minh họa; thực tế nên là boost, hard filter chỉ khi DA09 xác nhận.

---

## Query 2

User:

```text
Tôi muốn resort có bãi biển riêng và hồ bơi
```

Mapping:

```json
{
  "hard_filters": {
    "private_beach": true,
    "pool": true,
    "accommodation_type": "Resort"
  }
}
```

---

## Query 3

User:

```text
Tôi muốn đi với người yêu, chỗ nào đẹp và riêng tư
```

Mapping:

```json
{
  "hard_filters": {},
  "soft_boost": {
    "PURPOSE_ROMANTIC": true,
    "AMEN_PRIVATE_POOL": true,
    "AMEN_BEACHFRONT": true,
    "couple_score": "high"
  }
}
```

---

## Query 4

User:

```text
Check-in khách sạn này mấy giờ?
```

Mapping:

```json
{
  "qa_fact": "policy_operation_metadata.check_in_from"
}
```

---

## Query 5

User:

```text
Khách sạn này có bao nhiêu phòng?
```

Mapping:

```json
{
  "qa_fact": "policy_operation_metadata.number_of_rooms"
}
```

---

# 6. Những Field DA10 Không Nên Đưa Vào Metadata

Không nên đưa nguyên:

```yaml
do_not_use_as_metadata:
  - full image_urls list
  - full raw room_amenities list for every room
  - raw HTML
  - duplicated description sections
  - tracking/query params from URL
  - raw review comments without processing
```

Nên lưu chúng ở raw data hoặc detail document riêng.

---

# 7. Những Field Nên Lưu Nhưng Không Nên Index Toàn Bộ

```yaml
store_but_do_not_index_fully:
  - full description
  - sample_comments
  - full room_amenities
  - full images
```

Lý do:

* Dữ liệu dài.
* Có thể làm index phình to.
* Nên chunk riêng cho RAG nếu cần.

---


