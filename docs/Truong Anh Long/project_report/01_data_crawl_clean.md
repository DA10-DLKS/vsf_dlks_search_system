# Báo cáo 01 — Data: Crawl & Clean

Hệ thống tìm kiếm khách sạn DA10 lấy dữ liệu thật từ Agoda (không bịa số liệu), chuẩn hóa qua một pipeline nhiều lớp trước khi đưa vào tri thức / index. Báo cáo này mô tả chi tiết hai khâu đầu: **thu thập (crawl)** và **làm sạch (clean)**.

---

## 1. Tổng quan luồng dữ liệu

```
Agoda (GraphQL/REST nội bộ)
      │  crawler/  (Playwright + sniff network)
      ▼
data/raw/hotels/*.json        (520 khách sạn)
data/raw/reviews/*.json       (518 file review)
      │  ingestion/  (clean / dedup / validate)
      ▼
data/cleaned/*.json           (520 hồ sơ sạch)
data/quarantine/              (bản ghi rớt chuẩn — cách ly, không xóa)
```

Số liệu thực tế trong repo:

| Thư mục | Số file | Ý nghĩa |
|---|---|---|
| `data/raw` | ~1040 | hotels + reviews thô |
| `data/raw/reviews` | 518 | review chi tiết theo hotel |
| `data/cleaned` | 520 | hồ sơ khách sạn đã làm sạch (1 file/hotel) |
| `data/quarantine` | 18 | bản ghi bị cách ly do rớt chuẩn |

Phạm vi chốt: **chỉ Việt Nam, 520 khách sạn** (xem ghi chú corpus-scaling). Khách sạn không thuộc VN bị bỏ ngay ở khâu crawl (`filtered_country:`).

---

## 2. Khâu Crawl (`crawler/`)

### 2.1 Một cửa chạy duy nhất

`crawler/main.py` là entry point duy nhất, nhận **2 kiểu đầu vào**:

1. **Link khách sạn** → crawl đúng 1 khách sạn → 1 file JSON.
   ```
   python -m crawler.main "https://www.agoda.com/.../hotel.html?hotel=65153&..."
   ```
2. **Từ khóa** (không phải link) → search hàng loạt → nhiều file.
   ```
   python -m crawler.main "Vinpearl" --limit 5
   python -m crawler.main --keys "Sa Pa,Cần Thơ" --target-total 520
   ```

Tham số chính: `--site` (mặc định `agoda`), `--headful` (hiện trình duyệt), `--limit N`, `--target-total N` (dừng khi đủ tổng số file), `--recrawl` (chạy lại đúng các KS thiếu trường).

### 2.2 Crawl theo từ khóa — pipeline 3 bước trong cùng một tiến trình

`run_batch()` trong [crawler/main.py](crawler/main.py):

- **Bước 1/3 — `crawl_list`**: lấy danh sách khách sạn khớp từ khóa, loại các `hotel_id` đã có file raw (resume an toàn).
- **Bước 2/3 — `resolve_slugs`**: lấy `property_page` (slug) cho từng khách sạn.
- **Bước 3/3 — `crawl_detail`**: lấy chi tiết. **Checkpoint sau mỗi khách sạn** (`save_detail_progress`) → có thể dừng/tiếp tục bất kỳ lúc nào mà không mất tiến độ. Giữa các lần gọi có `time.sleep(random.uniform(*between))` theo `rate_limit.between_details` để tôn trọng tốc độ.

`--target-total` cho phép gom corpus đến đúng một con số (vd 520) qua nhiều từ khóa mà không vượt.

### 2.3 Cơ chế bắt dữ liệu — sniff network, không scrape HTML

Khác với cào HTML giòn, crawler dùng **Playwright** mở trang chi tiết và **bắt các response GraphQL/REST nội bộ** của Agoda. Mỗi nguồn được một parser riêng xử lý (`crawler/parsers/agoda.py`):

| Nguồn (endpoint) | Parser | Dữ liệu lấy ra |
|---|---|---|
| `propertyDetailsSearch` | `parse_property_details` | tên, loại hình, sao, địa chỉ, lat/long, tiện ích (gom nhóm), ảnh (có caption + category), điểm review, nearby_places |
| `room-grid` | `parse_room_grid` | loại phòng, diện tích (m²), sức chứa, loại giường, hướng phòng, tiện nghi phòng, giá (null nếu Agoda không trả — **không bịa**) |
| `HotelReviews` | `parse_reviews` | điểm tổng, grades theo hạng mục, review tags, word cloud, demographics (Cặp đôi/Gia đình/...), comment mẫu |
| `GetSecondaryData` | `parse_secondary` | mô tả đầy đủ (~14k ký tự, đã strip HTML), chính sách, phòng dateless |
| `faq` | `parse_faq` | câu hỏi + trả lời thật (thay placeholder `[hotel_name]`) |
| `activities` | `parse_activities` | hoạt động quanh khu vực |

Điểm đáng chú ý về độ trung thực dữ liệu:

- **Giá có thể null**: Agoda load giá bất đồng bộ; nếu không bắt được, để `price = None` thay vì điền số giả. Giá `0 ₫` cũng quy về null (chưa có giá thật).
- **Fallback grades**: nhiều KS multi-provider không trả `combinedReview.grades` qua `HotelReviews` (grades lazy theo tab) → lấy bù từ `propertyDetailsSearch` (endpoint details luôn về). Đây là logic chống mất dữ liệu, không phải bịa.
- **`suitable_for`** ưu tiên suy từ `demographics` review thật (nhóm khách thực tế đã ở), fallback `contentHighlights`.

### 2.4 Tổng hợp bản ghi — `build_record`

Sau khi gom đủ các nguồn, `build_record` ghép thành 1 record chuẩn, bổ sung các trường tổng hợp:
- alias kiểu "mẫu A" cho đồng đội: `district`/`province`, `rooms`, `rating_overall`, `rating_breakdown`.
- `tags` (gộp highlights + location_tags + view_types + suitable_for).
- `embedding_text`: một đoạn mô tả tổng hợp **chỉ từ trường thật** (tên, sao, địa chỉ, mô tả ngắn, tiện ích, điểm review, loại phòng, nearby) — dùng làm semantic profile cho vector search.
- `_sources_captured`: ghi lại đúng các nguồn đã bắt được (audit).

### 2.5 Recrawl & review

- **Recrawl** (`run_recrawl`): đọc `data/raw/recrawl_queue.json` do `crawler/validate.py` sinh ra (các KS thiếu trường) → crawl lại đúng từng cái → tự validate lại để cập nhật queue. Workflow chuẩn: `crawl → validate → --recrawl`.
- **Review crawler** (hướng riêng): cào review chi tiết/khách sạn, lưu `data/raw/reviews/`; mỗi khách sạn thu được ~100–250 review unique (518 file review trong repo).

---

## 3. Khâu Clean (`ingestion/`)

Lớp ingestion gồm 4 nhóm: **cleaning**, **deduplication**, **validation**, **connectors**.

### 3.1 Cleaning (`ingestion/cleaning/`)

| Module | Vai trò |
|---|---|
| `text_normalizer.py` | Chuẩn hóa văn bản tiếng Việt |
| `html_stripper.py` | Gỡ HTML còn sót (mô tả, chính sách) |
| `amenity_normalizer.py` | Chuẩn hóa tên tiện ích về dạng thống nhất |
| `occupancy_imputer.py` | Suy sức chứa phòng khi thiếu |
| `price_mocker.py` | Sinh giá placeholder (giá thật thường null từ Agoda) |
| `translator.py` | Dịch review không phải tiếng Việt sang tiếng Việt (deep-translator / Google engine) |

**`text_normalizer.py`** — trọng tâm chuẩn hóa, làm theo trình tự xác định:
1. `normalize_unicode` → NFC (gộp dấu tổ hợp, đồng nhất biểu diễn tiếng Việt).
2. `remove_control_chars` → bỏ ký tự điều khiển.
3. `remove_emoji` → bỏ emoji (dải Unicode đầy đủ: flags, emoticons, transport, dingbats, ZWJ, variation selectors).
4. `collapse_whitespace` → gộp khoảng trắng/xuống dòng thừa.
5. `normalize_punctuation` → quy chuẩn dấu gạch (en/em dash → `-`/`---`), nháy cong → nháy thẳng, `…` → `...`, non-breaking space → space.

Mặc định `preserve_case=True` (giữ hoa/thường) vì tên riêng/địa danh tiếng Việt cần case.

> ⚠ Lưu ý quan trọng (đã ghi nhận): bỏ dấu tiếng Việt sinh đồng âm khác thanh (`mạng`→`mang`). Việc fold dấu chỉ làm có kiểm soát ở tầng synonym, không làm thô bạo ở normalize.

### 3.2 Deduplication (`ingestion/deduplication/minhash.py`)

Phát hiện trùng/gần-trùng bằng **MinHash + LSH** (thư viện `datasketch`). Mục tiêu cam kết: **Duplicate Rate < 2%**. Khâu này cung cấp `duplicate_group_count` cho báo cáo chất lượng.

### 3.3 Validation (`ingestion/validation/`)

- **`schema_validator.py`**: định nghĩa trường bắt buộc theo schema quan hệ DA09 — `HOTEL_REQUIRED_FIELDS` (`id`, `name`, `source_url`), `ROOM_REQUIRED_FIELDS`, `NEARBY_PLACE_REQUIRED_FIELDS`, `ACTIVITY_REQUIRED_FIELDS`, kèm `HOTEL_REQUIRED_ALIASES` để chấp nhận tên trường tương đương.
- **`quality_checks.py`**: tính 2 metric cốt lõi và đối chiếu ngưỡng:
  - **Missing Rate < 5%** (`MISSING_RATE_TARGET = 0.05`)
  - **Duplicate Rate < 2%** (`DUPLICATE_RATE_TARGET = 0.02`)

  Trả về `QualityReport` (total_documents, missing_rate, duplicate_rate, missing_by_field, passed_missing, passed_duplicate) → xuất Markdown.

Bản ghi rớt chuẩn không bị xóa mà **đưa vào `data/quarantine/`** (18 bản ghi) — cách ly để rà soát, tránh mất dữ liệu im lặng.

---

## 4. Đầu ra & cam kết chất lượng

- **Đầu ra chuẩn**: `data/cleaned/*.json` (520 hồ sơ, 1 file/hotel) — nguồn cho chunking, indexing, knowledge engineering.
- **Cam kết SLA dữ liệu**: Missing < 5%, Duplicate < 2% (kiểm bằng `quality_checks`).
- **Nguyên tắc trung thực**: không bịa giá, không bịa grades, ghi `_sources_captured` để audit; dữ liệu thiếu → quarantine hoặc recrawl, không vá bằng số giả (trừ `price_mocker` đánh dấu rõ là placeholder).

## 5. Tái lập

```bash
# Crawl theo target
python -m crawler.main --keys "Vinpearl,Mường Thanh,Fusion" --target-total 520

# Kiểm tra & sinh queue recrawl
python -m crawler.validate
python -m crawler.main --recrawl

# Chất lượng (missing/duplicate)
python -m ingestion.validation.quality_checks   # qua runner tương ứng
```
