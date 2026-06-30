# PostgreSQL Database Schema - Detailed Column Analysis

**Date**: 2026-06-08  
**Project**: DA10 - Travel Assistant (Hotel Knowledge Platform)

Tài liệu này phân tích chi tiết từng cột (field) trong mỗi bảng PostgreSQL, bao gồm kiểu dữ liệu, constraint, và mục đích sử dụng.

---

## 1. Bảng `hotels` - Thông tin cốt lõi khách sạn

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | INTEGER | PRIMARY KEY | Định danh duy nhất của khách sạn từ Agoda | `625168` |
| `name` | VARCHAR(255) | NOT NULL | Tên khách sạn | `Vinpearl Resort & Spa Phú Quốc` |
| `property_type` | VARCHAR(100) | - | Loại hình bất động sản | `Resort`, `Hotel`, `Villa` |
| `accommodation_type` | VARCHAR(100) | - | Loại chỗ ở | `Hotel`, `Serviced Apartment` |
| `star_rating` | NUMERIC(3,1) | - | Hạng sao (0-5) | `5.0` |
| `is_luxury` | BOOLEAN | DEFAULT FALSE | Cờ đánh dấu khách sạn sang trọng | `true` / `false` |
| `review_score` | NUMERIC(3,1) | - | Điểm đánh giá trung bình (0-10) | `8.5` |
| `review_count` | INTEGER | DEFAULT 0 | Tổng số đánh giá | `1200` |
| `address` | TEXT | - | Địa chỉ chi tiết | `Bãi Dài, Phú Quốc` |
| `city` | VARCHAR(100) | - | Thành phố (để join với City node trong Neo4j) | `Phú Quốc` |
| `city_id` | INTEGER | - | ID của thành phố | `1001` |
| `area` | VARCHAR(100) | - | Khu vực trong thành phố | `Bãi Dài` |
| `country` | VARCHAR(100) | - | Quốc gia | `Vietnam` |
| `latitude` | DOUBLE PRECISION | - | Tọa độ vĩ độ | `10.2167` |
| `longitude` | DOUBLE PRECISION | - | Tọa độ kinh độ | `103.8833` |
| `description` | TEXT | - | Mô tả dài về khách sạn | `Khu nghỉ dưỡng 5 sao nằm bên bờ biển...` |
| `source_url` | TEXT | - | URL nguồn từ Agoda | `https://agoda.com/...` |

**Constraints**: `PRIMARY KEY (id)`  
**Indexes**: `idx_hotels_city`, `idx_hotels_rating`

---

## 2. Bảng `hotel_images` - Quản lý hình ảnh khách sạn

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tự động của hình ảnh | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `url` | TEXT | NOT NULL | URL của hình ảnh | `https://images.agoda.com/...` |
| `is_primary` | BOOLEAN | DEFAULT FALSE | Cờ hình ảnh chính (thumbnail) | `true` / `false` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`

---

## 3. Bảng `hotel_policies` - Chính sách khách sạn

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `hotel_id` | INTEGER | PRIMARY KEY, FOREIGN KEY | Tham chiếu duy nhất đến `hotels(id)` | `625168` |
| `check_in_from` | VARCHAR(50) | - | Thời gian nhận phòng | `14:00` |
| `check_out_until` | VARCHAR(50) | - | Thời gian trả phòng | `12:00` |
| `service_fee_pct` | NUMERIC(5,2) | DEFAULT 0.00 | Phần trăm phí dịch vụ | `5.00` |
| `child_policy` | TEXT | - | Chính sách về trẻ em | `Trẻ dưới 12 tuổi miễn phí` |
| `pet_policy` | TEXT | - | Chính sách về thú cưng | `Thú cưng được phép` |
| `deposit_required` | BOOLEAN | DEFAULT FALSE | Cờ yêu cầu tiền cọc | `true` / `false` |
| `policy_notes` | TEXT[] | - | Mảng các ghi chú chính sách | `['No smoking', 'Quiet hours 22:00']` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`

---

## 4. Bảng `reviews` - Đánh giá chi tiết từ khách hàng

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tự động của đánh giá | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `reviewer_name` | VARCHAR(100) | - | Tên người đánh giá | `John Doe` |
| `reviewer_country` | VARCHAR(100) | - | Quốc gia của người đánh giá | `United States` |
| `rating` | NUMERIC(3,1) | - | Điểm đánh giá (1-10) | `8.5` |
| `review_date` | DATE | - | Ngày đánh giá | `2026-06-01` |
| `title` | TEXT | - | Tiêu đề đánh giá | `Great location and friendly staff` |
| `text` | TEXT | NOT NULL | Nội dung chi tiết đánh giá | `The resort is amazing...` |
| `positive_text` | TEXT | - | Các điểm tích cực được trích xuất | `Beautiful beach, good food` |
| `negative_text` | TEXT | - | Các điểm tiêu cực được trích xuất | `Expensive prices, slow wifi` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_reviews_hotel_rating`

---

## 5. Bảng `hotel_suitability` - Phân loại đối tượng khách hàng

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tự động | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `suitable_for_tag` | VARCHAR(100) | NOT NULL | Thẻ đối tượng khách hàng | `Gia đình`, `Cặp đôi`, `Công tác` |
| `mention_count` | INTEGER | - | Số lần được nhắc đến | `145` |
| `score` | NUMERIC(4,2) | - | Điểm phù hợp (0-100) | `85.50` |

**Unique Constraint**: `UNIQUE(hotel_id, suitable_for_tag)`  
**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_suitability_tag`

---

## 6. Bảng `review_aspects` - Khía cạnh đánh giá

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tự động | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `aspect_name` | VARCHAR(150) | NOT NULL | Tên khía cạnh được đánh giá | `Vị trí`, `Phục vụ`, `Sạch sẽ` |
| `mentioned` | INTEGER | - | Số lần khía cạnh được nhắc | `280` |
| `positive_pct` | NUMERIC(5,2) | - | Phần trăm đánh giá tích cực | `78.50` |

**Unique Constraint**: `UNIQUE(hotel_id, aspect_name)`  
**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_review_aspects_hotel`

---

## 7. Bảng `review_grades` - Điểm đánh giá chi tiết theo tiêu chí

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tự động | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `grade_name` | VARCHAR(150) | NOT NULL | Tên tiêu chí đánh giá | `Vị trí`, `Sạch sẽ`, `Giá trị tiền` |
| `grade_score` | NUMERIC(3,1) | - | Điểm đánh giá tiêu chí (0-10) | `8.5` |

**Unique Constraint**: `UNIQUE(hotel_id, grade_name)`  
**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**JSON Mapping**: Từ `reviews_detail.grades[].name` và `reviews_detail.grades[].score`

---

## 8. Bảng `amenity_categories` - Danh mục nhóm tiện ích

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID danh mục | `1`, `2`, ... |
| `name` | TEXT | UNIQUE, NOT NULL | Tên danh mục tiện ích | `Có trong tất cả phòng`, `Dịch vụ và tiện nghi` |

---

## 9. Bảng `amenities` - Danh sách các tiện ích hệ thống

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID tiện ích | `1`, `2`, ... |
| `name` | VARCHAR(150) | UNIQUE, NOT NULL | Tên tiện ích | `Nước đóng chai miễn phí`, `WiFi miễn phí` |
| `category` | VARCHAR(100) | - | Danh mục text (denormalized từ `amenity_categories`) | `Có trong tất cả phòng` |
| `category_id` | INTEGER | FOREIGN KEY | Tham chiếu đến `amenity_categories(id)` | `5` |

**Foreign Key**: `REFERENCES amenity_categories(id)`

---

## 10. Bảng `hotel_amenities` - Bảng trung gian gán tiện ích

| Cột | Kiểu dữ liệu | Constraint | Mô tả |
|:---|:---|:---|:---|
| `hotel_id` | INTEGER | PRIMARY KEY (part 1), FOREIGN KEY | Tham chiếu đến `hotels(id)` |
| `amenity_id` | INTEGER | PRIMARY KEY (part 2), FOREIGN KEY | Tham chiếu đến `amenities(id)` |

**Primary Key**: `(hotel_id, amenity_id)` - Composite key  
**Foreign Keys**: `REFERENCES hotels(id) ON DELETE CASCADE`, `REFERENCES amenities(id) ON DELETE CASCADE`

---

## 11. Bảng `rooms` - Chi tiết các loại phòng

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID phòng | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `room_type_id` | BIGINT | - | ID loại phòng từ Agoda API | `123456789` |
| `name` | VARCHAR(255) | NOT NULL | Tên phòng | `Deluxe Sea View Room` |
| `price` | NUMERIC(15,2) | - | Giá phòng mỗi đêm (VND) | `2500000.00` |
| `room_size` | VARCHAR(50) | - | Diện tích phòng | `50 m²` |
| `max_occupancy` | INTEGER | - | Số lượng khách tối đa | `4` |
| `bed_type` | VARCHAR(255) | - | Loại giường | `1 King Bed`, `2 Twin Beds` |
| `room_view` | VARCHAR(100) | - | Tầm nhìn từ phòng | `Sea View`, `Garden View` |
| `room_amenities` | TEXT[] | - | Mảng tiện ích trong phòng | `['AC', 'TV', 'Balcony']` |
| `images` | TEXT[] | - | Mảng URL ảnh phòng | `['https://...', 'https://...']` |
| `review_score` | NUMERIC(3,1) | - | Điểm đánh giá phòng | `8.7` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_rooms_hotel_id`, `idx_rooms_price`

---

## 12. Bảng `place_categories` - Danh mục nhóm địa điểm

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID danh mục | `1`, `2`, ... |
| `name` | TEXT | UNIQUE, NOT NULL | Tên danh mục | `Bãi biển`, `Sân bay`, `Nhà hàng` |

---

## 13. Bảng `nearby_places` - Các địa điểm lân cận (POI)

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID địa điểm | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `name` | VARCHAR(255) | NOT NULL | Tên địa điểm | `Vinwonders Phú Quốc` |
| `type` | VARCHAR(100) | - | Loại địa điểm (denormalized từ `place_categories`) | `Khu vui chơi` |
| `category_id` | INTEGER | FOREIGN KEY | Tham chiếu đến `place_categories(id)` | `8` |
| `distance_km` | NUMERIC(6,2) | - | Khoảng cách từ khách sạn (km) | `5.50` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`, `REFERENCES place_categories(id)`  
**Indexes**: `idx_nearby_places_hotel_id`

---

## 14. Bảng `activities` - Hoạt động giải trí/tour

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID hoạt động | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `activity_id` | BIGINT | - | ID hoạt động từ Agoda API | `987654321` |
| `title` | VARCHAR(255) | NOT NULL | Tên hoạt động | `Phiêu lưu biển` |
| `description` | TEXT | - | Mô tả chi tiết | `Tham gia tour biển 4 tiếng...` |
| `price_amount` | NUMERIC(15,2) | - | Giá vé (VND) | `500000.00` |
| `review_score` | NUMERIC(3,1) | - | Điểm đánh giá hoạt động | `9.0` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_activities_hotel_id`

---

## 15. Bảng `text_chunks` - Lưu trữ Vector Embeddings

| Cột | Kiểu dữ liệu | Constraint | Mô tả | Ví dụ |
|:---|:---|:---|:---|:---|
| `id` | SERIAL | PRIMARY KEY | ID chunk | `1`, `2`, ... |
| `hotel_id` | INTEGER | FOREIGN KEY, NOT NULL | Tham chiếu đến `hotels(id)` | `625168` |
| `chunk_type` | VARCHAR(50) | NOT NULL | Loại chunk cho RAG retrieval | `hotel_overview`, `room_detail`, `activity_detail`, `review_summary`, `review_aspect`, `review_grade` |
| `content` | TEXT | NOT NULL | Nội dung văn bản | `[Khách sạn]: Vinpearl... \| [Mô tả]: ...` |
| `embedding` | VECTOR(1024) | - | Vector embedding 1024 chiều (BGE-M3) | `[0.12, -0.05, ...]` |
| `metadata` | JSONB | NOT NULL | Metadata bổ sung (JSON) | `{"city": "Phú Quốc", "price": 2500000}` |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Thời gian tạo | `2026-06-08 10:00:00` |

**Foreign Key**: `REFERENCES hotels(id) ON DELETE CASCADE`  
**Indexes**: `idx_text_chunks_embedding` (HNSW), `idx_text_chunks_type`, `idx_text_chunks_metadata` (GIN)

---

## JSON Mapping Reference - Từ Agoda Data tới PostgreSQL

### Hotels Table - Mapping từ Root Level

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `id` | `$.id` | Integer | Agoda Hotel ID |
| `name` | `$.name` | String | Tên khách sạn chính thức |
| `property_type` | `$.property_type` | String | Ví dụ: "Resort", "Hotel" |
| `accommodation_type` | `$.accommodation_type` | String | Ví dụ: "Hotel", "Serviced Apartment" |
| `star_rating` | `$.star_rating` | Numeric | Từ 0-5 sao |
| `is_luxury` | `$.is_luxury` | Boolean | Cờ khách sạn sang trọng |
| `review_score` | `$.review_score` | Numeric | Điểm đánh giá trung bình (0-10) |
| `review_count` | `$.review_count` | Integer | Tổng số lượng đánh giá |
| `address` | `$.address` | String | Địa chỉ chi tiết |
| `city` | `$.city` | String | Tên thành phố |
| `city_id` | `$.city_id` | Integer | ID thành phố |
| `area` | `$.area` | String | Khu vực trong thành phố |
| `country` | `$.country` | String | Quốc gia |
| `latitude` | `$.latitude` | Numeric | Tọa độ vĩ độ |
| `longitude` | `$.longitude` | Numeric | Tọa độ kinh độ |
| `description` | `$.description` | String | Mô tả dài về khách sạn |
| `source_url` | `$.source_url` | String | URL Agoda |

### Hotel Images - Mapping từ `images` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `url` | `$.images[].url` | String | URL hình ảnh |
| `is_primary` | `$.images[].is_primary` | Boolean | Hình ảnh chính hay không |

### Hotel Policies - Mapping từ `useful_info` Object

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `check_in_from` | `$.useful_info.check_in_from` | String | Thời gian nhận phòng (HH:MM) |
| `check_out_until` | `$.useful_info.check_out_until` | String | Thời gian trả phòng (HH:MM) |
| `service_fee_pct` | `$.useful_info.service_fee_pct` | Numeric | Phần trăm phí dịch vụ |
| `child_policy` | `$.useful_info.child_policy` | String | Chính sách trẻ em |
| `pet_policy` | `$.useful_info.pet_policy` | String | Chính sách thú cưng |
| `deposit_required` | `$.useful_info.deposit_required` | Boolean | Cần tiền cọc hay không |
| `policy_notes` | `$.useful_info.policy_notes[]` | String Array | Mảng ghi chú chính sách |

### Reviews - Mapping từ `reviews_detail.reviews` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `reviewer_name` | `$.reviews_detail.reviews[].reviewer_name` | String | Tên người đánh giá |
| `reviewer_country` | `$.reviews_detail.reviews[].reviewer_country` | String | Quốc gia người đánh giá |
| `rating` | `$.reviews_detail.reviews[].rating` | Numeric | Điểm đánh giá (1-10) |
| `review_date` | `$.reviews_detail.reviews[].review_date` | Date | Ngày đánh giá |
| `title` | `$.reviews_detail.reviews[].title` | String | Tiêu đề đánh giá |
| `text` | `$.reviews_detail.reviews[].text` | String | Nội dung chi tiết |
| `positive_text` | `$.reviews_detail.reviews[].positive_text` | String | Điểm tích cực được trích xuất |
| `negative_text` | `$.reviews_detail.reviews[].negative_text` | String | Điểm tiêu cực được trích xuất |

### Review Aspects - Mapping từ `reviews_detail.tags` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `aspect_name` | `$.reviews_detail.tags[].tag` hoặc `.name` | String | Tên khía cạnh đánh giá |
| `mentioned` | `$.reviews_detail.tags[].mentioned` | Integer | Số lần được nhắc |
| `positive_pct` | `$.reviews_detail.tags[].positive_pct` | Numeric | % đánh giá tích cực |

### Review Grades - Mapping từ `reviews_detail.grades` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `grade_name` | `$.reviews_detail.grades[].name` | String | Tên tiêu chí đánh giá |
| `grade_score` | `$.reviews_detail.grades[].score` | Numeric | Điểm tiêu chí (0-10) |

### Hotel Suitability - Mapping từ `suitable_for` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `suitable_for_tag` | `$.suitable_for[].tag` | String | Thẻ đối tượng khách (Gia đình, Cặp đôi, v.v.) |
| `source` | Hardcoded | String | `suitable_for` |
| `mention_count` | `$.suitable_for[].mention_count` | Integer | Số lần được nhắc |
| `score` | `$.suitable_for[].score` | Numeric | Điểm phù hợp (0-100) |

### Amenities - Mapping từ `amenities` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `amenity_id` (hotel_amenities) | `$.amenities[].id` | Integer | Agoda Amenity ID |
| `amenity_name` | `$.amenities[].name` | String | Tên tiện ích |
| `category` | `$.amenities[].category` | String | Danh mục tiện ích |

### Rooms - Mapping từ `rooms` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `room_type_id` | `$.rooms[].room_type_id` | BigInt | ID loại phòng từ Agoda |
| `name` | `$.rooms[].name` | String | Tên loại phòng |
| `price` | `$.rooms[].price` | Numeric | Giá phòng mỗi đêm |
| `room_size` | `$.rooms[].room_size` | String | Diện tích phòng (m²) |
| `max_occupancy` | `$.rooms[].max_occupancy` | Integer | Số khách tối đa |
| `bed_type` | `$.rooms[].bed_type` | String | Loại giường |
| `room_view` | `$.rooms[].room_view` | String | Tầm nhìn (Sea View, Garden View) |
| `room_amenities` | `$.rooms[].amenities[]` | String Array | Mảng tiện ích trong phòng |
| `images` | `$.rooms[].images[]` | String Array | Mảng URL ảnh phòng |
| `review_score` | `$.rooms[].review_score` | Numeric | Điểm đánh giá phòng |

### Nearby Places - Mapping từ `nearby_places` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `name` | `$.nearby_places[].name` | String | Tên địa điểm |
| `type` | `$.nearby_places[].type` | String | Loại địa điểm |
| `distance_km` | `$.nearby_places[].distance_km` | Numeric | Khoảng cách từ khách sạn |

### Activities - Mapping từ `activities` Array

| PostgreSQL Column | JSON Path | Kiểu dữ liệu JSON | Ghi chú |
|:---|:---|:---|:---|
| `hotel_id` | `$.id` | Integer | Reference từ root |
| `activity_id` | `$.activities[].activity_id` | BigInt | ID hoạt động từ Agoda |
| `title` | `$.activities[].title` | String | Tên hoạt động |
| `description` | `$.activities[].description` | String | Mô tả chi tiết |
| `price_amount` | `$.activities[].price_amount` | Numeric | Giá vé |
| `review_score` | `$.activities[].review_score` | Numeric | Điểm đánh giá hoạt động |

### Text Chunks - Mapping từ Derived Content

| Trường | Nguồn JSON | Mô tả |
|:---|:---|:---|
| `hotel_overview` | Root level (name, description, star_rating, review_score) | Tóm tắt khách sạn |
| `room_detail` | `$.rooms[].name, price, room_size, bed_type, room_view` | Chi tiết loại phòng |
| `activity_detail` | `$.activities[].title, description, price_amount` | Chi tiết hoạt động |
| `review_summary` | Top 5 từ `$.reviews_detail.reviews[]` | Tóm tắt đánh giá |
| `review_aspect` | `$.reviews_detail.tags[]` | Khía cạnh đánh giá |
| `review_grade` | `$.reviews_detail.grades[]` | Điểm tiêu chí đánh giá |

---

## Neo4j Knowledge Graph Schema

Cấu trúc đồ thị giúp truy vấn các mối quan hệ phức tạp và thực hiện suy luận (Reasoning) dựa trên Ontology.

### 2.1. Các loại Node (Labels)

| Node Label | Thuộc tính chính | Mô tả |
|:---|:---|:---|
| **Hotel** | `id`, `name`, `star_rating`, `review_score`, `city` | Node trung tâm |
| **City** | `id`, `name` | Thành phố (Nha Trang, Phú Quốc, v.v.) |
| **Area** | `id`, `name` | Khu vực trong thành phố (Bãi Dài, Hòn Tre, v.v.) |
| **Room** | `id`, `name`, `price`, `max_occupancy`, `room_view` | Các loại phòng của khách sạn |
| **Place** | `id`, `name` | Địa điểm lân cận (LMK_...) |
| **PlaceCategory** | `id`, `name` | Nhóm địa điểm (Bãi biển, Sân bay, v.v.) |
| **Amenity** | `id`, `name` | Tiện ích (AMEN_...) |
| **AmenityCategory** | `id`, `name` | Nhóm tiện ích (Tiện nghi phòng, Giải trí, v.v.) |
| **TravelerType** | `id`, `name` | Đối tượng phù hợp (PURPOSE_...) |
| **ReviewAspect** | `id`, `name` | Khía cạnh đánh giá (REVASP_...) |
| **ReviewGrade** | `id`, `name` | Tiêu chí đánh giá (GRADE_...) |
| **Activity** | `id`, `title`, `price`, `review_score` | Hoạt động giải trí |

### 2.2. Các mối quan hệ (Relationships)

| Mối quan hệ | Từ Node | Đến Node | Thuộc tính |
|:---|:---|:---|:---|
| **LOCATED_IN** | Hotel | City | - |
| **IN_AREA** | Hotel | Area | - |
| **BELONGS_TO_CITY** | Area | City | - |
| **HAS_ROOM** | Hotel | Room | - |
| **NEARBY** | Hotel | Place | `distance_km` |
| **BELONGS_TO** | Place | PlaceCategory | - |
| **HAS_AMENITY** | Hotel | Amenity | - |
| **BELONGS_TO** | Amenity | AmenityCategory | - |
| **SUITABLE_FOR** | Hotel | TravelerType | - |
| **HAS_REVIEW_ASPECT** | Hotel | ReviewAspect | `mentioned`, `positive_pct` |
| **HAS_REVIEW_GRADE** | Hotel | ReviewGrade | `grade_score` |
| **OFFERS_ACTIVITY** | Hotel | Activity | - |

---

## Cơ chế đồng bộ và Ingestion

- **Tự động khởi tạo**: Script `ingest_data.py` gọi `init_schema()` để đảm bảo PostgreSQL schema luôn cập nhật từ `init_db.sql`.
- **Tự động xóa**: Thực hiện `TRUNCATE` PostgreSQL và `DETACH DELETE` Neo4j trước khi nạp mới để đảm bảo tính nhất quán.
- **ID