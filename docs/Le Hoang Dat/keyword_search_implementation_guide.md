# Keyword Search Implementation Guide

Tài liệu này ghi lại cách keyword search BM25 đang được triển khai và cách chạy với BM25 alias/version mới.

## 1. Trạng Thái Hiện Tại

Keyword search đã được tách khỏi `api/main.py` sang Layer 6:

```text
retrieval/lexical_search/service.py
```

Service chính:

```python
BM25SearchService
```

API runtime không trỏ trực tiếp vào index version. API đọc:

```env
BM25_INDEX=vsf_hotels_bm25_current
```

Alias `vsf_hotels_bm25_current` sẽ được trỏ sang version đã validate, ví dụ:

```text
vsf_hotels_bm25_current -> vsf_hotels_bm25_v1_0_0
```

`travel_bm25` là legacy index, không dùng cho release mới.

## 2. Endpoint Keyword Search

Endpoint hiện tại:

```text
GET /search?q=<query>
```

Không thêm `POST /search` ở giai đoạn keyword-only. `POST /search` thuộc phase hybrid search và Context API sau này.

Response giữ compatible:

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

## 3. Điều Kiện Trước Khi Chạy API

Đảm bảo:

- OpenSearch đang chạy.
- Đã tạo index version như `vsf_hotels_bm25_v1_0_0`.
- Đã index data vào target version.
- Alias `vsf_hotels_bm25_current` đã được promote sang version hợp lệ.

Kiểm tra alias:

```powershell
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
```

## 4. Chạy API

```powershell
venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra health:

```powershell
curl.exe http://localhost:8000/health
```

Gọi search:

```powershell
curl.exe "http://localhost:8000/search?q=khach%20san%20gan%20bien"
```

## 5. Metrics

```powershell
curl.exe http://localhost:8000/metrics
```

Metrics hiện có:

```text
search_bm25_request_duration_seconds
search_bm25_requests_total
search_bm25_errors_total
```

## 6. Benchmark

```powershell
venv\Scripts\python.exe scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10
```

Khi ghi SLO, cần ghi cả `Target QPS` và `Actual QPS` vì script benchmark hiện có thể tạo tải cao hơn target.

## 7. Test

Test keyword search và indexer:

```powershell
venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_retrieval.py tests\test_bm25_indexer.py
```

Compile nhanh:

```powershell
venv\Scripts\python.exe -m py_compile api\main.py retrieval\lexical_search\service.py indexing\bm25_index\index_bm25.py
```

Full suite:

```powershell
venv\Scripts\python.exe -m pytest
```

Ghi chú: full suite có thể còn lỗi ngoài phạm vi keyword search ở `tests/test_chunking.py`.

## 8. Troubleshooting

### API trả HTTP 503

Kiểm tra OpenSearch và alias:

```powershell
curl.exe http://localhost:9200
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
```

Kiểm tra `.env`:

```env
BM25_INDEX=vsf_hotels_bm25_current
```

### Search trả rỗng

Kiểm tra alias đang trỏ tới index có document:

```powershell
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
curl.exe "http://localhost:9200/vsf_hotels_bm25_v1_0_0/_count"
```

Nếu count bằng `0`, chạy lại quy trình index trong:

```text
docs/Le Hoang Dat/opensearch_index_run_guide.md
```

