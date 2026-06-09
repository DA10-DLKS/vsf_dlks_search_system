# Sprint 1 - Tóm tắt công việc (BM25-only)

Thời gian: Sprint 1, tập trung vào baseline BM25.

Mục tiêu: thiết lập baseline BM25-only, index dữ liệu sạch trong `data/cleaned/` vào OpenSearch index `travel_bm25`, thêm observability bằng Prometheus, và chuẩn bị benchmark để chốt SLO latency theo p95.

## Những việc đã làm

- Thêm file indexer: `indexing/bm25_index/index_bm25.py`. Script này đọc các file JSON trong `data/cleaned/` và bulk index vào OpenSearch index `travel_bm25`.
- Thêm mapping OpenSearch: `indexing/bm25_index/index_mapping.json`, bao gồm schema, settings, normalizer, nested fields và cấu hình `dynamic: strict`.
- Cập nhật indexer để stream dữ liệu và gửi bulk theo chunk nhỏ, tránh lỗi `429 circuit_breaking_exception` khi OpenSearch chạy local với heap nhỏ.
- Thêm cấu hình bulk indexing vào `.env` và `.env.example`:
  - `BULK_CHUNK_SIZE=25`
  - `BULK_MAX_CHUNK_BYTES=2097152`
- Thêm Prometheus instrumentation vào `api/main.py`:
  - Histogram `search_bm25_request_duration_seconds`
  - Counter `search_bm25_requests_total`
  - Counter `search_bm25_errors_total`
  - Endpoint `/metrics` để Prometheus scrape
  - Endpoint `/search` hiện là mock, chờ tích hợp truy vấn OpenSearch thực tế
- Tạo script benchmark: `scripts/benchmark_search.py`, hỗ trợ load generator async, thu p50, p95, p99, error rate và actual QPS.
- Thêm OpenSearch Dashboard vào `docker-compose.yml` với service `opensearch-dashboard`, expose tại `http://localhost:5601`.
- Tạo run guide index OpenSearch tại `docs/Le Hoang Dat/opensearch_index_run_guide.md`.

## Kết quả hiện tại

- OpenSearch và OpenSearch Dashboard đã có cấu hình Docker Compose.
- Mapping BM25 đã sẵn sàng để tạo index `travel_bm25`.
- Script index dữ liệu đã sẵn sàng và đã được tối ưu để tránh bulk request quá lớn.
- Dữ liệu nguồn nằm trong `data/cleaned/`.
- Prometheus metrics đã expose từ API, nhưng endpoint `/search` vẫn cần tích hợp OpenSearch để thu metrics thực tế.

## Hướng dẫn ngắn để lặp lại

1. Start OpenSearch và Dashboard:

```powershell
docker compose up -d opensearch opensearch-dashboard
```

2. Tạo index từ mapping:

```powershell
curl.exe -X PUT "http://localhost:9200/travel_bm25" `
  -H "Content-Type: application/json" `
  -d "@indexing/bm25_index/index_mapping.json"
```

3. Index dữ liệu sạch:

```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="travel_bm25"
$env:CLEANED_DATA_DIR="data/cleaned"
$env:BULK_CHUNK_SIZE="25"
$env:BULK_MAX_CHUNK_BYTES="2097152"

python indexing/bm25_index/index_bm25.py
```

4. Kiểm tra số lượng document:

```powershell
curl.exe "http://localhost:9200/travel_bm25/_count"
```

5. Test search nhanh:

```powershell
curl.exe -X GET "http://localhost:9200/travel_bm25/_search" `
  -H "Content-Type: application/json" `
  -d '{ "query": { "match": { "description": "khach san gan bien" } }, "size": 5 }'
```

6. Start API:

```powershell
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

7. Chạy benchmark:

```powershell
python scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10 --query-file tests/test_queries/queries.txt
```

## Lưu ý lỗi thường gặp

Nếu gặp lỗi:

```text
TransportError(429, 'circuit_breaking_exception', '[parent] Data too large ...')
```

Nguyên nhân là bulk request quá lớn so với heap OpenSearch. Giảm batch size rồi chạy lại:

```powershell
$env:BULK_CHUNK_SIZE="10"
$env:BULK_MAX_CHUNK_BYTES="1048576"
python indexing/bm25_index/index_bm25.py
```

Nếu lệnh search trả lỗi JSON parse hoặc `curl: Could not resolve host`, nguyên nhân thường là quote JSON sai trong PowerShell. Nên bọc JSON bằng dấu nháy đơn `'...'` và giữ nguyên dấu nháy kép `"` bên trong JSON.

## Next steps

- Tích hợp OpenSearch vào handler `/search` trong `api/main.py`.
- Verify kết quả search thực tế từ index `travel_bm25`.
- Chạy benchmark chính thức để thu p50, p95, p99 và error rate.
- Cập nhật SLO definition dựa trên kết quả benchmark thực tế.
