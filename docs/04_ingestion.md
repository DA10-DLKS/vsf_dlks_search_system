# 04 – Thu nạp & Xử lý dữ liệu (Layer 2)

`ingestion/` biến đầu ra thô của crawler thành tập dữ liệu sạch, đã kiểm định và khử trùng lặp.

## Kiến trúc Pipeline

```
data/raw/hotels/*.json
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  1. Cleaning (scripts/clean_pipeline.py)                  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  A. Xử lý văn bản (cho mọi text field)              │  │
│  │  ├── strip_html()    – BeautifulSoup strip HTML     │  │
│  │  ├── normalize_text() – Unicode NFC + emoji remove   │  │
│  │  └── translate_to_vi() – Deep-Translator → Google   │  │
│  │      (chỉ cho review response không phải tiếng Việt) │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  B. Amenity Normalizer (amenity_normalizer.py)       │  │
│  │                                                       │  │
│  │  Raw amenity string                                   │  │
│  │    │                                                   │  │
│  │    ▼                                                   │  │
│  │  Step 1 – Bỏ ký tự [] và (), giữ nguyên nội dung      │  │
│  │    │  "Wi-Fi [miễn phí]" → "Wi-Fi miễn phí"           │  │
│  │    ▼                                                   │  │
│  │  Step 2 – Chuẩn hóa Unicode + loại bỏ hậu tố verbose  │  │
│  │    │  "ở nơi công cộng", "trong tất cả các phòng" ...  │  │
│  │    ▼                                                   │  │
│  │  Step 3 – Canonical prefix mapping                    │  │
│  │    │  "wifi" / "wi-fi" / "internet" → "WiFi"          │  │
│  │    │  "máy lạnh" / "điều hòa" → "Điều hòa"           │  │
│  │    │  Chỉ thay thế prefix, giữ qualifier:              │  │
│  │    │  "wifi miễn phí" → "WiFi miễn phí"               │  │
│  │    ▼                                                   │  │
│  │  Step 4 – Fuzzy merge (difflib.SequenceMatcher)       │  │
│  │    │  Ngưỡng 0.80, ưu tiên item có "miễn phí"        │  │
│  │    │  "nước đóng chai" + "nước đóng chai miễn phí"    │  │
│  │    │  → "Nước đóng chai miễn phí"                     │  │
│  │    ▼                                                   │  │
│  │  Step 5 – Lọc basic amenities                         │  │
│  │    │  Loại: Máy sấy tóc, Két sắt, Bình chữa cháy,    │  │
│  │    │  Cân, Gương, TV/tivi, Tiện nghi, ...              │  │
│  │    │  (41 items là đồ cơ bản, không giúp phân biệt)    │  │
│  │    ▼                                                   │  │
│  │  Step 6 – Lọc generic nếu có phiên bản chi tiết       │  │
│  │    │  "WiFi" bị loại nếu đã có "WiFi miễn phí"        │  │
│  │    │  "Bữa sáng" bị loại nếu đã có "Bữa sáng tự chọn" │  │
│  │    │  "Spa" vẫn giữ nếu không có "Spa xông khô"        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  Áp dụng cho: amenities, amenities_general,               │
│  amenities_leisure, amenities_dining, room_amenities       │
└──────────────────────────────┬───────────────────────────┘
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
                               ▼
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

## Scripts

### `scripts/run_ingest.py` — Entry point chính
```bash
python scripts/run_ingest.py
# Skip từng bước:
python scripts/run_ingest.py --skip-dedup
python scripts/run_ingest.py --skip-clean --skip-dedup  # chỉ validate
```

Pipeline: **clean → dedup → validate**

### `scripts/clean_pipeline.py`
```bash
python scripts/clean_pipeline.py \
  --input-dir data/raw/hotels \
  --output-dir data/cleaned
```
Output: `data/cleaned/hotel_{id}.json`

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

## Kết quả hiện tại

| Metric | Giá trị | Target | Kết quả |
|---|---|---|---|
| Total documents | 27 | – | – |
| Missing rate | 0.0% | < 5.0% | ✅ |
| Duplicate rate | 0.0% | < 2.0% | ✅ |
| Amenity trung bình/hotel | ~81 (giảm từ ~167 raw) | – | – |
| Validation errors | 0 | – | ✅ |

## Hướng dẫn chạy end-to-end

```bash
# Xoá dữ liệu cũ
rm -rf data/cleaned data/quarantine data/dedup_groups.json docs/data_quality_report.md
mkdir -p data/cleaned data/quarantine

# Chạy pipeline đầy đủ
python scripts/run_ingest.py
```
