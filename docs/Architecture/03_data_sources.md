# 03 – Nguồn dữ liệu (Layer 1)

Dữ liệu du lịch được crawl từ web bởi `crawler/`.

## Nguồn hiện tại

| Nguồn | Thư mục | Ghi chú |
|---|---|---|
| Agoda | `crawler/spiders/agoda.py` | Hotels, rooms, reviews, amenities |

## Loại dữ liệu

| Loại | Ví dụ | Nguồn |
|---|---|---|
| Hotel info | tên, địa chỉ, hạng sao, tiện ích | Agoda hotel detail |
| Room types | tên phòng, giá, sức chứa, diện tích | Agoda room-grid |
| Reviews | đánh giá của khách hàng (positives/negatives) | Agoda reviews |
| Amenities | tiện nghi khách sạn (WiFi, pool, spa...) | Agoda amenities |
| Nearby places | điểm tham quan gần khách sạn | Agoda nearby |
| Activities | hoạt động du lịch | Agoda activities |

## Cấu trúc dữ liệu thô

```
data/raw/hotels/
├── hotel_65153.json      # Hotel detail + rooms + reviews
├── hotel_12345.json
└── ...

Mỗi file JSON chứa:
- title, star_rating, location (city, province, country)
- amenities[], amenities_general[]
- rooms[] (room_type_id, name, price_per_night, bed_type, max_occupancy)
- reviews[] (author, rating, text, positives, negatives, response)
```

## Tần suất crawl

- Agoda: crawl theo batch (không realtime)
- Dữ liệu được làm sạch và export qua `ingestion/` trước khi dùng
