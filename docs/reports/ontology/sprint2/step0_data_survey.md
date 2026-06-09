# Sprint 2 — Bước 0: Khảo sát trường dữ liệu thật

> **Mục đích:** Trước khi viết source-tag map + mapper, khảo sát 520 hotel Agoda đã clean
> để biết (1) có trường gì, (2) vocabulary nguồn dày bao nhiêu → ước lượng khối lượng map.
> **Không tạo concept mới ở bước này** — chỉ đo. Ngày: 2026-06-07. Corpus: 520 hotel VN.
>
> Số liệu sinh tự động từ `data/cleaned/hotel_*.json` + `data/raw/reviews/*.json`.

---

## 1. Cấu trúc 1 object (top-level keys quan trọng)

| Nhóm | Trường | Dùng cho |
|---|---|---|
| Định danh | `hotel_id`, `name`, `source_url`, `crawled_at` | id / provenance |
| Phân loại | `accommodation_type`, `property_type`, `star_rating`, `is_luxury`, `gold_circle_award_year` | object_type, price_tier |
| Vị trí | `country`, `province`, `city`, `district`, `area`, `latitude`, `longitude`, `city_id` | location (Sprint 1 đã xử lý) |
| Vocabulary nguồn | `amenities`, `amenity_groups`, `suitable_for`, `view_types`, `tags`, `location_tags`, `highlights` | **source-tag map (Bước 1)** |
| Quan hệ | `nearby_places` (`name`/`type`/`distance_km`) | nearby_places, quan hệ near |
| Số | `review_score`, `review_count`, `star_rating` | range_filters |
| Review (aggregate) | `reviews_detail` (`tags`, `grades`, `demographics`, `word_cloud`, `sample_comments`), `rating_breakdown` | **SOFT seed (Bước 5)** |
| Text | `description`, `description_short`, `embedding_text`, `highlights` | content_blocks + rule tagger |

---

## 2. Vocabulary nguồn — khối lượng phải map

| Trường | Unique values | Map → facet | Đánh giá |
|---|---:|---|---|
| `accommodation_type` | **13** | object_type (one) | ✅ Sprint 1 đã audit khớp 13/13 — map gần xong |
| `suitable_for` | **6** | purpose (many) | ✅ cố định 6 giá trị — map dễ |
| `rating_breakdown` keys | **7** | aspect (ABSA seed) | ✅ 7 aspect cố định |
| `view_types` | **23** | setting + amenity(view) | 🟡 mẫu "Hướng X" — quy tắc hóa được |
| `reviews_detail.tags` | **45** | aspect / amenity (soft seed) | 🟡 seed cho profile |
| `amenity_groups` keys | **29** | nhóm category | 🟡 dùng để map theo cụm |
| `tags` | **416** | hỗn hợp | 🟡 phần lớn TRÙNG view/suitable/amenity → lọc trùng trước |
| `location_tags` | **371** | setting/amenity/landmark | 🔴 lẫn tên riêng (vd "VinWonders Nha Trang") |
| `amenities` (flat) | **579** | amenity (many) | 🔴 **khối lớn nhất** — nhưng phân bố lệch |

### Phân bố `amenities` (579 unique) — lệch mạnh, map theo Pareto
- Top ~50 chuỗi: mỗi cái xuất hiện ở **>500 hotel** (WiFi 1268, lễ tân 24h 1171, ...).
- **102 chuỗi đuôi chỉ xuất hiện ở ≤2 hotel** (long tail).
- → **Chiến lược:** map kỹ top ~80–100 chuỗi (phủ >95% số lần xuất hiện); đuôi hiếm đẩy candidate_queue, không cố map hết.

### Giá trị cố định (map 1 lần là xong)
```
accommodation_type (13): Khách sạn(393) Resort(43) Căn hộ(37) Căn hộ dịch vụ(17)
  Nhà dân(10) Toàn bộ căn nhà(5) Nhà khách/B&B(5) Nhà nghỉ(3) Biệt thự nghỉ dưỡng(2)
  Bungalow(2) Biệt thự(1) Nhà nghỉ ven đường(1) Giường và Bữa sáng(1)

suitable_for (6): Khách du lịch một mình(501) Cặp đôi(499) Nhóm du khách(499)
  Gia đình có trẻ nhỏ(489) Khách đi công tác(451) Gia đình có thanh thiếu niên(451)

rating_breakdown aspects (7): Độ sạch sẽ · Vị trí · Dịch vụ · Cơ sở vật chất
  · Đáng tiền · Sự thoải mái và chất lượng phòng · Ăn uống
```

---

## 3. Review — phần SOFT KHÔNG còn bị chặn

> Đây là điều chỉnh so với phân tích ban đầu (tưởng review chưa crawl đủ).

| Chỉ số | Giá trị |
|---|---|
| Hotel có `reviews_detail` (aggregate) | **520 / 520** |
| Hotel có file review riêng (`data/raw/reviews/`) | **518 / 520** |
| Tổng review text thật | **112,276** |
| Review/hotel (min / median / mean / max) | 0 / **250** / 216 / 400 |
| Hotel có 0 review | 14 |
| Hotel có <10 review | 33 |

**Hệ quả:** Bước 5 (ABSA + hotel profile) có dữ liệu vững. Hai nguồn SOFT:
1. **Aggregate sẵn** (`reviews_detail.tags` `{tag, mentioned, positive_pct}` + `rating_breakdown` theo aspect) → seed profile gần như free.
2. **Per-review** (`text`, `rating`, `positives`/`negatives`, `reviewer_type`, `room_type`) → ABSA cho span dẫn chứng + concept ngoài 7 aspect (style/purpose).
- 14 hotel 0-review + 33 hotel <10-review: profile để `evidence_count` thấp → Wilson smoothing tự hạ score (đúng thiết kế, không cần xử lý đặc biệt).

---

## 4. Lưu ý kỹ thuật phát hiện ở Bước 0

1. **`nearby_places` dùng key `type` (không phải `category`)** — vd `{"name":"Bến tàu Bãi Cháy","type":"Bến Cảng và Bến Đò","distance_km":0.82}`. Bước build object phải đọc `type`.
2. **`tags` trùng nhiều với `view_types`/`suitable_for`/`location_tags`** — gom union rồi khử trùng trước khi map, tránh đếm 2 lần.
3. **`location_tags` lẫn tên riêng landmark** ("VinWonders Nha Trang", "Nha Trang beach") — không map thành concept facet; phần landmark đã có ở `location.generated.yaml` (Sprint 1).
4. **`star_rating` có giá trị 0.0 (32 hotel)** = chưa xếp hạng sao, KHÔNG phải 0 sao → coi là null khi suy price_tier.

---

## 5. Kết luận Bước 0 → vào Bước 1

- **Map được tự động ngay (Tầng 0), confidence cao:** object_type (13), purpose (6), aspect (7), view_types (23) → phủ 4 facet gần trọn.
- **Khối công việc chính:** amenity (~80–100 chuỗi top của 579) → AMEN_* concept.
- **SOFT (style/purpose-experience):** từ review — làm song song, KHÔNG chặn HARD.
- **Bước tiếp theo (Bước 1):** viết `ontology/source_tag_map.yaml` — map vocabulary nguồn → concept_id, đánh dấu giá trị chưa map được làm candidate.
