# Validation Rules — Kiểm định schema & chất lượng

> Owner: Đỗ Minh Hiếu (Data Quality)
> Schema nguồn: `contracts/data_schema.json` (dựa trên `relational_schema.md` từ DA09)
> Metric cam kết: **Missing Rate < 5%**, **Duplicate Rate < 2%**

## 1. Kiến trúc validate

Mỗi hotel JSON đầu vào được validate ở 2 cấp:

```
Cấp 1: Hotel document (top-level)
  ├── required: id, name, source_url
  └── optional: accommodation_type, star_rating, …, reviews_detail

Cấp 2: Sub-documents (nested arrays)
  ├── rooms[]        → required: hotel_id, name
  ├── nearby_places[] → required: hotel_id, name
  └── activities[]   → required: hotel_id, title
```

## 2. Required fields — Error (drop doc nếu thiếu)

### 2.1 Hotel level

| Field | Type | Ràng buộc | Lý do |
|---|---|---|---|
| `id` | integer | PRIMARY KEY, NOT NULL | Định danh duy nhất |
| `name` | string | VARCHAR(255), NOT NULL | Tìm kiếm & hiển thị |
| `source_url` | string | TEXT, NOT NULL | Trích dẫn nguồn |

### 2.2 Room level (trong `rooms[]`)

| Field | Type | Ràng buộc |
|---|---|---|
| `hotel_id` | integer | FK → hotels.id |
| `name` | string | VARCHAR(255), NOT NULL |

### 2.3 Nearby place level (trong `nearby_places[]`)

| Field | Type | Ràng buộc |
|---|---|---|
| `hotel_id` | integer | FK → hotels.id |
| `name` | string | VARCHAR(255), NOT NULL |

### 2.4 Activity level (trong `activities[]`)

| Field | Type | Ràng buộc |
|---|---|---|
| `hotel_id` | integer | FK → hotels.id |
| `title` | string | VARCHAR(255), NOT NULL |

## 3. Type & format checks — Warning (giữ doc, flag)

### 3.1 Numeric constraints

| Field | Min | Max | Step | Ghi chú |
|---|---|---|---|---|
| `star_rating` | 1.0 | 5.0 | 0.5 | Hotel rating |
| `review_score` | 0 | 10 | 0.1 | Hotel / room / activity |
| `latitude` | -90 | 90 | – | WGS84 |
| `longitude` | -180 | 180 | – | WGS84 |
| `price` / `price_amount` | 0 | – | – | VND |
| `distance_km` | 0 | – | – | Nearby place |
| `max_occupancy` | 1 | – | – | Số người |

Vi phạm → **warning**, không drop.

### 3.2 Format checks

| Field | Format | Ví dụ |
|---|---|---|
| `crawled_at` | ISO 8601 | `"2026-06-02T14:53:46"` |
| `images[]` | URI (https) | `"https://pix8.agoda.net/..."` |

### 3.3 Array checks

| Field | Expected type | Ghi chú |
|---|---|---|
| `amenities` | `array[string]` | Nếu là string → warning |
| `images` | `array[string (uri)]` | Nếu là array[object] → cảnh báo |
| `useful_info` | `object` (JSONB) | Nếu là string → warning |
| `reviews_detail` | `object` (JSONB) | Nếu là string → warning |
| `policyNotes` | `array[string]` | Nếu missing → warning |

## 4. Quy tắc riêng theo doc_type

Không có field `doc_type` trong schema. Thay vào đó, `accommodation_type` đóng vai trò phân loại:

| `accommodation_type` | Validation mở rộng |
|---|---|
| `"Resort"`, `"Khách sạn"`, `"Hotel"` | Bắt buộc có `star_rating`, `review_score`, `review_count` → warning nếu thiếu |
| `"Biệt thự"`, `"Villa"`, `"Homestay"` | `star_rating` optional |
| Thiếu / rỗng | Warning — không drop |

## 5. Đo Missing Rate

- **Công thức:** `missing_count / (total_hotels × num_required_fields_hotel)`
- Required fields hotel: `["id", "name", "source_url"]` (3 field)
- Cảnh báo khi `> 3%` (gần ngưỡng 5%)
- Báo cáo `missing_by_field` chi tiết theo từng field

## 6. Đo Duplicate Rate

- Dùng kết quả từ `scripts/dedup_pipeline.py` (`data/dedup_groups.json`)
- So sánh trên `description` và `name` sau khi clean
- **Công thức:** `số_doc_bị_loại_vì_trùng / total_hotels`
- Ngưỡng Jaccard mặc định: `≥ 0.85`

## 7. Quarantine

- Doc lỗi error → ghi vào `data/quarantine/hotels/` + lý do
- Doc cảnh báo warning → giữ nguyên, flag trong `metadata.validation_warnings`

## 8. Tham chiếu

| File | Vai trò |
|---|---|
| `contracts/data_schema.json` | JSON schema đầy đủ |
| `docs/relational_schema.md` | Schema gốc từ DA09 (PostgreSQL) |
| `ingestion/validation/schema_validator.py` | Code validate |
| `ingestion/validation/quality_checks.py` | Code đo missing rate + duplicate rate |
| `scripts/validation_pipeline.py` | Pipeline orchestration |
| `quality_report_mock.md` | Báo cáo mock (Sprint 2) |
| `data_quality_report.md` | Báo cáo real (Sprint 3) |
