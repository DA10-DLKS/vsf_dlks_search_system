# Domain Analysis — DA10 Knowledge Engineering

> **Task 1.1 (Sprint 1).** Owner: Trương Anh Long.
> **Nguồn dữ liệu phân tích:** **51 hotel** thật crawl từ Agoda (`data/raw/hotels/*.json`).
> **Trạng thái:** Bước 1, 3, 4 hoàn thành trên data thật. **Bước 2 (facet suy từ golden query) đang CHỜ golden set DA09 cấp** — đánh dấu rõ ở dưới, chưa bịa.
> **Cập nhật:** corpus mở rộng 27 → **51 hotel** (regenerate Lớp A, 2026-06-04). Số liệu dưới đây đã quét lại toàn bộ 51.

---

## 0. Phạm vi corpus thật (thống kê khách quan, 51 hotel)

> Bảng dưới TỰ SINH bởi `build_domain_stats.py` (Lớp A). Chạy lại khi corpus đổi.

<!-- AUTO-STATS:corpus:START -->
| Chiều | Giá trị nguồn (Agoda) → số hotel |
|---|---|
| `accommodation_type` | Khách sạn (33), Resort (10), Căn hộ (5), Biệt thự nghỉ dưỡng (1), Toàn bộ căn nhà (1), Căn hộ dịch vụ (1) |
| `property_type` | Hotel (45), NonHotel (4), SingleRoom (2) |
| `star_rating` | 5.0 (30), 4.0 (13), 3.0 (5), 4.5 (2), 0.0 (1) |
| `city` (21 nơi) | Nha Trang (10), Đà Nẵng (8), Hạ Long (5), Đảo Phú Quốc (4), Hội An (4), Hồ Chí Minh (3), Vinh (2), Hà Tĩnh (2), + 13 tỉnh/thành mỗi nơi 1 |
<!-- AUTO-STATS:corpus:END -->

> ⚠ Corpus vẫn lệch về **5 sao (30/51) + cụm Vinpearl/Melia**, nhưng đã ĐA DẠNG HƠN nhiều so với mốc 27: thêm phân khúc 4 sao (13) và 3 sao (5), thêm loại hình **Căn hộ (5)**, và phủ thêm điểm đến **Đà Nẵng (8), Hạ Long (5)**. Khi calibrate ngưỡng (Sprint 2) vẫn nhớ phân bố lệch 5 sao, nhưng nay đã có mẫu cho phân khúc thấp/loại hình apartment để kiểm.

---

## 1. Bước 1 — Danh sách semantic concept hay gặp (≥ 20)

Suy ra từ các trường ngữ nghĩa thật của Agoda (`tags`, `suitable_for`, `view_types`, `amenities`, `nearby_places`, `reviews_detail.tags`). Đây là **concept ứng viên** (chưa phải ID cuối — ID trung tính sẽ chốt ở Task 1.2). Cột "Bằng chứng nguồn" ghi đúng từ Agoda dùng.

### Nhóm OBJECT_TYPE (loại hình lưu trú)
| # | Concept ứng viên | Bằng chứng nguồn (Agoda) |
|---|---|---|
| O1 | hotel | accommodation_type "Khách sạn" (33) |
| O2 | resort | accommodation_type "Resort" (10) |
| O3 | villa | accommodation_type "Biệt thự nghỉ dưỡng" (1) |
| O4 | apartment / entire place | accommodation_type "Căn hộ" (5), "Căn hộ dịch vụ" (1), "Toàn bộ căn nhà" (1) |
| O5 | homestay | *không có trong corpus 51 hotel*; thêm vào ontology theo domain knowledge chuẩn ngành (loại hình phổ biến VN) |

> Nhóm này map 1-1 với facet `object_type` (`OBJ_HOTEL/RESORT/VILLA/APARTMENT/HOMESTAY`). Với 51 hotel, **apartment giờ có 7 mẫu** (Căn hộ 5 + Căn hộ dịch vụ 1 + Toàn bộ căn nhà 1) — `OBJ_APARTMENT` được củng cố bằng data thật. `OBJ_HOMESTAY` vẫn là concept Core suy từ domain knowledge, **chưa có mẫu trong corpus** — đánh dấu để khi mở rộng data thì kiểm lại.

### Nhóm AMENITY (tiện ích — sự thật/presence)
| # | Concept ứng viên | Bằng chứng nguồn (Agoda) |
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
- Gia đình có trẻ nhỏ (51) · Cặp đôi (50) · Khách du lịch một mình (50) · Nhóm du khách (50) · Gia đình có thanh thiếu niên (48) · Khách đi công tác (46)
<!-- AUTO-STATS:suitable_for:END -->

### 4.2 `view_types` (18 giá trị)
<!-- AUTO-STATS:view_types:START -->
- Hướng Thành phố (32) · Hướng Đại dương (17) · Hướng Biển (14) · Hướng Vườn (14) · Hướng Ngoài trời (11) · Hướng Núi (6) · Hướng biển (hướng một phần) (6) · Hướng Bể bơi (5) · Hướng Hồ (5) · Hướng Bãi biển (5) · Hướng Sông (4) · Hướng Đường phố (3)
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
- Dịch vụ (49) · Địa điểm (49) · Độ sạch sẽ (48) · Kích thước phòng (48) · Đáng tiền (46) · Độ thoải mái của phòng (45) · Nhận phòng (45) · Bữa sáng (43) · Bể bơi (41) · Hướng nhìn từ phòng (41) · Tiện ích tại cơ sở lưu trú (39) · Gia đình (34) · Phòng tắm (33) · Nhiều lựa chọn nhà hàng (31) · Tiện nghi trong phòng (30) · Không khí (27) · Bãi biển (25) · Điều hòa (25) · Bộ đồ giường (25) · Trả phòng (24)
<!-- AUTO-STATS:review_tags:END -->

> Các aspect này khớp 6 trục ABSA dự kiến (room, staff/service, location, food, cleanliness, value) + phát sinh thêm (pool, beach, check-in/out, atmosphere) → đã mở rộng facet `aspect` lên 7 concept ở Task 1.4 (thêm `ASPECT_FACILITIES`).

### 4.5 `nearby_places.type` — phân loại landmark (43 type)
<!-- AUTO-STATS:nearby_type:START -->
Nhiều nhất: Siêu Thị (86), Bệnh Viện và Cơ Sở Y Tế (79), Công Viên Công Cộng (29), Trung Tâm và Khu Mua Sắm (26), Sông và Hồ (24), Công Viên Giải Trí (22), Trung tâm thể thao và Yoga (21), Địa điểm giải trí (20), Bãi Biển (18), Sân Bay (18)...
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
