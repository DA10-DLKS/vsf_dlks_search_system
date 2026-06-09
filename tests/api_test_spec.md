# Tài Liệu Đặc Tả Test Cases API (API Test Specification)

Tài liệu này định nghĩa danh sách tham số cần điền (Request Parameters) và cấu trúc dữ liệu trả về thực tế (Expected Output) của tất cả 16 endpoint trong hệ thống OTA Travel Assistant API. Các dữ liệu mẫu được xây dựng dựa trên thông tin thực tế được lấy trực tiếp từ database Supabase của dự án (khách sạn Melia Vinpearl Riverfront Đà Nẵng - ID `4947690`).

---

## Swagger API
[https://supabase-ota-travel.onrender.com/docs#/](https://supabase-ota-travel.onrender.com/docs#/)


## 🔑 Cấu Hình Header Chung
Tất cả các endpoint (trừ `/health`) yêu cầu truyền thông tin xác thực sau qua Header:
- **Header Key**: `X-API-Key`
- **Header Value**: `<token_của_bạn>`

---

## 📋 Danh Sách Test Cases Cho 16 Endpoints

### 1. GET /health
Kiểm tra trạng thái hoạt động của hệ thống. Không yêu cầu API Key.

* **Tham số cần điền**: Không có.
* **Kết quả trả về thực tế (Response)**:
```json
{
  "status": "OK",
  "version": "2.0.0",
  "message": "OTA Travel Assistant API đang hoạt động bình thường."
}
```

---

### 2. GET /api/hotels
Tìm kiếm và lọc danh sách khách sạn.

* **Tham số cần điền**:
  * `city` (Query, Optional): `Đà Nẵng`
  * `accommodation_type` (Query, Optional): `Khách sạn`
  * `price_min` (Query, Optional): `1000000` (Giá phòng nhỏ nhất thực tế của khách sạn này là `1425768.00`)
  * `price_max` (Query, Optional): `8000000`
  * `review_score_min` (Query, Optional): `8.0`
  * `star_rating` (Query, Optional): `5`
  * `is_luxury` (Query, Optional): `false`
  * `amenities` (Query, Optional): `Bàn tiếp tân [24 giờ],Bãi đỗ xe [miễn phí]` (Phân tách bằng dấu phẩy)
  * `suitable_for` (Query, Optional): `Cặp đôi,Khách đi công tác`
  * `nearby_place_name` (Query, Optional): `Trung tâm Hỗ trợ Du khách Đà Nẵng`
  * `distance_max_km` (Query, Optional): `1.0` (Khoảng cách thực tế là `0.53` km)
  * `sort_by` (Query, Optional): `distance:asc` (Các giá trị khác: `review_score:desc`, `price:asc`, `price:desc`)
  * `page` (Query, Optional): `1`
  * `limit` (Query, Optional): `20`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
      "accommodation_type": "Khách sạn",
      "star_rating": 5.0,
      "is_luxury": false,
      "review_score": 8.9,
      "review_count": 10921,
      "address": "341 Đ. Trần Hưng Đạo, An Hải Bắc, Sơn Trà, Đà Nẵng 550000, Vietnam, An Hải Bắc, Đà Nẵng, Việt Nam",
      "city": "Đà Nẵng",
      "latitude": 16.0708026885986,
      "longitude": 108.229141235352,
      "description": "Khám phá Melia Vinpearl Riverfront Đà Nẵng - Khách sạn 5 sao tuyệt vời tại Đà Nẵng, Việt Nam\n\nMelia Vinpearl Riverfront Đà Nẵng là một khách sạn 5 sao nằm tại thành phố Đà Nẵng, Việt Nam. Với dịch vụ ",
      "amenities": [
        "Bàn tiếp tân [24 giờ]",
        "Bãi đỗ xe [gần bên]",
        "Bãi đỗ xe [miễn phí]",
        "Bãi đỗ xe [tại chỗ]",
        "Bình chữa cháy",
        "..."
      ],
      "suitable_for": [
        "Khách đi công tác",
        "Cặp đôi",
        "Khách du lịch một mình",
        "Gia đình có trẻ nhỏ",
        "Gia đình có thanh thiếu niên",
        "..."
      ],
      "policyNotes": [],
      "useful_info": {
        "Nhận phòng từ": "14:00",
        "Trả phòng đến": "12:00",
        "Số lượng phòng": "864",
        "Số lượng nhà hàng": "3",
        "Phí đưa đón sân bay": "350000 VND",
        "Phí bữa sáng (áp dụng khi không bao gồm trong giá phòng)": "280000 VND"
      },
      "images": [
        "https://pix8.agoda.net/hotelImages/4947690/0/bfb51fa3976c865ea22b803dd1b7ca78.jpeg?ce=2&s=1024x768"
      ],
      "rooms": {
        "min_price": 1425768.0
      },
      "nearby_places": [
        {
          "name": "Trung tâm Hỗ trợ Du khách Đà Nẵng",
          "type": "Thông Tin Du Lịch và Du Hành",
          "distance_km": 0.53
        }
      ]
    }
  ]
}
```

---

### 3. GET /api/hotels/{id}
Lấy thông tin chi tiết đầy đủ của một khách sạn cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690` (Melia Vinpearl Riverfront Đà Nẵng)
* **Kết quả trả về thực tế (Response)**:
```json
{
  "id": 4947690,
  "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
  "accommodation_type": "Khách sạn",
  "star_rating": 5.0,
  "is_luxury": false,
  "review_score": 8.9,
  "review_count": 10921,
  "address": "341 Đ. Trần Hưng Đạo, An Hải Bắc, Sơn Trà, Đà Nẵng 550000, Vietnam, An Hải Bắc, Đà Nẵng, Việt Nam",
  "city": "Đà Nẵng",
  "latitude": 16.0708026885986,
  "longitude": 108.229141235352,
  "description": "Khám phá Melia Vinpearl Riverfront Đà Nẵng - Khách sạn 5 sao....",
  "amenities": [
    "Bàn tiếp tân [24 giờ]",
    "Bãi đỗ xe [gần bên]",
    "Bãi đỗ xe [miễn phí]",
    "Bãi đỗ xe [tại chỗ]",
    "Bình chữa cháy",
    "..."
  ],
  "suitable_for": [
    "Khách đi công tác",
    "Cặp đôi",
    "Khách du lịch một mình",
    "Gia đình có trẻ nhỏ",
    "Gia đình có thanh thiếu niên",
    "..."
  ],
  "useful_info": {
    "Nhận phòng từ": "14:00",
    "Trả phòng đến": "12:00",
    "Số lượng phòng": "864",
    "Số lượng nhà hàng": "3",
    "Phí đưa đón sân bay": "350000 VND",
    "Phí bữa sáng (áp dụng khi không bao gồm trong giá phòng)": "280000 VND"
  },
  "policyNotes": [],
  "images": [
    "https://pix8.agoda.net/hotelImages/4947690/0/bfb51fa3976c865ea22b803dd1b7ca78.jpeg?ce=2&s=1024x768",
    "..."
  ],
  "reviews_detail": [
    {
      "date": "11 tháng 5 2026",
      "text": "Ngày cuối cùng ở Đà Nẵng, tôi đã quyết định tận hưởng một chút sang trọng và chọn một khách sạn 5 sao. Với mức giá chỉ tương đương một khách sạn kinh doanh ở Nhật Bản, tôi đã có một trải nghiệm rất xa hoa. Tôi cũng đã nhận được massage tại spa với giá ưu đãi dành riêng cho khách lưu trú. Bữa sáng có đa dạng món ăn đến từ các quốc gia khác nhau. Trong phòng có mini bếp, tủ lạnh, và két sắt, cùng với 2 chai nước khoáng miễn phí. Hơn nữa, ngay gần đó có Vincom Plaza, rất tiện lợi cho việc mua sắm siêu thị đi bộ.",
      "title": "Kỳ nghỉ hợp lý và sang trọng.",
      "rating": 9.2,
      "check_in": "Tháng 5 năm 2026",
      "room_type": "Phòng Loại Sang",
      "rating_text": "Trên cả tuyệt vời",
      "reviewer_name": "Noriko",
      "reviewer_type": "Du lịch một mình",
      "reviewer_country": "Nhật Bản"
    }
  ],
  "source_url": "https://www.agoda.com/vinpearl-condotel-riverfront-da-nang/hotel/da-nang-vn.html?hotel=4947690&currency=VND&checkIn=2026-06-12&checkOut=2026-06-13&rooms=1&adults=2&children=0"
}
```

---

### 4. GET /api/hotels/{id}/images
Lấy tất cả hình ảnh của một khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "hotel_name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
  "images": [
    "https://pix8.agoda.net/hotelImages/4947690/0/bfb51fa3976c865ea22b803dd1b7ca78.jpeg?ce=2&s=1024x768",
    "..."
  ]
}
```

---

### 5. GET /api/hotels/{id}/policies
Lấy chính sách của khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `65153`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 65153,
  "policyNotes": [
    "Chỗ nghỉ không cho phép mang đồ ăn và thức uống từ bên ngoài vào..."
  ],
  "useful_info": {
    "Nhận phòng từ": "15:00",
    "Trả phòng đến": "12:00",
    "Số lượng phòng": "533",
    "Số lượng nhà hàng": "4",
    "Số tầng khách sạn": "5",
    "Điện áp trong phòng": "220",
    "Phí đưa đón sân bay": "450000 VND",
    "Số lượng quán bar/lounge": "4",
    "Phòng / tầng không hút thuốc": "no",
    "Thời gian đến sân bay (phút)": "30",
    "Khách sạn được xây vào năm": "2003",
    "Khoảng cách từ trung tâm thành phố": "6km",
    "Khách sạn được nâng cấp gần nhất vào": "2021"
  }
}
```

---

### 6. GET /api/hotels/{id}/reviews
Lấy phân tích đánh giá chi tiết (grades + tags).

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "review_score": 8.9,
  "review_count": 10921,
  "reviews_detail": {
    "grades": {
      "location": 9.3,
      "cleanliness": 9.7,
      "service": 9.5,
      "facilities": 9.0,
      "value": 9.4
    },
    "tags": [
      "nhân viên thân thiện",
      "vị trí đẹp",
      "phòng sạch sẽ",
      "view tốt",
      "đáng đồng tiền"
    ]
  }
}
```

---

### 7. GET /api/hotels/{id}/location
Lấy tọa độ bản đồ và danh sách đầy đủ địa danh lân cận của khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
  "address": "341 Đ. Trần Hưng Đạo, An Hải Bắc, Sơn Trà, Đà Nẵng 550000, Vietnam, An Hải Bắc, Đà Nẵng, Việt Nam",
  "city": "Đà Nẵng",
  "latitude": 16.0708026885986,
  "longitude": 108.229141235352,
  "nearby_places": [
    {
      "id": 161,
      "name": "Bưu điện trung tâm thành phố Đà Nẵng",
      "type": "Dịch Vụ Internet, Bưu Chính và Điện Thoại",
      "distance_km": 0.49
    },
    {
      "id": 162,
      "name": "Trung tâm Hỗ trợ Du khách Đà Nẵng",
      "type": "Thông Tin Du Lịch và Du Hành",
      "distance_km": 0.53
    },
    "..."
  ]
}
```

---

### 8. GET /api/hotels/{id}/rooms
Lấy danh sách các loại phòng hiện có của khách sạn kèm theo các bộ lọc.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `min_occupancy` (Query, Optional): `2`
  * `room_view` (Query, Optional): `Thành phố`
  * `sort_by` (Query, Optional): `price:asc`
  * `limit` (Query, Optional): `10`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "rooms": [
    {
      "id": 166,
      "hotel_id": 4947690,
      "room_type_id": "633404800",
      "name": "Phòng Loại Sang 3 Người Lớn (Deluxe Room 3 Adults)",
      "price": 1425768.0,
      "room_size": "41 m²",
      "max_occupancy": 2,
      "bed_type": "1 giường lớn hoặc 2 giường đơn",
      "room_view": "Hướng Thành phố",
      "room_amenities": [
        "1 giường lớn hoặc 2 giường đơn",
        "41 m²",
        "Ban công/sân hiên",
        "Bàn làm việc",
        "Bếp",
        "Bố trí và nội thất phòng",
        "Bộ kim chỉ",
        "Các loại khăn",
        "Cách âm",
        "Cân",
        "Cửa sổ",
        "Dép đi trong nhà",
        "Ghế sofa",
        "Giá treo quần áo",
        "Giải trí ",
        "Gương",
        "Hướng Thành phố",
        "Không hút thuốc",
        "Khả năng tiếp cận cho người khuyết tật",
        "Khả năng tiếp cận cho người khó đi lại",
        "Két sắt trong phòng",
        "Máy sấy tóc",
        "Nước đóng chai miễn phí",
        "Phòng tắm và vật dụng vệ sinh",
        "Quạt",
        "Quần áo và Giặt ủi",
        "Rèm che ánh sáng",
        "TV",
        "Thùng rác",
        "Tiện nghi",
        "Truyền hình cáp/vệ tinh",
        "Tính năng an toàn và an ninh",
        "Tủ lạnh",
        "Tủ quần áo",
        "Vòi sen",
        "Vật dụng tắm rửa",
        "phòng tắm riêng",
        "Áo choàng tắm",
        "Ăn uống",
        "Điều hòa",
        "Điện thoại",
        "Đầu báo khói",
        "Ấm nước điện"
      ],
      "images": [
        "https://pix8.agoda.net/hotelImages/4947690/514453130/3a09e8ca45c72139bdb799be1029ed1c.jpeg?ce=2&s=800x600"
      ],
      "review_score": 9.2
    },
    {
      "id": 161,
      "hotel_id": 4947690,
      "room_type_id": "514453134",
      "name": "Suite",
      "price": 1659458.0,
      "room_size": "53 m²",
      "max_occupancy": 2,
      "bed_type": "1 giường lớn",
      "room_view": "Hướng Thành phố",
      "room_amenities": [
        "1 giường lớn",
        "53 m²",
        "Ban công/sân hiên",
        "Bàn làm việc",
        "Bình chữa cháy",
        "Bếp",
        "Bố trí và nội thất phòng",
        "Bồn tắm",
        "Bộ kim chỉ",
        "Các loại khăn",
        "Cách âm",
        "Cân",
        "Cửa sổ",
        "Cửa sổ mở",
        "Dành cho trẻ em",
        "Dép đi trong nhà",
        "Dịch vụ báo thức",
        "Dịch vụ và tiện nghi",
        "Dọn phòng hằng ngày",
        "Ghế sofa",
        "Giá treo quần áo",
        "Giường cũi của em bé (theo yêu cầu)",
        "Giải trí ",
        "Gương",
        "Hướng Thành phố",
        "Khu vực tiếp khách",
        "Khả năng tiếp cận cho người khuyết tật",
        "Khả năng tiếp cận cho người khó đi lại",
        "Két sắt trong phòng",
        "Máy sấy tóc",
        "Nước đóng chai miễn phí",
        "Phòng tắm có băng ghế tắm",
        "Phòng tắm và vật dụng vệ sinh",
        "Quạt",
        "Quần áo và Giặt ủi",
        "Rèm che ánh sáng",
        "TV",
        "TV [màn hình phẳng]",
        "Thùng rác",
        "Tiện nghi",
        "Tiện nghi là/ủi",
        "Truyền hình cáp/vệ tinh",
        "Tính năng an toàn và an ninh",
        "Tính năng an toàn/bảo mật",
        "Tủ lạnh",
        "Tủ lạnh nhỏ trong phòng",
        "Tủ quần áo",
        "Vòi sen",
        "Vải trải giường",
        "Vật dụng tắm rửa",
        "Wi-Fi [miễn phí]",
        "phòng tắm riêng",
        "Áo choàng tắm",
        "Ăn uống",
        "Điều hòa",
        "Điện thoại",
        "Đầu báo khói",
        "Đồng hồ báo thức",
        "Ấm nước",
        "Ấm nước điện",
        "Ổ cắm điện gần giường"
      ],
      "images": [
        "https://pix8.agoda.net/hotelImages/4947690/514453134/3555567c0c9fa0d8617f7dcfe7c08e17.jpeg?ce=2&s=800x600"
      ],
      "review_score": 9.1
    },
    "..."
  ]
}
```

---

### 9. GET /api/rooms/{id}
Lấy thông tin chi tiết một phòng cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `160` (Phòng Family Suite)
* **Kết quả trả về thực tế (Response)**:
```json
{
  "id": 160,
  "hotel_id": 4947690,
  "room_type_id": "514453132",
  "name": "Phòng Suite gia đình (Family Suite)",
  "price": 4178804.0,
  "room_size": "53 m²",
  "max_occupancy": 4,
  "bed_type": "1 giường lớn và 1 giường tầng",
  "room_view": "Hướng Thành phố",
  "room_amenities": [
    "1 giường lớn và 1 giường tầng",
    "53 m²",
    "Ban công/sân hiên",
    "Bàn làm việc",
    "Bình chữa cháy",
    "Bếp",
    "Bố trí và nội thất phòng",
    "Bồn tắm",
    "Bộ kim chỉ",
    "Các loại khăn",
    "Cách âm",
    "Cân",
    "Cửa sổ",
    "Cửa sổ mở",
    "Dành cho trẻ em",
    "Dép đi trong nhà",
    "Dịch vụ báo thức",
    "Dịch vụ và tiện nghi",
    "Dọn phòng hằng ngày",
    "Ghế sofa",
    "Giá treo quần áo",
    "Giường cũi của em bé (theo yêu cầu)",
    "Giải trí ",
    "Gương",
    "Hướng Thành phố",
    "Khu vực tiếp khách",
    "Khả năng tiếp cận cho người khuyết tật",
    "Khả năng tiếp cận cho người khó đi lại",
    "Két sắt trong phòng",
    "Máy sấy tóc",
    "Nước đóng chai miễn phí",
    "Phòng tắm có băng ghế tắm",
    "Phòng tắm và vật dụng vệ sinh",
    "Quạt",
    "Quần áo và Giặt ủi",
    "Rèm che ánh sáng",
    "TV",
    "TV [màn hình phẳng]",
    "Thùng rác",
    "Tiện nghi",
    "Tiện nghi là/ủi",
    "Truyền hình cáp/vệ tinh",
    "Tính năng an toàn và an ninh",
    "Tính năng an toàn/bảo mật",
    "Tủ lạnh",
    "Tủ lạnh nhỏ trong phòng",
    "Tủ quần áo",
    "Vòi sen",
    "Vải trải giường",
    "Vật dụng tắm rửa",
    "Wi-Fi [miễn phí]",
    "phòng tắm riêng",
    "Áo choàng tắm",
    "Ăn uống",
    "Điều hòa",
    "Điện thoại",
    "Đầu báo khói",
    "Đồng hồ báo thức",
    "Ấm nước điện",
    "Ổ cắm điện gần giường"
  ],
  "images": [
    "https://pix8.agoda.net/hotelImages/4947690/514453132/aa8bf8075916c0451ef2cd857a7f6bfc.jpeg?ce=2&s=800x600",
    "..."
  ],
  "review_score": 8.6
}
```

---

### 10. GET /api/hotels/{id}/nearby-places
Lấy danh sách các địa điểm lân cận khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `type` (Query, Optional): `Dịch Vụ Internet, Bưu Chính và Điện Thoại` (Tìm kiếm case-insensitive)
  * `distance_max_km` (Query, Optional): `0.5` (Khoảng cách bưu điện là `0.49` km)
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "nearby_places": [
    {
      "id": 161,
      "hotel_id": 4947690,
      "name": "Bưu điện trung tâm thành phố Đà Nẵng",
      "type": "Dịch Vụ Internet, Bưu Chính và Điện Thoại",
      "distance_km": 0.49
    }
  ]
}
```

---

### 11. GET /api/hotels/{id}/activities
Lấy danh sách các hoạt động vui chơi liên kết với khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `price_max` (Query, Optional): `800000` (Thực tế vé pháo hoa là `751400.00`)
  * `sort_by` (Query, Optional): `price:asc`
  * `limit` (Query, Optional): `2`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel_id": 4947690,
  "activities": [
    {
      "id": 162,
      "hotel_id": 4947690,
      "title": "DIFF 2026 | Vé tham dự Lễ hội Pháo hoa Quốc tế Đà Nẵng | Nhận voucher miễn phí trên KKday",
      "description": "<ul><li>Nhận nhiều loại voucher hấp dẫn, bao gồm vé xem <a href=\"https://www.kkday.com/vi/product/148999\">Áo Dài Show</a>, <a href=\"https://www.kkday.com/vi/product/529239\">Bảo tàng Đà Nẵng</a>, cùng ",
      "price_amount": 751400,
      "review_score": 4.6
    },
    {
      "id": 163,
      "hotel_id": 4947690,
      "title": "Private Car Transfer: Da Nang Airport to Hotel",
      "description": "Travel between Da Nang Airport, the train station, and your hotel in the city center with a private car transfer. This service is available for both arrivals and departures.\n\n- Complimentary transfers",
      "price_amount": 90174,
      "review_score": 4.8
    }
  ]
}
```

---

### 12. GET /api/activities
Tìm kiếm các hoạt động giải trí trên toàn hệ thống.

* **Tham số cần điền**:
  * `city` (Query, Optional): `Đà Nẵng`
  * `sort_by` (Query, Optional): `price:asc`
  * `limit` (Query, Optional): `5`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "data": [
    {
      "id": 163,
      "hotel_id": 4947690,
      "title": "Private Car Transfer: Da Nang Airport to Hotel",
      "description": "Travel between Da Nang Airport, the train station, and your hotel in the city center with a private car transfer. This service is available for both arrivals and departures.\n\n- Complimentary transfers",
      "price_amount": 90174.0,
      "review_score": 4.8,
      "hotel": {
        "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
        "city": "Đà Nẵng"
      }
    },
    "..."
  ]
}
```

---

### 13. GET /api/hotels/{id}/combo
Tạo gợi ý gói combo khách sạn kèm hoạt động ước tính cho một khách sạn cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `nights` (Query, Optional): `3`
  * `guests` (Query, Optional): `2`
  * `include_activities` (Query, Optional): `true`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel": {
    "id": 4947690,
    "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
    "star_rating": 5.0,
    "review_score": 8.9,
    "recommended_room": {
      "name": "Phòng Loại Sang 3 Người Lớn (Deluxe Room 3 Adults)",
      "price": 1425768.0,
      "room_view": "Hướng Thành phố"
    }
  },
  "activities": [
    {
      "id": 170,
      "title": "Private Transfer: Da Nang Airport to Hotel",
      "price_amount": 93192.0,
      "review_score": 5.0
    },
    {
      "id": 168,
      "title": "[Giảm 20%] Xe đưa đón riêng Hội An – Đà Nẵng và ngược lại",
      "price_amount": 263024.0,
      "review_score": 4.9
    },
    "..."
  ],
  "estimated_total": 3744316.0
}
```
*(Cách tính `estimated_total` = [Phòng Deluxe Room 3 Adults (1,425,768) * 2 đêm] + [Hoạt động 1 (93,192) * 2 khách] + [Hoạt động 2 (263,024) * 2 khách] + [Hoạt động 3 (90,174) * 2 khách] = 2,851,536 + 186,384 + 526,048 + 180,348 = 3,744,316.0 VND. Lưu ý: số đêm khách sạn thực tế bằng `nights - 1` = 2 đêm).*

---

### 14. GET /api/hotels/combo-suggest
Đề xuất gói combo khách sạn + hoạt động phù hợp với ngân sách tổng.

* **Tham số cần điền**:
  * `city` (Query, Required): `Đà Nẵng`
  * `budget_total` (Query, Required): `11000000` (Kiểu số thực)
  * `guests` (Query, Optional): `2`
  * `nights` (Query, Optional): `3`
  * `suitable_for` (Query, Optional): `Cặp đôi`
  * `min_occupancy` (Query, Optional): `2`
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotel": {
    "id": 4947690,
    "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
    "star_rating": 5.0,
    "review_score": 8.9,
    "suitable_for": [
      "Khách đi công tác",
      "Cặp đôi",
      "Khách du lịch một mình",
      "Gia đình có trẻ nhỏ",
      "Gia đình có thanh thiếu niên",
      "..."
    ],
    "recommended_room": {
      "name": "Phòng Loại Sang 3 Người Lớn (Deluxe Room 3 Adults)",
      "price": 1425768.0,
      "max_occupancy": 2
    }
  },
  "activities": [
    {
      "id": 170,
      "title": "Private Transfer: Da Nang Airport to Hotel",
      "description": "Travel from Da Nang airport to your hotel with a private transfer service. Your driver will meet you at the exit gate and assist with your luggage to the vehicle parked in the airport lot.\n\n- Optional",
      "price_amount": 93192.0,
      "review_score": 5.0
    },
    {
      "id": 168,
      "title": "[Giảm 20%] Xe đưa đón riêng Hội An – Đà Nẵng và ngược lại",
      "description": "Di chuyển thuận tiện giữa Hội An và Đà Nẵng với dịch vụ xe đưa đón riêng, phù hợp cho hành trình khám phá miền Trung.\n\n- Xe đón trong vòng 30 phút sau khi đặt\n- Tài xế giàu kinh nghiệm cùng hệ thống x",
      "price_amount": 263024.0,
      "review_score": 4.9
    },
    "..."
  ],
  "total_cost": 3744316.0,
  "remaining_budget": 7255684.0
}
```

---

### 15. GET /api/hotels/compare
So sánh thông tin của nhiều khách sạn song song.

* **Tham số cần điền**:
  * `ids` (Query, Required): `4947690,1985199` (So sánh Melia Đà Nẵng và Phú Quốc)
* **Kết quả trả về thực tế (Response)**:
```json
{
  "hotels": [
    {
      "id": 1985199,
      "name": "Melia Vinpearl Phú Quốc (Melia Vinpearl Phu Quoc)",
      "star_rating": 5.0,
      "is_luxury": false,
      "review_score": 8.6,
      "review_count": 3145,
      "reviews_detail": {
        "grades": {
          "location": 8.6,
          "cleanliness": 9.0,
          "service": 8.8,
          "facilities": 8.3,
          "value": 8.7
        }
      },
      "amenities": [
        "Ban công/sân hiên",
        "Bi-a",
        "Bàn tiếp tân [24 giờ]",
        "Bàn ăn",
        "Bãi biển riêng",
        "..."
      ],
      "rooms": {
        "min_price": 2777272.0
      },
      "images": [
        "https://pix8.agoda.net/hotelImages/1985199/0/1d3916b0c85240c95d9eab3f78b7d147.jpeg?ce=2&s=1024x768"
      ]
    },
    {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
      "star_rating": 5.0,
      "is_luxury": false,
      "review_score": 8.9,
      "review_count": 10921,
      "reviews_detail": {
        "grades": {
          "location": 9.3,
          "cleanliness": 9.7,
          "service": 9.5,
          "facilities": 9.0,
          "value": 9.4
        }
      },
      "amenities": [
        "Bàn tiếp tân [24 giờ]",
        "Bãi đỗ xe [gần bên]",
        "Bãi đỗ xe [miễn phí]",
        "Bãi đỗ xe [tại chỗ]",
        "Bình chữa cháy",
        "..."
      ],
      "rooms": {
        "min_price": 1425768.0
      },
      "images": [
        "https://pix8.agoda.net/hotelImages/4947690/0/bfb51fa3976c865ea22b803dd1b7ca78.jpeg?ce=2&s=1024x768"
      ]
    }
  ]
}
```

---

### 16. GET /api/hotels/{id}/similar
Gợi ý các khách sạn tương tự (cùng thành phố, cùng loại) nhưng rẻ hơn ít nhất 10%.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690` (Để xem gợi ý tương tự của khách sạn Đà Nẵng này).
  * *Lưu ý*: Vì trong thành phố Đà Nẵng chỉ có duy nhất 1 khách sạn Melia Vinpearl Riverfront, nên nếu gọi API này, hệ thống sẽ trả về danh sách gợi ý rỗng (không tìm thấy khách sạn khác cùng thành phố).
* **Kết quả trả về thực tế (Response cho ID 4947690 - Đà Nẵng)**:
```json
{
  "reference_hotel": {
    "id": 4947690,
    "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
    "review_score": 8.9,
    "amenities": [
      "Bàn tiếp tân [24 giờ]",
      "Bãi đỗ xe [gần bên]",
      "Bãi đỗ xe [miễn phí]",
      "Bãi đỗ xe [tại chỗ]",
      "Bình chữa cháy"
    ],
    "rooms": {
      "min_price": 1425768.0
    }
  },
  "similar_hotels": []
}
```

* **Kết quả trả về thực tế (Response cho ID 1986410 - Nha Trang/Cam Ranh)**:
Để mô tả khi tìm thấy đề xuất (chẳng hạn với Resort Meliá Vinpearl Cam Ranh, ID `1986410`):
```json
{
  "reference_hotel": {
    "id": 1986410,
    "name": "Khu nghỉ dưỡng bãi biển Meliá Vinpearl Cam Ranh (Meliá Vinpearl Cam Ranh Beach Resort)",
    "review_score": 8.9,
    "amenities": [
      "Ban công/sân hiên",
      "Bàn làm việc",
      "Bàn tiếp tân [24 giờ]",
      "Bàn ăn",
      "Bãi biển riêng"
    ],
    "rooms": {
      "min_price": 2071148.0
    }
  },
  "similar_hotels": [
    {
      "id": 263516,
      "name": "Vinpearl Luxury Nha Trang",
      "star_rating": 5.0,
      "review_score": 9.3,
      "amenities": [
        "Ban công/sân hiên",
        "Bàn làm việc",
        "Bàn tiếp tân [24 giờ]",
        "Bãi biển riêng",
        "Bãi đỗ xe [miễn phí]"
      ],
      "rooms": {
        "min_price": 1703580.0
      },
      "price_saving_pct": 18,
      "images": [
        "https://pix8.agoda.net/hotelImages/263516/0/971c2f65505bea02b4755cfd12606df7.jpeg?ce=2&s=1024x768"
      ]
    },
    {
      "id": 65153,
      "name": "Vinpearl Resort Nha Trang",
      "star_rating": 5.0,
      "review_score": 8.7,
      "amenities": [
        "Ban công/sân hiên",
        "Bàn làm việc",
        "Bàn tiếp tân [24 giờ]",
        "Báo động trực quan",
        "Bãi biển riêng"
      ],
      "rooms": {
        "min_price": 1333506.0
      },
      "price_saving_pct": 36,
      "images": [
        "https://pix8.agoda.net/hotelImages/65153/0/be0784e5018c37a577a275eeab890d4a.jpeg?ce=2&s=1024x768"
      ]
    }
  ]
}
```
