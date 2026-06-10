# Database & Graph Schema Summary - Post Deployment

**Date**: 2026-06-08
**Project**: DA10 - Travel Assistant (Hotel Knowledge Platform)

Tài liệu này tổng hợp cấu trúc dữ liệu hiện tại sau khi đã cập nhật SQL Schema và Ingestion Pipeline để hỗ trợ RAG (Retrieval-Augmented Generation) và Knowledge Graph với kiến trúc phân cấp (Hierarchical Architecture).

---

## 1. PostgreSQL Relational & Vector Schema

Hệ thống sử dụng PostgreSQL với extension `pgvector` để lưu trữ dữ liệu có cấu trúc và các đoạn văn bản đã được nhúng (embeddings).

### 1.1. Phân tích chi tiết các bảng quan hệ (Relational Tables)

#### 1.1.1. Bảng `hotels` - Thông tin cốt lõi
| Cột | Kiểu dữ liệu | Mô tả |
|:---|:---|:---|
| `id` | INTEGER (PK) | ID khách sạn từ Agoda |
| `name` | VARCHAR(255) | Tên khách sạn |
| `property_type` | VARCHAR(100) | Loại hình (Resort, Hotel,...) |
| `star_rating` | NUMERIC(3,1) | Hạng sao (0-5) |
| `is_luxury` | BOOLEAN | Đánh dấu hạng sang |
| `review_score` | NUMERIC(3,1) | Điểm đánh giá trung bình |
| `address` | TEXT | Địa chỉ chi tiết |
| `city` | VARCHAR(100) | Thành phố |
| `description` | TEXT | Mô tả tổng quan |

#### 1.1.2. Bảng `hotel_policies` - Chính sách
| Cột | Kiểu dữ liệu | Mô tả |
|:---|:---|:---|
| `hotel_id` | INTEGER (PK, FK) | Tham chiếu tới `hotels.id` |
| `check_in_from` | VARCHAR(50) | Giờ nhận phòng |
| `check_out_until` | VARCHAR(50) | Giờ trả phòng |
| `child_policy` | TEXT | Chính sách trẻ em |
| `pet_policy` | TEXT | Chính sách thú cưng |

#### 1.1.3. Bảng `reviews` - Đánh giá khách hàng
| Cột | Kiểu dữ liệu | Mô tả |
|:---|:---|:---|
| `hotel_id` | INTEGER (FK) | Tham chiếu tới `hotels.id` |
| `rating` | NUMERIC(3,1) | Điểm đánh giá của khách |
| `title` | TEXT | Tiêu đề đánh giá |
| `text` | TEXT | Nội dung đánh giá chi tiết |
| `positive_text` | TEXT | Điểm tích cực trích xuất |
| `negative_text` | TEXT | Điểm tiêu cực trích xuất |

#### 1.1.4. Bảng `rooms` - Loại phòng
| Cột | Kiểu dữ liệu | Mô tả |
|:---|:---|:---|
| `hotel_id` | INTEGER (FK) | Tham chiếu tới `hotels.id` |
| `name` | VARCHAR(255) | Tên loại phòng |
| `price` | NUMERIC(15,2) | Giá phòng |
| `room_size` | VARCHAR(50) | Diện tích |
| `max_occupancy` | INTEGER | Số khách tối đa |
| `bed_type` | VARCHAR(255) | Loại giường |
| `room_view` | VARCHAR(100) | Hướng nhìn |

#### 1.1.5. Bảng `amenities` & `nearby_places` (Metadata)
| Bảng | Cột quan trọng | Mô tả |
|:---|:---|:---|
| **amenities** | `name`, `category` | Tên tiện ích và nhóm phân loại |
| **nearby_places** | `name`, `type`, `distance_km` | Tên POI, loại POI và khoảng cách |

### 1.2. Bảng Vector (Vector DB)

| Tên bảng | Cột | Mô tả |
|:---|:---|:---|
| **text_chunks** | `hotel_id` | Tham chiếu tới `hotels.id` |
| | `chunk_type` | Loại chunk (overview, room, review,...) |
| | `content` | Nội dung văn bản gốc |
| | `embedding` | Vector 1024D (BGE-M3) |
| | `metadata` | JSONB chứa thông tin bổ trợ |

**Các loại Chunk (`chunk_type`):**
1. `hotel_overview`: Tổng quan khách sạn.
2. `description_section`: Các đoạn mô tả chi tiết (đã được chunking theo paragraph).
3. `policy`: Chi tiết chính sách.
4. `amenities_summary`: Tóm tắt tiện ích.
5. `nearby_places`: Danh sách địa điểm lân cận.
6. `room_detail`: Chi tiết từng loại phòng.
7. `activity_detail`: Chi tiết từng hoạt động.
8. `review_summary`: Tóm tắt các đánh giá tiêu biểu.
9. `review_aspect`: Chi tiết từng khía cạnh đánh giá (Vị trí, Phục vụ, v.v.)

---

## 2. Neo4j Knowledge Graph Schema

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
| **OFFERS_ACTIVITY** | Hotel | Activity | - |

---

## 3. Cơ chế đồng bộ và Ingestion

- **Tự động khởi tạo**: Script `ingest_data.py` gọi `init_schema()` để đảm bảo PostgreSQL schema luôn cập nhật từ `init_db.sql`.
- **Tự động xóa**: Thực hiện `TRUNCATE` PostgreSQL và `DETACH DELETE` Neo4j trước khi nạp mới để đảm bảo tính nhất quán.
- **ID Mapping**: 
  - Room/Activity ID được prefix bằng `hotel_id` để tránh xung đột giữa các khách sạn.
  - Place/Amenity/TravelerType sử dụng Concept ID từ Ontology (ví dụ: `LMK_VINWONDERS_NHA_TRANG`).
- **Hybrid Search**: 
  - PostgreSQL xử lý **Vector Search** (pgvector) và **Structured Filtering**.
  - Neo4j xử lý **Graph Traversal** và **Ontology Reasoning**.