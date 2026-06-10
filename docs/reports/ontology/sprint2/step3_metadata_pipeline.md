# Sprint 2 — Bước 3: Metadata Pipeline (map / validate / reconcile)

> **Sản phẩm:** [metadata_pipeline.py](../../../../knowledge_engineering/enrichment/metadata_pipeline.py)
> + output `hotel_metadata.json` (520 hotel, gitignore — derived). Ngày: 2026-06-08.
> Với data Agoda giàu, đây là MAP + VALIDATE + RECONCILE (không trích từ text thô).

## 3 việc

### (1) MAP — location + range_filters + nearby
- **location**: country/province/city/district/area + lat/lng từ field structured (Sprint 1 đã clean).
  Phủ **520/520**, 0 thiếu country, 0 thiếu toạ độ.
- **range_filters** (số, KHÔNG phải concept): `star_rating` (0.0=chưa xếp hạng→None), `review_score`,
  `price_min_vnd`.
- **nearby_places**: đọc đúng key `type` (không phải `category` — phát hiện Bước 0), sort theo
  distance_km, cắt top 10. Phủ 520/520.

### (2) RECONCILE — suy `price_tier`, KHÔNG tin `is_luxury` mù
Phát hiện: **101/520 hotel star≥5 nhưng `is_luxury=False`** — Agoda gắn cờ không nhất quán.
Logic suy (gộp nhiều tín hiệu, ưu tiên bằng chứng cứng):
| Điều kiện | → tier |
|---|---|
| star≥5 + (Gold Circle hoặc is_luxury=True) | PRICE_LUXURY |
| star≥5 (không gold/luxury) | PRICE_UPSCALE *(không thổi mọi 5 sao thành luxury)* |
| star 4–4.5 | PRICE_UPSCALE |
| star 3–3.5 | PRICE_MID |
| star <3 | PRICE_BUDGET |
| star 0/None (chưa xếp hạng) | None (dựa range_filter giá) |

**Phân bố:** LUXURY 78 · UPSCALE 214 · MID 141 · BUDGET 55 · None 32.
**30 ca mâu thuẫn đã reconcile đúng** — vd Novotel Phú Quốc / Mường Thanh Luxury / FLC Luxury /
Imperial Vũng Tàu: 5 sao + Gold Circle nhưng is_luxury=False → **tin star+gold → PRICE_LUXURY**
(ghi `price_tier_note` để audit). Đúng tinh thần Task 2.3 "đừng tin cờ nguồn mù".

### (3) VALIDATE
Khối semantic (concept_id) validate bằng `schema.py` (pydantic) ở Bước 4 khi ghép thành object.
Pipeline này lo phần map/số.

## ⚠ 2 vấn đề DATA NGUỒN (không phải lỗi pipeline → báo Data Quality)

1. **Giá bị cap 5 triệu.** `rooms[].price_per_night`: **928 room đúng 5.000.000 chẵn, 0 room >5tr**
   → giá là **placeholder/cap** từ khâu clean, KHÔNG phải giá thật. `price_min_vnd` hiện chỉ tin được
   cho hotel giá <5tr. Range thật: 200k → median 1.46tr → cap 5tr. **→ Đề nghị DQ crawl lại giá thật.**
2. **`room_grid.cheapest_price` rỗng 520/520** → phải lấy giá từ `rooms[].price_per_night` (519/520 có).
   1 hotel thiếu hẳn giá.
3. **4 hotel data nghèo** (amenities=0–1) đã ghi nhận ở Bước 2 → cùng nhóm cần DQ rà.

## Kết luận → Bước 4
metadata (location + range + price_tier + nearby) + tag HARD (Bước 2) → đủ nguyên liệu **build
knowledge_object phần HARD** cho 520 hotel (Bước 4), validate bằng schema.py. Giá để placeholder,
gắn cờ `price_unreliable` chờ DQ.
