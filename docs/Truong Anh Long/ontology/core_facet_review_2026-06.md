# Review Core Ontology theo facet (2026-06-25, trước demo mentor)

Cách làm: với mỗi facet, từ DATA xem lấy được full gì → so ontology hiện tại → vá cái "đúng và có ý nghĩa" theo GÓC KHÁCH HÀNG (giữ nếu khách hay hỏi, kể cả phổ biến). KHÔNG re-embed (chỉ chạy mapper/profile/build_objects → JSON metadata).

---

## 1. amenity — ĐÃ SỬA
- 44 → 59 concept (+15 theo góc khách: BREAKFAST, BATHTUB, LAUNDRY, 24H_FRONTDESK, SMOKING/NON_SMOKING, FAMILY_ROOM, CAR_RENTAL, LOUNGE, LIBRARY, WATERPARK, NIGHTCLUB, EVENT_VENUE, WORKSPACE, FEMALE_ONLY).
- Vá biến thể surface + bug raw-vs-cleaned (source_tag_map phải dùng chuỗi data/cleaned/).
- Kết quả: 11.858 amenity tags, phủ 34.5%, 15/15 concept gán vào hotel.
- Chi tiết: [amenity_customer_review.md](amenity_customer_review.md).

## 2. object_type — ĐÃ SỬA (nhẹ)
- 9 concept đủ; 13/13 accommodation_type → 8 OBJ_*, 520/520 hotel gán, 0 sót.
- Vá surface_form query: condotel/căn hộ khách sạn→APARTMENT, nhà nguyên căn→HOMESTAY, nhà trọ/motel→GUESTHOUSE.
- KHÔNG thêm hostel/capsule/glamping (0 hotel VN).

## 3. setting — ĐÃ SỬA (gồm code)
- 7 concept đủ. Bug: 79 KS lõi HN/HCM thiếu SETTING_CITY_CENTER (rule chỉ bắt chữ "trung tâm" trong address).
- Vá rule build_objects: tín hiệu "Cách trung tâm TP ≤2km" (data-driven) + whitelist quận lõi HN/HCM.
- CITY_CENTER 39→133 hotel, hotel thiếu setting 150→97 (còn lại là KS đô thị thuần — đúng), 0 gắn nhầm ngoại vi.
- Vá surface: nông thôn/vùng quê/ngoại ô→SETTING_NATURE.

## 4. aspect (VIEW) — ĐÃ SỬA
- Thêm ASPECT_VIEW (SOFT): tách "view đẹp/xấu" (quality) khỏi SETTING_VIEW ("có view", presence).
- Điểm từ review tag "Hướng nhìn từ phòng" (337 hotel, positive_pct) — không LLM.
- "view xấu" giờ route ASPECT_VIEW (không bị hiểu ngược thành "có view").
- ⏳ NGOÀI SCOPE: chữ "xấu"=đảo chiều xếp hotel score-thấp là việc intent parser (query_negation chỉ bắt "không/tránh"), CHƯA làm.

## 5. purpose — ĐÃ SỬA (gồm code)
- Vấn đề: suitable_for loãng (450/520 hotel đủ 5 purpose); điểm chỉ 3/6 nhóm, SOLO/GROUP/WELLNESS=0.
- Wire fallback chain: demographics (shrinkage, 5 nhóm) > review_tag > derived (WELLNESS từ SPA+QUIET ×0.8) > presence.
- 6/6 purpose có điểm (451-501 hotel/nhóm). metadata.purpose giữ DA09 audience; điểm vào semantic_profile.

## 6. style — KHÔNG ĐỘNG CORE (ổn) — ⚠ GHI NHẬN lỗ hổng ABSA-recall
Style core ỔN: 15 concept, ĐÃ có điểm đầy đủ (nguồn absa 1219 + absa+tags 320 + tags 48), lọc ngưỡng 0.6 → metadata. KHÁC purpose (purpose từng thiếu điểm). KHÔNG thêm/xóa concept.

**Lỗ hổng (KHÔNG phải ontology — ở tầng ABSA recall, để backfill sau):**

| Concept | hotel có điểm | review thô NHẮC | Chẩn đoán |
|---|---:|---:|---|
| STYLE_EUROPEAN_JAPANESE | 0 | 204 | ABSA bỏ sót |
| STYLE_AESTHETIC | 0 | 70 | ABSA bỏ sót |
| STYLE_VINTAGE | 1 | 43 | ABSA bỏ sót |
| STYLE_MINIMALIST | 1 | 42 | ABSA bỏ sót |
| STYLE_LIVELY | 5 | 89 | ABSA bỏ sót |

→ Review CÓ nhắc (40-204 lần) nhưng ABSA chưa gán → KHÔNG xóa concept (sẽ bỏ sót đúng), KHÔNG sửa surface (gốc ở gán hotel). Thuốc đúng = **backfill ABSA** (gọi LLM batch, tốn RPD — xem [[absa-rpd-batching]], [[absa-style-recall-golden]]). Việc riêng, ngoài scope review ontology core.

---

## Review tag CHƯA map (cân nhắc khi tới aspect mở rộng)
8/45 review tag chưa map: Vòi sen(152)/Nước nóng(125)/Bồn tắm(61) → chi tiết phòng (gộp ASPECT_ROOM?); Di chuyển(75)/Mua sắm(25) → gần ASPECT_LOCATION; An toàn(45) → đáng cân nhắc (khách nữ/gia đình hỏi); Chủ nhà(32) → host homestay; Cuộc sống về đêm(21)/Hoạt động(34) → STYLE_LIVELY/location.

## 7. price_tier — ĐÃ SỬA (gồm code)
- 4 concept đủ; suy từ star+gold+luxury (cẩn thận, không thổi 5 sao→luxury). Khớp giá thật tốt.
- Giá SỐ tách riêng ở range_filters (đúng thiết kế). Tier chỉ là phân khúc ngữ nghĩa.
- Gap: 32 hotel star=None → tier=None, dù CẢ 32 có giá thật (600k-1.5tr) → khách hỏi "giá rẻ" bỏ sót.
- Vá infer_price_tier (metadata_pipeline): star=None + có giá thật (không capped) → suy tier từ giá.
  Ngưỡng data-driven: BUDGET<450k | MID 450k-1.2tr | UPSCALE 1.2-3.5tr | LUXURY≥3.5tr (từ median tier theo star).
- Kết quả: None 32→0 (30 MID + 2 UPSCALE), 0 regression hotel có star, đánh dấu price_inferred để audit.
- Đúng ý định comment ontology dòng 120 ("star=None → dựa range_filter giá").

---

## TỔNG KẾT đợt review
- 7 facet review xong. Sửa: amenity, object_type, setting, aspect(VIEW), purpose, price_tier. KHÔNG đụng: style (ổn).
- Code sửa: build_objects (CITY_CENTER, derive_purpose), profile_builder (demographics+derived), metadata_pipeline (price từ giá).
- KHÔNG re-embed lần nào (chỉ mapper/profile/metadata→build_objects → JSON metadata).
- Ghi nhận để xử lý sau: ABSA-recall 5 style concept; intent parser "view xấu"=đảo chiều; review tag chưa map (An toàn/Chủ nhà).
