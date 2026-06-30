# Báo cáo 05 — Search Indexing

Hệ thống dùng **hai chỉ mục song song** trên cùng một nguồn dữ liệu (`data/cleaned` + nhãn KE), phục vụ hai loại tín hiệu bù nhau:

- **BM25 (lexical)** trên **OpenSearch** — khớp từ khóa chính xác, lọc theo trường.
- **Vector (semantic)** trên **Qdrant** — khớp ý nghĩa, bge-m3 1024 chiều.

Cả hai cùng nhúng nhãn ontology (`ontology_concepts`, `nearby_landmarks`...) từ `knowledge_objects.json` → retrieval lọc theo concept trên cả hai backend.

---

## 1. Hạ tầng index (docker-compose)

| Service | Image | Port | Vai trò |
|---|---|---|---|
| `opensearch` | opensearchproject/opensearch:2 | 9200 | BM25 index |
| `opensearch-dashboard` | opensearch-dashboards:2 | 5601 | xem/inspect index |
| `qdrant` | qdrant/qdrant:latest | 6333 | vector store |
| `postgres` | postgres:16 | 5432 | hard filter có cấu trúc (production) |

Qdrant lưu tại `./.docker_volumes/qdrant_storage`, OpenSearch tại `./.docker_volumes/opensearch_data`.

> ⚠ `.docker_volumes` bị git track có chủ đích (skip embedding). Chạy Docker xong `git status` sẽ bẩn; dọn = `git restore` + `git clean -fd` **chỉ trong `.docker_volumes`** (không toàn repo) + merge ff-only.

---

## 2. BM25 index — OpenSearch (`indexing/bm25_index/`)

### 2.1 Tổ chức index & alias

- **Index runtime / alias**: `vsf_hotels_bm25_current` (env `BM25_INDEX`).
- **Blue-green qua alias**: build vào index versioned (`BM25_TARGET_INDEX`), validate xong mới `promote_alias` **đổi alias nguyên tử** sang index mới (`indices.update_aliases` remove+add trong 1 lệnh). → reindex không downtime, rollback dễ.
- Promote chỉ chạy khi `BM25_PROMOTE_ALIAS=true` **và** `failed == 0`.

### 2.2 Một document = một khách sạn (denormalized)

`iter_docs` đọc từng file `data/cleaned/*.json`, dựng 1 index doc theo `index_mapping.json`, **nhúng nested** rooms / nearby_places / activities vào cùng document hotel (denormalize để 1 lần match ra đủ ngữ cảnh):

- Trường phẳng: name, accommodation_type, star_rating, is_luxury, review_score, review_count, address, city, lat/long, description, amenities, suitable_for...
- **Giá phòng** chuẩn hóa qua `parse_price` (xử lý "₫", dấu chấm ngăn nghìn VND → số; null nếu không có — **không bịa**).
- **Nested**: `rooms[]`, `nearby_places[]`, `activities[]`.

### 2.3 Nhãn ontology join theo hotel_id

Mỗi doc gọi `labels_for(hotel_id)` (cùng nguồn KE với vector) và nhúng:
```
ontology_concepts, strong_feel_concepts, location_concept, nearby_landmarks
```
→ OpenSearch **filter theo concept** (terms query) ngoài match text. Đảm bảo BM25 và vector chia sẻ cùng vocabulary tri thức.

### 2.4 Bulk indexing & độ bền

`run_indexing` dùng `helpers.streaming_bulk`:
- `chunk_size=50`, `max_chunk_bytes=5MB` (env override được).
- `raise_on_error=False` → đếm success/failed, in 3 lỗi đầu, **không vỡ cả batch** vì 1 doc hỏng.
- Yêu cầu index tồn tại với mapping đã thống nhất trước khi chạy (không tự tạo mapping bừa).

### 2.5 Tiếng Việt

`reindex_vietnamese.py` — reindex với analyzer/cấu hình tiếng Việt phù hợp (tách từ, fold dấu có kiểm soát) để BM25 khớp đúng truy vấn tiếng Việt.

---

## 3. Vector index — Qdrant (`indexing/vector_index/`)

### 3.1 Cấu hình

`qdrant_index.py`:
- **Collection**: `vsf_travel` (env override).
- **Vector**: `size=1024` (bge-m3), `distance=COSINE`.
- **Embedding**: bge-m3, L2-normalized → cosine = dot product.

### 3.2 Một chunk = một point

Khác BM25 (doc-level), Qdrant là **chunk-level**:
- Tái dùng `chunk_document` (báo cáo 03): text từ `data/cleaned` + nhãn KE đã đính.
- Mỗi chunk → 1 point: `vector = embed(chunk.text)`, `payload = chunk.to_payload()` (gồm `ontology_concepts` / `semantic_profile` / `nearby_landmarks`... cho retrieval filter/rerank).
- **Point id ổn định**: `uuid5(NAMESPACE_URL, chunk_id)` — Qdrant yêu cầu uuid/int, map từ chunk_id sha1 → upsert idempotent.

### 3.3 Checkpoint & resume

`data/qdrant_index_checkpoint.json` lưu tiến độ → reindex lớn dừng/tiếp tục không mất công, batch mặc định 64.

### 3.4 Tham chiếu pgvector

Có sẵn `pgvector_index.py` (Postgres + pgvector) làm phương án tham chiếu, nhưng `.env` cấu hình Qdrant và service Qdrant đang chạy → **tầng vector dùng Qdrant**. `iter_clean_documents` được tái dùng giữa hai backend.

---

## 4. Sự khác biệt cấp độ giữa hai index (và cách fusion xử lý)

| | BM25 (OpenSearch) | Vector (Qdrant) |
|---|---|---|
| Đơn vị | document (1/hotel) | chunk (nhiều/hotel) |
| chunk_id | `bm25_hotel_<id>` | sha1 thật của chunk |
| Tín hiệu | từ khóa, filter trường | ngữ nghĩa |

Vì chunk_id hai bên không trùng, fusion **không** dedupe theo chunk_id mà **RRF ở cấp hotel** (`rrf_by_hotel`, xem báo cáo 04 §6.1). Cả hai đều nhận `candidate_hotel_ids` để chỉ chấm trong tập đã lọc.

---

## 5. Tái lập

```bash
# BM25 (cần index tồn tại với mapping chuẩn trước)
python -m indexing.bm25_index.index_bm25
python -m indexing.bm25_index.reindex_vietnamese

# Vector (Qdrant)
.venv/Scripts/python.exe -X utf8 -m indexing.vector_index.qdrant_index

# Kiểm tra
curl localhost:9200/_cat/indices       # OpenSearch
curl localhost:6333/collections        # Qdrant
```
