# So sánh Kiến trúc Graph: Hiện tại vs. Đề xuất

Tài liệu này so sánh kiến trúc Knowledge Graph đang triển khai trong `ingest_data.py` với kiến trúc mục tiêu được đề xuất.

## 1. Bảng so sánh chi tiết

| Thành phần | Kiến trúc Hiện tại (Implemented) | Kiến trúc Đề xuất (Proposed) | Trạng thái |
|:---|:---|:---|:---|
| **Địa lý** | `city` là thuộc tính của node `Hotel` | `Hotel -[:LOCATED_IN]-> City` | ⚠️ Khác biệt |
| **Khu vực** | Chưa triển khai | `Hotel -[:IN_AREA]-> Area` | ❌ Thiếu |
| **Phòng** | `Hotel -[:HAS_ROOM]-> Room` | `Hotel -[:HAS_ROOM]-> Room` | ✅ Khớp |
| **Tiện nghi** | `Hotel -[:HAS_AMENITY]-> Amenity` (category là thuộc tính) | `Amenity -[:BELONGS_TO]-> AmenityCategory` | ⚠️ Khác biệt |
| **Địa điểm** | `Hotel -[:NEARBY]-> Place` (category là thuộc tính) | `Place -[:BELONGS_TO]-> PlaceCategory` | ⚠️ Khác biệt |
| **Đối tượng** | `Hotel -[:SUITABLE_FOR]-> TravelerType` | `Hotel -[:SUITABLE_FOR]-> TravelerType` | ✅ Khớp |
| **Đánh giá** | `Hotel -[:HAS_REVIEW_ASPECT]-> ReviewAspect` | `Hotel -[:HAS_REVIEW_ASPECT]-> ReviewAspect` | ✅ Khớp |
| **Hoạt động** | `Hotel -[:OFFERS_ACTIVITY]-> Activity` | `Hotel -[:OFFERS_ACTIVITY]-> Activity` | ✅ Khớp |
| **Chính sách** | Lưu ở PostgreSQL | `Hotel -[:HAS_POLICY]-> Policy` | ❌ Thiếu |
| **Dữ liệu thô** | Lưu ở PostgreSQL (`text_chunks`) | `Hotel -[:HAS_CHUNK]-> TextChunk` | ❌ Thiếu |

## 2. Phân tích các điểm khác biệt chính

### 2.1. Chuẩn hóa Node (Normalization)
- **Hiện tại**: Các thông tin như `City`, `Category` đang được lưu dưới dạng thuộc tính (Property) của node chính để tối ưu tốc độ truy vấn đơn giản.
- **Đề xuất**: Muốn tách các thông tin này thành các Node riêng biệt. Việc này giúp thực hiện các truy vấn suy luận tốt hơn (ví dụ: "Tìm các khách sạn cùng khu vực", "Tìm các tiện ích thuộc cùng nhóm giải trí").

### 2.2. Tích hợp Policy & TextChunk vào Graph
- **Hiện tại**: `Policy` và `TextChunk` (Vector) đang được ưu tiên lưu trữ tại PostgreSQL để phục vụ tìm kiếm Vector và lọc thuộc tính nhanh.
- **Đề xuất**: Đưa vào Graph sẽ giúp LLM có thể "du hành" trên đồ thị để lấy context thay vì chỉ dựa vào Vector Search. Tuy nhiên, việc lưu `TextChunk` (số lượng lớn) vào Neo4j cần cân nhắc về hiệu năng.

### 2.3. Phân cấp (Hierarchy)
- Kiến trúc đề xuất có tính phân cấp cao hơn (`Amenity -> Category`, `Place -> Category`), hỗ trợ tốt cho việc mở rộng Ontology sau này.

## 3. Đề xuất hành động (Action Plan)

Để đạt được kiến trúc đề xuất, cần thực hiện các thay đổi sau trong pipeline:
1. **Tách City/Area**: Tạo node `City` và `Area` riêng, tạo quan hệ `LOCATED_IN`.
2. **Tách Category**: Tạo node `AmenityCategory` và `PlaceCategory`, liên kết từ `Amenity`/`Place`.
3. **Bổ sung Policy Node**: Trích xuất các chính sách quan trọng thành node để truy vấn logic.
4. **Cân nhắc TextChunk**: Nếu cần RAG kết hợp Graph (GraphRAG), sẽ bổ sung node `TextChunk` liên kết với `Hotel`.