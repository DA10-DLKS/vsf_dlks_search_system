# Đề xuất Data Schema cho DA10 — Bản gửi DA09 review

> **Tác giả:** Đỗ Minh Hiếu (Data Quality, DA10)
> **Mục đích:** Đề xuất schema document mục tiêu để DA09 review và chốt.
> **Cơ sở:** Crawl thử nghiệm 27 khách sạn Vinpearl từ Agoda (`data/raw/hotels/`).
> **Deadline đề xuất:** Cuối Tuần 1 Sprint 1.

## 1. Nguyên tắc

- Schema này là **TARGET** — document sau khi DA10 xử lý (làm sạch, validate, khử trùng lặp) sẽ có shape này.
- Crawl data có thể chứa nhiều field hơn → `ingestion/` sẽ **giữ field hợp lệ, drop field không nằm trong schema** (trừ `_raw` backup).
- Tất cả text field phải qua `cleaning/` (strip HTML, normalize Unicode, collapse whitespace).
- Mỗi document được định danh duy nhất bằng `id`.

## 2. Schema đề xuất

### 2.1 Core fields — bắt buộc (required)

Những field này phải có ở **mọi document**; nếu thiếu → doc bị quarantine (error).

| Field | Type | Format / Ràng buộc | Ví dụ | Ghi chú |
|---|---|---|---|---|
| `id` | `string` | UUID `doc_<uuid>` | `doc_a1b2c3d4` | Định danh duy nhất, ổn định qua các pipeline |
| `doc_type` | `string` | enum: `"hotel"`, `"resort"`, `"villa"`, `"attraction"`, `"faq"`, `"review"`, `"article"` | `"hotel"` | Dùng để chọn validation rule & ontology mapping |
| `source` | `string` | domain crawl | `"agoda.com"` | Nguồn gốc dữ liệu |
| `source_url` | `string` | URI, **required** | `"https://www.agoda.com/..."` | Dùng để trích dẫn nguồn |
| `crawled_at` | `string` | ISO 8601 datetime | `"2026-06-02T14:53:46"` | Thời điểm crawl |
| `name` | `string` | min 1, max 300 | `"Vinpearl Resort Nha Trang"` | Tên khách sạn / điểm đến |
| `description` | `string` | min 1, đã strip HTML | `"Vinpearl Resort Nha Trang - Kỳ nghỉ tuyệt vời..."` | Nội dung chính → embedding & BM25 |
| `language` | `string` | enum: `"vi"`, `"en"` | `"vi"` | Mặc định `"vi"` |

### 2.2 Location fields — khuyến nghị (recommended)

| Field | Type | Format / Ràng buộc | Ví dụ | Coverage (trên 27 hotel) |
|---|---|---|---|---|
| `address` | `string` | - | `"Đảo Hòn Tre, Nha Trang"` | 100% |
| `city` | `string` | - | `"Nha Trang"` | 100% |
| `province` | `string` | - | `"Khánh Hòa"` | 100% |
| `district` | `string` | - | `"Hòn Tre"` | 100% |
| `latitude` | `number` | WGS84, -90..90 | `12.2215` | 100% |
| `longitude` | `number` | WGS84, -180..180 | `109.2463` | 100% |
| `country` | `string` | - | `"Việt Nam"` | 100% |
| `postal_code` | `string` | - | `"650000"` | 100% |

### 2.3 Property-specific fields — tuỳ chọn (optional)

Tuỳ `doc_type` mà các field này có hoặc không. Nếu thiếu → **warning**, không drop.

| Field | Type | Ràng buộc | Áp dụng cho | Ví dụ |
|---|---|---|---|---|
| `star_rating` | `number` | 1.0 – 5.0 (step 0.5) | hotel/resort/villa | `5.0` |
| `property_type` | `string` | - | hotel/resort/villa | `"Hotel"`, `"Resort"` |
| `accommodation_type` | `string` | - | hotel/resort/villa | `"Khách sạn"`, `"Resort"` |
| `review_score` | `number` | 0 – 10 | hotel/resort/villa/attraction | `8.7` |
| `review_count` | `integer` | >= 0 | hotel/resort/villa/attraction | `8281` |
| `check_in_from` | `string` | HH:MM | hotel/resort/villa | `"15:00"` |
| `check_out_until` | `string` | HH:MM | hotel/resort/villa | `"12:00"` |
| `number_of_rooms` | `integer` | >= 0 | hotel/resort/villa | `533` |
| `number_of_floors` | `integer` | >= 0 | hotel/resort/villa | `5` |
| `year_built` | `string` | năm YYYY | hotel/resort/villa | `"2003"` |
| `amenities` | `array[string]` | - | hotel/resort/villa | `["Hồ bơi", "Wifi miễn phí", ...]` |
| `image_urls` | `array[string]` | URI | tất cả | `["https://...jpg", ...]` |
| `is_luxury` | `boolean` | - | hotel/resort/villa | `false` |

### 2.4 Nested / enriched fields

Những field này là kết quả của pipeline ingestion (do DA10 tự xử lý), không phải từ crawl thô.

| Field | Type | Mô tả | Pipeline xử lý |
|---|---|---|---|
| `metadata` | `object` | metadata đã làm giàu (theo `metadata_schema.yaml`, do Long phụ trách) | knowledge_engineering/ |
| `embedding_ids` | `object` | reference đến chunk ID trong vector store | indexing/embedding |
| `cleaned_at` | `string` | timestamp pipeline ingestion chạy | ingestion/ |
| `cleaning_version` | `string` | version của cleaning rules đã áp dụng | ingestion/ |
| `dedup_group_id` | `string` | nếu doc bị gom vào nhóm trùng | ingestion/deduplication |

## 3. So sánh coverage trên crawl thật

Để DA09 dễ hình dung: dưới đây là field coverage từ **27 hotel Agoda** hiện có.

### 3.1 100% coverage — có thể coi là required

```
crawled_at, source_url, hotel_id, name, property_type,
accommodation_type, star_rating, is_luxury, review_score,
review_count, address, area, city, country, postal_code,
latitude, longitude, description, check_in_from,
check_out_until, year_built, number_of_floors, number_of_rooms,
image_count, amenities_count, district, province, image_urls,
amenities, amenity_groups, highlights, location_tags,
nearby_places, room_grid, rooms, useful_info, secondary, tags,
suitable_for, faq, activities, view_types, _sources_captured,
embedding_text
```

### 3.2 < 100% coverage (cần quyết định: required hay optional?)

| Field | Coverage | Lý do thiếu |
|---|---|---|
| `reviews_detail` | 96% (26/27) | Có thể 1 hotel chưa có review |
| `rating_overall` | 59% (16/27) | Rating lấy từ nguồn khác nhau |
| `rating_count` | 59% (16/27) | Rating lấy từ nguồn khác nhau |
| `rating_breakdown` | 59% (16/27) | Rating breakdown có thể không có cho mọi hotel |

## 4. Đề xuất validation rules

Dựa trên schema này, DA10 (Hiếu) sẽ implement `validation_rules.md` chi tiết. DA09 chỉ cần chốt các mục sau:

### 4.1 Required fields cuối cùng

Dựa vào mục đích của DA10 (Search + Context API), tôi đề xuất **required fields**:

1. `id` — định danh
2. `doc_type` — phân loại
3. `source` — nguồn
4. `source_url` — trích dẫn
5. `name` — tìm kiếm
6. `description` — embedding & full-text search
7. `language` — xử lý ngôn ngữ
8. `crawled_at` — temporal

→ DA09 có muốn thêm / bỏ field nào không?

### 4.2 Search-critical fields (dùng trong retrieval)

Những field này được index riêng để hybrid search hoạt động tốt:

| Field | Index technique | Weight |
|---|---|---|
| `name` | BM25 (boosted) + vector | high |
| `description` | BM25 + vector | high |
| `city`, `province`, `district` | BM25 (filter) | medium |
| `amenities` | BM25 (keyword match) | low |
| `tags`, `suitable_for` | BM25 | medium |

### 4.3 Format constraints cần chốt

| Constraint | Đề xuất | Để DA09 chốt |
|---|---|---|
| Date format | ISO 8601 (`YYYY-MM-DDThh:mm:ss`) | ☐ |
| Price format | `{ "currency": "VND", "amount": 450000 }` | ☐ |
| Language code | `"vi"` / `"en"` | ☐ |
| Coordinate system | WGS84 (lat, lng float) | ☐ |
| Image URL | absolute URL, https | ☐ |
| Rating range | 0–10 (review_score), 1–5 (star_rating) | ☐ |

## 5. Câu hỏi cho DA09

Để chốt schema, DA09 vui lòng trả lời:

1. **Required fields** — Bộ 8 field ở 4.1 có đủ không? Cần thêm `address`, `city`, `latitude`, `longitude` vào required không? (search theo location)
2. **doc_type enum** — `["hotel", "resort", "villa", "attraction", "faq", "review", "article"]` có đủ cho use case của DA09 không?
3. **Field mapping** — DA09 có field nào cần thêm mà Agoda không có? (vd: `description_short`, `price_range`...)
4. **Custom metadata** — DA09 có yêu cầu enrich metadata riêng không? (vd: PII flags, content category tags...)
5. **Format constraints** — Mục 4.3 có gì cần sửa không?

## 6. Timeline

| Mốc | Hành động | Người |
|---|---|---|
| **Tuần 1 Sprint 1** | Gửi proposal này cho DA09 | Đỗ Minh Hiếu |
| **Cuối Tuần 1** | DA09 review + chốt schema | DA09 |
| **Đầu Tuần 2** | DA10 implement validation rules theo schema đã chốt | Đỗ Minh Hiếu |

---

> **Liên hệ:** Đỗ Minh Hiếu — Data Quality, DA10.
> File này: `docs/data_schema_proposal.md`
> Crawl data mẫu: `data/raw/hotels/` (27 hotel Agoda)
