# Golden Query Set (KE) — nhãn concept cho 32 câu hỏi

> **Owner:** Trương Anh Long (Knowledge Engineering, DA10). **Sprint 1 — mở khóa Task 1.1 Bước 2 + Task 1.7.**
>
> **Đây KHÔNG phải file golden_dataset_ota.md.** File kia (`docs/golden_dataset_ota.md`) là API
> contract của Team 9 + groundtruth *retrieval* (`hotel_ids`/`chunk_id`). File NÀY là tầng nhãn
> **ngữ nghĩa** mà KE cần: mỗi câu hỏi → tập `concept_id` mong đợi (parse query ra đúng concept),
> `range_filter` mong đợi, và `expansion_should_help` (concept mà luật query_expansion *nên* kéo thêm).
>
> **Mục đích:**
> 1. **Task 1.1 Bước 2** — gom golden query theo facet (mỗi câu đã gắn facet → thống kê độ phủ facet).
> 2. **Task 1.7** — chạy A/B từng luật `query_expansion.yaml`: luật nào kéo đúng concept trong
>    `expansion_should_help` mà KHÔNG kéo rác → `verified`; ngược lại → `rejected`.
>
> **Quy ước:**
> - `query` lấy nguyên văn 🙋 trong `docs/golden_dataset_ota.md` (đã đồng bộ địa danh/hotel có thật).
> - `expected_concepts`: chỉ gồm concept_id **tồn tại** trong `ontology/core/*.yaml`, nhóm theo facet.
>   `one`-facet (object_type/location/price_tier) → tối đa 1 id; `many`-facet → list.
> - `expected_range_filters`: filter SỐ (star/score/price/distance) — KHÔNG phải concept (xem `facets.yaml`).
> - `expansion_should_help`: concept KE kỳ vọng luật expansion thêm vào để TĂNG recall. Rỗng `[]`
>   nghĩa là câu không cần expansion (đã đủ concept tường minh) → dùng làm **ca âm** (expansion KHÔNG được
>   làm nhiễu các câu này).
> - `hotel_ids`: copy từ 🎯 groundtruth của file OTA để truy được precision/recall thực tế.
>
> Ontology version: `concepts_v2.0.0`. Tổng: **32 query**.

---

## Bảng tổng hợp độ phủ facet (Task 1.1 Bước 2)

| Facet | Số câu chạm tới | Câu |
|---|---|---|
| object_type | 8 | Q1-02, Q1-04, Q3-*, Q5-01, Q6-*, Q7-04, Q7-05 |
| location (place) | 12 | Q1-01..Q1-06, Q5-04, Q6-02, Q6-03, Q7-02, Q7-03 |
| location (landmark/near) | 3 | Q4-03, Q7-03 |
| amenity | 6 | Q1-05, Q3-03, Q4-02, Q7-04 |
| setting | 3 | Q4-02, Q7-04 |
| price_tier | 3 | Q1-04, Q7-04 |
| purpose | 7 | Q1-06, Q6-03, Q7-02 |
| style | 2 | Q7-02 |
| range_filter (score/price/star/distance) | 14 | Q1-02, Q1-03, Q1-04, Q3-02, Q3-05, Q4-04, Q6-02, Q7-02, Q7-03, Q7-04, ... |
| **Không map được facet nào** (pure-detail theo hotel/room id) | 11 | Q2-01..Q2-05, Q3-01, Q3-04, Q4-01, Q5-01..Q5-03, Q6-01 |

> **Nhận xét độ phủ:** golden set chạm **8/8 facet** + cả 4 range_filter. Nhóm "pure-detail" (Q2, một
> phần Q3/Q4/Q5) là câu **lookup theo id** (đã biết hotel) — không có concept để mở rộng, nên là tập
> kiểm tra "expansion không được phá lookup". facet `aspect` chỉ xuất hiện ngầm ở Q2-04/Q7-01 (grades),
> chưa có câu hỏi trực tiếp theo khía cạnh → **gap**: nên bổ sung query kiểu "khách sạn sạch sẽ ở X" ở vòng sau.

---

## 1. Tìm kiếm & Lọc Khách sạn

### Q1-01 — Tìm khách sạn theo thành phố
```jsonc
{
  "query": "Cho tôi xem danh sách khách sạn ở Đà Nẵng",
  "expected_concepts": {
    "object_type": ["OBJ_HOTEL"],          // "khách sạn" — lưu ý có thể hiểu rộng = mọi lưu trú
    "location":    ["LOC_DA_NANG"]
  },
  "expected_range_filters": {},
  "expansion_should_help": [],              // câu list thuần — KHÔNG cần expansion (ca âm)
  "hotel_ids": [1062253, 182167, 1985160, 271561]
}
```

### Q1-02 — Lọc theo loại hình + giá
```jsonc
{
  "query": "Tôi muốn tìm Căn hộ ở Đà Nẵng, giá khoảng 1–2 triệu một đêm",
  "expected_concepts": {
    "object_type": ["OBJ_APARTMENT"],
    "location":    ["LOC_DA_NANG"]
  },
  "expected_range_filters": { "price": { "min": 1000000, "max": 2000000 } },
  "expansion_should_help": [],
  "hotel_ids": [46045575, 43573013]
}
```

### Q1-03 — Lọc theo điểm đánh giá cao
```jsonc
{
  "query": "Khách sạn nào được đánh giá trên 9 điểm ở Nha Trang?",
  "expected_concepts": {
    "object_type": ["OBJ_HOTEL"],
    "location":    ["LOC_NHA_TRANG"]
  },
  "expected_range_filters": { "review_score": { "min": 9.0 } },
  "expansion_should_help": [],
  "hotel_ids": [263516, 75690457, 210187, 33589745, 78340310, 83464707]
}
```

### Q1-04 — Tìm resort hạng sang (luxury)
```jsonc
{
  "query": "Tìm resort 5 sao hạng sang ở Nha Trang cho tôi",
  "expected_concepts": {
    "object_type": ["OBJ_RESORT"],
    "location":    ["LOC_NHA_TRANG"],
    "price_tier":  ["PRICE_LUXURY"]         // "hạng sang" -> luxury tier
  },
  "expected_range_filters": { "star_rating": { "eq": 5 } },
  // luật PRICE_LUXURY + STYLE_LUXURY trong query_expansion.yaml -> kỳ vọng kéo các tiện ích hạng sang:
  "expansion_should_help": ["AMEN_SPA", "AMEN_PRIVATE_POOL", "AMEN_SEA_VIEW"],
  "hotel_ids": [263516]
}
```

### Q1-05 — Lọc theo tiện ích cụ thể
```jsonc
{
  "query": "Khách sạn ở Đà Lạt có hồ bơi và cho phép mang thú cưng không?",
  "expected_concepts": {
    "object_type": ["OBJ_HOTEL"],
    "amenity":     ["AMEN_POOL"]            // "hồ bơi". "thú cưng" CHƯA có concept (gap, xem _note)
  },
  "expected_range_filters": {},
  "expansion_should_help": [],
  "_note": "Đà Lạt CHƯA có concept location (corpus Sprint1 không có Đà Lạt) -> location bỏ trống = gap. 'thú cưng' không có concept amenity -> gap, cần Candidate.",
  "hotel_ids": [49851722, 31642453, 168993]
}
```

### Q1-06 — Tìm khách sạn phù hợp đối tượng
```jsonc
{
  "query": "Khách sạn nào ở Sầm Sơn phù hợp cho gia đình có trẻ nhỏ?",
  "expected_concepts": {
    "object_type": ["OBJ_HOTEL"],
    "location":    ["LOC_BAI_BIEN_SAM_SON"], // Sầm Sơn (city con của tỉnh Thanh Hóa) — concept tự sinh, parser bắt qua surface "sầm sơn"
    "purpose":     ["PURPOSE_FAMILY"]
  },
  "expected_range_filters": {},
  // luật PURPOSE_FAMILY -> [AMEN_KIDS_CLUB, AMEN_KIDS_POOL]:
  "expansion_should_help": ["AMEN_KIDS_CLUB", "AMEN_KIDS_POOL"],
  "_note": "LOC_BAI_BIEN_SAM_SON tự sinh từ data (parent LOC_THANH_HOA_TINH). Surface 'sầm sơn' thêm qua CITY_OVERRIDE.",
  "hotel_ids": [25455208, 926899, 2265300, 745965]
}
```

---

## 2. Chi tiết Khách sạn (pure-detail — lookup theo hotel, KHÔNG có concept để mở rộng)

> Cả nhóm Q2 là câu hỏi *về một hotel đã biết*. `expected_concepts` rỗng (không phải query khám phá).
> Vai trò trong Task 1.7: **ca âm** — query_expansion KHÔNG được kích hoạt / không thêm concept ở đây.

### Q2-01 — Thông tin tổng quan
```jsonc
{ "query": "Cho tôi biết thêm về khách sạn Vinpearl Resort & Spa Nha Trang Bay",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "hotel_lookup_by_name", "hotel_ids": [805030] }
```

### Q2-02 — Xem ảnh
```jsonc
{ "query": "Cho tôi xem ảnh của khách sạn này",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "hotel_images (ngữ cảnh = 805030)", "hotel_ids": [805030] }
```

### Q2-03 — Chính sách & phụ thu
```jsonc
{ "query": "Chính sách nhận phòng và các khoản phụ thu của khách sạn này là gì?",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "hotel_policies", "hotel_ids": [805030] }
```

### Q2-04 — Đánh giá chi tiết (chạm aspect ngầm)
```jsonc
{ "query": "Khách hàng đánh giá khách sạn này như thế nào? Điểm mạnh yếu là gì?",
  "expected_concepts": { "aspect": ["ASPECT_SERVICE", "ASPECT_CLEANLINESS", "ASPECT_ROOM", "ASPECT_LOCATION", "ASPECT_FOOD", "ASPECT_VALUE", "ASPECT_FACILITIES"] },
  "expected_range_filters": {}, "expansion_should_help": [],
  "_note": "Aspect xuất hiện ngầm qua grades — KHÔNG dùng để filter, chỉ phục vụ ABSA/ranking Sprint 2.",
  "_intent": "hotel_reviews", "hotel_ids": [805030] }
```

### Q2-05 — Vị trí & bản đồ
```jsonc
{ "query": "Khách sạn Vinpearl Hạ Long ở đâu, cách trung tâm bao xa?",
  "expected_concepts": { "location": ["LOC_HA_LONG"] },
  "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "hotel_location", "hotel_ids": [1015998] }
```

---

## 3. Thông tin & Lựa chọn Phòng

### Q3-01 — Danh sách loại phòng
```jsonc
{ "query": "Khách sạn này có những loại phòng nào?",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "room_list (ngữ cảnh = 805030)", "hotel_ids": [805030] }
```

### Q3-02 — Phòng theo số người
```jsonc
{ "query": "Tôi đi 4 người, có phòng nào phù hợp không?",
  "expected_concepts": {},
  "expected_range_filters": { "min_occupancy": { "min": 4 } },   // attr phòng (room-level), không phải concept
  "expansion_should_help": [],
  "_intent": "room_filter_by_occupancy", "hotel_ids": [805030] }
```

### Q3-03 — Phòng view biển
```jsonc
{ "query": "Có phòng view biển không, giá khoảng bao nhiêu?",
  "expected_concepts": { "amenity": ["AMEN_SEA_VIEW"] },   // "view biển" -> sea view (áp ở cấp phòng)
  "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "room_filter_by_view", "hotel_ids": [805030] }
```

### Q3-04 — Chi tiết một loại phòng
```jsonc
{ "query": "Cho tôi xem chi tiết phòng Loại Sang Giường Đôi Hướng Đại Dương",
  "expected_concepts": { "amenity": ["AMEN_SEA_VIEW"] },   // "Hướng Đại Dương" trong tên phòng
  "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "room_detail_by_name", "hotel_ids": [805030] }
```

### Q3-05 — Phòng rẻ nhất
```jsonc
{ "query": "Phòng rẻ nhất ở khách sạn này là bao nhiêu?",
  "expected_concepts": {},
  "expected_range_filters": { "price": { "sort": "asc", "limit": 1 } },
  "expansion_should_help": [],
  "_intent": "room_cheapest", "hotel_ids": [805030] }
```

---

## 4. Địa điểm Lân cận

### Q4-01 — Tất cả địa điểm gần hotel
```jsonc
{ "query": "Xung quanh khách sạn Vinpearl có những gì vui chơi?",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "nearby_all (ngữ cảnh = 805030)", "hotel_ids": [805030] }
```

### Q4-02 — Lọc địa điểm theo loại (bãi biển)
```jsonc
{ "query": "Gần đây có bãi biển hoặc điểm tắm biển nào không?",
  "expected_concepts": {
    "setting": ["SETTING_COASTAL"],     // "bãi biển" -> bối cảnh ven biển
    "amenity": ["AMEN_BEACHFRONT"]      // hoặc near-beach
  },
  "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "nearby_filter_by_type=beach", "hotel_ids": [805030] }
```

### Q4-03 — Tìm hotel gần landmark cụ thể
```jsonc
{
  "query": "Tôi muốn đi VinWonders Nha Trang, khách sạn nào ở gần nhất?",
  "expected_concepts": {
    "location": ["LMK_VINWONDERS_NHA_TRANG"]   // landmark -> quan hệ near (ontology.yaml)
  },
  "expected_range_filters": { "distance_km": { "sort": "asc" } },
  "expansion_should_help": [],
  "_intent": "hotels_near_landmark", "hotel_ids": [65153, 805030, 263516, 6251087]
}
```

### Q4-04 — Địa điểm trong bán kính
```jsonc
{ "query": "Trong vòng 5km quanh khách sạn có những điểm tham quan nào?",
  "expected_concepts": {},
  "expected_range_filters": { "distance_km": { "max": 5 } },
  "expansion_should_help": [],
  "_intent": "nearby_within_radius (ngữ cảnh = 805030)", "hotel_ids": [805030] }
```

---

## 5. Hoạt động Giải trí

### Q5-01 — Hoạt động của hotel
```jsonc
{ "query": "Khách sạn này có những hoạt động vui chơi gì?",
  "expected_concepts": {}, "expected_range_filters": {}, "expansion_should_help": [],
  "_intent": "hotel_activities (ngữ cảnh = 805030)", "hotel_ids": [805030] }
```

### Q5-02 — Hoạt động theo giá
```jsonc
{ "query": "Có hoạt động nào dưới 500k không?",
  "expected_concepts": {},
  "expected_range_filters": { "price": { "max": 500000 } },   // giá activity (activity-level)
  "expansion_should_help": [],
  "_intent": "activities_filter_by_price", "hotel_ids": [805030] }
```

### Q5-03 — Hoạt động đánh giá cao nhất
```jsonc
{ "query": "Hoạt động được đánh giá cao nhất tại đây là gì?",
  "expected_concepts": {},
  "expected_range_filters": { "review_score": { "sort": "desc" } },  // score activity thang /5
  "expansion_should_help": [],
  "_intent": "activities_top_rated", "hotel_ids": [805030] }
```

### Q5-04 — Hoạt động theo thành phố (toàn hệ thống)
```jsonc
{
  "query": "Có những trải nghiệm vui chơi độc đáo nào ở Phú Quốc?",
  "expected_concepts": { "location": ["LOC_PHU_QUOC"] },
  "expected_range_filters": {},
  // luật LOC_PHU_QUOC -> [SETTING_ISLAND, AMEN_BEACHFRONT]; câu này về activity nên expansion KHÔNG nên
  // đổi tập hotel -> dùng để test luật location KHÔNG over-trigger trên intent activity:
  "expansion_should_help": [],
  "_intent": "activities_by_city",
  "hotel_ids": [10247322, 1032420, 1157572, 1624474, 1985199]
}
```

---

## 6. Gói Combo Khách sạn + Vui chơi

### Q6-01 — Combo nghỉ dưỡng + vui chơi
```jsonc
{
  "query": "Tư vấn cho tôi gói combo 3 ngày 2 đêm ở Nha Trang bao gồm cả vé vui chơi",
  "expected_concepts": { "location": ["LOC_NHA_TRANG"] },
  "expected_range_filters": {},
  "expansion_should_help": [],
  "_intent": "combo_suggest", "hotel_ids": [805030]
}
```

### Q6-02 — Combo theo ngân sách
```jsonc
{
  "query": "Ngân sách 5 triệu cho 2 người đi Đà Lạt 2 ngày bao gồm cả vé vui chơi, có được không?",
  "expected_concepts": {},   // Đà Lạt chưa có concept location (gap) -> để trống
  "expected_range_filters": { "budget_total": { "max": 5000000 } },
  "expansion_should_help": [],
  "_note": "Cần concept LOC_DA_LAT khi corpus mở rộng (Đà Lạt đã xuất hiện ở Q1-05, Q6-02).",
  "hotel_ids": [14626926]
}
```

### Q6-03 — Combo gia đình
```jsonc
{
  "query": "Gợi ý gói gia đình 4 người (2 người lớn + 2 trẻ em) đi Phú Quốc 3N2Đ",
  "expected_concepts": {
    "location": ["LOC_PHU_QUOC"],
    "purpose":  ["PURPOSE_FAMILY"]
  },
  "expected_range_filters": { "min_occupancy": { "min": 4 } },
  // PURPOSE_FAMILY -> kids facilities; LOC_PHU_QUOC -> island/beach:
  "expansion_should_help": ["AMEN_KIDS_CLUB", "AMEN_KIDS_POOL"],
  "hotel_ids": [1157572]
}
```

---

## 7. So sánh & Gợi ý Cá nhân hóa

### Q7-01 — So sánh 2 khách sạn
```jsonc
{
  "query": "So sánh Pullman Đà Nẵng và Marriott Đà Nẵng giúp tôi chọn",
  "expected_concepts": {
    "object_type": ["OBJ_RESORT"],          // cả 2 là resort
    "location":    ["LOC_DA_NANG"],
    "aspect":      ["ASPECT_SERVICE", "ASPECT_CLEANLINESS", "ASPECT_ROOM", "ASPECT_VALUE"]
  },
  "expected_range_filters": {},
  "expansion_should_help": [],
  "_intent": "compare_two_hotels (ids đã biết)", "hotel_ids": [182167, 1985160]
}
```

### Q7-02 — Cặp đôi tuần trăng mật
```jsonc
{
  "query": "Gợi ý khách sạn lãng mạn cho tuần trăng mật ở Phú Quốc, budget 10 triệu 3 đêm",
  "expected_concepts": {
    "location": ["LOC_PHU_QUOC"],
    "purpose":  ["PURPOSE_ROMANTIC"],       // "tuần trăng mật"
    "style":    ["STYLE_ROMANTIC"]          // "lãng mạn"
  },
  "expected_range_filters": { "price": { "max": 3400000 } },  // 10tr / 3 đêm ~ 3.33tr/đêm
  // PURPOSE_ROMANTIC -> [AMEN_SEA_VIEW, STYLE_ROMANTIC, AMEN_PRIVATE_POOL]; STYLE_ROMANTIC -> [PURPOSE_ROMANTIC, AMEN_SEA_VIEW]:
  "expansion_should_help": ["AMEN_SEA_VIEW", "AMEN_PRIVATE_POOL"],
  "hotel_ids": [51060966, 39532985]
}
```

### Q7-03 — Gần sân bay
```jsonc
{
  "query": "Tôi đến Đà Nẵng muộn, tìm khách sạn gần sân bay nhất để nghỉ",
  "expected_concepts": {
    "object_type": ["OBJ_HOTEL"],
    "location":    ["LOC_DA_NANG"]
    // "sân bay Đà Nẵng" là landmark near nhưng chưa có concept LMK_SAN_BAY_DA_NANG (gap)
  },
  "expected_range_filters": { "distance_km": { "max": 5, "sort": "asc" } },
  "expansion_should_help": [],
  "_note": "Cần concept landmark LMK_SAN_BAY_DA_NANG (airport) cho quan hệ near.",
  "hotel_ids": [70410096]
}
```

### Q7-04 — Tiêu chí tổng hợp
```jsonc
{
  "query": "Tìm resort có spa, hồ bơi vô cực, gần biển, điểm trên 9, giá dưới 5 triệu đêm",
  "expected_concepts": {
    "object_type": ["OBJ_RESORT"],
    "amenity":     ["AMEN_SPA", "AMEN_INFINITY_POOL", "AMEN_BEACHFRONT"],  // spa + hồ bơi vô cực + gần biển
    "setting":     ["SETTING_COASTAL"]
  },
  "expected_range_filters": { "review_score": { "min": 9.0 }, "price": { "max": 5000000 } },
  // tất cả tiêu chí đã tường minh -> expansion KHÔNG cần thêm (ca âm đa-concept):
  "expansion_should_help": [],
  "_note": "AMEN_INFINITY_POOL: corpus ít gắn nhãn vô cực -> retrieval thực tế relax xuống AMEN_POOL (xem 🎯 OTA).",
  "hotel_ids": [263516, 1015998]
}
```

### Q7-05 — Khách sạn tương tự
```jsonc
{
  "query": "Có khách sạn nào giống Vinpearl Resort & Golf Nam Hội An nhưng rẻ hơn không?",
  "expected_concepts": {
    "object_type": ["OBJ_RESORT"],
    "location":    ["LOC_HOI_AN"]
  },
  "expected_range_filters": { "price": { "rel": "< reference_hotel.min_price" } },
  "expansion_should_help": [],
  "_intent": "similar_cheaper (reference_hotel = 4593719)",
  "reference_hotel_id": 4593719,
  "hotel_ids": [1994212]
}
```

---

## Cách dùng để verify query_expansion (Task 1.7)

Cho mỗi luật `X -> [Y1, Y2...]` trong `ontology/query_expansion.yaml`:

1. **Tập kích hoạt** = các câu có `X` trong `expected_concepts`.
2. **Đúng (hit)** = `Yi` xuất hiện trong `expansion_should_help` của câu đó → luật kéo đúng concept hữu ích.
3. **Nhiễu (noise)** = luật kích hoạt trên câu có `expansion_should_help: []` (ca âm) và làm đổi tập kết quả.
4. Đo Recall@k trước/sau khi áp luật (dùng `hotel_ids` làm groundtruth):
   - Recall tăng & không nhiễu → `status: verified`.
   - Recall không đổi hoặc giảm precision → `status: rejected` (xóa khỏi file).

**Ví dụ:** luật `PURPOSE_FAMILY -> [AMEN_KIDS_CLUB, AMEN_KIDS_POOL]` kích hoạt ở Q1-06, Q6-03 — cả hai có
đúng 2 concept đó trong `expansion_should_help` → ứng viên `verified` (chốt sau khi đo Rec@k trên pipeline Sprint 2).

---

## Gap đã ghi nhận (cần Candidate / mở rộng — KHÔNG tự thêm vào Core)

> **Cập nhật (corpus VN 520; location + facet audit):** 4/5 gap đã HẾT — Đà Lạt, Sầm Sơn, sân bay
> Đà Nẵng (location tự sinh) + thú cưng (AMEN_PET_FRIENDLY đã lên Core). Chỉ còn 1 gap thật (aspect query).

| Gap | Câu | Trạng thái |
|---|---|---|
| ~~Concept location `LOC_DA_LAT`~~ | Q1-05, Q6-02 | ✅ ĐÃ CÓ `LOC_DA_LAT` (tự sinh từ 23 hotel Đà Lạt). |
| ~~Concept Sầm Sơn~~ | Q1-06 | ✅ ĐÃ CÓ `LOC_BAI_BIEN_SAM_SON` (tự sinh). |
| ~~Concept sân bay Đà Nẵng~~ | Q7-03 | ✅ ĐÃ CÓ `LMK_SAN_BAY_QUOC_TE_DA_NANG` (landmark tự sinh từ nearby_places). |
| ~~Concept amenity "thú cưng"~~ | Q1-05 | ✅ ĐÃ CÓ `AMEN_PET_FRIENDLY` (Core, 144 hotel). LƯU Ý vẫn thiếu field `pet_policy` trong clean data → báo Data Quality. |
| Facet `aspect` chưa có câu hỏi trực tiếp | (chỉ ngầm Q2-04, Q7-01) | ⏳ CÒN: bổ sung query "khách sạn sạch sẽ / dịch vụ tốt ở X" ở vòng golden tiếp theo. |
