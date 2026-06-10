# Keyword Search Implementation Guide

Tài liệu này ghi lại các thay đổi keyword search BM25 sau khi đã có OpenSearch index `travel_bm25`, kèm hướng dẫn chạy và test.

## 1. Thay Đổi Đã Thực Hiện

### Tách keyword search sang Layer 6

Logic BM25 không còn nằm trực tiếp trong `api/main.py`. Phần truy vấn OpenSearch đã được tách sang:

```text
retrieval/lexical_search/service.py
```

Service chính:

```python
BM25SearchService
```

Nhiệm vụ:

- Nhận query text.
- Build OpenSearch `multi_match` query.
- Gọi OpenSearch index `travel_bm25`.
- Map OpenSearch hits về response shape đang dùng bởi API.

Các field search hiện tại:

```python
["name", "description^2", "city", "address", "amenities"]
```

Các field trả về từ `_source`:

```python
[
    "id",
    "name",
    "accommodation_type",
    "star_rating",
    "review_score",
    "address",
    "city",
    "description",
]
```

### Giữ `GET /search`

Endpoint hiện tại vẫn là:

```text
GET /search?q=<query>
```

Không thêm `POST /search` ở giai đoạn keyword-only. `POST /search` sẽ dành cho giai đoạn hybrid search hoàn chỉnh, khi output cần làm input cho Context API.

Response vẫn giữ compatible:

```json
{
  "query": "khach san gan bien",
  "results": [
    {
      "id": 123,
      "name": "Test Hotel",
      "accommodation_type": "hotel",
      "star_rating": 5,
      "review_score": 9.1,
      "address": "Ha Long",
      "city": "ha long",
      "description": "Khach san gan bien",
      "score": 12.5
    }
  ],
  "took_ms": 7,
  "total_hits": 1
}
```

### Error handling

Nếu OpenSearch hoặc keyword backend lỗi, API trả:

```text
HTTP 503
```

Response:

```json
{
  "detail": "Keyword search backend unavailable"
}
```

### Metrics

Các Prometheus metrics hiện có vẫn được giữ:

```text
search_bm25_request_duration_seconds
search_bm25_requests_total
search_bm25_errors_total
```

## 2. Điều Kiện Trước Khi Chạy

Đảm bảo đã có:

- OpenSearch đang chạy.
- Index `travel_bm25` đã được tạo bằng mapping.
- Dữ liệu trong `data/cleaned/` đã được index vào `travel_bm25`.
- File `.env` có cấu hình:

```env
OPENSEARCH_URL=http://localhost:9200
BM25_INDEX=travel_bm25
```

Nếu chưa index data, xem thêm:

```text
docs/Le Hoang Dat/opensearch_index_run_guide.md
```

## 3. Hướng Dẫn Chạy

### Start OpenSearch

```powershell
docker compose up -d opensearch opensearch-dashboard
```

Kiểm tra OpenSearch:

```powershell
curl.exe http://localhost:9200
```

Kiểm tra số document:

```powershell
curl.exe "http://localhost:9200/travel_bm25/_count"
```

### Start API

Chạy từ root project:

```powershell
venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra health:

```powershell
curl.exe http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok"
}
```

### Gọi keyword search API

```powershell
curl.exe "http://localhost:8000/search?q=khach%20san%20gan%20bien"
```

Hoặc dùng query tiếng Việt có dấu:

```powershell
curl.exe "http://localhost:8000/search?q=kh%C3%A1ch%20s%E1%BA%A1n%20g%E1%BA%A7n%20bi%E1%BB%83n"
```

Nếu dùng trình duyệt, có thể mở trực tiếp:

```text
http://localhost:8000/search?q=khach%20san%20gan%20bien
```

### Xem metrics

```powershell
curl.exe http://localhost:8000/metrics
```

## 4. Hướng Dẫn Benchmark

Chạy benchmark hiện có:

```powershell
venv\Scripts\python.exe scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10
```

Các chỉ số cần ghi lại:

- `Errors`
- `Error rate`
- `Actual QPS`
- `P50`
- `P95`
- `P99`
- `Max`
- `StdDev`

Lưu ý: script benchmark hiện có thể tạo `Actual QPS` cao hơn `Target QPS`. Khi ghi SLO, cần ghi cả hai giá trị để tránh hiểu nhầm điều kiện tải.

## 5. Hướng Dẫn Test

### Test phần keyword search liên quan

```powershell
venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_retrieval.py
```

Kết quả hiện tại:

```text
3 passed
```

### Compile nhanh các file đã thay đổi

```powershell
venv\Scripts\python.exe -m py_compile api\main.py retrieval\lexical_search\service.py tests\test_api.py tests\test_retrieval.py
```

### Full test suite

```powershell
venv\Scripts\python.exe -m pytest
```

Ghi chú: tại thời điểm cập nhật tài liệu này, full suite còn lỗi ở `tests/test_chunking.py` liên quan review chunking trả list rỗng. Lỗi đó không nằm trong phạm vi keyword search refactor.

## 6. Troubleshooting

### API trả HTTP 503

Nguyên nhân thường gặp:

- OpenSearch chưa chạy.
- Index `travel_bm25` chưa tồn tại.
- `.env` đang trỏ sai `OPENSEARCH_URL` hoặc `BM25_INDEX`.

Kiểm tra:

```powershell
curl.exe http://localhost:9200
curl.exe "http://localhost:9200/_cat/indices?v"
```

### Search trả rỗng

Kiểm tra số document:

```powershell
curl.exe "http://localhost:9200/travel_bm25/_count"
```

Nếu `count = 0`, cần chạy lại index data theo guide:

```text
docs/Le Hoang Dat/opensearch_index_run_guide.md
```

### Pytest báo thiếu `opensearchpy`

Nguyên nhân là đang chạy Python global thay vì venv của project.

Chạy bằng:

```powershell
venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_retrieval.py
```

Không chạy bằng:

```powershell
python -m pytest
```

nếu `python` không trỏ vào `venv`.

## 7. Ghi Chú Thiết Kế

- `GET /search` là endpoint tạm để validate BM25 baseline và benchmark keyword search.
- `POST /search` chưa được thêm vì thuộc phase hybrid search.
- Keyword search service hiện là building block để hybrid search dùng lại sau.
- Chưa thêm filter, reranking hoặc vector fusion trong bước này.
- Chưa chuyển sang `AsyncOpenSearch` vì SLO baseline hiện tại vẫn đạt; đây là hướng tối ưu sau nếu tải tăng.

