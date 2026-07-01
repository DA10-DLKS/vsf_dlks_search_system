# 02 — API Reference

> **Nguồn sự thật:** [`api/main.py`](../../api/main.py) và [`api/frontend_adapter.py`](../../api/frontend_adapter.py).
> Tài liệu này liệt kê **đúng những endpoint đang chạy** (không phải bản đề xuất).
> Base URL local mặc định: `http://localhost:8000`.

## Bảng tổng hợp endpoint

| # | Method | Path | Handler | Mục đích |
|---|--------|------|---------|----------|
| 1 | GET | `/health` | `health` | Liveness đơn giản |
| 2 | GET | `/health/deep` | `health_deep` | Probe OpenSearch + Qdrant + Postgres |
| 3 | GET | `/metrics` | `metrics` | Prometheus metrics |
| 4 | GET | `/observability/slow_requests` | `slow_requests` | Truy vết request chậm từ log |
| 5 | GET | `/search` | `search_bm25` | BM25 keyword search (baseline) |
| 6 | GET | `/hybrid_search` | `hybrid_search` | Hybrid retrieval Node 1→9 (shape pipeline) |
| 7 | GET | `/hotel/{hotel_id}/ask` | `hotel_ask` | Hỏi trong phạm vi 1 khách sạn |
| 8 | GET | `/eval/golden` | `eval_golden` | Chạy golden dataset → metric |
| 9 | POST | `/search` | `fe_search` | **Frontend** search → `results[]` |
| 10 | POST | `/context` | `fe_context` | **Frontend** context 1 khách sạn |
| — | (mount) | `/ui` | StaticFiles | Phục vụ `frontend/` tĩnh |

> `/search` xuất hiện 2 lần: **GET** = BM25 thuần, **POST** = full hybrid cho frontend. Khác method → khác handler.

---

## 1. `GET /health`

- **Mục đích:** liveness probe (k8s/uptime).
- **Tham số:** không.
- **Response `200`:**
```json
{ "status": "ok" }
```

---

## 2. `GET /health/deep`

- **Mục đích:** kiểm tra sâu — probe OpenSearch, Qdrant, Postgres qua `observability.health.deep_health`. Cập nhật gauge `da10_dependency_up`.
- **Tham số:** không.
- **Response:** `200` nếu tất cả dependency OK, **`503`** nếu bất kỳ cái nào down. Body do `deep_health()` sinh (trạng thái từng dependency).

---

## 3. `GET /metrics`

- **Mục đích:** endpoint Prometheus scrape. Gộp cả `da10_*` (observability) lẫn `search_bm25_*` (cũ) trong 1 `generate_latest`.
- **Response:** `200`, `Content-Type: text/plain; version=0.0.4` (Prometheus text format).

---

## 4. `GET /observability/slow_requests`

Đọc `logs/da10.jsonl`, trả các request **đã hoàn tất** (kèm query + breakdown `stage_ms`) để truy vết request chậm — "poor man's tracing" theo `request_id`.

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `min_ms` | float | `0` | `>= 0` | Chỉ lấy request có `latency_ms >= ngưỡng` |
| `limit` | int | `50` | `1..500` | Số request gần nhất trả về |

- **Response `200`:**
```json
{
  "threshold_ms": 0,
  "count": 2,
  "requests": [
    {
      "timestamp": "2026-06-30T10:12:03.456Z",
      "request_id": "a1b2c3d4e5f6",
      "event": "search_completed",
      "query": "resort yên tĩnh gần biển đà nẵng",
      "latency_ms": 812.4,
      "stage_ms": { "intent": 5.1, "filter": 40.2, "text_retrieval": 610.0, "fusion": 12.0, "rerank": 130.0, "context": 15.1 },
      "n_results": 5,
      "rerank_method": "density_fallback"
    }
  ]
}
```
- Sắp xếp **mới nhất lên đầu**. Chỉ lấy các event thuộc `{search_completed, hybrid_search_completed, context_completed}`.
- Nếu chưa có file log: `{ "threshold_ms": ..., "count": 0, "requests": [], "note": "logs/da10.jsonl chưa có" }`.
- **Mã lỗi:** `500` nếu đọc log lỗi (`detail="Đọc log lỗi: ..."`).

---

## 5. `GET /search` — BM25 keyword search (baseline)

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `q` | string | *(bắt buộc)* | — | Câu tìm kiếm |
| `size` | int | `10` | `1..20` | Số kết quả BM25 |

- **Xử lý:** gọi thẳng `BM25SearchService.search(q, size)`; response là **shape gốc của BM25 service** (không qua adapter).
- **Ví dụ:** `GET /search?q=resort%20nha%20trang&size=5`
- **Mã lỗi:** **`503`** — `detail="Keyword search backend unavailable"` (OpenSearch không sẵn).

---

## 6. `GET /hybrid_search` — Hybrid retrieval (shape pipeline)

Chạy pipeline Node 1→9 và trả **nguyên shape pipeline** (dùng để debug/kiểm tra retrieval).

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `q` | string | *(bắt buộc)* | — | Câu hỏi tiếng Việt |
| `top_n` | int | `5` | `1..20` | Số khách sạn trả về |
| `answer` | bool | `false` | — | `true` → sinh câu trả lời LLM (Node 9) |

- **Response `200` (rút gọn):**
```json
{
  "intent": {
    "query": "resort yên tĩnh gần biển đà nẵng dưới 3 triệu",
    "concepts": ["AMEN_SEA_VIEW", "OBJ_RESORT", "STYLE_QUIET"],
    "city": "đà nẵng",
    "range": { "price_max": 3000000 },
    "price_tiers": [], "purposes": [], "exclude_concepts": []
  },
  "n_candidates": 42,
  "n_fused": 42,
  "rerank_method": "density_fallback",
  "stage_ms": { "intent": 5.1, "filter": 40.2, "text_retrieval": 610.0, "fusion": 12.0, "rerank": 130.0, "context": 15.1 },
  "top_hotels": [
    { "hotel_id": 1032041, "hotel_name": "…", "score": 0.83, "chunks": [ ... ] }
  ],
  "context_package": { "query": "…", "chunks": [ { "hotel_id": 1032041, "score": 0.83, "...": "..." } ], "metadata": { "intent": { } } },
  "prompt": "…prompt text cho LLM…"
}
```
- Nếu `answer=true`: có thêm key `"answer": { "answer": "…", ... }`.
- **Mã lỗi:** **`500`** — `detail="Hybrid search error: <exc>"`.

> Cấu trúc `top_hotels[]` / `context_package` do `retrieval/hybrid_search/pipeline.py` và `context/` quyết định — nếu cần chi tiết field, xem 2 module đó.

---

## 7. `GET /hotel/{hotel_id}/ask` — Hỏi trong 1 khách sạn

Semantic-search các **chunk** liên quan nhất tới câu hỏi, **chỉ trong 1 khách sạn** (Qdrant filter `payload.hotel_id == hotel_id`). Không sinh LLM.

### 7.1 Request — tham số

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `hotel_id` | int | *(bắt buộc)* | path param | ID khách sạn cần hỏi |
| `q` | string | *(bắt buộc)* | không rỗng | Câu hỏi tiếng Việt (VD: "có cho mang thú cưng không") |
| `top_k` | int | `5` | `1..20` | Số chunk liên quan trả về |
| `sections` | string[] | `null` | enum, lặp tham số | Lọc phụ theo section; OR giữa các section |

- **`sections` giá trị hợp lệ:** `description`, `room_type`, `faq`, `overview`, `semantic_profile`. Cú pháp lặp: `?sections=faq&sections=description`. Chỉ lọc trên payload Qdrant, **không đụng vector**.
- **Ví dụ:** `GET /hotel/542/ask?q=có%20hồ%20bơi%20không&top_k=3&sections=faq`

### 7.2 Response `200` — envelope

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `hotel_id` | int | — | echo | Đúng `hotel_id` trong path |
| `query` | string | — | echo | Đúng câu hỏi `q` đã gửi |
| `sections_filter` | string[] | `[]` | — | Các section đã lọc (rỗng nếu không truyền `sections`) |
| `count` | int | — | `= len(chunks)` | Số chunk trả về |
| `chunks` | object[] | `[]` | có thể rỗng | Danh sách chunk khớp (xem 7.3) |

### 7.3 Response — mỗi phần tử `chunks[]`

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `chunk_id` | string | — | có thể null | ID chunk trong Qdrant |
| `text` | string | — | có thể null | Nội dung đoạn văn khớp câu hỏi |
| `section` | string | — | 1 trong enum `sections` | Section nguồn của chunk (description/faq/…) |
| `source_type` | string | — | có thể null | Loại nguồn của chunk |
| `score` | float | — | ~0..1 (cosine) | Điểm tương đồng ngữ nghĩa với câu hỏi |

- **Ví dụ response:**
```json
{
  "hotel_id": 542,
  "query": "có hồ bơi không",
  "sections_filter": ["faq"],
  "count": 2,
  "chunks": [
    { "chunk_id": "chunk_542_faq_3", "text": "Khách sạn có hồ bơi ngoài trời…", "section": "faq", "source_type": "faq", "score": 0.71 }
  ]
}
```
- **Mã lỗi:**
  - **`503`** — `detail="Vector search backend unavailable"` (Qdrant/model không sẵn).
  - **`500`** — `detail="Hotel ask error: <exc>"`.

---

## 8. `GET /eval/golden` — Chạy golden dataset

Chạy bộ câu golden → trả metric Recall/Precision/Hit/MRR/nDCG (summary + per-query). **Đồng bộ** — request chờ tới khi chạy xong.

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `k` | int | `10` | `1..50` | Cắt top-K khi tính metric |
| `limit` | int | `10` | `1..100` | Số câu golden chạy (giữ nhỏ cho nhanh) |
| `use_services` | bool | `false` | — | `true` = dùng vector+BM25; `false` = candidate-only (nhanh, nhẹ RAM) |

- ⚠️ ~2s/câu (candidate-only) → `limit` lớn có thể mất vài phút. Cập nhật gauge `da10_eval_metric`.
- **Response `200`:**
```json
{
  "summary": { "k": 10, "recall": 0.62, "precision": 0.31, "hit": 0.8, "rr": 0.55, "ndcg": 0.6, "n_queries": 10 },
  "per_query": [ { "query": "…", "recall": 0.5, "...": "..." } ],
  "duration_s": 21.4,
  "mode": "candidate-only"
}
```
- **Mã lỗi:** **`500`** — `detail="Golden eval error: <exc>"`.

---

## 9. `POST /search` — Frontend search

Chạy hybrid retrieval **không sinh LLM answer** (cho nhanh) rồi dịch sang schema frontend qua `to_search_response()`.

### 9.1 Request body (`SearchRequest`)

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `query` | string | *(bắt buộc)* | không rỗng | Câu tìm kiếm tiếng Việt (parse intent từ đây) |
| `filters` | object \| null | `null` | — | **Nhận nhưng chưa dùng** trong handler (xem ⚠️ dưới) |
| `top_n` | int | `10` | `1..10` (`ge=1, le=10`) | Số khách sạn tối đa trả về |

> ⚠️ `filters` được khai báo trong schema nhưng handler `fe_search` **không truyền xuống pipeline** —
> lọc thực tế suy ra từ `query` (intent parser). Xem [04_Business_Logic_Decision_Notes.md](04_Business_Logic_Decision_Notes.md).

- **Ví dụ request:**
```json
{ "query": "resort yên tĩnh gần biển đà nẵng dưới 3 triệu", "top_n": 5 }
```

### 9.2 Response `200` — envelope

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `query` | string | — | echo | Đúng `query` đã gửi |
| `total` | int | — | `= len(results)` | Số khách sạn trả về |
| `results` | object[] | `[]` | rỗng nếu không khớp | Danh sách khách sạn (xem 9.3) |

### 9.3 Response — mỗi phần tử `results[]`

> `results[]` = **merge nguyên object khách sạn từ `hotel_detail_cache.json`** + thêm `score` + `rooms_matching`.
> `rooms` bị **ghi đè** bằng danh sách phòng đã lọc giá (nếu query nêu giá). Bảng dưới liệt kê các trường thực có trong cache.

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `hotel_id` | int | — | — | ID khách sạn |
| `score` | float | — | 4 chữ số thập phân | **Do API thêm** — điểm relevance của KS (từ pipeline) |
| `name` | string | — | — | Tên khách sạn (hiển thị) |
| `name_original` / `name_alt` | string | — | có thể rỗng | Tên gốc / tên thay thế |
| `accommodation_type` | string | — | — | Loại lưu trú (Khách sạn/Resort/Homestay…) |
| `brand` | string | — | có thể rỗng | Chuỗi/thương hiệu KS |
| `star_rating` | float | — | 1.0–5.0 | Hạng sao |
| `is_luxury` | bool | — | — | Cờ khách sạn cao cấp |
| `review_score` | float | — | 1.0–10.0 | Điểm đánh giá tổng |
| `review_count` | int | — | ≥0 | Số lượt đánh giá |
| `reviews_detail` | object | — | — | Tổng hợp review (xem 9.5) |
| `description` | string | — | — | Mô tả khách sạn |
| `suitable_for` | string[] | — | — | Phù hợp với (Cặp đôi/Gia đình…) |
| `amenities` | string[] | — | — | Danh sách tiện nghi |
| `address` / `city` / `district` / `province` | string | — | — | Địa chỉ & hành chính |
| `latitude` / `longitude` | float | — | — | Toạ độ |
| `check_in_from` / `check_out_until` | string | — | — | Giờ nhận/trả phòng |
| `number_of_rooms` / `number_of_floors` / `year_built` | string | — | — | Thông tin toà nhà (lưu dạng chuỗi) |
| `price_from` | int | — | VND, có thể `null` | Giá thấp nhất; **tính lại** theo phòng đã lọc nếu query nêu giá |
| `rooms` | object[] | — | đã lọc giá | Danh sách phòng (xem 9.4) — chỉ phòng trong dải giá nếu query nêu giá |
| `rooms_matching` | object[] | — | = `rooms` | **Do API thêm** — alias của `rooms` sau lọc (frontend đọc để highlight) |
| `nearby_places` | object[] | `[]` | — | Địa điểm lân cận (xem 9.5) |
| `activities` | object[] | `[]` | — | Hoạt động giải trí (xem 9.5) |
| `useful_info` | object | `{}` | key động | Thông tin hữu ích (phí wifi, chính sách…), số key thay đổi theo KS |
| `images` | string[] | `[]` | — | URL ảnh |
| `source_url` | string | — | — | Link nguồn (Agoda…) |

### 9.4 Response — mỗi phần tử `rooms[]` / `rooms_matching[]`

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `name` / `name_en` | string | — | — | Tên loại phòng (VI / EN) |
| `room_type_id` | int | — | — | ID loại phòng |
| `price_per_night` | int | — | VND, có thể `null` | Giá/đêm — **trường dùng để lọc dải giá** |
| `original_price` | int | — | VND | Giá gốc (trước giảm) |
| `room_size` | string | — | vd "38 m²" | Diện tích (chuỗi hiển thị) |
| `size_sqm` | float | — | — | Diện tích (số, m²) |
| `max_occupancy` | int | — | ≥1 | Số khách tối đa |
| `bed_type` | string | — | — | Loại giường |
| `room_view` | string | — | có thể rỗng | Hướng nhìn (biển/thành phố…) |
| `room_amenities` / `facilities` | string[] | — | — | Tiện nghi phòng |
| `review_score` | float | — | — | Điểm đánh giá phòng |
| `is_sold_out` | bool | — | — | Cờ hết phòng |

### 9.5 Response — object con dùng chung

**`nearby_places[]`**

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `name` | string | — | — | Tên địa điểm |
| `type` | string | — | — | Loại (Bãi biển/Nhà hát…) |
| `distance_km` | float | — | km | Khoảng cách tới KS |

**`activities[]`**

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `activity_id` | int | — | — | ID hoạt động |
| `title` | string | — | — | Tên hoạt động |
| `description` | string | — | — | Mô tả |
| `price` | int | — | VND | Giá |
| `review_score` | float | — | — | Điểm đánh giá |
| `review_count` | int | — | ≥0 | Số lượt đánh giá |

**`reviews_detail`**

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `score` | float | — | 1.0–10.0 | Điểm review tổng |
| `review_count` | int | — | ≥0 | Số lượt đánh giá |
| `comments_count` | int | — | ≥0 | Số bình luận |

- **Ví dụ response (rút gọn):**
```json
{
  "query": "resort yên tĩnh gần biển đà nẵng dưới 3 triệu",
  "total": 5,
  "results": [
    {
      "hotel_id": 1032041,
      "score": 0.8312,
      "name": "…",
      "accommodation_type": "Resort",
      "star_rating": 4.0,
      "review_score": 8.6,
      "price_from": 1800000,
      "rooms": [ { "name": "…", "price_per_night": 1800000, "room_view": "biển", "max_occupancy": 2 } ],
      "rooms_matching": [ { "name": "…", "price_per_night": 1800000 } ],
      "nearby_places": [ { "name": "…", "type": "Bãi biển", "distance_km": 0.4 } ],
      "activities": [],
      "useful_info": { "Phí Wifi": "Miễn phí" },
      "images": ["https://…"],
      "source_url": "https://www.agoda.com/…"
    }
  ]
}
```
- Không có hotel nào khớp → `{ "query": ..., "results": [], "total": 0 }`.
- Hotel_id không có trong cache → **bỏ qua** (log warning), không gây lỗi.
- **Mã lỗi:** **`500`** — `detail="Search error: <exc>"`.

---

## 10. `POST /context` — Frontend context 1 khách sạn

Sinh context (bao gồm câu trả lời LLM) cho **1 khách sạn user đã chọn** qua `build_hotel_context()`. Không search lại.

### 10.1 Request body (`ContextRequest`)

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `result_id` | string | *(bắt buộc)* | dạng `"hotel_<id>"` | ID kết quả; id lấy từ `results[].hotel_id` của `POST /search` |
| `query` | string \| null | `null` | — | Câu hỏi gốc — để answer bám nhu cầu + đánh dấu concept `matched` |

- **Ví dụ request:**
```json
{ "result_id": "hotel_542", "query": "gần biển yên tĩnh cho 2 người" }
```

### 10.2 Response `200` — envelope

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `result_id` | string | — | echo | Đúng `result_id` đã gửi |
| `llm_context` | string | `""` | rỗng nếu LLM lỗi | Câu trả lời do LLM sinh, grounded trên evidence ABSA |
| `citations` | object[] | — | 1 phần tử | Trích dẫn nguồn (xem 10.3) |
| `source_documents` | object[] | — | 1 phần tử | Tài liệu nguồn (xem 10.4) |
| `context_chunks` | object[] | `[]` | — | Các chunk hiển thị "vì sao gợi ý" (xem 10.5) |
| `evidence` | object | — | — | Evidence ABSA thô: `positives` + `negatives` (xem 10.6) |

### 10.3 Response — mỗi phần tử `citations[]`

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `id` | string | — | `cit_<hotel_id>` | ID trích dẫn |
| `source_document_id` | string | — | `doc_<hotel_id>` | Trỏ tới `source_documents[].id` |
| `label` | string | — | — | Tên khách sạn |
| `url` | string | `""` | có thể rỗng | Link nguồn (từ `provenance.source_url`) |
| `quote` | string | — | ≤160 ký tự | 160 ký tự đầu của mô tả (hoặc grounded text) |

### 10.4 Response — mỗi phần tử `source_documents[]`

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `id` | string | — | `doc_<hotel_id>` | ID tài liệu |
| `title` | string | — | — | Tên khách sạn |
| `type` | string | `"hotel_detail"` | cố định | Loại tài liệu |
| `url` | string | `""` | có thể rỗng | Link nguồn |

### 10.5 Response — mỗi phần tử `context_chunks[]`

> 3 loại `source_type`: `hotel_content` (mô tả), `absa_positive` (điểm mạnh), `absa_negative` (điểm yếu có trích review).

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `chunk_id` | string | — | `chunk_<id>_<loại>` | ID chunk hiển thị |
| `hotel_name` | string | — | — | Tên khách sạn |
| `source_type` | string | — | enum 3 loại | Loại chunk (content/positive/negative) |
| `text` | string | — | — | Nội dung hiển thị (template tiếng Việt) |
| `score` | float \| null | `null` | null với `hotel_content` | Điểm ABSA (positive: score, negative: negative_score) |
| `metadata` | object | — | — | Khác nhau theo loại: `location` / `concept`+`evidence_count`+`matched` / `concept`+`matched`+`spans` |

### 10.6 Response — object `evidence`

**`evidence.positives[]`**

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `concept` | string | — | mã concept | Concept tích cực (vd `ASPECT_LOCATION`) |
| `aspect` | string | — | — | Nhãn tiếng Việt của concept |
| `score` | float | — | 2 chữ số thập phân | Điểm tích cực từ ABSA |
| `evidence_count` | int | — | ≥1 | Số lượt review làm bằng chứng |
| `matched` | bool | — | — | `true` nếu concept khớp nhu cầu trong `query` |

**`evidence.negatives[]`**

| Query param | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|-------------|------|----------|-----------|---------|
| `concept` | string | — | mã concept | Concept tiêu cực |
| `aspect` | string | — | — | Nhãn tiếng Việt của concept |
| `negative_score` | float | — | 2 chữ số thập phân | Điểm tiêu cực từ ABSA |
| `spans` | string[] | `[]` | tối đa 2 | Trích review thật minh hoạ mặt hạn chế |
| `matched` | bool | — | — | `true` nếu concept khớp nhu cầu trong `query` |

- **Ví dụ response (rút gọn):**
```json
{
  "result_id": "hotel_542",
  "llm_context": "…câu trả lời do LLM sinh, grounded trên evidence ABSA…",
  "citations": [
    { "id": "cit_542", "source_document_id": "doc_542", "label": "…tên KS…", "url": "https://…", "quote": "…160 ký tự đầu…" }
  ],
  "source_documents": [
    { "id": "doc_542", "title": "…tên KS…", "type": "hotel_detail", "url": "https://…" }
  ],
  "context_chunks": [
    { "chunk_id": "chunk_542_overview", "hotel_name": "…", "source_type": "hotel_content", "text": "…", "score": null, "metadata": { "location": "…" } },
    { "chunk_id": "chunk_542_pos_ASPECT_LOCATION", "source_type": "absa_positive", "text": "Điểm mạnh (khớp nhu cầu): Vị trí — …", "score": 0.82, "metadata": { "concept": "ASPECT_LOCATION", "evidence_count": 40, "matched": true } },
    { "chunk_id": "chunk_542_neg_ASPECT_ROOM", "source_type": "absa_negative", "text": "Mặt hạn chế: Phòng (điểm tiêu cực …). Trích review thật: …", "score": 0.3, "metadata": { "concept": "ASPECT_ROOM", "matched": false, "spans": ["…"] } }
  ],
  "evidence": {
    "positives": [ { "concept": "ASPECT_LOCATION", "aspect": "Vị trí", "score": 0.82, "evidence_count": 40, "matched": true } ],
    "negatives": [ { "concept": "ASPECT_ROOM", "aspect": "Phòng", "negative_score": 0.3, "spans": ["…"], "matched": false } ]
  }
}
```
- **Mã lỗi:** **`500`** — `detail="Context error: <exc>"`.

---

## 11. Quy ước lỗi chung

FastAPI trả lỗi dưới dạng `{ "detail": "<message>" }`. Bảng mã lỗi thực tế trong code:

| HTTP | Endpoint | `detail` | Nguyên nhân |
|------|----------|----------|-------------|
| `422` | mọi endpoint | (FastAPI validation) | Sai kiểu/thiếu tham số bắt buộc, vượt ràng buộc `ge/le` |
| `503` | `GET /health/deep` | body deep_health | Có dependency down |
| `503` | `GET /search` | `Keyword search backend unavailable` | OpenSearch không sẵn |
| `503` | `GET /hotel/{id}/ask` | `Vector search backend unavailable` | Qdrant/model không sẵn |
| `500` | `GET /observability/slow_requests` | `Đọc log lỗi: …` | Lỗi đọc file log |
| `500` | `GET /hybrid_search` | `Hybrid search error: …` | Lỗi trong pipeline |
| `500` | `GET /hotel/{id}/ask` | `Hotel ask error: …` | Lỗi vector search |
| `500` | `GET /eval/golden` | `Golden eval error: …` | Lỗi khi eval |
| `500` | `POST /search` | `Search error: …` | Lỗi pipeline/adapter |
| `500` | `POST /context` | `Context error: …` | Lỗi build context / LLM |

> Không có handler nào trả `404 HOTEL_NOT_FOUND` như bản đề xuất. Ở `POST /search`, hotel_id
> không có trong cache bị **bỏ qua** (log warning), không gây lỗi. Ở `POST /context`, hotel_id
> không tồn tại vẫn chạy (dùng object rỗng → context nghèo), không ném 404.

---

## 12. Header đáng chú ý

- **Request:** `X-Request-ID` (tùy chọn) — nếu client/proxy gửi, mọi log của request mang đúng id đó; không có thì server tự sinh (12 hex).
- **Response:** `X-Request-ID` — luôn trả về để client đối chiếu log.
- **CORS:** `allow_origins=["*"]`, mọi method/header (frontend chạy origin khác gọi được).
