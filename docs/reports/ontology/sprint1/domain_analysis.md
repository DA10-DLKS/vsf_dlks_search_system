# Domain Analysis — DA10 Knowledge Engineering

> **Task 1.1 (Sprint 1).** Owner: Trương Anh Long.
> **Nguồn dữ liệu phân tích:** **520 hotel** thật crawl từ Agoda (`data/raw/hotels/*.json`).
> **Trạng thái:** Bước 1, 3, 4 hoàn thành trên data thật. **Bước 2 (facet suy từ golden query)** dùng golden set KE [`golden_query_concepts.md`](golden_query_concepts.md).
> **Cập nhật:** corpus 27 → 51 → 555 → **520 hotel** (chốt cuối: CHỈ VIỆT NAM — đã lọc bỏ hotel nước ngoài; regenerate Lớp A).
> ✅ **Phạm vi đã chốt:** 100% Việt Nam (520 hotel). Location ontology toàn cầu cũ đã thu về VN: 1 country / 14 province / 69 city / 126 area / 153 landmark.

---

## 0. Phạm vi corpus thật (thống kê khách quan, 520 hotel VN)

> Bảng dưới TỰ SINH bởi `build_domain_stats.py` (Lớp A). Chạy lại khi corpus đổi.

<!-- AUTO-STATS:corpus:START -->
| Chiều | Giá trị nguồn (Agoda) → số hotel |
|---|---|
| `accommodation_type` | Khách sạn (393), Resort (43), Căn hộ (37), Căn hộ dịch vụ (17), Nhà dân (10), Toàn bộ căn nhà (5), Nhà khách / Nhà nghỉ B&B (5), Nhà nghỉ (3), Biệt thự nghỉ dưỡng (2), Bungalow (2), Biệt thự (1), Nhà nghỉ ven đường (1), Giường và Bữa sáng (1) |
| `property_type` | Hotel (465), NonHotel (46), SingleRoom (9) |
| `star_rating` | 5.0 (149), 3.0 (131), 4.0 (124), 2.0 (39), 0.0 (32), 4.5 (19), 3.5 (10), 1.0 (9), 2.5 (7) |
| `city` (69 nơi) | Hà Nội (60), Hồ Chí Minh (49), Đà Nẵng (48), Nha Trang (39), Đảo Phú Quốc (28), Hội An (25), Đà Lạt (23), Hạ Long (22), + 26 tỉnh/thành mỗi nơi 1 |
<!-- AUTO-STATS:corpus:END -->

> ⚠ Với 520 hotel VN, phân bố (xem AUTO-STATS trên): **5 sao 149 / 4 sao 124 / 3 sao 131** + phân khúc thấp (2 sao 39, 0 sao 32) đã có mẫu thật để calibrate. Loại hình thêm **Căn hộ dịch vụ (17), Toàn bộ căn nhà (5), Nhà dân (10), B&B, Bungalow** — xuất hiện loại CHƯA có concept (xem mục Gap → candidate_queue, Lớp B). Địa danh **69 thành phố VN** (Hà Nội 60, HCM 49, Đà Nẵng 48...) — toàn bộ đã có concept location tự sinh (location.generated.yaml).

---

## 1. Bước 1 — Danh sách semantic concept hay gặp (≥ 20)

Suy ra từ các trường ngữ nghĩa thật của Agoda (`tags`, `suitable_for`, `view_types`, `amenities`, `nearby_places`, `reviews_detail.tags`). Đây là **concept ứng viên** (chưa phải ID cuối — ID trung tính sẽ chốt ở Task 1.2). Cột "Bằng chứng nguồn" ghi đúng từ Agoda dùng.

### Nhóm OBJECT_TYPE (loại hình lưu trú)
| # | Concept ứng viên | Bằng chứng nguồn (Agoda) |
|---|---|---|
| O1 | hotel | accommodation_type "Khách sạn" (393) |
| O2 | resort | accommodation_type "Resort" (43) |
| O3 | villa | accommodation_type "Biệt thự nghỉ dưỡng" (2), "Biệt thự" (1) |
| O4 | apartment / entire place | accommodation_type "Căn hộ" (37), "Căn hộ dịch vụ" (17), "Toàn bộ căn nhà" (5) |
| O5 | homestay | *vẫn không có "Homestay" thuần trong corpus 520 VN*; nhưng XUẤT HIỆN loại gần kề CHƯA có concept: "Nhà dân" (10), "Nhà khách / Nhà nghỉ B&B" (5), "Nhà nghỉ" (3), "Bungalow" (2), "Nhà nghỉ ven đường" (1), "Giường và Bữa sáng" (1) — xem mục Gap |

> Nhóm này map 1-1 với facet `object_type` (`OBJ_HOTEL/RESORT/VILLA/APARTMENT/HOMESTAY`). Với 520 hotel VN, **apartment có 59 mẫu** (Căn hộ 37 + Căn hộ dịch vụ 17 + Toàn bộ căn nhà 5) — `OBJ_APARTMENT` được củng cố mạnh. **Loại hình mới chưa có concept:** Nhà dân, B&B, Nhà nghỉ, Bungalow → cần đưa vào `candidate_queue.yaml` (Lớp B). `OBJ_HOMESTAY` vẫn không có mẫu "Homestay" thuần.

### Nhóm AMENITY (tiện ích — sự thật/presence)

> ⚠ Số đếm trong ngoặc ở bảng AMENITY/VIEW/REVIEW-TAG dưới đây là **mốc 51 hotel cũ**, CHƯA đếm lại trên 555 (tránh ghi số bịa). Sự *tồn tại* concept vẫn đúng; số tuyệt đối sẽ lớn hơn. Số 555 chính xác xem các bảng AUTO-STATS đã regenerate phía dưới.

| # | Concept ứng viên | Bằng chứng nguồn (Agoda, đếm trên mốc 51) |
|---|---|---|
| 1 | beachfront / bãi biển riêng | tag "Bãi biển riêng" (15), "Lối ra bãi biển thuận tiện" (17) |
| 2 | pool | amenity "Bể bơi"; review tag "Bể bơi" (41/51 hotel) |
| 3 | infinity / view pool | amenity "Bể bơi có tầm nhìn" |
| 4 | kids pool | amenity "Bể bơi [trẻ em]" |
| 5 | spa | amenity "Spa", "Spa/xông khô"; tag "Spa nổi bật" |
| 6 | sauna | amenity "Xông khô" (10), "Phòng xông ướt" |
| 7 | gym / fitness | amenity "Phòng tập"; review tag "Phòng tập" (16) |
| 8 | kids club | amenity "CLB trẻ em"; review tag "Cơ sở vật chất cho trẻ em" (12) |
| 9 | private beach | tag "Bãi biển riêng" (15) |
| 10 | airport shuttle | tag "Đưa đón sân bay" (39) |
| 11 | free wifi | tag "Wi-Fi miễn phí trong tất cả các phòng!" (47) |
| 12 | bar | tag "Quán bar" (34), "Quán bar cạnh bể bơi" (15) |
| 13 | restaurant / dining | amenity "Nhà hàng" (9); review tag "Nhiều lựa chọn nhà hàng" (31) |
| 14 | sea view | view_type "Hướng Đại dương" (17), "Hướng Biển" (14) |
| 15 | garden view | view_type "Hướng Vườn" (14) |
| 16 | city view | view_type "Hướng Thành phố" (32) |

### Nhóm PURPOSE / AUDIENCE (nhóm khách)
| # | Concept ứng viên | Bằng chứng nguồn |
|---|---|---|
| 17 | family | suitable_for "Gia đình có trẻ nhỏ" (51), "Gia đình có thanh thiếu niên" (48) |
| 18 | couple / romantic | suitable_for "Cặp đôi" (50) |
| 19 | solo | suitable_for "Khách du lịch một mình" (50) |
| 20 | group | suitable_for "Nhóm du khách" (50) |
| 21 | business | suitable_for "Khách đi công tác" (46) |

### Nhóm STYLE / SETTING / ASPECT (trải nghiệm — từ review)
| # | Concept ứng viên | Bằng chứng nguồn |
|---|---|---|
| 22 | quiet | sample_comment: "Bãi biển thì yên tĩnh..."; mô tả "không gian yên tĩnh và tĩnh lặng" |
| 23 | luxury | star 5.0 (30), gold_circle award; description "sang trọng / đẳng cấp" |
| 24 | nature / scenic | tag "Tầm nhìn đẹp" (22), "Vị trí lý tưởng" (28) |
| 25 | ASPECT_CLEANLINESS | review tag "Độ sạch sẽ" (48); grade "Độ sạch sẽ" |
| 26 | ASPECT_SERVICE / STAFF | review tag "Dịch vụ" (49); grade "Dịch vụ" |
| 27 | ASPECT_LOCATION | review tag "Địa điểm" (49); grade "Vị trí" |
| 28 | ASPECT_FOOD | review tag "Bữa sáng" (43); grade "Ăn uống" |
| 29 | ASPECT_ROOM | review tag "Kích thước phòng" (48), "Độ thoải mái của phòng" (45) |
| 30 | ASPECT_VALUE | review tag "Đáng tiền" (46); grade "Đáng tiền" |

> Đã đạt **≥ 20 concept** (30 ứng viên). Lưu ý nguyên tắc Task 1.2: concept **TRUNG TÍNH** — `ASPECT_CLEANLINESS` chứ không `ROOM_CLEAN`; tốt/xấu để ở `sentiment`.

---

## 2. Bước 2 — Facet suy từ golden query · ⏳ CHỜ GOLDEN SET

> **CHƯA LÀM — thiếu đầu vào.** DA10 Task 1.1 bước 2 yêu cầu: "Nhóm 30+ golden query theo chiều quan tâm → ra danh sách facet ứng viên." Golden set (30–50 query có nhãn) do **DA09 cấp** và repo hiện **chưa có** (`evaluation/relevance_labels/` mới chỉ có README + .gitkeep).
>
> **Khi nhận golden set, bổ sung vào đây:** bảng `query → (facet quan tâm + concept)`, từ đó chốt danh sách facet và kiểm chéo với facet sơ bộ ở mục 4 dưới.

**Facet ứng viên sơ bộ (suy TỪ DATA, không từ query — sẽ kiểm lại bằng golden set):**
`object_type`, `location`, `purpose`, `amenity`, `price_tier`, `style`, `aspect` (cho ABSA). Đây mới là giả thuyết từ cấu trúc Agoda, chưa xác nhận bằng hành vi query thật.

---

## 3. Bước 3 — Đặc thù tiếng Việt cần xử lý

| Hiện tượng | Ví dụ thật trong corpus | Hệ quả cho normalize/synonym |
|---|---|---|
| Biến thể vùng miền | nguồn dùng "**Bể bơi**"; người dùng (miền Nam) gõ "**hồ bơi**" | cần synonym map cả hai → cùng concept |
| Từ ghép | "hồ bơi", "bãi biển", "nhà hàng" | cần tách từ (underthesea) giữ ghép |
| Từ mượn / song ngữ trộn | word_cloud có "swimming pool", "water park", "cable car"; tag "Nha Trang beach" | xử lý cả nhãn EN lẫn VI |
| Không dấu | người dùng gõ "gan bien", "ho boi", "resort gan bien" | cần biến thể fold (bỏ dấu) trong synonym |
| Viết tắt | "ks" (khách sạn) | bổ sung surface form viết tắt |
| Đa dạng diễn đạt view | "Hướng Đại dương" / "Hướng Biển" / "Hướng biển (hướng một phần)" / "Hướng Bãi biển" | nhiều surface → cùng concept SEA_VIEW |

---

## 4. Bước 4 — Vốn từ vựng nguồn (chuẩn bị `source_tag_map.yaml`)

Vocabulary **đúng như Agoda ghi** (đếm trên 51 hotel). Đây là đầu vào cho Task 2.2 (Source-tag Mapping). Concept đích để TRỐNG ở đây — chốt sau khi có ontology Core (Task 1.2).

### 4.1 `suitable_for` (6 giá trị — phủ gần hết corpus)
<!-- AUTO-STATS:suitable_for:START -->
- Khách du lịch một mình (501) · Cặp đôi (499) · Nhóm du khách (499) · Gia đình có trẻ nhỏ (489) · Khách đi công tác (451) · Gia đình có thanh thiếu niên (451)
<!-- AUTO-STATS:suitable_for:END -->

### 4.2 `view_types` (18 giá trị)
<!-- AUTO-STATS:view_types:START -->
- Hướng Thành phố (286) · Hướng Ngoài trời (122) · Hướng Vườn (115) · Hướng Biển (107) · Hướng Đại dương (97) · Hướng Núi (63) · Hướng Đường phố (47) · Hướng Sông (44) · Hướng Không có cửa sổ (39) · Hướng biển (hướng một phần) (36) · Hướng Bể bơi (35) · Hướng Bãi biển (30)
<!-- AUTO-STATS:view_types:END -->

### 4.3 `tags` top-level (132 unique — trộn purpose + amenity + landmark + style)
Nhóm theo loại (giá trị tiêu biểu, số ≥ 5):
- **Purpose:** Gia đình có trẻ nhỏ (51), Cặp đôi (50), Nhóm du khách (50), Khách du lịch một mình (50), Gia đình có thanh thiếu niên (48), Khách đi công tác (46), Được gia đình đánh giá cao (17), Được khách đi công tác đánh giá cao (13), Phù hợp cho trẻ em (8)
- **Amenity:** Wi-Fi miễn phí trong tất cả các phòng! (47), Dọn phòng hằng ngày (43), Đưa đón sân bay (39), Quán bar (34), Lối ra bãi biển thuận tiện (17), Bãi biển riêng (15), Quán bar cạnh bể bơi (15), Bể bơi nổi bật (12), Xông khô (10), Nhà hàng (9), Bồn tắm nước nóng (8), Điều hòa (7)
- **View/Setting:** Hướng Thành phố (32), Bãi biển (25), Địa danh và thắng cảnh (23), Lối ra bãi biển thuận tiện (17), Hướng Đại dương (17), Hướng Biển (14), Hướng Vườn (14), Hướng Ngoài trời (11), trong nội thành (10), Hướng Núi (6), Hướng biển (hướng một phần) (6)
- **Style/Quality (mang sẵn polarity — KHÔNG đưa vào ID concept):** Vị trí lý tưởng (28), Tầm nhìn đẹp (22), Giá trị vượt trội (17), Rất sạch sẽ (17), Dịch vụ chăm sóc khách chuyên nghiệp (16), Phòng nghỉ thoải mái chất lượng cao (13), Ẩm thực nổi bật (8), Tiện nghi cơ sở lưu trú được đánh giá cao (6), Tiện nghi phòng được đánh giá cao (6)
- **Landmark (→ quan hệ `near`, Task 1.5):** Dragon Bridge (8) [Đà Nẵng], Nha Trang beach (7), Po Nagar Cham Towers (6), VinWonders/Vinpearl Safari Phu Quoc, Ben Thanh Market, War Remnants Museum...

> ⚠ **Lưu ý cho Task 2.2/2.3:** các tag "Rất sạch sẽ", "Vị trí lý tưởng", "Giá trị vượt trội"... đã **nhúng sẵn polarity tích cực** từ Agoda. Map chúng về concept TRUNG TÍNH (`ASPECT_CLEANLINESS` + `sentiment: positive`), KHÔNG tạo concept `CLEAN`/`GOOD_VALUE`.

### 4.4 `reviews_detail.tags` — aspect vocabulary (43 unique, dùng cho ABSA Sprint 2)
<!-- AUTO-STATS:review_tags:START -->
- Dịch vụ (475) · Độ sạch sẽ (473) · Địa điểm (466) · Độ thoải mái của phòng (451) · Đáng tiền (443) · Kích thước phòng (438) · Nhận phòng (407) · Bữa sáng (347) · Hướng nhìn từ phòng (337) · Phòng tắm (332) · Tiện nghi trong phòng (330) · Bộ đồ giường (294) · Thiết kế phòng (291) · Nhiều lựa chọn nhà hàng (288) · Tiện ích tại cơ sở lưu trú (282) · Bể bơi (269) · Điều hòa (267) · Không khí (259) · Gia đình (221) · Cách âm (219)
<!-- AUTO-STATS:review_tags:END -->

> Các aspect này khớp 6 trục ABSA dự kiến (room, staff/service, location, food, cleanliness, value) + phát sinh thêm (pool, beach, check-in/out, atmosphere) → đã mở rộng facet `aspect` lên 7 concept ở Task 1.4 (thêm `ASPECT_FACILITIES`).

### 4.5 `nearby_places.type` — phân loại landmark (43 type)
<!-- AUTO-STATS:nearby_type:START -->
Nhiều nhất: Bệnh Viện và Cơ Sở Y Tế (830), Siêu Thị (616), Trung Tâm và Khu Mua Sắm (406), Sân Bay (380), Công Viên Công Cộng (309), Địa điểm giải trí (205), Bãi Biển (160), Nơi Thờ Cúng (135), Đài Kỷ Niệm và Di Tích Lịch Sử (131), Quán Rượu (124)...
→ Mỗi `nearby_places` có `distance_km` → chuẩn hóa thẳng vào quan hệ `near` (Task 1.5).
<!-- AUTO-STATS:nearby_type:END -->

> **22 quan hệ near** đã sinh tự động cho 6 landmark Core (xem `relations_near.generated.yaml`).

---

## 5. Done criteria (Task 1.1)

- [x] ≥ 20 semantic concept (35 ứng viên: 5 object_type + 30 còn lại, có bằng chứng nguồn trên 51 hotel) — mục 1
- [ ] ≥ 30 golden query nhóm theo facet — **CHỜ golden set DA09** (mục 2)
- [x] Danh sách facet ứng viên (sơ bộ từ data) — mục 2 + 4
- [x] Ghi chú vocabulary nguồn (Agoda) — mục 4

> **Mở khóa phần còn lại:** cần DA09 cấp golden set (30–50 query có nhãn) để hoàn tất bước 2 và kiểm chéo facet.
