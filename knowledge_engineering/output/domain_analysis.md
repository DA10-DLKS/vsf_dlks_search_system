# Domain Analysis — DA10 Knowledge Engineering

> **Task 1.1 (Sprint 1).** Owner: Trương Anh Long.
> **Nguồn dữ liệu phân tích:** 27 hotel thật crawl từ Agoda (`data/raw/hotels/*.json`).
> **Trạng thái:** Bước 1, 3, 4 hoàn thành trên data thật. **Bước 2 (facet suy từ golden query) đang CHỜ golden set DA09 cấp** — đánh dấu rõ ở dưới, chưa bịa.

---

## 0. Phạm vi corpus thật (thống kê khách quan, 27 hotel)

| Chiều | Giá trị nguồn (Agoda) → số hotel |
|---|---|
| `accommodation_type` | Khách sạn (15), Resort (10), Biệt thự nghỉ dưỡng (1), Toàn bộ căn nhà (1) |
| `property_type` | Hotel (26), SingleRoom (1) |
| `star_rating` | 5.0 (24), 4.0 (2), 3.0 (1) |
| `city` (15 nơi) | Nha Trang (6), Đảo Phú Quốc (4), Hội An (3), Hồ Chí Minh (2), Hà Tĩnh (2), + 10 tỉnh/thành mỗi nơi 1 |

> ⚠ Corpus lệch mạnh về **Vinpearl/Melia 5 sao** → khi calibrate ngưỡng (Sprint 2) phải nhớ phân bố này, tránh kết luận quá tự tin cho phân khúc thấp/loại hình villa-homestay (rất ít mẫu).

---

## 1. Bước 1 — Danh sách semantic concept hay gặp (≥ 20)

Suy ra từ các trường ngữ nghĩa thật của Agoda (`tags`, `suitable_for`, `view_types`, `amenities`, `nearby_places`, `reviews_detail.tags`). Đây là **concept ứng viên** (chưa phải ID cuối — ID trung tính sẽ chốt ở Task 1.2). Cột "Bằng chứng nguồn" ghi đúng từ Agoda dùng.

### Nhóm AMENITY (tiện ích — sự thật/presence)
| # | Concept ứng viên | Bằng chứng nguồn (Agoda) |
|---|---|---|
| 1 | beachfront / bãi biển riêng | tag "Bãi biển riêng" (13), "Lối ra bãi biển thuận tiện" (11) |
| 2 | pool | amenity "Bể bơi"; review tag "Bể bơi" (24/27 hotel) |
| 3 | infinity / view pool | amenity "Bể bơi có tầm nhìn" |
| 4 | kids pool | amenity "Bể bơi [trẻ em]" |
| 5 | spa | amenity "Spa", "Spa/xông khô"; tag "Spa nổi bật" |
| 6 | sauna | amenity "Xông khô", "Phòng xông ướt" |
| 7 | gym / fitness | amenity "Phòng tập"; review tag "Phòng tập" (10) |
| 8 | kids club | amenity "CLB trẻ em" |
| 9 | private beach | tag "Bãi biển riêng" |
| 10 | airport shuttle | tag "Đưa đón sân bay" (18) |
| 11 | free wifi | tag "Wi-Fi miễn phí trong tất cả các phòng!" (23) |
| 12 | bar | tag "Quán bar" (20), "Quán bar cạnh bể bơi" (10) |
| 13 | restaurant / dining | amenity "Nhà hàng"; review tag "Nhiều lựa chọn nhà hàng" (20) |
| 14 | sea view | view_type "Hướng Đại dương" (12), "Hướng Biển" (5) |
| 15 | garden view | view_type "Hướng Vườn" (13) |
| 16 | city view | view_type "Hướng Thành phố" (13) |

### Nhóm PURPOSE / AUDIENCE (nhóm khách)
| # | Concept ứng viên | Bằng chứng nguồn |
|---|---|---|
| 17 | family | suitable_for "Gia đình có trẻ nhỏ" (26), "Gia đình có thanh thiếu niên" (25) |
| 18 | couple / romantic | suitable_for "Cặp đôi" (26) |
| 19 | solo | suitable_for "Khách du lịch một mình" (25) |
| 20 | group | suitable_for "Nhóm du khách" (26) |
| 21 | business | suitable_for "Khách đi công tác" (24) |

### Nhóm STYLE / SETTING / ASPECT (trải nghiệm — từ review)
| # | Concept ứng viên | Bằng chứng nguồn |
|---|---|---|
| 22 | quiet | sample_comment: "Bãi biển thì yên tĩnh..."; mô tả "không gian yên tĩnh và tĩnh lặng" |
| 23 | luxury | star 5.0 (24), gold_circle award; description "sang trọng / đẳng cấp" |
| 24 | nature / scenic | tag "Khung cảnh thiên nhiên tuyệt đẹp", "Tầm nhìn đẹp" (13) |
| 25 | ASPECT_CLEANLINESS | review tag "Độ sạch sẽ" (25); grade "Độ sạch sẽ" |
| 26 | ASPECT_SERVICE / STAFF | review tag "Dịch vụ" (25); grade "Dịch vụ" |
| 27 | ASPECT_LOCATION | review tag "Địa điểm" (25); grade "Vị trí" |
| 28 | ASPECT_FOOD | review tag "Bữa sáng" (24); grade "Ăn uống" |
| 29 | ASPECT_ROOM | review tag "Kích thước phòng" (25), "Độ thoải mái của phòng" (24) |
| 30 | ASPECT_VALUE | review tag "Đáng tiền" (24); grade "Đáng tiền" |

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

Vocabulary **đúng như Agoda ghi** (đếm trên 27 hotel). Đây là đầu vào cho Task 2.2 (Source-tag Mapping). Concept đích để TRỐNG ở đây — chốt sau khi có `concepts.yaml` (Task 1.2).

### 4.1 `suitable_for` (6 giá trị — phủ gần hết corpus)
- Cặp đôi (26) · Gia đình có trẻ nhỏ (26) · Nhóm du khách (26) · Khách du lịch một mình (25) · Gia đình có thanh thiếu niên (25) · Khách đi công tác (24)

### 4.2 `view_types` (11 giá trị)
- Hướng Vườn (13) · Hướng Thành phố (13) · Hướng Đại dương (12) · Hướng Ngoài trời (6) · Hướng Biển (5) · Hướng Bể bơi (5) · Hướng Hồ (3) · Hướng Bãi biển (3) · Hướng Sông (3) · Hướng biển (hướng một phần) (2) · Hướng Núi (2)

### 4.3 `tags` top-level (87 unique — trộn purpose + amenity + landmark + style)
Nhóm theo loại (giá trị tiêu biểu, số ≥ 3):
- **Purpose:** Cặp đôi (26), Gia đình có trẻ nhỏ (26), Nhóm du khách (26), Gia đình có thanh thiếu niên (25), Khách du lịch một mình (25), Khách đi công tác (24), Phù hợp cho trẻ em (7), Được gia đình đánh giá cao (6), Được khách đi công tác đánh giá cao (3)
- **Amenity:** Wi-Fi miễn phí trong tất cả các phòng! (23), Quán bar (20), Đưa đón sân bay (18), Bãi biển riêng (13), Bể bơi nổi bật (10), Quán bar cạnh bể bơi (10), Xông khô (9), Bồn tắm nước nóng (4), Phòng xông ướt (3), Điều hòa (4)
- **View/Setting:** Hướng Vườn (13), Hướng Thành phố (13), Hướng Đại dương (12), Hướng Ngoài trời (6), Hướng Biển (5), Hướng Bể bơi (5), Hướng Hồ (3), Hướng Bãi biển (3), Hướng Sông (3), Hướng biển (hướng một phần) (2)
- **Style/Quality (mang sẵn polarity — KHÔNG đưa vào ID concept):** Tầm nhìn đẹp (13), Vị trí lý tưởng (11), Rất sạch sẽ (9), Dịch vụ chăm sóc khách chuyên nghiệp (9), Phòng nghỉ thoải mái chất lượng cao (8), Giá trị vượt trội (8), Bữa sáng ngon miệng (5), Ẩm thực nổi bật (4), Tiện nghi thể thao xuất sắc (4)
- **Landmark (→ quan hệ `near`, Task 1.5):** Nha Trang beach (4), VinWonders Nha Trang (3), Vinpearl Safari Phu Quoc (3), Vinwonders Phu Quoc (3), Ben Thanh Market (2), Central Post Office (2), The Independence Palace (2), War Remnants Museum (2), Po Nagar Cham Towers (2)

> ⚠ **Lưu ý cho Task 2.2/2.3:** các tag "Rất sạch sẽ", "Vị trí lý tưởng", "Giá trị vượt trội"... đã **nhúng sẵn polarity tích cực** từ Agoda. Map chúng về concept TRUNG TÍNH (`ASPECT_CLEANLINESS` + `sentiment: positive`), KHÔNG tạo concept `CLEAN`/`GOOD_VALUE`.

### 4.4 `reviews_detail.tags` — aspect vocabulary (41 unique, dùng cho ABSA Sprint 2)
- Dịch vụ (25) · Độ sạch sẽ (25) · Địa điểm (25) · Kích thước phòng (25) · Bữa sáng (24) · Độ thoải mái của phòng (24) · Bể bơi (24) · Đáng tiền (24) · Tiện ích tại cơ sở lưu trú (23) · Nhận phòng (22) · Hướng nhìn từ phòng (22) · Nhiều lựa chọn nhà hàng (20) · Gia đình (19) · Không khí (18) · Trả phòng (16) · Phòng tắm (14) · Bãi biển (14) · Phòng tập (10) · Spa (9) · Điều hòa (9)

> Các aspect này khớp 6 trục ABSA dự kiến (room, staff/service, location, food, cleanliness, value) + phát sinh thêm (pool, beach, check-in) → cân nhắc mở rộng facet `aspect` ở Task 1.4.

### 4.5 `nearby_places.type` — phân loại landmark (38 type)
Nhiều nhất: Bệnh Viện/Cơ Sở Y Tế (45), Siêu Thị (23), Sân Bay (18), Công Viên Giải Trí (16), Sông và Hồ (15), Bãi Biển (13), Sân Gôn (7)...
→ Mỗi `nearby_places` có `distance_km` → chuẩn hóa thẳng vào quan hệ `near` (Task 1.5).

---

## 5. Done criteria (Task 1.1)

- [x] ≥ 20 semantic concept (30 ứng viên, có bằng chứng nguồn) — mục 1
- [ ] ≥ 30 golden query nhóm theo facet — **CHỜ golden set DA09** (mục 2)
- [x] Danh sách facet ứng viên (sơ bộ từ data) — mục 2 + 4
- [x] Ghi chú vocabulary nguồn (Agoda) — mục 4

> **Mở khóa phần còn lại:** cần DA09 cấp golden set (30–50 query có nhãn) để hoàn tất bước 2 và kiểm chéo facet.
