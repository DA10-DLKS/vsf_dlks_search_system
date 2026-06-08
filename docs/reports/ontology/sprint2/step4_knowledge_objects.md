# Sprint 2 — Bước 4: Build Knowledge Object (phần HARD)

> **Sản phẩm:** [build_objects.py](../../../../knowledge_engineering/enrichment/build_objects.py)
> + output `knowledge_objects.json` (520 object, gitignore — derived, tái sinh bằng script).
> Ghép tag (Bước 2) + metadata (Bước 3) → knowledge_object phần HARD. Ngày: 2026-06-08.

## 🎯 MỐC QUAN TRỌNG
Sau Bước 4, **520 hotel đã được gắn nhãn concept đầy đủ phần cứng** → câu *"lọc hotel có hồ bơi
ở Đà Nẵng"* giờ **trả lời được**. Đây là caveat lớn nhất ở handover Sprint 1 ("hotel CHƯA gắn
concept") — nay đã gỡ cho phần HARD.

## Object gồm gì (theo CONTRACT metadata_schema.yaml + SAMPLE)
- `semantic_metadata`: concept_id theo facet. **one** (object_type/price_tier) → 1 id; **many**
  (amenity/setting/purpose) → list. SOFT (style/aspect) để trống → Bước 5.
- `tags`: provenance từng nhãn (concept/confidence/sources) — cho governance/audit.
- `range_filters`: star/review_score/price_min + cờ `price_capped`.
- `location`: country/province/city/district/area + lat/lng.
- `nearby_places`: name/category/distance (sort gần nhất).
- `provenance`: source/url/crawled_at/mapper_version/price_note.

## Validate — CỔNG CHẤT LƯỢNG
| Kiểm | Kết quả |
|---|---|
| pydantic `schema.py` (concept tồn tại + required field) | **520/520 hợp lệ** ✅ |
| concept lạ trong semantic_metadata | 0 ✅ |
| cardinality one (object_type/price_tier không phải list) | 0 vi phạm ✅ |

## Độ phủ semantic_metadata /520
| Facet | Phủ | Ghi chú |
|---|---|---|
| object_type | **100%** | 1/hotel (đã sửa cardinality ở Bước 2) |
| amenity | **99%** (517) | |
| purpose | **97%** (504) | |
| price_tier | **94%** (488) | 32 None = chưa xếp sao (đúng) |
| setting | **42%** (218) | 302 hotel không setting = **đa số KS nội thành**, không có view tự nhiên — đúng, không phải lỗi |

## Giá fake — xử lý (theo thống kê + quyết định user)
- Thống kê: **90.9% hotel giá min <5tr** (phân bố tự nhiên 500k–2tr nhiều nhất); chỉ **9.1% (47 hotel)
  giá min =5tr chẵn = bị cap**.
- Xử lý: gắn cờ **`price_capped: true`** cho đúng 47 hotel đó + `provenance.price_note`. Tầng search
  thấy cờ → không lọc-giá cứng cho nhóm này; 472 hotel còn lại giá dùng bình thường.
- `price_tier` KHÔNG bị ảnh hưởng (suy từ star+gold, không từ giá).

## Known limitations (nhỏ, ghi để vòng sau)
1. **Setting từ location chưa gắn:** chỉ 4 LOC concept có `related` SETTING (Phú Quốc/Cửa Lò/Cửa Đại/
   Hòn Tre). Hotel biển có thể thiếu SETTING_COASTAL nếu phòng không có view biển. Lợi ích nhỏ →
   để vòng tinh chỉnh (cần map hotel→LOC qua registry).
2. **location.province đôi khi = city** (vd "Nha Trang" thay vì "Khánh Hòa") — vấn đề data nguồn,
   báo Data Quality. Không chặn (city/area vẫn đúng).
3. `semantic_metadata.location` chưa gắn concept_id `LOC_*` (mới có text+toạ độ) — đủ filter/hiển thị;
   gắn LOC concept để dùng cho quan hệ near là tinh chỉnh sau.

## Kết luận → Bước 5
Object HARD xong cho 520 hotel, validate sạch. Còn **phần SOFT** (style/aspect + sentiment từ
112k review) — Bước 5 (ABSA + hotel profile), gắn bổ sung vào object. Rồi Bước 6 hợp nhất + bàn giao.
