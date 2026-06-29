# Refined Graph & Table Design - Bỏ `TextChunk` khỏi Neo4j

**Ngày**: 2026-06-08  
**Mục tiêu**: Điều chỉnh kiến trúc Graph/Table dựa trên dữ liệu mẫu Agoda, cân nhắc loại bỏ node `TextChunk` khỏi Neo4j để phù hợp hơn với vai trò của từng hệ lưu trữ.

---

## 1. Kết luận thiết kế

Nên **bỏ node `TextChunk` khỏi Neo4j**.

`TextChunk` nên được giữ ở **PostgreSQL/pgvector** và/hoặc index sang **Elasticsearch** vì đây là dữ liệu phục vụ retrieval văn bản/vector, không phải thực thể tri thức ổn định trong graph.

Kiến trúc phù hợp nhất là:

```text
PostgreSQL
├── Lưu dữ liệu chuẩn hóa dạng bảng
├── Lưu text_chunks + embedding cho Vector Search
└── Là nguồn dữ liệu chính cho filtering/ranking

Elasticsearch
└── Index text_chunks.content cho BM25 / keyword retrieval

Neo4j
├── Lưu thực thể tri thức có quan hệ rõ ràng
├── Hỗ trợ ontology reasoning / graph traversal
└── Không lưu TextChunk để tránh graph bị phình và trùng dữ liệu
```

---

## 2. Vì sao nên bỏ `TextChunk` khỏi Neo4j?

| Tiêu chí | Có `TextChunk` trong Neo4j | Bỏ `TextChunk` khỏi Neo4j |
|:---|:---|:---|
| Mục đích dữ liệu | Text retrieval / vector retrieval | Graph reasoning / entity relation |
| Hiệu năng | Dễ làm graph phình nhanh | Graph gọn, traversal nhanh |
| Trùng dữ liệu | Trùng với PostgreSQL `text_chunks` và Elasticsearch | Không trùng |
| Cập nhật dữ liệu | Nhiều chunk phải sync sang Neo4j | Chỉ sync entity/relationship |
| Phù hợp Neo4j | Thấp | Cao |
| Phù hợp RAG | Có thể dùng nhưng không tối ưu | Tốt hơn: Graph lấy entity, Vector lấy context |

**Kết luận**:  
`TextChunk` là artifact của pipeline RAG, không phải entity domain như `Hotel`, `Room`, `Amenity`, `Place`. Vì vậy nên để trong PostgreSQL/pgvector.

---

## 3. Graph Schema đề xuất sau khi bỏ `TextChunk`

Dựa trên data mẫu `hotel_1994212_vinpearl-hoi-an-villas.json`, graph nên tập trung vào các thực thể có quan hệ rõ ràng:

```text
Hotel
├── LOCATED_IN -> City
├── IN_AREA -> Area
├── HAS_ROOM -> Room
├── HAS_AMENITY -> Amenity -> AmenityCategory
├── NEARBY {distance_km} -> Place -> PlaceCategory
├── SUITABLE_FOR -> TravelerType
├── HAS_REVIEW_ASPECT {mentioned, positive_pct} -> ReviewAspect
└── OFFERS_ACTIVITY -> Activity
```

Có thể bổ sung quan hệ:

```text
Area -[:BELONGS_TO_CITY]-> City
```

Không khuyến nghị:

```text
Hotel -[:HAS_CHUNK]-> TextChunk
```

Có thể cân nhắc nhưng không bắt buộc:

```text
Hotel -[:HAS_POLICY]-> Policy
```

Với dữ liệu hiện tại, `Policy` nên giữ ở PostgreSQL vì chính sách chủ yếu dùng để filter/trả lời trực tiếp, không có nhiều quan hệ phức tạp cần graph traversal.

---

## 4. Mapping từ dữ liệu mẫu sang Graph Node

### 4.1. Hotel

Nguồn dữ liệu mẫu:

```json
{
  "hotel_id": 1994212,
  "name": "Vinpearl Hoi An Villas",
  "property_type": "Hotel",
  "accommodation_type": "Resort",
  "star_rating": 5.0,
  "review_score": 7.8,
  "review_count": 15,
  "address": "Cửa Đại, Hội An, Quảng Nam, Việt Nam...",
  "area": "Cửa Đại",
  "city": "Hội An",
  "country": "Việt Nam",
  "latitude": 15.88068675994873,
  "longitude": 108.38843536376953
}
```

Node:

```cypher
(:Hotel {
  id: 1994212,
  name: "Vinpearl Hoi An Villas",
  property_type: "Hotel",
  accommodation_type: "Resort",
  star_rating: 5.0,
  review_score: 7.8,
  review_count: 15,
  latitude: 15.88068675994873,
  longitude: 108.38843536376953
})
```

### 4.2. City

Nguồn:

```json
"city": "Hội An"
```

Node:

```cypher
(:City {
  id: "CITY_HOI_AN",
  name: "Hội An"
})
```

Relationship:

```cypher
(:Hotel)-[:LOCATED_IN]->(:City)
```

### 4.3. Area

Nguồn:

```json
"area": "Cửa Đại"
```

Node:

```cypher
(:Area {
  id: "AREA_HOI_AN_CUA_DAI",
  name: "Cửa Đại"
})
```

Relationships:

```cypher
(:Hotel)-[:IN_AREA]->(:Area)
(:Area)-[:BELONGS_TO_CITY]->(:City)
```

### 4.4. Room

Nguồn:

```json
{
  "room_type_id": 11305152,
  "name": "Villa 3 phòng ngủ hướng biển (3-Bedroom Ocean View Villa)",
  "max_occupancy": 6,
  "bed_type": "1 giường lớn / 1 giường lớn / 2 giường đơn",
  "room_view": "Hướng Đại dương",
  "price_per_night": 3820457.0,
  "review_score": 8.0
}
```

Node:

```cypher
(:Room {
  id: "room_1994212_11305152",
  room_type_id: 11305152,
  name: "Villa 3 phòng ngủ hướng biển (3-Bedroom Ocean View Villa)",
  max_occupancy: 6,
  bed_type: "1 giường lớn / 1 giường lớn / 2 giường đơn",
  room_view: "Hướng Đại dương",
  price: 3820457.0,
  review_score: 8.0
})
```

Relationship:

```cypher
(:Hotel)-[:HAS_ROOM]->(:Room)
```

### 4.5. Amenity và AmenityCategory

Data mẫu có `amenity_groups`, rất phù hợp để tạo node category:

```json
"amenity_groups": {
  "Thư giãn & Vui chơi giải trí": [
    "Bể bơi",
    "Mát-xa",
    "Phòng tập",
    "Spa"
  ],
  "Ăn uống": [
    "Bữa sáng [tự chọn]",
    "Nhà hàng",
    "Quán bar"
  ]
}
```

Nodes:

```cypher
(:Amenity {id: "AMEN_BE_BOI", name: "Bể bơi"})
(:AmenityCategory {id: "AMENCAT_THU_GIAN_VUI_CHOI_GIAI_TRI", name: "Thư giãn & Vui chơi giải trí"})
```

Relationships:

```cypher
(:Hotel)-[:HAS_AMENITY]->(:Amenity)
(:Amenity)-[:BELONGS_TO]->(:AmenityCategory)
```

### 4.6. Place và PlaceCategory

Nguồn:

```json
{
  "name": "Bãi biển Cửa Đại",
  "type": "Bãi Biển",
  "distance_km": 2.39
}
```

Nodes:

```cypher
(:Place {
  id: "PLACE_BAI_BIEN_CUA_DAI",
  name: "Bãi biển Cửa Đại"
})

(:PlaceCategory {
  id: "PLACECAT_BAI_BIEN",
  name: "Bãi Biển"
})
```

Relationships:

```cypher
(:Hotel)-[:NEARBY {distance_km: 2.39}]->(:Place)
(:Place)-[:BELONGS_TO]->(:PlaceCategory)
```

### 4.7. TravelerType

Nguồn có thể lấy từ:

- `suitable_for`
- `reviews_detail.demographics`

Ví dụ trong data mẫu:

```json
"demographics": [
  {
    "name": "Cặp đôi",
    "count": 2,
    "score": 6.0
  },
  {
    "name": "Gia đình có trẻ nhỏ",
    "count": 1,
    "score": 8.4
  }
]
```

Node:

```cypher
(:TravelerType {
  id: "PURPOSE_ROMANTIC",
  name: "Cặp đôi"
})
```

Relationship:

```cypher
(:Hotel)-[:SUITABLE_FOR {
  count: 2,
  score: 6.0
}]->(:TravelerType)
```

Nếu dữ liệu `suitable_for` đã có sẵn, vẫn nên dùng làm nguồn chính. `reviews_detail.demographics` có thể bổ sung thuộc tính `count`, `score`.

### 4.8. ReviewAspect

Nguồn hiện tại:

```json
"reviews_detail": {
  "tags": []
}
```

Nếu `tags` có dữ liệu:

```json
{
  "tag": "Vị trí",
  "mentioned": 20,
  "positive_pct": 85
}
```

Node:

```cypher
(:ReviewAspect {
  id: "REVASP_VI_TRI",
  name: "Vị trí"
})
```

Relationship:

```cypher
(:Hotel)-[:HAS_REVIEW_ASPECT {
  mentioned: 20,
  positive_pct: 85
}]->(:ReviewAspect)
```

### 4.9. Activity

Nếu data có `activities`:

```cypher
(:Hotel)-[:OFFERS_ACTIVITY]->(:Activity)
```

Node:

```cypher
(:Activity {
  id: "act_1994212_xxx",
  title: "...",
  price: 0,
  review_score: 0
})
```

---

## 5. PostgreSQL Table Design đề xuất

PostgreSQL vẫn là nguồn dữ liệu chính, bao gồm cả dữ liệu structured và vector retrieval.

### 5.1. Bảng lõi

| Table | Vai trò |
|:---|:---|
| `hotels` | Metadata chính của khách sạn |
| `hotel_images` | Ảnh khách sạn |
| `hotel_policies` | Chính sách check-in/out, trẻ em, thú cưng, phí |
| `rooms` | Loại phòng, giá, sức chứa, tiện nghi phòng |
| `amenities` | Danh mục tiện ích |
| `amenity_categories` | Nhóm tiện ích từ `amenity_groups` |
| `hotel_amenities` | Mapping khách sạn - tiện ích |
| `nearby_places` | Địa điểm gần khách sạn |
| `place_categories` | Nhóm địa điểm từ `nearby_places.type` |
| `activities` | Hoạt động/tour |
| `reviews` | Review chi tiết |
| `review_aspects` | Aspect sentiment |
| `hotel_suitability` | Đối tượng phù hợp |
| `text_chunks` | Chunk văn bản + embedding cho RAG |

### 5.2. Bảng nên bổ sung so với hiện tại

#### `amenity_categories`

```sql
CREATE TABLE IF NOT EXISTS amenity_categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);
```

#### Cập nhật `amenities`

```sql
ALTER TABLE amenities
ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES amenity_categories(id);
```

Hiện tại `amenities.category` đang lưu dạng text. Có thể giữ `category` để backward compatibility, nhưng nên thêm `category_id` để chuẩn hóa.

#### `place_categories`

```sql
CREATE TABLE IF NOT EXISTS place_categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);
```

#### Cập nhật `nearby_places`

```sql
ALTER TABLE nearby_places
ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES place_categories(id);
```

Hiện tại `nearby_places.type` đang lưu category dạng text. Có thể giữ `type`, nhưng nên thêm `category_id`.

#### Cập nhật `hotels`

Data mẫu có `area`, `country`, `property_type`, `accommodation_type`, `city_id`.

```sql
ALTER TABLE hotels
ADD COLUMN IF NOT EXISTS area TEXT,
ADD COLUMN IF NOT EXISTS country TEXT,
ADD COLUMN IF NOT EXISTS property_type TEXT,
ADD COLUMN IF NOT EXISTS city_id INTEGER;
```

#### `hotel_suitability` nên bổ sung dữ liệu từ demographics

```sql
ALTER TABLE hotel_suitability
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'suitable_for',
ADD COLUMN IF NOT EXISTS mention_count INTEGER,
ADD COLUMN IF NOT EXISTS score NUMERIC(4,2);
```

---

## 6. `text_chunks` vẫn giữ trong PostgreSQL

Không đưa vào Neo4j, nhưng vẫn rất cần trong RAG.

```text
text_chunks
├── hotel_id
├── chunk_type
├── content
├── embedding vector(1024)
└── metadata JSONB
```

Các loại chunk nên giữ:

| chunk_type | Nguồn |
|:---|:---|
| `hotel_overview` | `name`, `star_rating`, `address`, `description` |
| `description_section` | `description` chia paragraph |
| `policy` | `check_in_from`, `check_out_until`, `useful_info`, `secondary.hotel_policy` |
| `amenities_summary` | `amenities`, `amenity_groups` |
| `nearby_places` | `nearby_places` |
| `room_detail` | `rooms` |
| `activity_detail` | `activities` |
| `review_summary` | `reviews_detail.reviews` |
| `review_aspect` | `reviews_detail.tags` |

**Lý do giữ `text_chunks` trong PostgreSQL**:

- Phục vụ vector search bằng `pgvector`.
- Có thể index sang Elasticsearch cho BM25.
- Metadata JSONB giúp filter theo `hotel_id`, `city`, `chunk_type`, `price`, `room_view`.
- Không làm graph bị phình to.

---

## 7. Kiến trúc Hybrid Retrieval sau khi bỏ `TextChunk` khỏi Graph

```text
User Query
   |
   v
Intent Parsing
   |
   +--> PostgreSQL filter
   |       - city
   |       - area
   |       - star_rating
   |       - max_price
   |       - review_score
   |
   +--> Neo4j Graph reasoning
   |       - suitable_for
   |       - amenity category
   |       - nearby place category
   |       - city/area relation
   |
   +--> PostgreSQL pgvector
   |       - semantic text_chunks retrieval
   |
   +--> Elasticsearch
           - BM25 text_chunks retrieval

Fusion/Rerank
   |
   v
LLM Answer
```

---

## 8. Neo4j schema cuối cùng đề xuất

### Nodes

| Label | Nguồn data mẫu | Vai trò |
|:---|:---|:---|
| `Hotel` | `hotel_id`, `name`, `star_rating`, `review_score` | Node trung tâm |
| `City` | `city` | Địa danh cấp thành phố |
| `Area` | `area`, `district` | Khu vực trong thành phố |
| `Room` | `rooms[]` | Loại phòng |
| `Amenity` | `amenities`, `amenity_groups` | Tiện ích |
| `AmenityCategory` | key của `amenity_groups` | Nhóm tiện ích |
| `Place` | `nearby_places[]` | Địa điểm xung quanh |
| `PlaceCategory` | `nearby_places[].type` | Loại địa điểm |
| `TravelerType` | `suitable_for`, `reviews_detail.demographics` | Nhóm khách phù hợp |
| `ReviewAspect` | `reviews_detail.tags` | Khía cạnh review |
| `Activity` | `activities[]` | Hoạt động/tour |

### Relationships

| Relationship | From | To | Thuộc tính |
|:---|:---|:---|:---|
| `LOCATED_IN` | `Hotel` | `City` | - |
| `IN_AREA` | `Hotel` | `Area` | - |
| `BELONGS_TO_CITY` | `Area` | `City` | - |
| `HAS_ROOM` | `Hotel` | `Room` | - |
| `HAS_AMENITY` | `Hotel` | `Amenity` | - |
| `BELONGS_TO` | `Amenity` | `AmenityCategory` | - |
| `NEARBY` | `Hotel` | `Place` | `distance_km` |
| `BELONGS_TO` | `Place` | `PlaceCategory` | - |
| `SUITABLE_FOR` | `Hotel` | `TravelerType` | `source`, `count`, `score` |
| `HAS_REVIEW_ASPECT` | `Hotel` | `ReviewAspect` | `mentioned`, `positive_pct` |
| `OFFERS_ACTIVITY` | `Hotel` | `Activity` | - |

---

## 9. Thay đổi cần triển khai trong code

### 9.1. `init_db.sql`

Nên bổ sung:

1. `amenity_categories`
2. `place_categories`
3. `hotels.area`
4. `hotels.country`
5. `hotels.property_type`
6. `hotels.city_id`
7. `amenities.category_id`
8. `nearby_places.category_id`
9. `hotel_suitability.source`, `mention_count`, `score`

### 9.2. `ingest_data.py`

Nên cập nhật Neo4j ingestion:

1. Tạo `City` node từ `data.city`.
2. Tạo `Area` node từ `data.area` hoặc `data.district`.
3. Tạo relationship:
   - `Hotel -[:LOCATED_IN]-> City`
   - `Hotel -[:IN_AREA]-> Area`
   - `Area -[:BELONGS_TO_CITY]-> City`
4. Tạo `AmenityCategory` từ `amenity_groups`.
5. Tạo `Amenity -[:BELONGS_TO]-> AmenityCategory`.
6. Tạo `PlaceCategory` từ `nearby_places[].type`.
7. Tạo `Place -[:BELONGS_TO]-> PlaceCategory`.
8. Dùng `reviews_detail.demographics` để bổ sung `TravelerType` nếu thiếu `suitable_for`.
9. Không tạo `TextChunk` node trong Neo4j.
10. Không tạo `HAS_CHUNK` relationship.

---

## 10. Final Architecture

```text
                       +---------------------+
                       |      PostgreSQL     |
                       |---------------------|
                       | hotels              |
                       | rooms               |
                       | amenities           |
                       | amenity_categories  |
                       | nearby_places       |
                       | place_categories    |
                       | hotel_policies      |
                       | reviews             |
                       | review_aspects      |
                       | hotel_suitability   |
                       | text_chunks vector  |
                       +----------+----------+
                                  |
                                  | text_chunks.content
                                  v
                       +---------------------+
                       |    Elasticsearch    |
                       |---------------------|
                       | BM25 hotel_chunks   |
                       +---------------------+

                       +---------------------+
                       |        Neo4j        |
                       |---------------------|
                       | Hotel               |
                       | City                |
                       | Area                |
                       | Room                |
                       | Amenity             |
                       | AmenityCategory     |
                       | Place               |
                       | PlaceCategory       |
                       | TravelerType        |
                       | ReviewAspect        |
                       | Activity            |
                       +---------------------+
```

**Quyết định cuối**:

- `TextChunk`: **Không là Neo4j node**.
- `TextChunk`: **Giữ là PostgreSQL vector table + Elasticsearch index**.
- Neo4j chỉ giữ domain entities và semantic relationships.
- `Policy`: giữ PostgreSQL trước; chỉ đưa lên graph nếu phát sinh nhiều truy vấn reasoning về chính sách.