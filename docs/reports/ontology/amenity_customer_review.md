# Amenity — Review lại theo GÓC KHÁCH HÀNG

**2 nguyên tắc đã chốt:**
1. Giữ amenity nếu **khách hay hỏi** — kể cả phổ biến (wifi, đỗ xe). Giá trị = trả lời được câu hỏi + lọc mặt phủ định (KS KHÔNG có).
2. Thuộc tính phòng (bồn tắm, hút thuốc, phòng gia đình) **vẫn gắn amenity cấp hotel** theo quy tắc any-room (≥1 phòng có).

> File này thay cho amenity_noise_review.md cũ (lọc theo "phân biệt" — đã bỏ).

---

## A. ỨNG VIÊN CONCEPT MỚI (khách hỏi nhiều, ontology CHƯA có)

| # | Concept đề xuất | Label | ~Freq | Chuỗi data nguồn | Lý do (khách hỏi gì) |
|---|---|---|---:|---|---|
| 1 | `AMEN_BREAKFAST` | Bữa sáng | 238 | Bữa sáng [tự chọn/miễn phí/kiểu Á/lục địa/Mỹ...] | Khách hỏi "có ăn sáng không / ăn sáng buffet". Hiện lẫn vào RESTAURANT. |
| 2 | `AMEN_BATHTUB` | Bồn tắm | 115 | Bồn tắm, Bồn tắm/vòi sen riêng, Bồn tắm gỗ Hinoki | Cặp đôi/nghỉ dưỡng hỏi "phòng có bồn tắm". Thuộc tính phòng -> any-room. |
| 3 | `AMEN_LAUNDRY` | Dịch vụ giặt là | 451 | Dịch vụ giặt là, Giặt khô, Dịch vụ ủi đồ | Khách đi dài ngày hỏi "có giặt đồ không". (khác AMEN_WASHING_MACHINE tự giặt) |
| 4 | `AMEN_24H_FRONTDESK` | Lễ tân 24 giờ | 461 | Bàn tiếp tân [24 giờ], Nhận phòng [24 giờ] | Khách bay đêm hỏi "check-in khuya / lễ tân 24/24". |
| 5 | `AMEN_SMOKING` | Khu vực hút thuốc / cho hút thuốc | 356 | Khu vực hút thuốc, Cho phép hút thuốc | Khách hút thuốc hỏi "có được hút thuốc". Thuộc tính phòng -> any-room. |
| 6 | `AMEN_NON_SMOKING` | Phòng không hút thuốc | 442 | Phòng không hút thuốc, Hoàn toàn không hút thuốc | Khách dị ứng khói hỏi "phòng không hút thuốc". Thuộc tính phòng -> any-room. |
| 7 | `AMEN_FAMILY_ROOM` | Phòng gia đình / thông nhau | 392 | Phòng gia đình, Có các phòng thông nhau | Gia đình hỏi "phòng cho 4 người / 2 phòng thông nhau". any-room. |
| 8 | `AMEN_CAR_RENTAL` | Thuê xe / taxi | 271 | Ô tô cho thuê, Dịch vụ taxi | Khách hỏi "thuê xe máy/ô tô, gọi taxi". (khác AMEN_AIRPORT_SHUTTLE) |
| 9 | `AMEN_LOUNGE` | Phòng chờ / khu vực chung TV | 229 | Phòng chờ chung/khu vực TV, Khu vực tiếp khách | Khách hỏi "có sảnh chờ / khu vực chung". |
| 10 | `AMEN_LIBRARY` | Thư viện | 26 | Thư viện | Khách thích yên tĩnh/đọc sách hỏi. (đang defer) |
| 11 | `AMEN_WATERPARK` | Công viên nước | 40 | Công viên nước, Cầu trượt nước | Gia đình hỏi "có công viên nước / cầu trượt nước". (đang defer) |
| 12 | `AMEN_NIGHTCLUB` | Câu lạc bộ đêm | 43 | Câu lạc bộ đêm | Khách trẻ hỏi "có bar/club về đêm". gần STYLE_LIVELY (đang defer) |
| 13 | `AMEN_EVENT_VENUE` | Tổ chức sự kiện / tiệc cưới | 282 | Địa điểm cho sự kiện đặc biệt, Tổ chức sự kiện, Địa điểm cầu hôn | Khách hỏi "tổ chức tiệc cưới / sự kiện / cầu hôn". Khác phòng họp BUSINESS. |
| 14 | `AMEN_WORKSPACE` | Bàn / không gian làm việc | 298 | Bàn làm việc, Tiện nghi làm việc, Không gian làm việc cho laptop | Khách công tác/workation hỏi "phòng có bàn làm việc". related BUSINESS. |
| 15 | `AMEN_ADULTS_FEMALE` | Cơ sở chỉ dành cho nữ | 3 | Cơ sở lưu trú chỉ dành cho nữ giới | Khách nữ đi một mình hỏi. Hiếm (3 hotel) nhưng đặc thù. |

## B. BỔ SUNG SURFACE_FORMS (concept ĐÃ CÓ, thiếu biến thể chuỗi)

> source_tag_map khớp chuỗi chính xác; biến thể `[...]`/`(...)`/`/` chưa khớp -> recall gap.

| Concept | ~Freq | Biến thể chuỗi cần thêm |
|---|---:|---|
| `AMEN_WIFI` | 492 | Internet, Wi-Fi ở nơi công cộng, Wi-Fi [miễn phí], Truy cập Internet - không dây/mạng LAN, Internet có dây |
| `AMEN_PARKING` | 378 | Bãi đỗ xe [miễn phí/tại chỗ/gần bên/trả phí], Bãi đậu xe (tính phí), Bãi đỗ xe có nhân viên |
| `AMEN_POOL` | 171 | Bể bơi [ngoài trời/trong nhà], Lối vào hồ bơi |
| `AMEN_SPA` | 200 | Spa/xông khô, Xông khô, Tẩy tế bào chết, Liệu pháp Body Wrap, Ghế mát-xa, Tắm suối nước nóng |
| `AMEN_GOLF` | 88 | Sân gôn [tại chỗ nghỉ], Sân gôn (trong vòng 3 km), Sân gôn nhỏ |
| `AMEN_BALCONY` | 102 | Ban công/sân hiên (biến thể dấu /) |
| `AMEN_BIKE` | 162 | Bãi đỗ xe đạp |
| `AMEN_AC` | 432 | Máy điều hòa ở khu vực chung |
| `AMEN_WATERSPORT` | 20 | Lướt ván buồm, Học lướt sóng, Thể thao dưới nước (có/không động cơ) |
| `AMEN_GAME_ROOM` | 22 | Bảng phi tiêu, Bãi chơi bowling, Thiết bị chơi điện tử, Trò chơi board game |
| `AMEN_STREAMING` | 1 | Video truyền phát như Netflix (có phí), Phim miễn phí |
| `AMEN_GARDEN` | 3 | Vườn hoặc sân sau |
| `AMEN_RESTAURANT` | 152 | Nhà hàng phục vụ bữa tối/tráng miệng/salad/soup/món tự chọn, Nhà hàng ẩm thực quốc tế/phương Tây/Trung Quốc |

## C. THẬT SỰ BỎ (khách gần như không hỏi khi tìm khách sạn)

| Nhóm | Phạm vi | Lý do bỏ |
|---|---|---|
| Khoảng cách "Cách bãi biển/PTCC X mét" | ~190 chuỗi | Thuộc nearby/range_filter — khách hỏi "gần biển" thì ta đã có AMEN_BEACHFRONT + nearby; con số mét cụ thể không phải amenity. |
| COVID / khử trùng / khẩu trang / giãn cách | 31 chuỗi | Biện pháp tạm thời 2020-2021, đã lỗi thời 2026. Không ai search. |
| Ngôn ngữ nhân viên (trừ tiếng Anh) | ~43 chuỗi | Tiếng Séc/Hungary/Latvia... — khách VN/quốc tế không lọc KS theo NV nói tiếng Latvia. (cân nhắc GIỮ riêng "tiếng Anh" nếu cần) |
| Vật dụng phòng vụn vặt | Máy sấy tóc, Dép, Gương, Móc, Bộ kim chỉ, Ổ điện, Đèn đọc sách, Thùng rác... | Khách không search KS theo "có máy sấy tóc". Mặc định ngầm hiểu có. |
| An ninh phổ biến | CCTV, Bình chữa cháy, Đầu báo khói/CO, Bảo vệ 24h | Khách hỏi "an toàn không" -> trả lời bằng review/rating, không phải amenity riêng từng thiết bị. |
| Hành chính lễ tân vụn | Giữ hành lý, Có hóa đơn, Đổi ngoại tệ, Dịch vụ bưu chính, Dọn phòng hằng ngày | Dịch vụ vận hành mặc định, khách không lọc KS theo "có giữ hành lý". |
| Vệ sinh phòng giữa các lần ở | Phòng được vệ sinh giữa các lần ở, Băng niêm phong... | Quy trình vận hành, không phải tiện ích khách chọn. |
| Bố cục/loại không gian trùng object_type | Toàn bộ nhà, Căn hộ riêng, Song lập, Biệt lập | Đã có ở facet object_type, không lặp ở amenity. |
| Tọa lạc trung tâm X | 9 chuỗi | Là location/SETTING_CITY_CENTER, suy từ field location. |
| Chi tiết khuyết tật / thú cưng / trẻ em lẻ | ~31 chuỗi | Đã gom vào WHEELCHAIR / PET_FRIENDLY / KIDS_CLUB-BABYSITTING. Không tách concept lẻ từng món. |

---

## Cần anh chốt

1. **Mục A**: duyệt từng concept (Y/N). Cái nào hiếm (<10 hotel: nữ-giới, thư viện) có muốn giữ không?
2. **AMEN_SMOKING / NON_SMOKING / FAMILY_ROOM / BATHTUB**: xác nhận gắn theo any-room ở cấp hotel.
3. **Mục C dòng "tiếng Anh"**: có tách riêng AMEN_ENGLISH_STAFF cho khách quốc tế không?
4. Sau khi chốt A: tôi thêm vào core/amenity.yaml + source_tag_map, rồi mới vá B.
