# API Test Spec V2 - Based on 520 `cleaned_test` Hotels

Tài liệu này dùng để test Swagger/Postman cho backend FastAPI hiện tại.

Nguồn dữ liệu test: 520 file JSON trong `cleaned_test/*.json`, đã sinh ra `insert_data.sql`.

Golden hotel dùng xuyên suốt spec:

```json
{
  "hotel_id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "property_type": "Hotel",
  "accommodation_type": "Resort",
  "star_rating": 5.0,
  "is_luxury": true,
  "review_score": 9.0,
  "review_count": 4121,
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "area": "Hạ Long",
  "city": "Hạ Long",
  "country": "Việt Nam",
  "city_id": 10779,
  "latitude": 20.941213607788086,
  "longitude": 107.02555084228516,
  "check_in_from": "15:00",
  "check_out_until": "12:00"
}
```

Golden related data từ `cleaned_test/hotel_1015998.json`:

- Amenity: `Bàn tiếp tân 24 giờ`
- Amenity category: `Tiện nghi phổ biến`
- Suitability tag: `Cặp đôi`
- Nearby place: `Bến tàu du lịch Bãi Cháy`, type `Bến Cảng và Bến Đò`, distance `0.82`
- Room type id: `7558808`, room name `Phòng Deluxe Có Giường Cỡ King (deluxe king)`
- Activity id: `1587993`, title `[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp`
- Review grade: `Sự thoải mái và chất lượng phòng`, score `9.4`
- Review aspect: `Dịch vụ`, mentioned `146`, positive_pct `74.0`
- First reviewer: `Nak`, country `Hàn Quốc`, rating `10.0`

Assumption để test các endpoint dùng `SERIAL id`:

- Chạy `init_db.sql` trước, sau đó chạy `insert_data.sql` trên database trống.
- Khi đó các bản ghi đầu tiên trong các bảng serial thuộc hotel `1015998`:
  - `hotel_images.id = 1`
  - `reviews.id = 1`
  - `rooms.id = 1`
  - `nearby_places.id = 1`
  - `activities.id = 1`
- Nếu DB của bạn đã import nhiều lần hoặc sequence khác, hãy gọi endpoint list trước rồi dùng `id` trả về cho endpoint detail.

Base URL:

```text
http://localhost:5000
```

Render URL:

```text
https://<render-service-url>
```

Header chung, trừ `/health`:

```http
X-API-Key: <API_SECRET_KEY>
```

## 1. Health

Input:

```http
GET /health
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "status": "OK",
  "version": "2.0.0",
  "message": "OTA Travel Assistant API đang hoạt động bình thường."
}
```

## 2. List Hotels By City

Input:

```http
GET /api/hotels
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "city": "Hạ Long",
  "accommodation_type": "Resort",
  "star_rating_min": 5,
  "review_score_min": 9,
  "is_luxury": true,
  "page": 1,
  "limit": 20,
  "sort_by": "review_score:desc"
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "total_pages": 1,
  "data": [
    {
      "id": 1015998,
      "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "property_type": "Hotel",
      "accommodation_type": "Resort",
      "star_rating": 5.0,
      "is_luxury": true,
      "review_score": 9.0,
      "review_count": 4121,
      "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": 10779,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.941213607788086,
      "longitude": 107.02555084228516,
      "source_url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998&currency=VND&checkIn=2026-06-13&checkOut=2026-06-14&rooms=1&adults=2&children=0",
      "min_room_price": 5000000.0,
      "primary_image": "https://pix8.agoda.net/hotelImages/1015998/-1/5393e9bfae5b5927c4f3f3d2dd5088d7.jpg?ce=0&s=1024x768",
      "amenities": [
        {
          "name": "Bàn tiếp tân 24 giờ"
        }
      ],
      "suitability": [
        {
          "tag": "Cặp đôi"
        }
      ]
    }
  ]
}
```

## 3. List Hotels With Amenity, Suitability, Nearby Place

Input:

```http
GET /api/hotels
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "city": "Hạ Long",
  "amenities": "Bàn tiếp tân 24 giờ",
  "suitable_for": "Cặp đôi",
  "nearby_place_name": "Bến tàu du lịch Bãi Cháy",
  "distance_max_km": 1,
  "sort_by": "distance:asc",
  "page": 1,
  "limit": 10
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 4,
  "page": 1,
  "limit": 10,
  "total_pages": 1,
  "data": [
    {
      "id": 38722254,
      "name": "Khách sạn Radisson Blu Vịnh Hạ Long (Radisson Blu Hotel, Ha Long Bay)",
      "property_type": "Hotel",
      "accommodation_type": "Khách sạn",
      "star_rating": 5,
      "is_luxury": true,
      "review_score": 9.2,
      "review_count": 1272,
      "address": "No. 47, Lot N8-1, Cai Dam Urban Area, Bai Chay, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": 17182,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.9487495422363,
      "longitude": 107.024642944336,
      "description": "Khám Phá Radisson Blu Hotel, Hạ Long Bay",
      "source_url": "https://www.agoda.com/radisson-blu-hotel-ha-long-bay/hotel/h-long-vn.html?hotel=38722254&currency=VND&checkIn=2026-06-16&checkOut=2026-06-17&rooms=1&adults=2&children=0",
      "min_room_price": 4730000,
      "primary_image": "https://pix8.agoda.net/hotelImages/38722254/0/65ac1dfba6d8845340d8a32adca5c8b1.jpeg?s=1024x768",
      "amenities": [
        {
          "id": 124,
          "name": "Bác sĩ y tá trực",
          "category": "Độ sạch sẽ và an toàn",
          "category_id": 5
        },
        {
          "id": 1,
          "name": "Bàn tiếp tân 24 giờ",
          "category": "Tiện nghi phổ biến",
          "category_id": 1
        },
        "..."
      ]
    },
    {
      "id": 31461091,
      "name": "Green bay hotel Ha Long",
      "property_type": "Hotel",
      "accommodation_type": "Khách sạn",
      "star_rating": 2,
      "is_luxury": false,
      "review_score": 9.1,
      "review_count": 467,
      "address": "Sunplaza Grand World, khu 5A, phường Bãi Cháy, Thành Phố Hạ Long M2 - 10, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": 17182,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.9461097717285,
      "longitude": 107.035636901855,
      "description": "Nằm tại vị trí thuận tiện ở Bãi Cháy, Hạ Long, ",
      "source_url": "https://www.agoda.com/green-bay-hotel-ha-long_2/hotel/all/h-long-vn.html?hotel=31461091&currency=VND&checkIn=2026-06-14&checkOut=2026-06-15&rooms=1&adults=2&children=0",
      "min_room_price": 620000,
      "primary_image": "https://q-xx.bstatic.com/xdata/images/hotel/max1024x768/350897237.jpg?k=3a518405ae2966296900b2a76e5e24e6a1059d9168b8811d1f6dbcdff147f128&o=",
      "amenities": [
        {
          "id": 1,
          "name": "Bàn tiếp tân 24 giờ",
          "category": "Tiện nghi phổ biến",
          "category_id": 1
        },
        {
          "id": 88,
          "name": "Bảo vệ 24 giờ",
          "category": "Dễ dàng tiếp cận",
          "category_id": 10
        },
        "..."
      ]
    },
    {
      "id": 36224135,
      "name": "Khách sạn Sunland Hạ Long (Sunland HaLong Hotel)",
      "property_type": "Hotel",
      "accommodation_type": "Khách sạn",
      "star_rating": 3,
      "is_luxury": false,
      "review_score": 8.8,
      "review_count": 1780,
      "address": "E421 Sun Plaza Sunworld, Bãi Cháy, Thành phố Hạ Long, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": 17182,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.9489072961545,
      "longitude": 107.037032378813,
      "description": "Khám phá Sunland HaLong Hotel: Nơi lưu trú lý c",
      "source_url": "https://www.agoda.com/new-sun-ha-long-hotel/hotel/ha-long-vn.html?hotel=36224135&currency=VND&checkIn=2026-06-13&checkOut=2026-06-14&rooms=1&adults=2&children=0",
      "min_room_price": 910000,
      "primary_image": "https://pix8.agoda.net/hotelImages/36224135/-1/fe19cdecf9a4ab2abce82db71ed36c4b.jpg?ce=0&s=1024x768",
      "amenities": [
        {
          "id": 124,
          "name": "Bác sĩ y tá trực",
          "category": "Độ sạch sẽ và an toàn",
          "category_id": 5
        },
        {
          "id": 2872,
          "name": "Bãi chơi bowling",
          "category": "Thư giãn & Vui chơi giải trí",
          "category_id": 4
        },
        "..."
      ],
      "suitability": [
        {
          "id": 3097,
          "tag": "Cặp đôi",
          "mention_count": 765,
          "score": 9.3
        },
        {
          "id": 3101,
          "tag": "Nhóm du khách",
          "mention_count": 259,
          "score": 9
        },
        {
          "id": 3096,
          "tag": "Khách đi công tác",
          "mention_count": 6,
          "score": 8.6
        },
        {
          "id": 3099,
          "tag": "Gia đình có trẻ nhỏ",
          "mention_count": 333,
          "score": 8.4
        },
        {
          "id": 3100,
          "tag": "Gia đình có thanh thiếu niên",
          "mention_count": 17,
          "score": 8.3
        },
        {
          "id": 3098,
          "tag": "Khách du lịch một mình",
          "mention_count": 110,
          "score": 8.1
        }
      ]
    },
    {
      "id": 1015998,
      "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "property_type": "Hotel",
      "accommodation_type": "Resort",
      "star_rating": 5,
      "is_luxury": true,
      "review_score": 9,
      "review_count": 4121,
      "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": null,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.9412136077881,
      "longitude": 107.025550842285,
      "description": "Vinpearl Resort & Spa Hạ Long - Nghỉ dưỡng tuyệt vời tại Hạ Long...",
      "source_url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998&currency=VND&checkIn=2026-06-13&checkOut=2026-06-14&rooms=1&adults=2&children=0",
      "min_room_price": 5000000,
      "primary_image": "https://pix8.agoda.net/hotelImages/1015998/-1/5393e9bfae5b5927c4f3f3d2dd5088d7.jpg?ce=0&s=1024x768",
      "amenities": [
        {
          "id": 2,
          "name": "Bãi biển riêng",
          "category": "Tiện nghi phổ biến",
          "category_id": 1
        },
        {
          "id": 104,
          "name": "Ban công sân hiên",
          "category": "Có trong tất cả phòng",
          "category_id": 12
        },
        "..."
      ],
      "suitability": [
        {
          "id": 2,
          "tag": "Cặp đôi",
          "mention_count": 368,
          "score": 9.2
        },
        {
          "id": 5,
          "tag": "Gia đình có thanh thiếu niên",
          "mention_count": 227,
          "score": 9.2
        },
        {
          "id": 4,
          "tag": "Gia đình có trẻ nhỏ",
          "mention_count": 359,
          "score": 9.2
        },
        {
          "id": 6,
          "tag": "Nhóm du khách",
          "mention_count": 101,
          "score": 9.2
        },
        {
          "id": 3,
          "tag": "Khách du lịch một mình",
          "mention_count": 40,
          "score": 8.9
        },
        {
          "id": 1,
          "tag": "Khách đi công tác",
          "mention_count": 68,
          "score": 8.8
        }
      ]
    }
  ]
}

```

## 4. Compare Hotels

Input:

```http
GET /api/hotels/compare
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "ids": "1015998,4947690"
}
```

Expected status: `200`

Expected output:

```json
{
  "hotels": [
    {
      "id": 1015998,
      "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "city": "Hạ Long",
      "accommodation_type": "Resort",
      "review_score": 9.0,
      "..."
    },
    {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
      "city": "Đà Nẵng",
      "accommodation_type": "Khách sạn",
      "review_score": 8.9,
      "..."
    }
  ]
}
```

## 5. Hotel Detail

Input:

```http
GET /api/hotels/1015998
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "property_type": "Hotel",
  "accommodation_type": "Resort",
  "star_rating": 5.0,
  "is_luxury": true,
  "review_score": 9.0,
  "review_count": 4121,
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "city": "Hạ Long",
  "area": "Hạ Long",
  "country": "Việt Nam",
  "images": [
    {
      "hotel_id": 1015998,
      "is_primary": true
    }
  ],
  "policy": {
    "hotel_id": 1015998,
    "check_in_from": "15:00",
    "check_out_until": "12:00",
    "service_fee_pct": 5.0,
    "pet_policy": "Không được phép đưa thú nuôi vào",
    "deposit_required": false
  },
  "amenities": [
    {
      "name": "Bàn tiếp tân 24 giờ"
    }
  ],
  "suitability": [
    {
      "suitable_for_tag": "Cặp đôi"
    }
  ],
  "review_grades": [
    {
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4
    }
  ],
  "review_aspects": [
    {
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0
    }
  ],
  "reviews": [
    {
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0
    }
  ],
  "rooms": [
    {
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)"
    }
  ],
  "nearby_places": [
    {
      "name": "Bến tàu du lịch Bãi Cháy",
      "distance_km": 0.82
    }
  ],
  "activities": [
    {
      "activity_id": 1587993
    }
  ]
}
```

## 6. Hotel Images

Input:

```http
GET /api/hotels/1015998/images
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "images": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "url": "https://pix8.agoda.net/hotelImages/1015998/-1/5393e9bfae5b5927c4f3f3d2dd5088d7.jpg?ce=0&s=1024x768",
      "is_primary": true
    }
  ]
}
```

## 7. Hotel Policies

Input:

```http
GET /api/hotels/1015998/policies
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "check_in_from": "15:00",
  "check_out_until": "12:00",
  "service_fee_pct": 5,
  "child_policy": "Không có thông tin",
  "pet_policy": "Không được phép đưa thú nuôi vào",
  "deposit_required": false,
  "policy_notes": [
    "Giường phụ và Phụ phí cho người ở thêm",
    "Sẽ có phụ phí bắt buộc cho tiệc tối Gala Giáng sinh và Năm mới. Phụ phí này không bao gồm trong giá phòng.",
    "Quý khách vui lòng cung cấp giấy tờ tùy thân hợp lệ do chính phủ quy định (ví dụ: hộ chiếu, chứng minh nhân dân, bằng lái xe, v.v.) khi nhận phòng. Đối với trẻ em, vui lòng cung cấp giấy khai sinh. Nếu không có giấy khai sinh, trẻ em dưới 140 cm sẽ được coi là trẻ em từ 4 – 12 tuổi..."
  ]
}
```

## 8. Hotel Amenities

Input:

```http
GET /api/hotels/1015998/amenities
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "amenities": [
    {
      "hotel_id": 1015998,
      "amenity_id": 1,
      "name": "Bàn tiếp tân 24 giờ",
      "category": "Tiện nghi phổ biến",
      "category_id": 1,
      "category_name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 9. Hotel Suitability

Input:

```http
GET /api/hotels/1015998/suitability
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "suitability": [
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Khách đi công tác"
    },
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Cặp đôi"
    }
  ]
}
```

## 10. Hotel Reviews Bundle

Input:

```http
GET /api/hotels/1015998/reviews
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 10,
  "page": 1,
  "limit": 20,
  "total_pages": 1,
  "data": [
    {
      "hotel_id": 1015998,
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0,
      "title": "Vịnh Hạ Long hòn đảo xinh đẹp"
    }
  ],
  "grades": [
    {
      "hotel_id": 1015998,
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4
    }
  ],
  "aspects": [
    {
      "hotel_id": 1015998,
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0
    }
  ]
}
```

## 11. Hotel Rooms

Input:

```http
GET /api/hotels/1015998/rooms
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "min_occupancy": 2,
  "room_view": "Hướng Vườn",
  "price_max": 5000000,
  "sort_by": "price:asc",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
      "price": 5000000.0,
      "room_size": "38 m²",
      "max_occupancy": 3,
      "bed_type": "1 giường lớn",
      "room_view": "Hướng Vườn",
      "review_score": 9.353
    }
  ]
}
```

## 12. Hotel Nearby Places

Input:

```http
GET /api/hotels/1015998/nearby-places
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "type": "Bến Cảng và Bến Đò",
  "distance_max_km": 1
}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "nearby_places": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "name": "Bến tàu du lịch Bãi Cháy",
      "type": "Bến Cảng và Bến Đò",
      "distance_km": 0.82,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 13. Hotel Activities

Input:

```http
GET /api/hotels/1015998/activities
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "price_max": 1000000,
  "review_score_min": 4.5,
  "sort_by": "review_score:desc"
}
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "activities": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
      "price_amount": 853886.0,
      "review_score": 4.9,
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 14. Hotel Location

Input:

```http
GET /api/hotels/1015998/location
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "city": "Hạ Long",
  "city_id": 10779,
  "area": "Hạ Long",
  "country": "Việt Nam",
  "latitude": 20.941213607788086,
  "longitude": 107.02555084228516,
  "nearby_places": [
    {
      "name": "Bến tàu du lịch Bãi Cháy",
      "distance_km": 0.82
    }
  ]
}
```

## 15. Hotel Text Chunks

Input:

```http
GET /api/hotels/1015998/text-chunks
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "include_embedding": false
}
```

Expected status: `200`

Expected output vì bạn chưa insert bảng `text_chunks`:

```json
{
  "hotel_id": 1015998,
  "text_chunks": []
}
```

## 16. Similar Hotels

Input:

```http
GET /api/hotels/1015998/similar
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "limit": 5
}
```

Expected status: `200`

Expected output:

```json
{
  "reference_hotel": {
    "id": 1015998,
    "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
    "city": "Hạ Long",
    "accommodation_type": "Resort",
    "min_room_price": 5000000.0
  },
  "similar_hotels": []
}
```

Nếu trong 520 khách sạn có resort khác cùng `city`, `accommodation_type`, và khoảng giá tương đương, `similar_hotels` sẽ là mảng có phần tử.

## 17. Global Rooms

Input:

```http
GET /api/rooms
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "city": "Hạ Long",
  "min_occupancy": 2,
  "price_max": 5000000,
  "sort_by": "price:asc",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
      "price": 5000000.0,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 18. Room Detail

Input:

```http
GET /api/rooms/1
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "room_type_id": 7558808,
  "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
  "price": 5000000.0,
  "room_size": "38 m²",
  "max_occupancy": 3,
  "bed_type": "1 giường lớn",
  "room_view": "Hướng Vườn",
  "review_score": 9.353,
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 19. Global Nearby Places

Input:

```http
GET /api/nearby-places
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "city": "Hạ Long",
  "name": "Bến tàu du lịch Bãi Cháy",
  "type": "Bến Cảng và Bến Đò",
  "distance_max_km": 1,
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "name": "Bến tàu du lịch Bãi Cháy",
      "type": "Bến Cảng và Bến Đò",
      "distance_km": 0.82,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 20. Place Categories

Input:

```http
GET /api/place-categories
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Bến Cảng và Bến Đò"
    }
  ]
}
```

## 21. Global Activities

Input:

```http
GET /api/activities
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "city": "Hạ Long",
  "title": "Diamond Era",
  "price_max": 1000000,
  "review_score_min": 4.5,
  "sort_by": "review_score:desc",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
      "price_amount": 853886.0,
      "review_score": 4.9,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 22. Activity Detail

Input:

```http
GET /api/activities/1
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "activity_id": 1587993,
  "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
  "price_amount": 853886.0,
  "review_score": 4.9,
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 23. Amenity Categories

Input:

```http
GET /api/amenity-categories
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 24. Amenities

Input:

```http
GET /api/amenities
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "name": "Bàn tiếp tân 24 giờ",
  "category": "Tiện nghi phổ biến",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "name": "Bàn tiếp tân 24 giờ",
      "category": "Tiện nghi phổ biến",
      "category_id": 1,
      "category_name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 25. Global Hotel Suitability

Input:

```http
GET /api/hotel-suitability
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "tag": "Cặp đôi",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Cặp đôi",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 26. Global Reviews

Input:

```http
GET /api/reviews
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "rating_min": 10,
  "reviewer_country": "Hàn Quốc",
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0,
      "title": "Vịnh Hạ Long hòn đảo xinh đẹp",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 27. Review Detail

Input:

```http
GET /api/reviews/1
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "reviewer_name": "Nak",
  "reviewer_country": "Hàn Quốc",
  "rating": 10.0,
  "title": "Vịnh Hạ Long hòn đảo xinh đẹp",
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 28. Review Grades

Input:

```http
GET /api/review-grades
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "grade_name": "Sự thoải mái và chất lượng phòng"
}
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel_id": 1015998,
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 29. Review Aspects

Input:

```http
GET /api/review-aspects
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "aspect_name": "Dịch vụ"
}
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel_id": 1015998,
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 30. Global Text Chunks

Input:

```http
GET /api/text-chunks
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "hotel_id": 1015998,
  "chunk_type": "hotel_overview",
  "include_embedding": false,
  "page": 1,
  "limit": 20
}
```

Expected status: `200`

Expected output vì bạn chưa insert bảng `text_chunks`:

```json
{
  "total": 0,
  "page": 1,
  "limit": 20,
  "total_pages": 0,
  "data": []
}
```

## 31. Hotel Combo

Input:

```http
GET /api/hotels/1015998/combo
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "nights": 2,
  "guests": 2,
  "include_activities": true
}
```

Expected status: `200`

Expected output:

```json
{
  "hotel": {
    "id": 1015998,
    "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)"
  },
  "room": {
    "id": 1,
    "hotel_id": 1015998,
    "room_type_id": 7558808,
    "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
    "price": 5000000.0,
    "max_occupancy": 3
  },
  "nights": 2,
  "guests": 2,
  "activities": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "price_amount": 853886.0,
      "review_score": 4.9
    }
  ],
  "room_total": 10000000.0,
  "activities_total": 1707772.0,
  "estimated_total": 11707772.0
}
```

## 32. Combo Suggest

Input:

```http
GET /api/hotels/combo-suggest
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "city": "Hạ Long",
  "budget_total": 12000000,
  "guests": 2,
  "nights": 2,
  "suitable_for": "Cặp đôi",
  "limit": 5
}
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel": {
        "id": 1015998,
        "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
        "city": "Hạ Long",
        "room_id": 1,
        "room_name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
        "room_price": 5000000.0,
        "max_occupancy": 3,
        "room_view": "Hướng Vườn",
        "bed_type": "1 giường lớn"
      },
      "room": {
        "id": 1,
        "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
        "price": 5000000.0,
        "max_occupancy": 3,
        "room_view": "Hướng Vườn",
        "bed_type": "1 giường lớn"
      },
      "activities": [
        {
          "activity_id": 1587993,
          "price_amount": 853886.0
        }
      ],
      "room_total": 10000000.0,
      "activities_total": 1707772.0,
      "estimated_total": 11707772.0,
      "remaining_budget": 292228.0
    }
  ]
}
```

## Negative Tests

### 33. Missing API Key

Input:

```http
GET /api/hotels
```

Query JSON:

```json
{}
```

Expected status: `401`

Expected output:

```json
{
  "detail": "Invalid or missing API Key. Provide it via 'X-API-Key' header."
}
```

### 34. Hotel Not Found

Input:

```http
GET /api/hotels/999999999
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{}
```

Expected status: `404`

Expected output:

```json
{
  "detail": "Không tìm thấy khách sạn."
}
```

### 35. Invalid Compare IDs

Input:

```http
GET /api/hotels/compare
X-API-Key: <API_SECRET_KEY>
```

Query JSON:

```json
{
  "ids": "abc,xyz"
}
```

Expected status: `400`

Expected output:

```json
{
  "detail": "ids phải chứa ít nhất một số nguyên."
}
```

