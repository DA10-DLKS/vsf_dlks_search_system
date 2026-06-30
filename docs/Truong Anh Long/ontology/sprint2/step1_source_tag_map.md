# Sprint 2 — Bước 1: Source-tag Mapping (Tầng 0)

> **Sản phẩm:** [ontology/source_tag_map.yaml](../../../../ontology/source_tag_map.yaml) v1.0.0.
> Map vocabulary nguồn Agoda → concept_id ĐÃ TỒN TẠI. Lớp phủ rẻ & chắc nhất, chạy
> TRƯỚC rule/embedding/LLM trong ontology_mapper (Bước 2). Ngày: 2026-06-07.

## Map những gì

| Trường nguồn | Map → facet | Giá trị nguồn map | Ghi chú |
|---|---|---|---|
| `accommodation_type` (13) | object_type | 13/13 | đủ |
| `suitable_for` (6) | purpose | 6/6 | đủ |
| `view_types` (23) | setting + AMEN_SEA_VIEW + AMEN_POOL | 16/23 | 7 hướng đô thị/không-cảnh cố ý skip |
| `amenities` (579) | amenity (AMEN_*) | ~90 chuỗi top | Pareto: phủ phần đầu, đuôi → _unmapped/_skip |

Tham chiếu concept_id riêng biệt, tất cả tồn tại trong `ontology/core/`.

### Duyệt candidate (2026-06-08) — bổ sung 5 amenity concept
Sau khảo sát `_unmapped`, đã duyệt 18 ứng viên (candidate_queue + _unmapped): **5 promote / 10 defer / 1 reject**.
- ✅ **Promote → core/amenity.yaml** (amenity hard, lọc được): `AMEN_TENNIS`(61) · `AMEN_KARAOKE`(65) ·
  `AMEN_GAME_ROOM`(67, gộp bi-a+bóng bàn) · `AMEN_WATERSPORT`(101) · `AMEN_HIKING`(65). → core: 414→**419** concept; amenity 25→**30**.
- ⏸ **Defer** (chờ query log / review ABSA): purpose MICE/Wedding/Workation/Backpacker/Staycation ·
  setting Countryside · style Vintage/Traditional/Boutique (marketing-fluff) · amenity Yoga (tạm gộp GYM).
- ❌ **Reject** (không phân biệt khi search): Đổi ngoại tệ (514 hotel nhưng KS nào cũng có).
- synonym_dictionary regenerate: 1365 → **1432 form**.

## Độ phủ thực đo trên 520 hotel

| Trường | Phủ | Diễn giải |
|---|---|---|
| accommodation_type | **100%** (520/520) | mọi hotel có object_type |
| suitable_for | **100%** (2890/2890) | mọi giá trị purpose map được |
| view_types | **53.7%** | phần còn lại là hướng đô thị — skip cố ý |
| **amenities (theo hotel)** | **99.0%** (515/520) | **hotel có ≥1 amenity concept** |
| amenities (theo lần xuất hiện chuỗi) | 28.8% | mẫu số gồm ~vạn chuỗi noise (xem dưới) |

**Vì sao 28.8% chuỗi nhưng 99% hotel?** Phần lớn chuỗi không-map là **noise không mang giá trị lọc**
(lễ tân 24h, tiếng Việt/Anh, bảo vệ 24h, dọn phòng, an toàn COVID, vật dụng phòng vụn vặt).
Đo theo *hotel* mới phản ánh đúng giá trị: 99% hotel được phủ, cả 25 AMEN_* concept đều có coverage
(trừ `AMEN_SEA_VIEW` đến từ `view_types`, không phải `amenities` — mapper gộp 2 trường ở Bước 2).

Phủ theo concept (source-tag): WiFi 510 · AC 478 · Parking 475 · Restaurant 445 · KidsClub 421 ·
Elevator 419 · Shuttle 389 · Garden 377 · Bar 320 · Wheelchair 315 · Cafe 297 · Meeting 291 ·
Pool 280 · Gym 258 · Spa 250 · Bike 223 · Kitchen 196 · KidsPool 171 · InfinityPool 153 · Golf 133 ·
Beachfront 99 · Babysitting 93 · Pet 74 · PrivatePool 17.

## _unmapped (ứng viên candidate, KHÔNG tự thêm core)

Vocabulary lặp nhiều nhưng chưa có concept — đối chiếu `candidate_queue.yaml`:
Karaoke(130) · Tennis/cầu lông/bóng quần(158) · Yoga(120) · Bi-a/bóng bàn(180) · Đổi ngoại tệ(514) ·
Hiking(130) · Watersport[xuồng/câu cá/lặn/snorkel](424). Nhiều cái ĐÃ ở candidate_queue từ Sprint 1.

## _skip (không map — kèm lý do theo nhóm)

Ngôn ngữ phục vụ · "Cách bãi biển X mét" (→range/nearby) · "Tọa lạc trung tâm X" (→location) ·
biện pháp COVID · vật dụng phòng vụn vặt · dịch vụ hành chính/lễ tân chung · an ninh chung ·
hút thuốc (thuộc tính phòng). Chi tiết trong `_skip` của file YAML.

## Kết luận → Bước 2

source_tag_map phủ ~99% hotel cho 4 facet hard (object_type, purpose, một phần setting/amenity)
với confidence cao, gần như free. Phần CÒN LẠI cho ontology_mapper (Bước 2):
- **AMEN_SEA_VIEW** từ view_types (gộp trường).
- Amenity cách-nói-lạ trong `description` (rule + embedding).
- SOFT facets (style/aspect) từ review (Bước 5).
