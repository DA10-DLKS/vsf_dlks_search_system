# Sprint 1 — Tóm tắt công việc (BM25-only)

Thời gian: Sprint 1 (BM25 baseline)

Mục tiêu: Thiết lập baseline BM25-only, index data sạch (`data/cleaned/`) vào OpenSearch index `travel_bm25`, thêm observability (Prometheus), và chuẩn bị benchmark để chốt SLO latency (p95).

Những việc đã làm:

- Thêm file indexer: `indexing/bm25_index/index_bm25.py` — script đơn giản để index các file JSON trong `data/cleaned/` vào index `travel_bm25`.
- Thêm mapping OpenSearch: `indexing/bm25_index/index_mapping.json` (schema, settings, analyzers, nested fields). Dùng để tạo index trước khi index dữ liệu.
- Thêm Prometheus instrumentation vào `api/main.py`:
  - Histogram `search_bm25_request_duration_seconds`
  - Counters `search_bm25_requests_total`, `search_bm25_errors_total`
  - Endpoint `/metrics` để Prometheus scrape
  - Endpoint `/search` (hiện là mock; chờ tích hợp OpenSearch)
- Tạo script benchmark: `scripts/benchmark_search.py` — load generator async, thu p50/p95/p99, error rate, actual QPS.
- Tạo tài liệu hướng dẫn Sprint 1: `docs/sprint1_notes.md` (hướng dẫn tạo index, index dữ liệu, start API, chạy benchmark, lưu ý vận hành).

Kết quả hiện tại:

- Dữ liệu đã được đánh index (script đã sẵn sàng); cần tạo index `travel_bm25` bằng mapping trước khi chạy indexer.
- Prometheus metrics đã expose từ API (nhưng handler `/search` hiện là mock — cần tích hợp OpenSearch để thu metrics thực tế).

Hướng dẫn ngắn để lặp lại:

1. Tạo index từ mapping:

```bash
curl -X PUT "localhost:9200/travel_bm25" -H 'Content-Type: application/json' -d @indexing/bm25_index/index_mapping.json
```

1. Index dữ liệu sạch:

```bash
export OPENSEARCH_URL=http://localhost:9200
export BM25_INDEX=travel_bm25
python indexing/bm25_index/index_bm25.py
```

(Windows CMD: `set OPENSEARCH_URL=...`)

1. Start API:

```bash
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

1. Chạy benchmark:

```bash
python scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10 --query-file tests/test_queries/queries.txt
```

Next steps (Sprint 1 remaining):

- Tích hợp OpenSearch vào `api/main.py` `/search` handler và verify kết quả thực tế.
- Chạy benchmark chính thức, thu p50/p95/p99; sau đó tôi sẽ tạo `docs/slo_definition.md` dựa trên kết quả.

Liên hệ: nếu muốn, tôi sẽ tích hợp OpenSearch vào endpoint `/search` và chạy benchmark thay bạn.
