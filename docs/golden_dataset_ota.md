# Golden Dataset — Hệ thống OTA Du lịch

> **Cấu trúc mỗi bản ghi:**
> - 🙋 **Câu hỏi người dùng** — ngôn ngữ tự nhiên như người thật gõ vào chatbot/search bar.
> - 💬 **Phản hồi người dùng mong muốn** — nội dung hiển thị thân thiện, dễ đọc.
> - 📦 **Phản hồi API Backend** — các trường dữ liệu cần trả về từ database để tổng hợp câu trả lời.

---

## Mục lục Nghiệp vụ

| # | Nghiệp vụ | Số câu hỏi |
|---|-----------|-----------|
| 1 | [Tìm kiếm & Lọc Khách sạn](#1-tìm-kiếm--lọc-khách-sạn) | 6 |
| 2 | [Chi tiết Khách sạn](#2-chi-tiết-khách-sạn) | 5 |
| 3 | [Thông tin & Lựa chọn Phòng](#3-thông-tin--lựa-chọn-phòng) | 5 |
| 4 | [Địa điểm Lân cận](#4-địa-điểm-lân-cận) | 4 |
| 5 | [Hoạt động Giải trí](#5-hoạt-động-giải-trí) | 4 |
| 6 | [Gói Combo Khách sạn + Vui chơi](#6-gói-combo-khách-sạn--vui-chơi) | 3 |
| 7 | [So sánh & Gợi ý Cá nhân hóa](#7-so-sánh--gợi-ý-cá-nhân-hóa) | 5 |

---

## 1. Tìm kiếm & Lọc Khách sạn

---

### Q1-01 — Tìm khách sạn theo thành phố

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem danh sách khách sạn ở Đà Nẵng"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 35 khách sạn tại Đà Nẵng.

1. ★★★★☆  Mercure Đà Nẵng French Village Bà Nà Hills
   Loại: Khách sạn  |  Điểm đánh giá: 8.8/10 (18.998 đánh giá)
   Địa chỉ: Bà Nà Hills, Hoà Vang, Đà Nẵng
   Giá từ: 1.220.000 VND/đêm
   [Xem chi tiết]

2. ★★★★★  Khu nghỉ dưỡng Pullman Đà Nẵng
   Loại: Resort  |  Điểm đánh giá: 8.9/10 (4.733 đánh giá)
   Giá từ: 4.310.000 VND/đêm
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": { "city": "Đà Nẵng", "page": 1, "limit": 20 },
  "response": {
    "total": 35,
    "page": 1,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "review_count": "integer",
        "address": "text",
        "city": "varchar",
        "images": ["text — ảnh đại diện [0]"],
        "latitude": "double",
        "longitude": "double"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật từ data/cleaned: city=Đà Nẵng (35 hotel). Top theo review_score (bỏ hotel có review_count quá thấp).
  // Câu liệt kê → groundtruth là tập + thứ tự top; ở đây ghi vài hotel đầu đại diện.
  "hotel_ids": [1062253, 182167, 1985160, 271561],
  "context_chunks": [
    "acc_1062253#overview", "acc_182167#overview",
    "acc_1985160#overview", "acc_271561#overview"
  ],
  "_note": "Câu list-by-city → context là chunk #overview mỗi hotel. chunk_id sinh tạm theo quy ước."
}
```

---

### Q1-02 — Lọc theo loại hình lưu trú

🙋 **Câu hỏi người dùng:**
> "Tôi muốn tìm Căn hộ ở Đà Nẵng, giá khoảng 1–2 triệu một đêm"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 5 Căn hộ tại Đà Nẵng trong khoảng giá 1.000.000 – 2.000.000 VND/đêm.

1. Khách sạn căn hộ The Sun Đà Nẵng
   Điểm đánh giá: 8.8/10 (628 đánh giá) | Giá từ: 1.660.000 VND/đêm
   Phù hợp: Cặp đôi, Gia đình
   [Xem chi tiết]

2. Gia Hưng Apartment Mường Thanh
   Điểm đánh giá: 7.6/10 | Giá từ: 1.500.000 VND/đêm
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Đà Nẵng",
    "accommodation_type": "Căn hộ",
    "price_min": 1000000,
    "price_max": 2000000
  },
  "response": {
    "total": 5,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "review_score": "numeric",
        "review_count": "integer",
        "address": "text",
        "suitable_for": ["text[]"],
        "images": ["text — ảnh đại diện [0]"],
        "rooms": {
          "min_price": "numeric — giá phòng rẻ nhất trong khách sạn"
        }
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI: "Homestay ở Hội An" → "Căn hộ ở Đà Nẵng". Corpus KHÔNG có Homestay nào (0/555),
  // và Hội An không có căn hộ → đổi địa danh sang Đà Nẵng (5 căn hộ thật). Lọc theo giá 1-2tr.
  "hotel_ids": [46045575, 43573013],
  "context_chunks": [
    "acc_46045575#overview", "acc_46045575#rooms",
    "acc_43573013#overview", "acc_43573013#rooms"
  ],
  "_note": "Câu lọc loại hình + giá → context gồm #overview + #rooms (chứa giá). chunk_id sinh tạm."
}
```

---

### Q1-03 — Lọc theo điểm đánh giá cao

🙋 **Câu hỏi người dùng:**
> "Khách sạn nào được đánh giá trên 9 điểm ở Nha Trang?"

💬 **Phản hồi người dùng mong muốn:**
```
6 khách sạn đánh giá xuất sắc (≥ 9.0) tại Nha Trang:

★ Vinpearl Luxury Nha Trang — 9.3/10 (4.207 đánh giá)
★ Mercure Nha Trang Beach — 9.1/10 (79 đánh giá)
★ Khách sạn & Spa Sheraton Nha Trang — 9.0/10 (4.633 đánh giá)
★ The Westin Cam Ranh — 9.0/10 (620 đánh giá)
...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Nha Trang",
    "review_score_min": 9.0,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "review_count": "integer",
        "accommodation_type": "varchar",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: city=Nha Trang + review_score>=9.0, sort desc. 6 hotel đạt (data/cleaned).
  "hotel_ids": [263516, 75690457, 210187, 33589745, 78340310, 83464707],
  "context_chunks": [
    "acc_263516#overview", "acc_75690457#overview", "acc_210187#overview",
    "acc_33589745#overview", "acc_78340310#overview", "acc_83464707#overview"
  ],
  "_note": "Câu lọc theo điểm → groundtruth là toàn bộ tập đạt ngưỡng. chunk_id sinh tạm."
}
```

---

### Q1-04 — Tìm khách sạn hạng sang (Luxury)

🙋 **Câu hỏi người dùng:**
> "Tìm resort 5 sao hạng sang ở Nha Trang cho tôi"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 1 Resort 5 sao hạng sang tại Nha Trang:

🏆 ★★★★★  Vinpearl Luxury Nha Trang
   Loại: Resort (hạng sang)  |  Điểm: 9.3/10 (4.207 đánh giá)
   Tiện ích nổi bật: Bãi biển riêng, Bể bơi ngoài trời, Ban công/sân hiên
   Phù hợp: Cặp đôi, Gia đình có trẻ nhỏ, Khách công tác
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Nha Trang",
    "accommodation_type": "Resort",
    "star_rating": 5,
    "is_luxury": true,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "is_luxury": "boolean",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[] — top 5 tiện ích"],
        "images": ["text — ảnh đại diện [0]"],
        "rooms": {
          "min_price": "numeric"
        }
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc THẬT từ data/cleaned: accommodation_type=Resort + star_rating=5 + city=Nha Trang + is_luxury=true.
  // Đã ĐỔI địa danh Phú Quốc → Nha Trang: ở Phú Quốc 0 hotel đạt is_luxury=true (cả Vinpearl/Sheraton 5★ đều false),
  // còn Nha Trang có Vinpearl Luxury (is_luxury=true, score 9.3). Giữ nguyên tiêu chí is_luxury của Team 9.
  "hotel_ids": [263516],
  "context_chunks": [
    "acc_263516#overview",
    "acc_263516#amenities"
  ],
  "_note": "chunk_id sinh TẠM theo quy ước acc_<hotel_id>#<section>; chunk thật chưa tồn tại (chunking Sprint 2/3)."
}
```

---

### Q1-05 — Lọc theo tiện ích cụ thể

🙋 **Câu hỏi người dùng:**
> "Khách sạn ở Đà Lạt có hồ bơi và cho phép mang thú cưng không?"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 3 khách sạn tại Đà Lạt có hồ bơi:

1. Khách sạn Golden Sun Đà Lạt
   Điểm: 9.3/10 (1.346 đánh giá) | Loại: Khách sạn ★★★★
   ✓ Hồ bơi  |  Giá từ: 2.240.000 VND/đêm
   [Xem chi tiết]

2. Mercure Đà Lạt Resort
   Điểm: 8.8/10 (2.350 đánh giá) | ★★★★
   ✓ Hồ bơi  |  Giá từ: 2.800.000 VND/đêm
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Đà Lạt",
    "amenities": ["Hồ bơi", "Cho phép thú cưng"]
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "review_score": "numeric",
        "amenities": ["text[] — toàn bộ danh sách tiện ích"],
        "policyNotes": ["text[] — chính sách thú cưng, phụ phí"],
        "useful_info": "jsonb — chi tiết phí dịch vụ",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: city=Đà Lạt + có amenity "bể bơi" (3 hotel). LƯU Ý: tiêu chí "thú cưng" KHÔNG lọc được —
  // corpus/clean data không có field pet_policy → đã BỎ tiêu chí đó, chỉ lọc hồ bơi. Cần Data Quality bổ sung field thú cưng.
  "hotel_ids": [49851722, 31642453, 168993],
  "context_chunks": [
    "acc_49851722#overview", "acc_49851722#amenities",
    "acc_31642453#amenities", "acc_168993#amenities"
  ],
  "_note": "Câu lọc tiện ích → context #amenities. 'thú cưng' chưa có data → kết quả chỉ phản ánh tiêu chí hồ bơi. chunk_id tạm."
}
```

---

### Q1-06 — Tìm khách sạn phù hợp đối tượng

🙋 **Câu hỏi người dùng:**
> "Khách sạn nào ở Sầm Sơn phù hợp cho gia đình có trẻ nhỏ?"

💬 **Phản hồi người dùng mong muốn:**
```
7 khách sạn tại Sầm Sơn lý tưởng cho gia đình có trẻ nhỏ:

1. Khách sạn FLC Grand Sầm Sơn
   Điểm: 8.8/10 (2.321 đánh giá) | ★★★★★
   Phù hợp: Gia đình có trẻ nhỏ, Nhóm du khách
   Giá từ: 3.390.000 VND/đêm
   [Xem chi tiết]

2. FLC Luxury Resort Samson
   Điểm: 8.8/10 (804 đánh giá) | ★★★★★ Resort
   Giá từ: 4.930.000 VND/đêm
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Sầm Sơn",
    "suitable_for": "Gia đình có trẻ nhỏ",
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "suitable_for": ["text[]"],
        "amenities": ["text[] — lọc các tiện ích liên quan trẻ em"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: khu vực Sầm Sơn (city = "Thanh Hoá / Bãi biển Sầm Sơn") + suitable_for chứa "Gia đình".
  // 7 hotel đạt; lấy top theo review_score. (Người dùng gõ "Sầm Sơn" → khớp city có chứa "Sầm Sơn".)
  "hotel_ids": [25455208, 926899, 2265300, 745965],
  "context_chunks": [
    "acc_25455208#overview", "acc_926899#overview",
    "acc_2265300#overview", "acc_745965#overview"
  ],
  "_note": "Câu lọc đối tượng (suitable_for) → context #overview. chunk_id sinh tạm."
}
```

---

## 2. Chi tiết Khách sạn

---

### Q2-01 — Xem thông tin tổng quan khách sạn

🙋 **Câu hỏi người dùng:**
> "Cho tôi biết thêm về khách sạn Vinpearl Resort & Spa Nha Trang Bay"

💬 **Phản hồi người dùng mong muốn:**
```
🏨 Vinpearl Resort & Spa Nha Trang Bay
⭐⭐⭐⭐⭐ | Điểm: 8.8/10 (10.862 đánh giá) | Resort

📍 Hòn Tre, Hòn Tre, Nha Trang, Việt Nam

📝 Mô tả:
Nằm ở vị trí trung tâm tại Hòn Tre của Nha Trang, resort 5 sao với bãi đỗ xe
miễn phí, gần các điểm tham quan nổi tiếng. Khu nghỉ dưỡng có bãi biển riêng,
hồ bơi ngoài trời, spa và sân golf tại chỗ.

🛎 Tiện ích nổi bật:
✓ Đưa đón sân bay  ✓ Bãi biển riêng  ✓ Xông khô
✓ Phòng xông ướt  ✓ Điều hòa

📌 Phù hợp cho: Khách công tác, Cặp đôi, Khách du lịch một mình, Gia đình
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}",
  "path_params": { "id": "integer" },
  "response": {
    "id": "integer",
    "name": "varchar",
    "accommodation_type": "varchar",
    "star_rating": "numeric",
    "is_luxury": "boolean",
    "review_score": "numeric",
    "review_count": "integer",
    "address": "text",
    "city": "varchar",
    "latitude": "double",
    "longitude": "double",
    "description": "text",
    "amenities": ["text[]"],
    "suitable_for": ["text[]"],
    "useful_info": "jsonb",
    "policyNotes": ["text[]"],
    "images": ["text[]"],
    "reviews_detail": "jsonb",
    "source_url": "text"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Câu hỏi chi tiết 1 hotel theo tên → khớp đúng "Vinpearl Resort & Spa Nha Trang Bay".
  // hotel_id thật trong corpus (data/cleaned/hotel_805030.json). Lưu ý: review_score thật 8.8 (không phải 9.0 như mô tả bịa ở phần 💬).
  "hotel_ids": [805030],
  "context_chunks": [
    "acc_805030#overview",   // mô tả tổng quan
    "acc_805030#amenities",  // tiện ích nổi bật
    "acc_805030#location",   // vị trí Hòn Tre + nearby
    "acc_805030#rooms",      // các loại phòng
    "acc_805030#reviews"     // điểm đánh giá (chunk dự kiến, chờ review crawl)
  ],
  "_note": "Câu detail → toàn bộ chunk của 1 hotel là context đúng. chunk_id sinh tạm theo quy ước."
}
```

---

### Q2-02 — Xem hình ảnh khách sạn

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem ảnh của khách sạn này"

💬 **Phản hồi người dùng mong muốn:**
```
📸 Bộ sưu tập ảnh — Vinpearl Resort & Spa Nha Trang Bay
[159 ảnh]

[Ảnh 1: Ngoại cảnh khách sạn]
[Ảnh 2: Bể bơi ngoài trời]
[Ảnh 3: Villa 2 tầng có hồ bơi riêng]
...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/images",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "hotel_name": "varchar",
    "images": ["text[] — toàn bộ URL ảnh khách sạn"]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = ngữ cảnh Q2-01 → 805030. image_count thật = 159 (data/cleaned).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#overview"],
  "_note": "Câu xem ảnh → chỉ cần định danh hotel; ảnh ở field images, không phải chunk text. chunk_id tạm."
}
```

---

### Q2-03 — Xem chính sách & lưu ý đặc biệt

🙋 **Câu hỏi người dùng:**
> "Chính sách nhận phòng và các khoản phụ thu của khách sạn này là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
📋 Chính sách & Lưu ý — Vinpearl Resort & Spa Nha Trang Bay

🕐 Nhận phòng: từ 15:00 | Trả phòng: đến 12:00
🛎 Quầy tiếp tân mở đến: 23:59
🚗 Phí đưa đón sân bay: 1.700.000 VND | Phí giữ xe hàng ngày: Miễn phí (0 VND)
🏨 Số phòng: 651 | Số tầng: 11 | Xây năm: 2015 (nâng cấp 2016)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/policies",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "policyNotes": ["text[]"],
    "useful_info": "jsonb — check_in_time, check_out_time, service_fee, child_policy, pet_policy, deposit_required"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. Số liệu lấy thật từ useful_info (data/cleaned).
  // LƯU Ý: clean data KHÔNG có pet_policy / service_fee % / child_policy → các dòng đó trong 💬 gốc là bịa, đã bỏ.
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#policies"],
  "_note": "Câu chính sách → context #policies (từ useful_info). Thiếu field pet/service_fee → cần Data Quality bổ sung. chunk_id tạm."
}
```

---

### Q2-04 — Xem điểm đánh giá chi tiết

🙋 **Câu hỏi người dùng:**
> "Khách hàng đánh giá khách sạn này như thế nào? Điểm mạnh yếu là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
⭐ Đánh giá chi tiết — Vinpearl Resort & Spa Nha Trang Bay
Tổng điểm: 8.8/10 từ 10.862 đánh giá

Dịch vụ:        █████████░  9.1
Sạch sẽ:        █████████░  9.0
Phòng:          █████████░  9.0
Cơ sở vật chất:  ████████░░  8.9
Đáng tiền:       ████████░░  8.9
Vị trí:         ████████░░  8.6
Ăn uống:        ████████░░  8.3

🏷 Tags phổ biến từ khách hàng:
#dịch vụ  #bể bơi  #bữa sáng  #độ sạch sẽ  #địa điểm  #bãi biển
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/reviews",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "review_score": "numeric",
    "review_count": "integer",
    "reviews_detail": "jsonb — grades: { location, cleanliness, service, facilities, value }, tags: [text[]]"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. grades + tags lấy thật từ reviews_detail (data/cleaned).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#reviews"],
  "_note": "Câu đánh giá chi tiết → context #reviews (grades + review tags). chunk_id tạm."
}
```

---

### Q2-05 — Tra cứu vị trí & bản đồ

🙋 **Câu hỏi người dùng:**
> "Khách sạn Vinpearl Hạ Long ở đâu, cách trung tâm bao xa?"

💬 **Phản hồi người dùng mong muốn:**
```
📍 Vị trí — Vinpearl Resort & Spa Hạ Long
Địa chỉ: Đảo Rều, Bãi Cháy, Hạ Long, Quảng Ninh

📏 Khoảng cách:
• Trung tâm thành phố: 6 km
• Một số địa điểm lân cận (xem nearby_places)

🗺 [Xem bản đồ]
Tọa độ: 20.9412° N, 107.0256° E
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/location",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "name": "varchar",
    "address": "text",
    "city": "varchar",
    "latitude": "double",
    "longitude": "double",
    "nearby_places": [
      {
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI "Amanoi (Phan Rang)" → "Vinpearl Hạ Long" (Amanoi không có trong corpus).
  // Tọa độ + địa chỉ + khoảng cách trung tâm lấy thật từ data/cleaned/hotel_1015998.json.
  "hotel_ids": [1015998],
  "context_chunks": ["acc_1015998#location"],
  "_note": "Câu vị trí/bản đồ → context #location (address, lat/lng, nearby_places). chunk_id tạm."
}
```

---

## 3. Thông tin & Lựa chọn Phòng

---

### Q3-01 — Xem danh sách loại phòng

🙋 **Câu hỏi người dùng:**
> "Khách sạn này có những loại phòng nào?"

💬 **Phản hồi người dùng mong muốn:**
```
🛏 Các loại phòng — Vinpearl Resort & Spa Nha Trang Bay (10 loại phòng)

1. Phòng Loại Sang Giường Đôi Hướng Đại Dương
   Diện tích: 45 m²  |  2 người  |  1 giường lớn  |  Hướng Đại dương
   Giá từ: 5.000.000 VND/đêm
   [Xem chi tiết]

2. Villa cạnh bãi biển 2 phòng ngủ có hồ bơi riêng
   Diện tích: 240 m²  |  Hướng Bãi biển  |  1 giường lớn + 2 giường đơn
   Giá từ: 5.000.000 VND/đêm
   [Xem chi tiết]

3. Biệt Thự 4 Phòng Ngủ - Hồ Bơi Riêng
   Tối đa 8 người  |  3 giường lớn + 2 giường đơn  |  Hướng Bể bơi
   Giá từ: 5.000.000 VND/đêm
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "rooms": [
      {
        "id": "integer",
        "room_type_id": "bigint",
        "name": "varchar",
        "price": "numeric",
        "room_size": "varchar",
        "max_occupancy": "integer",
        "bed_type": "varchar",
        "room_view": "varchar",
        "review_score": "numeric",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. 10 loại phòng thật từ rooms[] (data/cleaned).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms"],
  "_note": "Câu list phòng → context #rooms (toàn bộ room types). chunk_id tạm."
}
```

---

### Q3-02 — Tìm phòng theo số người

🙋 **Câu hỏi người dùng:**
> "Tôi đi 4 người, có phòng nào phù hợp không?"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 1 loại phòng phù hợp cho 4 người trở lên:

1. Biệt Thự 4 Phòng Ngủ - Hồ Bơi Riêng — tối đa 8 người
   3 giường lớn + 2 giường đơn  |  Hướng Bể bơi
   Giá từ: 5.000.000 VND/đêm
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "min_occupancy": 4 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "max_occupancy": "integer",
        "room_size": "varchar",
        "bed_type": "varchar",
        "price": "numeric",
        "room_amenities": ["text[]"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. Lọc rooms[] max_occupancy>=4: chỉ 1 phòng thật (Biệt thự 4PN, max 8).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms"],
  "_note": "Câu lọc phòng theo số người → context #rooms. chunk_id tạm."
}
```

---

### Q3-03 — Tìm phòng view biển

🙋 **Câu hỏi người dùng:**
> "Có phòng view biển không, giá khoảng bao nhiêu?"

💬 **Phản hồi người dùng mong muốn:**
```
🌊 Phòng hướng biển tại Vinpearl Resort & Spa Nha Trang Bay:

1. Phòng Loại Sang Giường Đôi Hướng Đại Dương
   45 m²  |  1 giường lớn  |  Hướng Đại dương
   Giá: 5.000.000 VND/đêm

2. Phòng Deluxe 2 giường Hướng biển
   45 m²  |  2 giường đơn  |  Hướng Đại dương
   Giá: 5.000.000 VND/đêm

3. Villa cạnh bãi biển 2 phòng ngủ có hồ bơi riêng
   240 m²  |  Hướng Bãi biển
   Giá: 5.000.000 VND/đêm
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "room_view": "Hướng Biển" },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "room_view": "varchar",
        "room_size": "varchar",
        "bed_type": "varchar",
        "price": "numeric",
        "review_score": "numeric",
        "room_amenities": ["text[]"],
        "images": ["text[]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. Lọc rooms[] có room_view chứa "biển"/"đại dương" (4 phòng thật).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms"],
  "_note": "Câu lọc phòng theo view → context #rooms. chunk_id tạm."
}
```

---

### Q3-04 — Xem chi tiết một loại phòng

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem chi tiết phòng Loại Sang Giường Đôi Hướng Đại Dương"

💬 **Phản hồi người dùng mong muốn:**
```
🛏 Phòng Loại Sang Giường Đôi Hướng Đại Dương — Vinpearl Resort & Spa Nha Trang Bay

📐 Diện tích: 45 m²   |  👥 Tối đa 2 người
🛏 Giường: 1 giường lớn   |  🌊 View: Hướng Đại dương

💰 Giá: từ 5.000.000 VND / đêm
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/rooms/{id}",
  "path_params": { "id": "integer" },
  "response": {
    "id": "integer",
    "hotel_id": "integer",
    "room_type_id": "bigint",
    "name": "varchar",
    "price": "numeric",
    "room_size": "varchar",
    "max_occupancy": "integer",
    "bed_type": "varchar",
    "room_view": "varchar",
    "room_amenities": ["text[]"],
    "review_score": "numeric",
    "images": ["text[]"]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI tên phòng "Premier Ocean View" (không có) → "Phòng Loại Sang Giường Đôi Hướng Đại Dương" (thật, room_type_id=4020083).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms"],
  "_note": "Câu chi tiết 1 phòng → context #rooms (room cụ thể). chunk_id tạm."
}
```

---

### Q3-05 — Tìm phòng giá rẻ nhất

🙋 **Câu hỏi người dùng:**
> "Phòng rẻ nhất ở khách sạn này là bao nhiêu?"

💬 **Phản hồi người dùng mong muốn:**
```
💡 Giá phòng thấp nhất tại Vinpearl Resort & Spa Nha Trang Bay:

Tất cả 10 loại phòng hiện cùng mức giá từ: 5.000.000 VND / đêm
Ví dụ: Phòng Loại Sang Giường Đôi (45 m², 2 người, 1 giường lớn)
[Đặt ngay]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "sort_by": "price:asc", "limit": 1 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "price": "numeric",
        "room_size": "varchar",
        "max_occupancy": "integer",
        "bed_type": "varchar",
        "room_amenities": ["text[]"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. price_per_night thật của 805030 = 5.000.000 cho mọi phòng
  // (LƯU Ý: đây là giá bị làm phẳng trong clean data — cần Data Quality kiểm tra cột giá).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms"],
  "_note": "Câu phòng rẻ nhất → sort rooms theo price asc. Giá 805030 đồng đều 5tr (placeholder). chunk_id tạm."
}
```

---

## 4. Địa điểm Lân cận

---

### Q4-01 — Xem tất cả địa điểm gần khách sạn

🙋 **Câu hỏi người dùng:**
> "Xung quanh khách sạn Vinpearl có những gì vui chơi?"

💬 **Phản hồi người dùng mong muốn:**
```
📍 Địa điểm nổi bật gần Vinpearl Resort & Spa Nha Trang Bay:

🎡 Khu vui chơi:
  • Công viên giải trí Vinpearl Land — 0.8 km
  • VinWonders Nha Trang — 0.86 km

⛳ Thể thao:
  • Khu du lịch Con Sẻ Tre — 0.71 km
  • Sân golf Vinpearl — 2.7 km

🏛 Văn hóa / Bảo tàng:
  • Dinh Bảo Đại — 2.78 km
  • Viện Hải Dương Học — 3.11 km

🏖 Bãi biển:
  • Biển Nha Trang — 3.4 km
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "nearby_places": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn Vinpearl" (ngữ cảnh Nha Trang) = 805030. nearby_places lấy thật 10 địa điểm (data/cleaned).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#location"],
  "_note": "Câu địa điểm quanh hotel → context #location (nearby_places). chunk_id tạm."
}
```

---

### Q4-02 — Lọc địa điểm theo loại

🙋 **Câu hỏi người dùng:**
> "Gần đây có bãi biển hoặc điểm tắm biển nào không?"

💬 **Phản hồi người dùng mong muốn:**
```
🏖 Bãi biển gần Vinpearl Resort & Spa Nha Trang Bay:

1. Biển Nha Trang — 3.4 km
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "query_params": { "type": "Bãi biển" },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. Lọc nearby_places type="Bãi Biển": chỉ "Biển Nha Trang" (3.4 km) trong data thật.
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#location"],
  "_note": "Câu lọc nearby theo loại → context #location. Data thật chỉ 1 bãi biển. chunk_id tạm."
}
```

---

### Q4-03 — Tìm khách sạn gần địa điểm cụ thể

🙋 **Câu hỏi người dùng:**
> "Tôi muốn đi VinWonders Nha Trang, khách sạn nào ở gần nhất?"

💬 **Phản hồi người dùng mong muốn:**
```
🏨 Khách sạn gần VinWonders Nha Trang nhất:

1. Vinpearl Resort Nha Trang — 0.58 km
   ★★★★★ | 8.7/10

2. Vinpearl Resort & Spa Nha Trang Bay — 0.8 km
   ★★★★★ | 8.8/10

3. Vinpearl Luxury Nha Trang — 0.81 km
   ★★★★★ | 9.3/10

4. Nha Trang Marriott Resort & Spa, Hòn Tre — 1.5 km
   ★★★★★ | 8.7/10
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "nearby_place_name": "VinWonders Nha Trang",
    "sort_by": "distance:asc",
    "city": "Nha Trang"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "nearby_places": [
          {
            "name": "varchar",
            "distance_km": "numeric — khoảng cách tới địa điểm tìm kiếm"
          }
        ],
        "rooms": {
          "min_price": "numeric"
        },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật từ data/cleaned: các hotel có nearby_places chứa "VinWonders Nha Trang" / "Vinpearl Land".
  // Sắp theo khoảng cách tăng dần (sort_by=distance:asc): 65153(0.58) < 805030(0.8) < 263516(0.81) < 6251087(1.5).
  "hotel_ids": [65153, 805030, 263516, 6251087],
  "context_chunks": [
    "acc_65153#location", "acc_805030#location",
    "acc_263516#location", "acc_6251087#location"
  ],
  "_note": "Câu near → chunk #location là context đúng (chứa nearby_places + distance). chunk_id sinh tạm theo quy ước."
}
```

---

### Q4-04 — Tìm địa điểm trong bán kính nhất định

🙋 **Câu hỏi người dùng:**
> "Trong vòng 5km quanh khách sạn có những điểm tham quan nào?"

💬 **Phản hồi người dùng mong muốn:**
```
🗺 Trong bán kính 5 km quanh Vinpearl Resort & Spa Nha Trang Bay (10 địa điểm):

📍 Dưới 1 km:
  • Khu du lịch Con Sẻ Tre (Thể thao) — 0.71 km
  • Công viên giải trí Vinpearl Land (Khu vui chơi) — 0.8 km
  • VinWonders Nha Trang (Khu vui chơi) — 0.86 km

📍 1 – 3 km:
  • Sân golf Vinpearl (Sân gôn) — 2.7 km
  • Dinh Bảo Đại (Di tích) — 2.78 km

📍 3 – 5 km:
  • Viện Hải Dương Học (Bảo tàng) — 3.11 km
  • Biển Nha Trang (Bãi biển) — 3.4 km
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "query_params": { "distance_max_km": 5 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn" = 805030 (ngữ cảnh Q4). Lọc nearby_places distance_km<=5: toàn bộ 10 địa điểm đều <5km (data thật).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#location"],
  "_note": "Câu nearby trong bán kính → context #location. chunk_id tạm."
}
```

---

## 5. Hoạt động Giải trí

---

### Q5-01 — Xem hoạt động của khách sạn

🙋 **Câu hỏi người dùng:**
> "Khách sạn này có những hoạt động vui chơi gì?"

💬 **Phản hồi người dùng mong muốn:**
```
🎉 Hoạt động & Vé vui chơi tại Vinpearl Resort & Spa Nha Trang Bay (10 hoạt động):

1. Vé vào cổng Công viên Chủ đề VinWonders Nha Trang
   💰 619.737 VND/người  |  ★ 4.6/5
   [Mua vé]

2. I-Resort Nha Trang Mud Bath Experience
   Trải nghiệm tắm bùn khoáng thư giãn
   💰 200.619 VND/người  |  ★ 4.8/5
   [Đặt ngay]

3. Vé Cáp Treo Vinpearl Harbour Nha Trang
   💰 400.504 VND/người
   [Mua vé]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. 10 activities thật (data/cleaned). LƯU Ý: review_score của activities thang /5 (không /10).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#activities"],
  "_note": "Câu hoạt động của hotel → context #activities. Giá lấy từ price.display...chargeTotal. chunk_id tạm."
}
```

---

### Q5-02 — Tìm hoạt động theo giá

🙋 **Câu hỏi người dùng:**
> "Có hoạt động nào dưới 500k không?"

💬 **Phản hồi người dùng mong muốn:**
```
💚 Hoạt động dưới 500.000 VND tại Vinpearl Resort & Spa Nha Trang Bay:

1. Vé vào cổng Vinpearl Harbour Nha Trang — 134.100 VND  ★ 4.2/5
2. I-Resort Nha Trang Mud Bath — 200.619 VND  ★ 4.8/5
3. Dịch vụ VIP Fast Track Sân bay Nha Trang — 215.378 VND  ★ 4.4/5
4. Vé Cáp Treo Vinpearl Harbour — 400.504 VND
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "query_params": { "price_max": 500000, "sort_by": "price:asc" },
  "response": {
    "data": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "khách sạn này" = 805030. Lọc activities có price<500.000 (data thật: nhiều hoạt động đạt).
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#activities"],
  "_note": "Câu lọc activities theo giá → context #activities. chunk_id tạm."
}
```

---

### Q5-03 — Tìm hoạt động đánh giá cao nhất

🙋 **Câu hỏi người dùng:**
> "Hoạt động được đánh giá cao nhất tại đây là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
🏆 Top 3 hoạt động được đánh giá cao nhất:

🥇 I-Resort Nha Trang Mud Bath Experience
   ★ 4.8/5  |  200.619 VND/người

🥈 Vé vào cổng Công viên Chủ đề VinWonders Nha Trang
   ★ 4.6/5  |  619.737 VND/người

🥉 Dịch vụ VIP Fast Track tại Sân bay Nha Trang
   ★ 4.4/5  |  215.378 VND/người
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "query_params": { "sort_by": "review_score:desc", "limit": 3 },
  "response": {
    "data": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // "tại đây" = 805030. Sort activities theo review_score desc (thang /5). Top: Mud Bath 4.8, VinWonders 4.6, Fast Track 4.4.
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#activities"],
  "_note": "Câu top hoạt động → context #activities. chunk_id tạm."
}
```

---

### Q5-04 — Tìm hoạt động trên toàn hệ thống theo thành phố

🙋 **Câu hỏi người dùng:**
> "Có những trải nghiệm vui chơi độc đáo nào ở Phú Quốc?"

💬 **Phản hồi người dùng mong muốn:**
```
🌴 Top hoạt động đặc sắc tại Phú Quốc:

1. Vé xem show Kiss Of The Sea tại Phú Quốc — từ 599.450 VND  ★ 4.6/5
2. Nhà hàng Camia Phú Quốc: Voucher & Đặt bàn — từ 532.895 VND  ★ 4.5/5
3. Vé VinWonders Phú Quốc - Safari Phú Quốc — từ 349.921 VND
4. Symphony Of The Sea | Phú Quốc — từ 424.925 VND
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/activities",
  "query_params": {
    "city": "Phú Quốc",
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "hotel_id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric",
        "hotel": {
          "name": "varchar",
          "city": "varchar"
        }
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Câu activities TOÀN HỆ THỐNG theo city=Phú Quốc → gom activities từ các hotel Phú Quốc (data thật).
  // hotel_ids = các hotel Phú Quốc có activities; vd 10247322 (Vida Loca) chứa show Kiss Of The Sea, Camia, VinWonders Safari.
  "hotel_ids": [10247322, 1032420, 1157572, 1624474, 1985199],
  "context_chunks": [
    "acc_10247322#activities", "acc_1032420#activities",
    "acc_1157572#activities", "acc_1624474#activities", "acc_1985199#activities"
  ],
  "_note": "Câu activities theo thành phố → context #activities của nhiều hotel cùng city. chunk_id tạm."
}
```

---

## 6. Gói Combo Khách sạn + Vui chơi

---

### Q6-01 — Gợi ý combo nghỉ dưỡng + vui chơi

🙋 **Câu hỏi người dùng:**
> "Tư vấn cho tôi gói combo 3 ngày 2 đêm ở Nha Trang bao gồm cả vé vui chơi"

💬 **Phản hồi người dùng mong muốn:**
```
🎁 Gợi ý Combo 3N2Đ Nha Trang — Dành cho 2 người

🏨 Khách sạn đề xuất:
   Vinpearl Resort & Spa Nha Trang Bay ★★★★★ (8.8/10)
   2 đêm × 5.000.000 VND = 10.000.000 VND

🎉 Hoạt động kèm theo (2 người):
   ✓ Vé VinWonders Nha Trang: 2 × 619.737 = 1.239.474 VND
   ✓ I-Resort Mud Bath: 2 × 200.619 = 401.238 VND

💰 Tổng ước tính: ~11.640.712 VND / 2 người
   (~ 5.820.356 VND / người)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/combo",
  "path_params": { "id": "integer" },
  "query_params": {
    "nights": 3,
    "guests": 2,
    "include_activities": true
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "star_rating": "numeric",
      "review_score": "numeric",
      "recommended_room": {
        "name": "varchar",
        "price": "numeric",
        "room_view": "varchar"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ],
    "estimated_total": "numeric — tổng ước tính (phòng × đêm + activities × guests)"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Combo Nha Trang → hotel 805030 (có cả rooms + activities thật). Giá phòng 5tr (placeholder), giá activity thật.
  "hotel_ids": [805030],
  "context_chunks": ["acc_805030#rooms", "acc_805030#activities"],
  "_note": "Câu combo → context #rooms (giá phòng) + #activities (vé). chunk_id tạm."
}
```

---

### Q6-02 — Tìm combo theo ngân sách

🙋 **Câu hỏi người dùng:**
> "Ngân sách 5 triệu cho 2 người đi Đà Lạt 2 ngày bao gồm cả vé vui chơi, có được không?"

💬 **Phản hồi người dùng mong muốn:**
```
✅ Hoàn toàn khả thi! Gợi ý trong ngân sách 5.000.000 VND / 2 người:

🏨 Sunshine - Tia Nắng Mới (Đà Lạt)
   2 đêm × 600.000 VND = 1.200.000 VND

🎉 Hoạt động (2 người):
   ✓ Vé Thung lũng Tình yêu Đà Lạt: 2 × 208.899 = 417.798 VND
   ✓ Trải nghiệm Alpine Coaster Datanla: 2 × 213.707 = 427.414 VND
   ✓ Fresh Garden & Fresh Zoo: 2 × 108.935 = 217.870 VND

💰 Tổng: ~2.263.082 VND — Còn dư ~2.736.918 VND trong ngân sách!
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/combo-suggest",
  "query_params": {
    "city": "Đà Lạt",
    "budget_total": 5000000,
    "guests": 2,
    "nights": 2
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "review_score": "numeric",
      "recommended_room": {
        "name": "varchar",
        "price": "numeric"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "price_amount": "numeric"
      }
    ],
    "total_cost": "numeric",
    "remaining_budget": "numeric"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI "Dalat Wonder Resort" (không có) → "Sunshine - Tia Nắng Mới" (14626926, Đà Lạt, có rooms+activities thật).
  "hotel_ids": [14626926],
  "context_chunks": ["acc_14626926#rooms", "acc_14626926#activities"],
  "_note": "Câu combo theo ngân sách → context #rooms + #activities. chunk_id tạm."
}
```

---

### Q6-03 — Combo gia đình

🙋 **Câu hỏi người dùng:**
> "Gợi ý gói gia đình 4 người (2 người lớn + 2 trẻ em) đi Phú Quốc 3N2Đ"

💬 **Phản hồi người dùng mong muốn:**
```
👨‍👩‍👧‍👦 Gói Gia đình 3N2Đ Phú Quốc — 4 người

🏨 Khu nghỉ dưỡng Novotel Phú Quốc ★★★★★ (8.7/10)
   Phòng Gia Đình (Family Room), tối đa 4 người: 2 đêm × 3.520.000 VND = 7.040.000 VND
   Phù hợp: Gia đình ✓

🎉 Hoạt động gia đình (4 người):
   ✓ Vé VinWonders Phú Quốc - Safari: 4 × 349.921 = 1.399.684 VND
   ✓ Show Kiss Of The Sea: 4 × 599.450 = 2.397.800 VND

💰 Tổng ước tính: ~10.837.484 VND
   (~ 2.709.371 VND / người)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/combo-suggest",
  "query_params": {
    "city": "Phú Quốc",
    "guests": 4,
    "nights": 3,
    "suitable_for": "Gia đình có trẻ nhỏ",
    "min_occupancy": 4
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "star_rating": "numeric",
      "review_score": "numeric",
      "suitable_for": ["text[]"],
      "recommended_room": {
        "name": "varchar",
        "max_occupancy": "integer",
        "price": "numeric"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ],
    "total_cost": "numeric"
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI "Premier Village" (không có) → "Novotel Phú Quốc" (1157572): Phú Quốc + suitable_for "Gia đình" + room max>=4 (Family Room).
  "hotel_ids": [1157572],
  "context_chunks": ["acc_1157572#rooms", "acc_1157572#activities"],
  "_note": "Câu combo gia đình → context #rooms (phòng max>=4) + #activities. chunk_id tạm."
}
```

---

## 7. So sánh & Gợi ý Cá nhân hóa

---

### Q7-01 — So sánh 2 khách sạn

🙋 **Câu hỏi người dùng:**
> "So sánh Pullman Đà Nẵng và Marriott Đà Nẵng giúp tôi chọn"

💬 **Phản hồi người dùng mong muốn:**
```
⚖️ So sánh chi tiết — Pullman Đà Nẵng vs Marriott Đà Nẵng

                      Pullman Đà Nẵng      Marriott Đà Nẵng
──────────────────────────────────────────────────────────
Xếp hạng sao          ★★★★★                ★★★★★
Điểm đánh giá         8.9/10               8.9/10
Giá phòng từ          4.310.000 VND        4.930.000 VND
Loại hình             Resort               Resort
Điểm dịch vụ          9.2                  9.4
Điểm sạch sẽ          9.2                  9.1
Phòng/thoải mái        —                    9.4

💡 Gợi ý: Giá tốt hơn → Pullman; chất lượng phòng & dịch vụ nhỉnh hơn → Marriott
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/compare",
  "query_params": { "ids": [182167, 1985160] },
  "response": {
    "hotels": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "is_luxury": "boolean",
        "review_score": "numeric",
        "review_count": "integer",
        "reviews_detail": "jsonb — grades chi tiết",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI "Fusion Maia / Four Seasons" (không có) → "Pullman / Marriott Đà Nẵng" (182167, 1985160 — 2 resort 5★ Đà Nẵng thật).
  // grades so sánh lấy thật từ reviews_detail của từng hotel.
  "hotel_ids": [182167, 1985160],
  "context_chunks": [
    "acc_182167#overview", "acc_182167#reviews",
    "acc_1985160#overview", "acc_1985160#reviews"
  ],
  "_note": "Câu so sánh → context #overview + #reviews (grades) của cả 2 hotel. chunk_id tạm."
}
```

---

### Q7-02 — Gợi ý cho cặp đôi tuần trăng mật

🙋 **Câu hỏi người dùng:**
> "Gợi ý khách sạn lãng mạn cho tuần trăng mật ở Phú Quốc, budget 10 triệu 3 đêm"

💬 **Phản hồi người dùng mong muốn:**
```
💑 Top khách sạn lãng mạn cho tuần trăng mật tại Phú Quốc
   (Ngân sách: ~3.300.000 VND/đêm)

1. ✨ Khách sạn Venice Phú Quốc
   ★★★★★ | 8.9/10 | Giá từ 2.040.000 VND/đêm
   Phù hợp: ❤️ Cặp đôi
   [Xem chi tiết]

2. Khách sạn Roma Phú Quốc
   8.9/10 | Giá từ 950.000 VND/đêm
   Phù hợp: ❤️ Cặp đôi
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Phú Quốc",
    "suitable_for": "Cặp đôi",
    "price_max": 3400000,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "suitable_for": ["text[]"],
        "amenities": ["text[]"],
        "description": "text — trích đoạn 200 ký tự đầu",
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: city=Phú Quốc + suitable_for "Cặp đôi" + giá<=3.4tr/đêm (budget 10tr/3 đêm), sort score desc.
  // (Hotel tên bịa La Veranda/Salinda không có → thay bằng hotel Phú Quốc thật khớp tiêu chí.)
  "hotel_ids": [51060966, 39532985],
  "context_chunks": [
    "acc_51060966#overview", "acc_39532985#overview"
  ],
  "_note": "Câu gợi ý cặp đôi theo budget → context #overview. chunk_id tạm."
}
```

---

### Q7-03 — Gợi ý khách sạn gần sân bay

🙋 **Câu hỏi người dùng:**
> "Tôi đến Đà Nẵng muộn, tìm khách sạn gần sân bay nhất để nghỉ"

💬 **Phản hồi người dùng mong muốn:**
```
✈️ Khách sạn gần Sân bay Đà Nẵng (cách dưới 5 km):

1. Tru by Hilton Trung tâm thành phố Đà Nẵng
   1.14 km từ Sân bay Quốc tế Đà Nẵng  |  ★★★  |  8.7/10
   Giá từ: 600.000 VND/đêm
   [Đặt ngay]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Đà Nẵng",
    "nearby_place_name": "Sân bay Đà Nẵng",
    "distance_max_km": 5,
    "sort_by": "distance:asc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "nearby_places": [
          {
            "name": "varchar",
            "type": "varchar",
            "distance_km": "numeric"
          }
        ],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: city=Đà Nẵng + nearby_places chứa "sân bay" + distance<5km. Data thật chỉ 1 hotel (Tru by Hilton, 1.14km).
  "hotel_ids": [70410096],
  "context_chunks": ["acc_70410096#location"],
  "_note": "Câu gần sân bay → context #location (nearby_places + distance). Data thật chỉ 1 kết quả. chunk_id tạm."
}
```

---

### Q7-04 — Gợi ý dựa trên tiêu chí tổng hợp

🙋 **Câu hỏi người dùng:**
> "Tìm resort có spa, hồ bơi vô cực, gần biển, điểm trên 9, giá dưới 5 triệu đêm"

💬 **Phản hồi người dùng mong muốn:**
```
🌟 Tìm thấy 2 resort tại Việt Nam khớp tiêu chí (Spa + hồ bơi + điểm ≥9):

1. Vinpearl Luxury Nha Trang
   ★★★★★ | 9.3/10
   ✓ Spa  ✓ Hồ bơi ngoài trời  ✓ Bãi biển riêng
   Giá từ: 5.000.000 VND/đêm

2. Vinpearl Resort & Spa Hạ Long
   ★★★★★ | 9.0/10
   ✓ Spa  ✓ Hồ bơi  ✓ Trên đảo Rều
   Giá từ: 5.000.000 VND/đêm
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "accommodation_type": "Resort",
    "amenities": ["Spa", "Hồ bơi vô cực", "Bãi biển riêng"],
    "review_score_min": 9.0,
    "price_max": 5000000,
    "sort_by": "review_score:desc"
  },
  "response": {
    "total": 4,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "city": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // Lọc thật: Resort + có spa + có bể bơi + review_score>=9 (toàn corpus). 2 hotel VN đạt: Vinpearl Luxury NT (9.3), Vinpearl Hạ Long (9.0).
  // (Tên bịa Radisson/TIA không có → thay bằng hotel thật. "hồ bơi vô cực" relax thành "có bể bơi" vì corpus ít gắn nhãn infinity.)
  "hotel_ids": [263516, 1015998],
  "context_chunks": [
    "acc_263516#amenities", "acc_1015998#amenities"
  ],
  "_note": "Câu đa tiêu chí → context #amenities (spa+pool) của các hotel đạt ngưỡng điểm. chunk_id tạm."
}
```

---

### Q7-05 — Gợi ý khách sạn tương tự

🙋 **Câu hỏi người dùng:**
> "Có khách sạn nào giống Vinpearl Resort & Golf Nam Hội An nhưng rẻ hơn không?"

💬 **Phản hồi người dùng mong muốn:**
```
💡 Các lựa chọn thay thế cho Vinpearl Resort & Golf Nam Hội An:

Vinpearl Resort & Golf Nam Hội An: ★★★★★ | 8.7/10 | từ 5.000.000 VND/đêm

Lựa chọn tương tự (cùng Hội An, Resort) nhưng tiết kiệm hơn:

1. Vinpearl Hoi An Villas
   ★★★★★ | 7.8/10 | từ 4.620.000 VND/đêm (-8%)
   Tương đồng: Resort tại Hội An, cùng hệ Vinpearl
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/similar",
  "path_params": { "id": "integer — ID Vinpearl Resort & Golf Nam Hội An (4593719)" },
  "query_params": {
    "price_max": "numeric — lấy max_price của khách sạn gốc × 0.8",
    "city": "varchar — cùng thành phố",
    "accommodation_type": "varchar — cùng loại",
    "sort_by": "review_score:desc"
  },
  "response": {
    "reference_hotel": {
      "id": "integer",
      "name": "varchar",
      "review_score": "numeric",
      "amenities": ["text[]"],
      "rooms": { "min_price": "numeric" }
    },
    "similar_hotels": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "price_saving_pct": "numeric — % tiết kiệm so với khách sạn gốc",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

🎯 **Ground-truth Answer (KE — chấm điểm retrieval):**
```jsonc
{
  // ĐÃ ĐỔI ref "Anantara Hội An" (không có) → "Vinpearl Resort & Golf Nam Hội An" (4593719, thật).
  // similar = Resort cùng Hội An, giá <= giá gốc: Vinpearl Hoi An Villas (1994212).
  "reference_hotel_id": 4593719,
  "hotel_ids": [1994212],
  "context_chunks": ["acc_4593719#overview", "acc_1994212#overview"],
  "_note": "Câu similar → context #overview của ref + hotel gợi ý. Corpus Hội An ít Resort nên ít lựa chọn. chunk_id tạm."
}
```

---

## Tổng hợp Danh sách API

| # | Endpoint | Method | Mô tả chức năng | Bảng dữ liệu |
|---|----------|--------|-----------------|-------------|
| 1 | `/api/hotels` | GET | Tìm kiếm & lọc danh sách khách sạn theo thành phố, loại, sao, điểm, tiện ích, đối tượng, khoảng giá | `hotels`, `rooms` |
| 2 | `/api/hotels/{id}` | GET | Lấy toàn bộ thông tin chi tiết một khách sạn | `hotels` |
| 3 | `/api/hotels/{id}/images` | GET | Lấy danh sách toàn bộ ảnh của một khách sạn | `hotels.images` |
| 4 | `/api/hotels/{id}/policies` | GET | Lấy chính sách nhận/trả phòng, phụ phí và ghi chú đặc biệt | `hotels.policyNotes`, `hotels.useful_info` |
| 5 | `/api/hotels/{id}/reviews` | GET | Lấy điểm đánh giá tổng quan và chi tiết theo từng tiêu chí | `hotels.review_score`, `hotels.reviews_detail` |
| 6 | `/api/hotels/{id}/location` | GET | Lấy tọa độ, địa chỉ và danh sách địa điểm lân cận kèm khoảng cách | `hotels`, `nearby_places` |
| 7 | `/api/hotels/{id}/rooms` | GET | Lấy danh sách loại phòng của khách sạn, hỗ trợ lọc theo số người, hướng view, giá | `rooms` |
| 8 | `/api/rooms/{id}` | GET | Lấy chi tiết đầy đủ một loại phòng cụ thể | `rooms` |
| 9 | `/api/hotels/{id}/nearby-places` | GET | Lấy danh sách địa điểm nổi bật gần khách sạn, hỗ trợ lọc theo loại và bán kính | `nearby_places` |
| 10 | `/api/hotels/{id}/activities` | GET | Lấy danh sách hoạt động vui chơi liên kết với khách sạn, hỗ trợ lọc theo giá và điểm | `activities` |
| 11 | `/api/activities` | GET | Tìm kiếm hoạt động giải trí trên toàn hệ thống theo thành phố, giá, điểm | `activities`, `hotels` |
| 12 | `/api/hotels/{id}/combo` | GET | Tạo gói combo khách sạn kèm hoạt động gợi ý, tính tổng chi phí ước tính | `hotels`, `rooms`, `activities` |
| 13 | `/api/hotels/combo-suggest` | GET | Gợi ý combo phù hợp theo ngân sách, số người, số đêm, thành phố | `hotels`, `rooms`, `activities` |
| 14 | `/api/hotels/compare` | GET | So sánh song song nhiều khách sạn theo tất cả tiêu chí | `hotels`, `rooms` |
| 15 | `/api/hotels/{id}/similar` | GET | Gợi ý các khách sạn tương tự nhưng rẻ hơn (cùng thành phố, cùng loại) | `hotels`, `rooms` |

---
