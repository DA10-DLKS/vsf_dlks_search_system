# 04 – Thu nạp & Xử lý dữ liệu (Layer 2)

`ingestion/` biến đầu ra thô của crawler thành tập dữ liệu sạch, đã kiểm định, khử trùng lặp, và sẵn sàng cho downstream (PostgreSQL).

## Kiến trúc Pipeline

```
data/raw/hotels/*.json
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Cleaning (scripts/clean_pipeline.py)                     │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  A. Xử lý văn bản (cho mọi text field)                │   │
│  │  ├── strip_html()      – BeautifulSoup strip HTML     │   │
│  │  ├── normalize_text()  – Unicode NFC + emoji remove    │   │
│  │  └── translate_to_vi() – Deep-Translator → Google     │   │
│  │      (chỉ cho review response không phải tiếng Việt)  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  B. Amenity Normalizer (amenity_normalizer.py)         │   │
│  │  (6 bước: strip bracket → clean text → canonical      │   │
│  │   prefix → fuzzy merge → filter basic → filter gen.)  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  C. Max Occupancy Imputer (occupancy_imputer.py)       │   │
│  │  ├── Dùng max_occupacity_raw → max_occupancy_text      │   │
│  │  ├── Parse bed_type / bed_types (số lượng + loại)      │   │
│  │  └── Fallback 2 người                                  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  D. Price Mocker (price_mocker.py)                     │   │
│  │  ├── price_per_night = base(stars) × brand × room     │   │
│  │  │   × city × size (deterministic, clamp star range)  │   │
│  │  └── original_price = price × discount (MD5 hash)     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Áp dụng cho: amenities, amenities_general/_leisure/_dining,│
│  room_amenities, rooms, room_grid.rooms                      │
└──────────────────────────────┬────────────────────────────┘
                               ▼
                       data/cleaned/hotel_{id}.json
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│  2. Deduplication (scripts/dedup_pipeline.py)            │
│  ├── MinHash + LSH (datasketch)                          │
│  ├── threshold Jaccard ≥ 0.85, 128 permutations          │
│  ├── Language-agnostic (character 5-gram)                │
│  └── Verify bằng exact Jaccard sau LSH query            │
└──────────────────────────────┬───────────────────────────┘
                               ▼
                       data/cleaned/hotel_{id}.json  (ghi đè)
                       data/dedup_groups.json
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│  3. Validation (scripts/validation_pipeline.py)          │
│  ├── schema_validator: validate theo data_schema.json    │
│  │   (required fields, numeric range, format, alias id)  │
│  ├── quality_checks: Missing Rate & Duplicate Rate       │
│  └── Quarantine: invalid docs → data/quarantine/         │
└──────────────────────────────┬───────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│  4. Export → PostgreSQL (scripts/export_db.py)            │
│  ├── Tạo bảng (Alembic migration)                        │
│  ├── INSERT 4 bảng: hotels, rooms, nearby_places,        │
│  │   activities                                           │
│  └── Dedup composite PK trước khi insert                 │
└──────────────────────────────────────────────────────────┘
                               │
                               ▼
                   PostgreSQL (localhost:5432)
                   docs/data_quality_report.md
```

## Modules

### `ingestion/cleaning/text_normalizer.py`
| Function | Kỹ thuật | Mô tả |
|---|---|---|
| `normalize_unicode()` | `unicodedata.normalize("NFC")` | Chuẩn hóa dấu tiếng Việt |
| `remove_control_chars()` | Regex `[\x00-\x08...]` | Loại bỏ ký tự điều khiển |
| `collapse_whitespace()` | Regex multi-space/newline | Chuẩn hóa khoảng trắng |
| `normalize_punctuation()` | Replace Unicode → ASCII | Dấu nháy, gạch ngang, ... |
| `remove_emoji()` | Regex Unicode block | Loại bỏ icon/emoji |
| `normalize_text()` | Combine all above | Pipeline tổng hợp |

### `ingestion/cleaning/html_stripper.py`
- Dùng BeautifulSoup strip HTML tags → plain text
- Extract `image_urls` + `links` từ thẻ `<img>` và `<a>`

### `ingestion/cleaning/amenity_normalizer.py`
Quy trình 6 bước xử lý amenities:

| Step | Kỹ thuật | Input | Output |
|---|---|---|---|---|
| 1. Strip brackets | Regex `\[` / `\]` / `\(` / `\)` | `Wi-Fi [miễn phí]` | `Wi-Fi miễn phí` |
| 2. Clean text | Unicode + suffix removal | `Wi-Fi miễn phí` | `wi-fi miễn phí` |
| 3. Canonical prefix | Regex pattern matching | `wi-fi miễn phí` → `WiFi miễn phí` | Chỉ thay prefix |
| 4. Fuzzy merge | `difflib.SequenceMatcher` (0.80) | `nước đóng chai` + `nước đóng chai miễn phí` | `Nước đóng chai miễn phí` |
| 5. Filter basic | Regex pattern list | `Tiện nghi` → ❌, `Máy sấy tóc` → ❌ | 41 basic items removed |
| 6. Filter generic | Smart word-prefix | `WiFi` → ❌ (nếu có `WiFi miễn phí`); `TV` → ❌ (nếu có `TV màn hình phẳng`) | Chỉ remove khi có specific variant |

### `ingestion/cleaning/translator.py`
- Dùng `deep-translator` (Google Translate engine)
- Cache theo text gốc để tránh dịch lại
- Heuristic detect tiếng Việt (kiểm tra ký tự có dấu)
- Chỉ dịch các field `text`, `title`, `positives`, `negatives`, `response` trong review comments

### `ingestion/cleaning/occupancy_imputer.py`

**Vấn đề:** Crawler không thu thập được `max_occupancy` cho ~90% rooms (đặc biệt là Muong Thanh hotels).

**Giải pháp:** Impute `max_occupancy` qua fallback chain 4 bước:

```
Bước 1: Dùng room.max_occupancy nếu đã có (> 0)
  Ví dụ: Vinpearl rooms → max_occupancy = 3 (giữ nguyên)

Bước 2: Parse room.max_occupancy_text nếu có
  Regex: r"(\d+)" → tìm số đầu tiên
  Ví dụ: "Tối đa 3 người lớn" → 3
         "8 người" → 8

Bước 3: Parse bed_types[] hoặc bed_type nếu 2 bước trên đều null
  Regex từng nhóm: (\d+)\s+giường\s+(loại giường)
  
  Map loại giường → sức chứa 1 người:

  | Loại giường | Sức chứa |
  |---|---|
  | đơn, semi-double | 1 |
  | đôi, lớn, đôi lớn, siêu lớn, king, queen | 2 |
  | tầng (bunk bed) | 2 |
  | sofa giường | 1 |

  Xử lý kết hợp (AND): từ khóa "và" hoặc ","
    "1 giường lớn và 2 giường đơn" → (1 × 2) + (2 × 1) = 4

  Xử lý hoặc (OR): từ khóa "/" hoặc "hoặc"
    "1 giường đôi lớn / 1 giường lớn" → max(2, 2) = 2

  Ví dụ cụ thể:

  | bed_type | Parse | Kết quả |
  |---|---|---|
  | "1 giường lớn" | 1 × 2 (lớn) | 2 |
  | "2 giường đơn" | 2 × 1 (đơn) | 2 |
  | "1 giường đôi" | 1 × 2 (đôi) | 2 |
  | "3 giường đơn" | 3 × 1 (đơn) | 3 |
  | "1 giường siêu lớn" | 1 × 2 (siêu lớn) | 2 |
  | "1 giường lớn và 2 giường đơn" | 2 + 2 | 4 |
  | "1 giường đôi lớn / 1 giường lớn" | max(2, 2) | 2 |
  | null / empty | — | fallback 2 |

Bước 4: Fallback = 2 (đa số phòng khách sạn chứa 2 người)
```

**Kết quả:** 463 rooms — 0% null max_occupancy ✅

### `ingestion/cleaning/price_mocker.py`

**Vấn đề:** Agoda API (`/api/v1/property/room-grid`) không trả giá phòng. Giá được load dynamic bằng JavaScript, crawler không với tới được.

**Giải pháp:** Tạo giá giả (mock) dựa trên đặc điểm của hotel và room, sử dụng MD5 hash để đảm bảo deterministic — cùng hotel_id + room_type_id → luôn ra cùng một giá.

#### Công thức `price_per_night`

```
price = base_mid(stars)
price × brand_factor
price × room_type_factor
price × city_factor
price × size_factor

price = clamp(base_min, base_max)        // giới hạn trong khung sao
price = round(price ÷ 10.000) × 10.000   // làm tròn đến 10k
```

#### Bảng giá cơ sở (VND)

Khung giá theo số sao, dùng `mid` làm starting point:

| Star rating | Min (base_min) | Mid (base_mid) | Max (base_max) |
|---|---|---|---|
| 5★ | 2.000.000 | 3.500.000 | 5.000.000 |
| 4★ | 1.200.000 | 2.100.000 | 3.000.000 |
| 3★ | 600.000 | 1.050.000 | 1.500.000 |
| 2★ | 300.000 | 550.000 | 800.000 |
| 1★ | 200.000 | 350.000 | 500.000 |
| Không có sao | 600.000 (default về 3★) | | |

Nếu sau khi nhân các hệ số, price vượt `base_max` → bị chặn lại. Tương tự nếu dưới `base_min` → kéo lên.

#### Hệ số nhân

**Brand factor** — dựa vào tên hotel:

| Tên chứa | Factor | Ví dụ |
|---|---|---|
| "Vinpearl" hoặc "Meliá"/"Melia" | 1.2× | Vinpearl Resort Nha Trang |
| "Muong Thanh" | 0.9× | Mường Thanh Sài Gòn Centre |
| Còn lại (Boutique, Homestay, ...) | 0.8× | Robins Homestay |

**Room type factor** — dựa vào tên phòng (match substring không phân biệt hoa/thường):

| Tên phòng chứa | Factor | Ví dụ |
|---|---|---|
| "Penthouse" | 2.0× | Penthouse Suite |
| "Suite" | 1.8× | Executive Suite |
| "Villa" | 1.6× | Villa Hồ Bơi |
| "Studio" | 1.4× | Studio Căn Hộ |
| "Deluxe" | 1.3× | Deluxe King Room |
| "Executive" | 1.3× | Executive Room |
| "Premier" | 1.2× | Premier Ocean View |
| "Family" | 1.1× | Family Room |
| "Superior" | 1.0× | Superior Double |
| "Standard" | 0.9× | Standard Twin |
| Không match | 1.0× | — |

**City factor** — dựa vào city của hotel:

| City chứa | Factor | Lý do |
|---|---|---|
| "Phú Quốc", "Nha Trang", "Hạ Long" | 1.3× | Điểm đến du lịch biển cao cấp |
| "Đà Nẵng", "Hội An", "Sầm Sơn", "Phan Thiết", "Đà Lạt" | 1.1× | Điểm đến du lịch phổ biến |
| Còn lại | 1.0× | — |

**Size factor** — dựa vào diện tích phòng:

```
size_factor = max(0.5, min(2.0, sqm / 30))
```

Với 30m² là diện tích chuẩn. Phòng 15m² → factor = 0.5, phòng 60m² → factor = 2.0.

Nếu không có `size_sqm`, parse từ `room_size` (vd: "45 m²" → 45). Nếu không có → factor = 1.0.

#### Công thức `original_price`

Mô phỏng giá gốc trước chiết khấu, dùng MD5 hash để deterministic:

```python
key = f"{hotel_id}_{room_type_id}"
hash_hex = MD5(key.encode()).hexdigest()[:8]
hash_int = int(hash_hex, 16)

discount = 1.2 + (hash_int % 6000) / 10000
# discount luôn nằm trong khoảng [1.20, 1.80]

original_price = round(price_per_night × discount ÷ 10.000) × 10.000
```

Lý do dùng MD5: thay thế `random.uniform(1.2, 1.8)` nhưng vẫn đảm bảo cùng hotel_id + room_type_id luôn ra cùng discount. Dùng 8 ký tự hex đầu (32-bit integer), mod 6000 để lấy phần thập phân, cộng với 1.2.

#### Ví dụ tính toán

**Hotel: Vinpearl Resort Nha Trang (5★), Room: Deluxe King (32m², room_type_id = 13678787)**

```
base_mid = 3.500.000
× brand (Vinpearl)       1.2   → 4.200.000
× room (Deluxe)          1.3   → 5.460.000
× city (Nha Trang)       1.3   → 7.098.000
× size (32/30 = 1.067)  1.067 → 7.571.200

clamp(2.000.000, 5.000.000) → 5.000.000
round 10k                    → 5.000.000  (= price_per_night)

key = "65153_13678787"
MD5 hex[:8] = "a1b2c3d4" → int = 2712849104
discount = 1.2 + (2712849104 % 6000) / 10000
         = 1.2 + 0.4704 = 1.6704

original = 5.000.000 × 1.6704 = 8.352.000 → round 10k → 8.350.000
```

**Hotel: Mường Thanh Sài Gòn Centre (3★), Room: Standard (25m²)**

```
base_mid = 1.050.000
× brand (Muong Thanh)    0.9   → 945.000
× room (mặc định)        1.0   → 945.000
× city (Sài Gòn)         1.0   → 945.000
× size (25/30 = 0.833)   0.833 → 787.500

clamp(600.000, 1.500.000) → 787.500
round 10k                  → 790.000  (= price_per_night)
```

#### Lưu ý

- Giá là **mock data**, không phải giá thật. Mục đích: cho phép các module downstream (search, ranking) có dữ liệu giá để test.
- Deterministic: chạy pipeline lại không làm thay đổi giá của cùng hotel_id / room_type_id.
- Dữ liệu Agoda gốc để `"price": null` — code cleaning xoá hẳn field `price` và thay bằng `price_per_night` + `original_price`.
- Áp dụng cho cả `rooms[]` và `room_grid.rooms[]`.

### `ingestion/validation/schema_validator.py`
- Validate hotel docs theo `contracts/data_schema.json` (DA09's PostgreSQL schema)
- 4 bảng: hotels, rooms, nearby_places, activities
- Alias `id` ↔ `hotel_id` (Agoda dùng `hotel_id`)
- Sub-document FK `hotel_id` implicit nếu parent có ID
- Numeric range checks, format checks (ISO 8601)

### `ingestion/validation/quality_checks.py`
| Metric | Target | Công thức |
|---|---|---|
| Missing Rate | < 5% | `missing_fields / total_required_fields` |
| Duplicate Rate | < 2% | `duplicate_docs / total_docs` |

### `ingestion/deduplication/minhash.py`
- `datasketch` MinHash + LSH
- 128 permutations, Jaccard threshold ≥ 0.85
- Character 5-gram, language-agnostic
- Verify bằng exact Jaccard sau LSH query

## So sánh kỹ thuật

| Kỹ thuật | Library | Use case | Ưu điểm | Nhược điểm |
|---|---|---|---|---|
| **HTML stripping** | BeautifulSoup | Loại bỏ HTML tags khỏi text | Chính xác, xử lý nested tags tốt | Chậm hơn regex thuần |
| **Unicode NFC** | `unicodedata` (built-in) | Chuẩn hóa dấu tiếng Việt | Built-in, zero dependency, nhanh | Không xử lý các dạng tổ hợp đặc biệt |
| **Emoji removal** | Regex Unicode block | Loại bỏ icon trong review | Không cần thêm dependency | Không bắt được 100% emoji mới |
| **Regex cleaning** | `re` (built-in) | Strip brackets, normalize punctuation, loại hậu tố | Nhanh, dễ maintain | Không linh hoạt với pattern phức tạp |
| **Canonical mapping** | Regex pattern match | Gom amenity cùng loại (`máy lạnh` → `Điều hòa`) | Kiểm soát được, dễ thêm mapping | Không tự học được biến thể mới |
| **Fuzzy merge** | `difflib.SequenceMatcher` | Gom amenity tương tự (`WiFi` + `WiFi miễn phí`) | Không cần training data, threshold chỉnh được | Threshold khó chọn, false positive với prefix chung |
| **Translation** | `deep-translator` | Dịch review response → tiếng Việt | Free, không cần API key, nhiều engine | Rate-limit, phụ thuộc internet |
| **MinHash LSH** | `datasketch` | Near-duplicate detection cho text | Scale tốt với hàng triệu doc, language-agnostic | Xác suất (cần verify bằng exact Jaccard) |
| **Schema validation** | Custom dataclass | Kiểm định required fields, range, format | Tùy chỉnh được theo schema | Phải maintain schema đồng bộ với DA09 |
| **Occupancy imputation** | Regex + heuristics | Fill max_occupancy từ bed_type | Zero dependency | Không chính xác với bed_type lạ |
| **Price mocking** | Deterministic MD5 | Tạo giá giả cho room | Deterministic, tái lập được | Giá không real (mock data) |

## Scripts

### `scripts/run_ingest.py` — Entry point chính
```bash
python scripts/run_ingest.py
# Skip từng bước:
python scripts/run_ingest.py --skip-dedup
python scripts/run_ingest.py --skip-clean --skip-dedup  # chỉ validate + db
python scripts/run_ingest.py --skip-clean --skip-dedup --skip-validate --skip-db  # chỉ clean
```

Pipeline: **clean → dedup → validate → PostgreSQL**

Flags:
| Flag | Skip bước |
|---|---|
| `--skip-clean` | Cleaning |
| `--skip-dedup` | Deduplication |
| `--skip-validate` | Validation |
| `--skip-db` | Export → PostgreSQL |

### `scripts/clean_pipeline.py`
```bash
python scripts/clean_pipeline.py \
  --input-dir data/raw/hotels \
  --output-dir data/cleaned
```
Output: `data/cleaned/hotel_{id}.json`

Lưu ý:
- File `recrawl_queue.json` (JSON array) bị skip tự động
- Xử lý cả `room_grid.rooms` (dữ liệu duplicate từ raw) giống `rooms[]`

### `scripts/dedup_pipeline.py`
```bash
python scripts/dedup_pipeline.py \
  --input-dir data/cleaned \
  --output-dir data/cleaned
```
Output: `data/cleaned/*.json` (ghi đè), `data/dedup_groups.json`

### `scripts/validation_pipeline.py`
```bash
python scripts/validation_pipeline.py \
  --input-dir data/cleaned \
  --report docs/data_quality_report.md
```
Output: `docs/data_quality_report.md`, `data/quarantine/quarantine_{id}.json` (nếu có lỗi)

### `scripts/export_db.py`
```bash
python scripts/export_db.py
```
Export cleaned JSON → PostgreSQL (4 bảng: hotels, rooms, nearby_places, activities).
Dedup composite PK trước insert, xoá child trước parent để tránh FK violation.

### `scripts/build_amenity_freq.py`
```bash
python scripts/build_amenity_freq.py
```
Output: `docs/amenity_frequency.tsv` — 432 unique amenities sorted by frequency.

## Kết quả hiện tại

| Metric | Giá trị | Target | Kết quả |
|---|---|---|---|---|
| Total documents | 51 | – | – |
| Missing rate | 0.0% | < 5.0% | ✅ |
| Duplicate rate | 0.0% | < 2.0% | ✅ |
| Amenity trung bình/hotel | ~81 (giảm từ ~167 raw) | – | – |
| Validation errors | 0 | – | ✅ |
| Null max_occupancy (rooms) | 0/463 | – | ✅ |
| Null price_per_night (rooms) | 0/463 | – | ✅ |

## Hướng dẫn chạy end-to-end

### Lần đầu (khởi tạo DB)

```bash
# Khởi động PostgreSQL
docker compose up -d postgres

# Tạo bảng (Alembic)
alembic upgrade head

# Chạy pipeline đầy đủ
python scripts/run_ingest.py
```

Chi tiết schema và query mẫu: [`docs/database_usage.md`](database_usage.md)

### Chạy lại (khi có data crawl mới)

```bash
# Chạy full pipeline
python scripts/run_ingest.py

# Hoặc skip các bước đã chạy
python scripts/run_ingest.py --skip-clean --skip-dedup  # chỉ validate + db
```
