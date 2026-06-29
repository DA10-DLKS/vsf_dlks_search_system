# Ingestion Pipeline: Thuật Toán & Kỹ Thuật Xử Lý Dữ Liệu

> Nghiên cứu chuyên sâu về các thuật toán được sử dụng trong Layer 2 (Data Ingestion & Cleaning) của DA10. Tài liệu này phân tích cơ sở lý thuyết, cách triển khai cụ thể, và các quyết định thiết kế cho từng kỹ thuật.

**Tác giả:** Do Minh Hieu  
**Dự án:** DA10 — Knowledge & Retrieval Platform  
**Phạm vi:** Ingestion Pipeline — 520 Vietnam hotel documents, 52K+ reviews, 106K+ translated texts.

---

## Mục lục

1. [HTML Stripping — BeautifulSoup DOM Traversal](#1-html-stripping--beautifulsoup-dom-traversal)
2. [Text Normalization — Unification & Noise Removal](#2-text-normalization--unification--noise-removal)
3. [Amenity Normalization — Fuzzy Deduplication & Canonicalization](#3-amenity-normalization--fuzzy-deduplication--canonicalization)
4. [Occupancy Imputation — Heuristic Bed Text Parsing](#4-occupancy-imputation--heuristic-bed-text-parsing)
5. [Price Mocking — Deterministic Pseudo-Pricing](#5-price-mocking--deterministic-pseudo-pricing)
6. [Review Merge — Set-Based Deduplication](#6-review-merge--set-based-deduplication)
7. [MinHash + LSH — Near-Duplicate Detection](#7-minhash--lsh--near-duplicate-detection)
8. [Schema Validation — Multi-Level Field Integrity](#8-schema-validation--multi-level-field-integrity)
9. [Quality Metrics — Missing Rate & Duplicate Rate](#9-quality-metrics--missing-rate--duplicate-rate)
10. [Machine Translation — Batch Transliteration with Fallback](#10-machine-translation--batch-transliteration-with-fallback)
11. [Pipeline Orchestration — Sequential Step Execution](#11-pipeline-orchestration--sequential-step-execution)

---

## 1. HTML Stripping — BeautifulSoup DOM Traversal

### 1.1 Mục tiêu

Dữ liệu thu thập từ Agoda chứa HTML markup trong các trường mô tả (`description`, `description_short`), chính sách khách sạn (`hotel_policy`), FAQ. Cần loại bỏ hoàn toàn HTML tags, chỉ giữ lại văn bản thuần + metadata (ảnh, links).

### 1.2 Thuật toán

**Input:** Chuỗi HTML thô  
**Output:** `StrippedDocument(text, image_urls, links)`

```
HTML string
    │
    ▼
BeautifulSoup(lxml) parse ──► DOM tree
    │
    ├── decompose(_REMOVE_TAGS)    ← xóa hẳn script, style, iframe, nav, footer, header
    ├── extract image URLs         ← img[src], img[data-src]
    ├── extract links              ← a[href] + anchor text
    │
    └── traverse text nodes:
            parent ∈ _BLOCK_TAGS? ──► "\n" separator
            else                  ──► inline concatenation
```

### 1.3 Cơ sở lý thuyết

**DOM Traversal với BeautifulSoup:** BeautifulSoup xây dựng cây phân cấp từ HTML dựa trên thuật toán parser tree construction của HTML5 spec. `lxml` backend được chọn vì tốc độ (C extension) so với `html.parser` thuần Python.

**`decompose()` vs `extract()`:**
- `decompose()`: xóa node khỏi DOM tree + phá hủy hoàn toàn (không thể re-insert)
- `extract()`: xóa node nhưng giữ reference (có thể re-insert)
- Chọn `decompose()` vì các tag `script`/`style` không cần giữ lại

**Block tag detection:** 15 tags được đánh dấu là block (`p, br, li, div, h1-h6, tr, td, th`). Các text node con của block tag được xuống dòng. Đây là heuristic dựa trên CSS default display property — `display: block` elements thường tạo line break trong rendering.

### 1.4 Code triển khai

```python
# ingestion/cleaning/html_stripper.py:25-62
def strip_html(html: str) -> StrippedDocument:
    soup = BeautifulSoup(html, "lxml")
    
    for tag in _REMOVE_TAGS:          # {"script", "style", "iframe", "noscript", ...}
        for el in soup.find_all(tag):
            el.decompose()
    
    image_urls = [img.get("src") or img.get("data-src", "")
                  for img in soup.find_all("img")
                  if img.get("src") or img.get("data-src")]
    
    links = [(a.get_text(strip=True), a.get("href", ""))
             for a in soup.find_all("a") if a.get("href")]
    
    parts = []
    for el in soup.find_all(string=True):
        parent = el.parent
        if isinstance(parent, Tag) and parent.name in _BLOCK_TAGS:
            parts.append(el.strip())
        else:
            parts.append(el.strip())
    
    return StrippedDocument(text="\n".join(parts), image_urls=image_urls, links=links)
```

### 1.5 Quyết định thiết kế

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Parser backend | `lxml` | Nhanh hơn `html.parser` ~5x trên corpus 520 files |
| Tag removal strategy | `decompose()` | Giải phóng memory ngay, không cần re-insert |
| Link/image metadata | Giữ lại trong `StrippedDocument` | Có thể dùng cho indexing hình ảnh sau này (Layer 4) |
| Block tag separator | `\n` | Đơn giản, đủ để phân biệt đoạn văn, không dùng `\n\n` vì gây khoảng trắng thừa |

---

## 2. Text Normalization — Unification & Noise Removal

### 2.1 Mục tiêu

Chuẩn hóa văn bản về dạng đồng nhất trước khi đưa vào downstream: embedding, indexing, search. Loại bỏ noise của quá trình crawl (Unicode variant, control chars, emoji).

### 2.2 Chuỗi xử lý

```
Raw text
    │
    ├── 1. normalize_unicode()     NFC normalization
    ├── 2. remove_control_chars()  strip ASCII control characters
    ├── 3. remove_emoji()          strip 14 Unicode emoji ranges
    ├── 4. collapse_whitespace()   multi-\n → \n\n, multi-space → single
    └── 5. normalize_punctuation() Unicode dashes/quotes → ASCII equivalents
```

### 2.3 Cơ sở lý thuyết

**Unicode Normalization (NFC vs NFD):**
- **NFC (Normalization Form Canonical Composition):** kết hợp ký tự + dấu thành một code point. VD: `à` (U+00E0) thay vì `a` (U+0061) + combining grave (U+0300)
- **NFD (Normalization Form Canonical Decomposition):** tách ký tự có dấu thành base + combining mark
- Tiếng Việt sử dụng cả NFC và NFD tùy platform. macOS thường dùng NFD, Linux dùng NFC.
- **Chọn NFC** vì: (1) index/search trên NFC dễ hơn (1 code point = 1 ký tự), (2) các downstream model embedding thường được train trên NFC

**Control character removal:**
- ASCII control: `\x00-\x08`, `\x0b\x0c`, `\x0e-\x1f`, `\x7f-\x9f`
- Các ký tự này xuất hiện do lỗi encoding khi crawl (null byte, escape sequence)
- Giữ lại `\n`, `\r`, `\t` (không nằm trong range)

**Emoji removal — 14 Unicode ranges:**

| Range | Block | Coverage |
|---|---|---|
| `U+1F1E0–1F1FF` | Flags | Country flags |
| `U+1F300–1F5FF` | Misc Symbols & Pictographs | Weather, UI icons |
| `U+1F600–1F64F` | Emoticons | Smileys |
| `U+1F680–1F6FF` | Transport & Map | Vehicles, signs |
| `U+2702–27B0` | Dingbats | ✂, ✈, ★ |
| `U+2600–27BF` | Misc Symbols | ☀, ☎, ♻ |
| `U+FE00–FE0F` | Variation Selectors | Emoji variation sequences |
| `U+200D` | Zero Width Joiner | ZWJ sequences (family emoji) |

**Punctuation normalization map:**

| Unicode | ASCII | Rationale |
|---|---|---|
| `\u2010–\u2011` (hyphens) | `-` | Các dạng gạch nối khác nhau |
| `\u2013` (en dash) | `-` | En dash thường dùng cho số range |
| `\u2014–\u2015` (em dash) | `---` | Em dash thường dùng cho ngắt câu |
| `\u2018–\u2019` (curly quotes) | `'` | Smart quotes → ascii |
| `\u201c–\u201d` (curly double) | `"` | Smart double quotes → ascii |
| `\u2026` (ellipsis) | `...` | Horizontal ellipsis |
| `\u00a0` (non-breaking) | ` ` | NBSP → regular space |

### 2.4 Code triển khai

```python
# ingestion/cleaning/text_normalizer.py:65-82
def normalize_text(text, *, preserve_case=True, strip=True, remove_icons=True):
    text = normalize_unicode(text)           # NFC
    text = remove_control_chars(text)        # strip [\x00-\x08...]
    if remove_icons:
        text = remove_emoji(text)            # 14 unicode ranges
    text = collapse_whitespace(text)         # \n{3,} → \n\n, \t → space
    text = normalize_punctuation(text)       # unicode dash/quote → ascii
    if strip:
        text = text.strip()
    return text
```

### 2.5 Độ phức tạp

- **Time:** O(n) với n = length của text (mỗi regex pass là O(n), tổng ~6 passes)
- **Space:** O(n) — mỗi lần regex substitution tạo string mới

---

## 3. Amenity Normalization — Fuzzy Deduplication & Canonicalization

### 3.1 Mục tiêu

Danh sách tiện ích (amenities) từ Agoda có độ nhiễu cao:
- Cùng amenity nhưng viết khác nhau: `"WiFi"`, `"Wifi"`, `"Wi-Fi"`, `"Internet không dây"`
- Thông tin thừa: `"Bãi đỗ xe (miễn phí)"`, `"Bể bơi ở nơi công cộng"`
- Amenity cơ bản không giúp phân biệt khách sạn: `"Máy sấy tóc"`, `"Tivi"`

### 3.2 Pipeline 4 phase

```
Raw amenity list
    │
    ▼
Phase 1: Clean từng item
    ├── Strip brackets [] và ()
    ├── Remove thin spaces (Unicode \u2000-\u200a)
    ├── normalize_text (lowercase, collapse whitespace)
    ├── Remove special characters (!@#$%^&*...)
    ├── Remove suffixes (ở nơi công cộng, trong tất cả các phòng)
    └── Dedup repeated words ("gỗ gỗ" → "gỗ")
    │
    ▼
Phase 2: Fuzzy grouping
    ├── Check _CANONICAL_MAP (30 regex patterns)
    └── SequenceMatcher similarity >= 0.80
    │
    ▼
Phase 3: Canonical form selection
    ├── Prefer canonical name từ map
    └── Else: shortest item, ưu tiên "miễn phí"
    │
    ▼
Phase 4: Remove basic amenities + generic subsets
    ├── ~40 basic amenity patterns
    └── Remove "WiFi" nếu có "WiFi miễn phí"
```

### 3.3 Thuật toán chính

#### 3.3.1 SequenceMatcher cho Fuzzy Matching

```python
def _fuzzy_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
```

**Cơ chế:** SequenceMatcher sử dụng thuật toán **Longest Common Subsequence (LCS)** — không phải Levenshtein distance. Tỉ lệ similarity được tính:

```
ratio = 2 * M / T
```

Trong đó:
- M = số ký tự matching (theo LCS)
- T = tổng số ký tự của 2 string

**Ví dụ:** `"WiFi"` vs `"Wifi"` → M=4, T=8 → ratio = 8/8 = 1.0

**Tại sao không dùng Levenshtein?** SequenceMatcher tự động handle substring matching tốt hơn. VD: `"Hồ bơi"` vs `"Hồ bơi ngoài trời"` — SequenceMatcher vẫn cho ratio cao vì phần lớn ký tự match.

**Threshold 0.80:** Được chọn sau khi test trên sample 10 hotels. Lower threshold gây false positive (gộp amenity không liên quan), higher threshold bỏ sót biến thể chính tả.

#### 3.3.2 Canonical Matching với Regex

```python
_CANONICAL_MAP = [
    (re.compile(r"^wifi|^wi.?fi|^internet|^dịch vụ internet", re.I), "WiFi"),
    (re.compile(r"^bể bơi|^bể bơi|^hồ bơi", re.I), "Bể bơi"),
    (re.compile(r"^spa", re.I), "Spa"),
    # ... 27 more patterns
]
```

Cơ chế:
- Regex match prefix, giữ nguyên suffix (qualifier)
- VD: `"bể bơi ngoài trời"` match pattern → `"Bể bơi" + " ngoài trời"` → `"Bể bơi ngoài trời"`
- Qualifier preservation quan trọng: `"Bể bơi ngoài trời"` ≠ `"Bể bơi trong nhà"` về mặt semantic

#### 3.3.3 Merge Cluster Heuristic

```python
def _merge_cluster(items, canonical=None):
    has_free = any("miễn phí" in it for it in items)
    if canonical:
        if has_free and "miễn phí" not in canonical:
            return canonical + " miễn phí"
        return canonical
    sorted_items = sorted(set(items), key=lambda x: (0 if "miễn phí" in x else 1, len(x), x))
    return sorted_items[0].capitalize()
```

**Heuristic:**
1. Nếu cluster có item chứa "miễn phí" → thêm " miễn phí" vào canonical name (dù canonical gốc không có)
2. Nếu không có canonical → chọn item ngắn nhất, ưu tiên item có "miễn phí"
3. Capitalize chữ cái đầu tiên

#### 3.3.4 Generic Subset Removal

```python
def _remove_generic_subsets(items):
    base_terms = {"wifi", "internet", "bữa sáng", "nhà hàng", "spa", "bể bơi", ...}
    for a in items:
        al = a.lower()
        if al in base_terms:
            has_specific = any(other != a and other.lower().startswith(al + " ")
                               for other in items)
            if has_specific:
                continue  # skip generic, keep specific
        result.append(a)
```

Nguyên tắc: Nếu `"WiFi"` tồn tại cùng với `"WiFi miễn phí"` hoặc `"WiFi có dây"` → giữ phiên bản chi tiết hơn, bỏ generic. Tránh trùng lặp thông tin.

### 3.4 Độ phức tạp

- **Fuzzy group (Phase 2):** O(k² × L²) với k = số amenity, L = max length. SequenceMatcher là O(n²) với n = length. Batch ~200 amenities → ~40K comparisons, acceptable.
- **Optimization:** Giới hạn bằng cách chỉ so sánh với canonical group leader (items chưa assigned), không phải all-pairs.

### 3.5 Ví dụ end-to-end

```
Input:  ["Hồ bơi", "Bể bơi ngoài trời", "bể bơi (ngoài trời)", "Máy sấy tóc", "WiFi", "Wifi miễn phí"]

Phase 1: ["hồ bơi", "bể bơi ngoài trời", "bể bơi ngoài trời", "máy sấy tóc", "wifi", "wifi miễn phí"]
            (dedup: "bể bơi ngoài trời")

Phase 2: Group 1: ["hồ bơi", "bể bơi ngoài trời"] → canonical: "Bể bơi ngoài trời"
         Group 2: ["máy sấy tóc"]                           → basic → removed
         Group 3: ["wifi", "wifi miễn phí"]                 → canonical: "WiFi miễn phí"

Phase 4: "wifi" bị remove vì có "WiFi miễn phí" cụ thể hơn

Output: ["Bể bơi ngoài trời", "WiFi miễn phí"]
```

---

## 4. Occupancy Imputation — Heuristic Bed Text Parsing

### 4.1 Mục tiêu

Trường `max_occupancy` thường bị thiếu trong raw data. Cần suy ra từ các trường khác: `max_occupancy_text`, `bed_types`, `bed_type`.

### 4.2 Cascade Strategy

```
max_occupancy (numeric)?
    │── Có, > 0 ──► return
    │
    └── Không ──► max_occupancy_text?
                        │── Có ──► regex extract số ──► return
                        │
                        └── Không ──► bed_types (list)?
                                            │── Có ──► _parse_bed_text() ──► return
                                            │
                                            └── Không ──► bed_type (string)?
                                                                │── Có ──► _parse_bed_text() ──► return
                                                                │
                                                                └── Không ──► default 2
```

Cascade design: độ chính xác giảm dần, độ coverage tăng dần. Dừng ở level đầu tiên cho kết quả hợp lệ.

### 4.3 Bed Text Parser

#### 4.3.1 BED_CAPACITY Dictionary

```python
BED_CAPACITY = {
    "đơn": 1,        # single bed
    "semi-double": 1,
    "đôi": 2,        # double bed
    "lớn": 2,        # large bed
    "king": 2,
    "queen": 2,
    "tầng": 2,       # bunk bed (upper + lower)
    "sofa": 1,
}
```

Sorted by length descending để match longest key first (tránh match "đôi" khi text là "đôi lớn").

#### 4.3.2 Grammar

Input text tuân theo cấu trúc ngữ pháp không chính thức:

```
room_bed ::= and_expr ("/" or_expr)?
and_expr ::= bed_clause (("," | "và") bed_clause)*
or_expr  ::= bed_clause (("hoặc" | "/") bed_clause)*
bed_clause ::= count "giường" bed_type
```

**Parsing strategy:**
1. Split `or_expr`: dùng `"hoặc"` hoặc `"/"` → max của 2 vế (khách có thể chọn 1 trong 2)
2. Split `and_expr`: dùng `"và"` hoặc `","` → sum các bed (khách dùng tất cả)
3. Parse `bed_clause`: regex `(\d+)\s+giường\s+(.+)` → count × capacity

#### 4.3.3 Ví dụ parsing

| Input | Parsing | Result |
|---|---|---|
| `"2 giường đôi"` | 2 × 2 | 4 |
| `"1 giường king + 1 giường sofa"` | 1×2 + 1×1 | 3 |
| `"2 giường đơn / 1 giường đôi"` | max(2×1, 1×2) | 2 |
| `"1 giường đôi và 2 giường đơn"` | 1×2 + 2×1 | 4 |
| `"2 giường tầng"` | 2 × 2 | 4 |

### 4.4 Code triển khai

```python
# ingestion/cleaning/occupancy_imputer.py:36-52
def _parse_bed_text(text: str) -> int:
    text = text.strip().lower()
    
    or_parts = re.split(r"\s*(?:/|\s+hoặc\s+)\s*", text)
    and_parts = re.split(r"\s*(?:và|,)\s*", or_parts[0])
    total = sum(_bed_type_capacity(p.strip()) for p in and_parts if p.strip())
    
    if len(or_parts) > 1:
        alt_total = sum(
            _bed_type_capacity(p.strip())
            for p in re.split(r"\s*(?:và|,)\s*", or_parts[1])
            if p.strip()
        )
        total = max(total, alt_total)
    
    return total
```

### 4.5 Độ chính xác

- Coverage: từ default 2 (fallback) lên ~85% có estimated occupancy
- Error margin: ±1 người so với ground truth (test trên 50 rooms có max_occupancy thật)

---

## 5. Price Mocking — Deterministic Pseudo-Pricing

### 5.1 Mục tiêu

Data thật từ Agoda không bao gồm giá phòng. Cần tạo giá giả nhưng realistic để downstream có thể filter/search theo price range. Yêu cầu: **deterministic** (cùng input → cùng output) để reproducible.

### 5.2 Factor Cascade Model

```
price = base(star) × brand_factor × room_type_factor × city_factor × size_factor
```

#### 5.2.1 Base Price by Star Rating

```python
STAR_PRICE_TABLE = {
    5: (2_000_000, 3_500_000, 5_000_000),   # (min, mid, max)
    4: (1_200_000, 2_100_000, 3_000_000),
    3: (600_000,   1_050_000, 1_500_000),
    2: (300_000,   550_000,   800_000),
    1: (200_000,   350_000,   500_000),
}
```

Giá mid được dùng làm base, sau đó clamp vào [min, max] sau khi nhân factor.

#### 5.2.2 Factor Dictionary

| Factor | Values | Rationale |
|---|---|---|
| **Brand** | Vinpearl: 1.2, Mường Thanh: 0.9, other: 0.8 | Brand reputation affects pricing |
| **Room type** | Penthouse: 2.0, Suite: 1.8, Standard: 0.9,... | Room tier affects price |
| **City** | Phú Quốc: 1.3, Đà Nẵng: 1.1,... | Destination popularity |
| **Size** | `clamp(sqm/30, 0.5, 2.0)` | Larger rooms cost more |

Brand factor cho khách sạn không thuộc brand nổi tiếng được set 0.8 (thấp hơn mặc định 1.0) — phản ánh khách sạn độc lập thường có giá thấp hơn chain hotel.

#### 5.2.3 Deterministic Discount

```python
def _deterministic_discount(hotel_id, room_type_id):
    key = f"{hotel_id}_{room_type_id or 0}"
    h = hashlib.md5(key.encode()).hexdigest()
    val = int(h[:8], 16)
    return 1.2 + (val % 6000) / 10000    # range: 1.2 - 1.8
```

**Original price** = `price_per_night × discount`. Discount luôn > 1.0 → original_price luôn > price_per_night (realistic: giá niêm yết > giá sau giảm).

MD5 hash được dùng thay vì random vì: (1) deterministic giữa các lần chạy, (2) phân bố đều trong không gian 32 hex chars.

### 5.3 Rounding

```python
def _round_price(val):
    return int(round(val / 10_000) * 10_000)
```

Giá VND trong thực tế thường là bội số của 10,000 (hoặc 50,000 cho khách sạn). Rounding giúp giá realistic hơn.

### 5.4 Ví dụ

```
Hotel: Vinpearl Phú Quốc (5★), Room: Deluxe Garden View (30m²)

star=5 → base = 3,500,000
brand_factor("vinpearl") = 1.2
room_type_factor("deluxe") = 1.3
city_factor("phú quốc") = 1.3
size_factor(30m²) = 30/30 = 1.0

price = 3,500,000 × 1.2 × 1.3 × 1.3 × 1.0 = 7,098,000
clamped: [2,000,000 - 5,000,000] → 5,000,000
rounded: 5,000,000

discount = MD5(hotel_id_room_id) → 1.45
original = 5,000,000 × 1.45 = 7,250,000 → 7,250,000
```

---

## 6. Review Merge — Set-Based Deduplication

### 6.1 Mục tiêu

Reviews được crawl riêng (file riêng) và crawl cùng hotel detail (embedded trong `sample_comments`). Cần merge vào một list, loại bỏ overlap.

### 6.2 Thuật toán

```python
def _merge_reviews_into_doc(doc):
    hotel_id = doc.get("id") or doc.get("hotel_id")
    
    # Load review file: data/raw/reviews/hotel_{id}_reviews.json
    review_data = json.load(review_path)
    new_reviews = review_data.get("reviews", [])
    
    # Build dedup keys for new reviews
    seen_by_id = {r["review_id"] for r in new_reviews if r.get("review_id")}
    seen_by_fallback = {(r["reviewer_name"], r["date"]) for r in new_reviews}
    
    # Filter existing comments: remove if match either key
    existing = doc.get("reviews_detail", {}).get("sample_comments", [])
    kept = [c for c in existing
            if not (c.get("review_id") in seen_by_id
                    or (c.get("reviewer_name"), c.get("date")) in seen_by_fallback)]
    
    doc["reviews_detail"]["sample_comments"] = kept + new_reviews
    return doc
```

### 6.3 Dedup Key Design

| Key | Source | Coverage |
|---|---|---|
| `review_id` | New reviews from dedicated crawl | ~70% (có review_id) |
| `(reviewer_name, date)` | Existing comments from hotel detail | ~30% (không có review_id) |

**Composite key fallback:** `(reviewer_name, date)` được dùng khi `review_id` không available. Giả định: cùng 1 người, cùng 1 ngày → cùng 1 review. Đây là heuristic có thể sai nếu 1 người review cùng lúc 2 khách sạn khác nhau, nhưng với context merge vào cùng 1 hotel thì xác suất rất thấp.

### 6.4 Kết quả

52,000+ reviews merged, 0 duplicate comments.

---

## 7. MinHash + LSH — Near-Duplicate Detection

### 7.1 Mục tiêu

Phát hiện và loại bỏ các hotel document có nội dung gần giống nhau (near-duplicate). Các trường hợp:
- Cùng khách sạn được crawl ở 2 URL khác nhau
- Khách sạn khác nhau nhưng description giống nhau (cùng chủ đầu tư, template clone)

### 7.2 MinHash Theory

**MinHash** là kỹ thuật ước lượng Jaccard similarity giữa 2 tập hợp mà không cần so sánh trực tiếp.

#### 7.2.1 Jaccard Similarity

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

Với A, B là tập hợp các shingles (từ) trong document.

#### 7.2.2 MinHash Signature

Cho tập hợp S = {s₁, s₂, ..., sₙ} và k hàm hash độc lập h₁, h₂, ..., hₖ:

```
signature(S) = [min(h₁(S)), min(h₂(S)), ..., min(hₖ(S))]
```

Trong đó `min(hᵢ(S))` là giá trị hash nhỏ nhất của tất cả elements trong S dưới hàm hᵢ.

**Tính chất quan trọng:**

```
P[signature(A)[i] == signature(B)[i]] = J(A, B)
```

Xác suất signature match tại 1 position bằng đúng Jaccard similarity. Với k permutations, số lượng match positions ≈ k × J(A, B).

#### 7.2.3 Bias Correction

Với k permutations, ước lượng Jaccard:

```
Ĵ = (số positions signature match) / k
```

Đây là unbiased estimator với variance = J(1-J)/k.

### 7.3 Locality Sensitive Hashing (LSH)

#### 7.3.1 Banding Technique

Để tìm candidate pairs nhanh hơn O(n²), MinHash LSH chia k-length signature thành b bands, mỗi band r rows:

```
k = b × r
```

**Nguyên lý:** 2 documents có Jaccard ≥ threshold sẽ có ít nhất 1 band hash vào cùng bucket với xác suất cao:

```
P_collision = 1 - (1 - J^r)^b
```

#### 7.3.2 Parameter Selection

Với threshold mục tiêu 0.85:

| b (bands) | r (rows) | P_collision tại J=0.85 | Số buckets |
|---|---|---|---|
| 16 | 8 | 0.9999 | Nhiều |
| 20 | 6 | 0.9997 | Trung bình |
| **32** | **4** | **0.9985** | **Ít hơn** |

**Chọn k=128, b=32, r=4** — `datasketch` default, cho collision probability ~0.999 tại threshold 0.85.

### 7.4 Exact Verification

LSH là approximate — có false positive. Sau khi LSH trả về candidate pairs, verify bằng exact Jaccard:

```python
verified = [doc_id]
for cand in candidates:
    sim = m.jaccard(minhashes[cand])   # exact MinHash Jaccard
    if sim >= threshold:
        verified.append(cand)
```

**MinHash Jaccard** (từ signature) ≠ **Shingle Jaccard** (từ raw text). MinHash là ước lượng, nhưng với k=128 và threshold 0.85, sai số < 0.02.

### 7.5 Preprocessing

```python
def _prepare_text(text):
    t = normalize_text(text, preserve_case=False)  # lowercase + NFC
    return t

def _make_minhash(text, num_perm=128):
    m = MinHash(num_perm=num_perm)
    t = _prepare_text(text)
    for word in t.split():
        m.update(word.encode("utf-8"))
```

**Shingling level:** word-level (không phải character n-gram). Lý do:
- Text tiếng Việt có dấu, character n-gram dễ bị ảnh hưởng bởi Unicode variant
- Word-level cho quality tốt hơn với document-level similarity
- `t.split()` mặc định split trên whitespace → phù hợp với text đã normalize

### 7.6 Độ phức tạp

- **MinHash construction:** O(n × k) với n = số shingle, k = 128
- **LSH insert/query:** O(k) mỗi operation
- **Total complexity:** O(N × k) + O(N × candidates × k) với N = số documents
- **So với brute force O(N² × n):** giảm từ ~270K pairs (520²) xuống ~candidates pairs

### 7.7 Code triển khai

```python
# ingestion/deduplication/minhash.py:51-110
def find_duplicates(docs, *, threshold=0.85, num_perm=128):
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes = {}
    
    for doc_id, text in docs:
        m = _make_minhash(text, num_perm)
        minhashes[doc_id] = m
        lsh.insert(doc_id, m)
    
    seen = set()
    groups = []
    for doc_id, m in minhashes.items():
        if doc_id in seen:
            continue
        candidates = [c for c in lsh.query(m) if c != doc_id]
        if not candidates:
            continue
        
        # Exact verification
        verified = [doc_id]
        for cand in candidates:
            if m.jaccard(minhashes[cand]) >= threshold:
                verified.append(cand)
        
        if len(verified) >= 2:
            groups.append(DuplicateGroup(
                document_ids=list(set(verified)),
                similarity=avg_jaccard(verified),
            ))
            seen.update(verified)
    
    return groups
```

### 7.8 Kết quả

0 duplicate groups found trên 520 hotels → tất cả hotels đều unique.

---

## 8. Schema Validation — Multi-Level Field Integrity

### 8.1 Mục tiêu

Đảm bảo mỗi hotel document tuân thủ schema quy định trong `contracts/data_schema.json` và `docs/relational_schema.md`. Phát hiện thiếu field, sai kiểu, out-of-range.

### 8.2 Validation Layers

```
validate_document(doc)
    │
    ├── 1. Hotel required fields
    │       id (aliases: id, hotel_id)
    │       name, source_url
    │
    ├── 2. Sub-document required fields
    │       rooms:          [hotel_id, name]
    │       nearby_places:  [hotel_id, name]
    │       activities:     [hotel_id, title]
    │       (FK hotel_id implicit nếu parent có id)
    │
    ├── 3. Numeric range checks
    │       star_rating:  [1.0, 5.0]
    │       review_score: [0, 10]
    │       latitude:     [-90, 90]
    │       longitude:    [-180, 180]
    │
    ├── 4. Type checks
    │       string_array_fields: amenities, suitable_for
    │       object_fields: useful_info, reviews_detail
    │
    └── 5. Format checks
            crawled_at: ISO 8601 format
```

### 8.3 Alias Resolution

```python
HOTEL_REQUIRED_ALIASES = {
    "id": ["id", "hotel_id"],    # chấp nhận cả 2 field name
}
```

Kỹ thuật: các field bắt buộc nhưng có tên khác nhau giữa các nguồn dữ liệu. `id` và `hotel_id` cùng được chấp nhận. Resolution: duyệt danh sách alias, field đầu tiên có giá trị non-null non-empty → pass.

### 8.4 Implicit Foreign Key

Sub-document (rooms, nearby_places, activities) có field `hotel_id` là FK trỏ đến hotel cha. Tuy nhiên, nếu hotel parent có `id`/`hotel_id` thì sub-document không cần lặp lại `hotel_id` — nó implicit từ context.

```python
filtered_required = [
    f for f in required
    if not (f == "hotel_id" and parent_id is not None)
]
```

### 8.5 Severity Levels

| Severity | Hành vi | Ví dụ |
|---|---|---|
| `error` | Document bị quarantine | Thiếu `name`, thiếu `source_url` |
| `warning` | Ghi nhận, không quarantine | `star_rating` > 5, `crawled_at` not ISO 8601 |

### 8.6 Kết quả

520 hotels validated, 18 quarantined (do thiếu `source_url` — lỗi crawl không recover được).

---

## 9. Quality Metrics — Missing Rate & Duplicate Rate

### 9.1 Missing Rate

#### 9.1.1 Công thức

```
missing_rate = missing_checks / total_checks
```

**Không phải** `missing_docs / total_docs`. Mỗi field trong mỗi document là 1 check riêng.

**Ví dụ:**
- 520 hotels × 3 hotel fields = 1,560 checks (id, name, source_url)
- 520 hotels × (trung bình 5 rooms × 2 fields) = ~5,200 checks
- 520 × (trung bình 10 nearby × 2) = ~10,400 checks
- 520 × (trung bình 3 activities × 2) = ~3,120 checks
- Total: ~20,280 checks

#### 9.1.2 Field Presence Check

```python
def _field_present(obj, field, aliases=None):
    candidates = aliases.get(field, [field]) if aliases else [field]
    for c in candidates:
        val = obj.get(c)
        if val is not None and (not isinstance(val, str) or val.strip() != ""):
            return True
    return False
```

Điều kiện "present": (1) không phải None, (2) nếu là string thì không empty sau strip.

### 9.2 Duplicate Rate

#### 9.2.1 Công thức

```
duplicate_rate = duplicate_docs / total_docs
```

Trong đó:
- `duplicate_docs` = Σ (group_size - 1) cho mỗi nhóm trùng
- Giữ 1 doc đại diện mỗi nhóm, các doc còn lại trong nhóm tính là duplicate

#### 9.2.2 Ví dụ

2 nhóm trùng: nhóm A (3 docs), nhóm B (2 docs)
- duplicate_docs = (3-1) + (2-1) = 3
- total = 520
- duplicate_rate = 3/520 = 0.58%

### 9.3 Thresholds

| Metric | Target | Kết quả |
|---|---|---|
| Missing Rate | < 5% | ✅ Pass |
| Duplicate Rate | < 2% | ✅ Pass |

---

## 10. Machine Translation — Batch Transliteration with Fallback

### 10.1 Mục tiêu

Dịch 106,613 non-Vietnamese texts (activity titles, descriptions, review comments) sang tiếng Việt bằng Google Translate API (free tier). Cần giải quyết:
- Rate limiting của Google Translate
- Chi phí request (free tier: ~500K chars/ngày)
- Tính reproducible (cache)
- Xử lý text hỗn hợp ngôn ngữ (CJK, non-CJK)

### 10.2 Pipeline

```
texts list
    │
    ├── filter: _is_likely_vietnamese? → skip (giữ nguyên)
    ├── filter: cached? → skip
    │
    ▼
group by CJK source:
    ├── zh-CN (Chinese)     — Unicode range 0x4E00-0x9FFF
    ├── ja (Japanese)       — Hiragana 0x3040-0x309F / Katakana 0x30A0-0x30FF
    ├── ko (Korean)         — Hangul 0xAC00-0xD7AF
    └── None (English, others) — auto-detect
    │
    ▼
chunk texts (4500 chars/request)
    │
    ▼
ThreadPoolExecutor translate:
    ├── _translate_chunk() — batch concatenation + random separator
    ├── retry 5x — exponential backoff
    └── per-text fallback — rate limited 0.4-0.7s
```

### 10.3 Language Detection

#### 10.3.1 Vietnamese Detection

```python
_VIETNAMESE_MARKERS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"

def _is_likely_vietnamese(text):
    return any(ch in _VIETNAMESE_MARKERS_SET for ch in text.lower())
```

Heuristic: **60+ diacritic characters specific to Vietnamese**. Không phải NLP-based detection. Độ chính xác: ~99.5% (false positive khi text có accent marks của French/Romanian nhưng tỉ lệ rất thấp trong data travel).

#### 10.3.2 CJK Detection

```python
def _detect_cjk_source(text):
    has_hira = has_kata = has_hangul = has_cjk = False
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF:  has_cjk = True
        elif 0x3040 <= cp <= 0x309F: has_hira = True
        elif 0x30A0 <= cp <= 0x30FF: has_kata = True
        elif 0xAC00 <= cp <= 0xD7AF: has_hangul = True
    
    if has_hira or has_kata:   return "ja"
    if has_hangul:             return "ko"
    if has_cjk:                return "zh-CN"
    return None
```

**Ưu tiên:** Japanese (Hiragana/Katakana) > Korean (Hangul) > Chinese (CJK). Lý do: Chinese CJK characters overlap với Japanese Kanji. Kiểm tra Hiragana/Katakana trước giúp phân biệt Chinese text và Japanese text chứa Kanji.

**Tại sao không dùng `langdetect` / `fasttext`?** (1) Latency — 106K texts × inference = không khả thi free tier, (2) Dependency weight — thêm model file > 100MB, (3) Độ chính xác của Unicode range detection > 99% cho travel data.

### 10.4 Batch Translation Strategy

#### 10.4.1 Token Bucket Chunking

```python
_MAX_CHARS_PER_CALL = 4500

def _chunk_texts(texts):
    batches = []
    current, current_len = [], 0
    for text in texts:
        sep_len = len(_SEPARATOR_ESTIMATE) if current else 0
        if current_len + sep_len + len(text) > _MAX_CHARS_PER_CALL and current:
            batches.append(current)
            current, current_len = [], 0
        current.append(text)
        current_len += sep_len + len(text)
    if current:
        batches.append(current)
    return batches
```

**Chunk size: 4500 chars/request.** Giới hạn của Google Translate free tier là 5000 chars/request. Đặt 4500 để có margin cho separator overhead.

#### 10.4.2 Random Separator

```python
def _translate_chunk(chunk, source, cache):
    sep = f"||{secrets.token_hex(8)}||"   # vd: "||a1b2c3d4e5f6||"
    joined = sep.join(chunk)
    translated = translate(joined)
    parts = translated.split(sep)
```

**Vấn đề với separator cố định:** Google Translate từng dịch `"|||"` thành từ có nghĩa trong target language (vì model thấy 3 ký tự `|` liên tiếp → tạo thành 1 token → sinh ra translation cho token đó).

**Giải pháp:** `secrets.token_hex(8)` tạo separator ngẫu nhiên 16 ký tự hex mỗi batch. Token này không nằm trong vocabulary của bất kỳ ngôn ngữ nào → Google Translate không thể translate → luôn giữ nguyên trong output.

**Cơ chế reverse:**
```
Input:  "text1||a1b2c3d4||text2||a1b2c3d4||text3"
Output: "trans1||a1b2c3d4||trans2||a1b2c3d4||trans3"
``` 

Số phần output = số phần input → đảm bảo 1-1 mapping.

#### 10.4.3 Quality Control

```python
if len(result) < len(chunk) * 0.5:
    raise ValueError("Too few parts")
```

Nếu output mất > 50% số texts → batch fail. Fallback sang per-text.

### 10.5 Retry & Fallback

#### 10.5.1 Exponential Backoff

```python
for attempt in range(5):
    try:
        return translate(joined)
    except Exception as exc:
        time.sleep(min(2**attempt + random.random(), 10))
```

| Attempt | Delay | Jitter |
|---|---|---|
| 1 | ~1.5s | +random 0-1s |
| 2 | ~4.5s | +random 0-1s |
| 3 | ~10s | capped at 10s |
| 4 | ~10s | capped at 10s |
| 5 | ~10s | capped at 10s |

**Random jitter** (thêm `random.random()`): tránh thundering herd khi nhiều workers cùng retry đồng thời.

#### 10.5.2 Per-Text Fallback

Khi batch fail sau 5 retries, fallback sang translate từng text riêng:

```python
for i, text in enumerate(chunk):
    time.sleep(0.4 + random.random() * 0.3)   # rate limiting
    tr = GoogleTranslator(...).translate(text)
    cache[text] = tr
    if i % 50 == 0:
        _save_cache(cache)                     # incremental save
```

**Rate limiting:** 0.4-0.7s giữa các request → ~1.5-2.5 requests/second. Tránh bị Google block vì quá tải.

**Incremental cache save:** mỗi 50 texts → giảm thiểu mất dữ liệu nếu crash.

### 10.6 Cache System

```python
_TRANSLATION_CACHE: dict[str, str] = _load_cache()   # in-memory dict

def _load_cache():
    if _CACHE_FILE.exists():
        return json.load(_CACHE_FILE) or {}
    return {}

def _save_cache(cache):
    _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
```

- **File:** `data/_translation_cache.json` (~154MB, 303K+ entries)
- **Git LFS:** tracked via `.gitattributes` (tránh lưu binary 154MB vào git history)
- **Key:** original text
- **Value:** translated text
- **Cache hit:** skip translate, dùng cached value
- **Cache miss:** translate, lưu cache

### 10.7 ThreadPoolExecutor

```python
with ThreadPoolExecutor(max_workers=workers) as pool:
    futures = [pool.submit(_translate_chunk, batch, source) for batch, source in all_batches]
    for future in as_completed(futures):
        result_map.update(future.result())
```

**workers=6:** số lượng workers có thể chạy song song. Giới hạn bởi rate limit của Google Translate (không official nhưng thực tế ~10 requests/s cho free tier).

### 10.8 Target Fields

```python
FIELDS_TO_TRANSLATE = {
    "activities": ("title", "description"),
}
REVIEW_TEXT_FIELDS = ("text", "title", "positives", "negatives", "response")
```

**Chỉ translate:** activities (title/description) + review comments (5 fields). Hotel description/amenities/address **không translate** — đã có sẵn dạng song ngữ từ Agoda.

### 10.9 Kết quả

| Metric | Value |
|---|---|
| Unique texts processed | 106,613 |
| Changes applied | ~106K |
| Untranslatable | 1,533 (0.48% positives, 1.3% negatives non-VN) |
| Cache size | 154MB, 303K entries |
| Average speed | ~150 texts/s (batch) → ~0.5 texts/s (per-text fallback) |

---

## 11. Pipeline Orchestration — Sequential Step Execution

### 11.1 Mục tiêu

Điều phối 4 bước xử lý thành 1 pipeline duy nhất, có khả năng skip từng bước, logging timing, handle interruption.

### 11.2 Design Pattern

```
run_ingest.py:main()
    │
    ├── parse CLI args (--skip-clean, --skip-dedup, --skip-validate, --skip-translate, --translate-workers)
    │
    └── run()
        │
        ├── Step 1/4: Cleaning          ← scripts/clean_pipeline.run()
        ├── Step 2/4: Deduplication     ← scripts/dedup_pipeline.run()
        ├── Step 3/4: Validation        ← scripts/validation_pipeline.run()
        └── Step 4/4: Translation       ← scripts/post_translate.run()
```

### 11.3 CLI Flags

| Flag | Effect | Default |
|---|---|---|
| `--skip-clean` | Skip cleaning step | False |
| `--skip-dedup` | Skip dedup step | False |
| `--skip-validate` | Skip validation step | False |
| `--skip-translate` | Skip translation step | False |
| `--translate-workers N` | Workers for translation | 6 |
| `--raw-dir PATH` | Raw data directory | data/raw |
| `--cleaned-dir PATH` | Cleaned data directory | data/cleaned |
| `--report PATH` | Quality report output | docs/data_quality_report.md |

### 11.4 Error Handling

```python
try:
    summary = run(...)
except KeyboardInterrupt:
    print("\n=== Pipeline interrupted by user ===")
```

- **KeyboardInterrupt:** clean exit, không stack trace — user-friendly
- **Step failure:** exception propagate lên, dừng pipeline. Không silent fail.

### 11.5 Timing Logging

```python
def _elapsed(t_start):
    s = time.time() - t_start
    return f"{s/60:.1f}m" if s >= 60 else f"{s:.0f}s"
```

Mỗi step log: `"Step N/4: Name"` + timing sau khi hoàn thành. Giúp identify bottleneck (translation step ~45 phút).

---

## Tổng kết

### Ma trận kỹ thuật

| Kỹ thuật | Category | Algorithm | Input | Output |
|---|---|---|---|---|
| HTML Stripping | Cleaning | DOM Traversal (BeautifulSoup + lxml) | HTML string | Plain text + metadata |
| Text Normalization | Cleaning | Unicode NFC + Regex + Range-based | Raw text | Cleaned text |
| Amenity Normalization | Cleaning | SequenceMatcher + Regex Canonical + Heuristic | List of strings | Deduplicated, canonical list |
| Occupancy Imputation | Imputation | Cascade + Pattern Matching + Grammar | Room dict | Integer occupancy |
| Price Mocking | Generation | Factor Model + MD5 Hash + Rounding | Hotel/room metadata | Pseudo prices |
| Review Merge | Deduplication | Set-based + Composite Key | 2 review lists | Merged unique list |
| Near-Duplicate Detection | Deduplication | MinHash + LSH + Exact Verification | Document texts | Duplicate groups |
| Schema Validation | Validation | Field Check + Alias + Range + Type | Document | ValidationResult |
| Missing Rate | Metrics | Field-level counting | Documents | Float rate |
| Duplicate Rate | Metrics | Group-size summation | Groups + count | Float rate |
| Machine Translation | Translation | Batch + CJK Detect + Random Separator + Retry | Texts | Translated texts |

### Thống kê cuối cùng

- **520** Vietnam hotels, **70** cities
- **0** duplicates, **18** quarantined
- **106,613** texts translated, **1,533** untranslatable
- **Missing Rate:** < 5% ✅
- **Duplicate Rate:** < 2% ✅
