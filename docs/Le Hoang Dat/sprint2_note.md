# Sprint 2 - Ghi Chú Công Việc Theo Ngày

Tài liệu này tổng hợp các nhiệm vụ đã thực hiện trong Sprint 2 cho phần OpenSearch, BM25 indexing, keyword search, SLO latency và benchmark.

## 09/06/2026 - OpenSearch Dashboard Và Quy Trình Index

### Cấu hình OpenSearch Dashboard

- Thêm service `opensearch-dashboard` vào `docker-compose.yml`.
- Sử dụng image:

```text
opensearchproject/opensearch-dashboards:2
```

- Expose dashboard tại:

```text
http://localhost:5601
```

- Cấu hình dashboard kết nối tới OpenSearch:

```text
OPENSEARCH_HOSTS=["http://opensearch:9200"]
```

### Hoàn thiện quy trình index data vào OpenSearch

- Cập nhật script `indexing/bm25_index/index_bm25.py` để tránh lỗi bulk quá lớn.
- Chuyển từ bulk toàn bộ document sang `streaming_bulk`.
- Thêm cấu hình batch:

```env
BULK_CHUNK_SIZE=25
BULK_MAX_CHUNK_BYTES=2097152
```

- Mục tiêu: tránh lỗi OpenSearch circuit breaker:

```text
429 circuit_breaking_exception
```

- Tạo/cập nhật tài liệu hướng dẫn chạy index:

```text
docs/Le Hoang Dat/opensearch_index_run_guide.md
```

## 10/06/2026 - Chuẩn Hóa Tên Và Version BM25 Index

- Thay naming cũ `travel_bm25` bằng chuẩn versioned index mới.
- Runtime/API dùng alias ổn định:

```env
BM25_INDEX=vsf_hotels_bm25_current
```

- Indexer nạp dữ liệu vào index version:

```env
BM25_TARGET_INDEX=vsf_hotels_bm25_v1_0_0
```

- Thêm alias promote có kiểm soát:

```env
BM25_ALIAS=vsf_hotels_bm25_current
BM25_PROMOTE_ALIAS=false
```

- Script chỉ promote alias khi:
  - `BM25_PROMOTE_ALIAS=true`
  - Bulk indexing không có failed docs

- Thêm rule riêng cho BM25 hotel index vào:

```text
docs/Le Hoang Dat/versioning.md
```

- Ghi rõ `travel_bm25` là legacy index, không dùng cho release mới.

## 10/06/2026 - Tách Keyword Search Sang Layer 6

- Tách logic BM25 keyword search khỏi `api/main.py`.
- Tạo service:

```text
retrieval/lexical_search/service.py
```

- Service chính:

```python
BM25SearchService
```

- API `GET /search` hiện gọi keyword search service thay vì gọi OpenSearch trực tiếp.
- Giữ response shape cũ để không phá benchmark và frontend/demo hiện tại.
- Chưa thêm `POST /search` vì endpoint này thuộc phase hybrid search và Context API sau này.

## 10/06/2026 - Cập Nhật Tài Liệu Keyword Search

- Tạo/cập nhật tài liệu:

```text
docs/Le Hoang Dat/keyword_search_implementation_guide.md
```

- Nội dung gồm:
  - Thay đổi kiến trúc keyword search
  - Cách chạy API
  - Cách gọi `GET /search`
  - Cách xem metrics
  - Cách benchmark
  - Cách test
  - Troubleshooting cho alias/index/OpenSearch

## 10/06/2026 - Đo Baseline Latency Ban Đầu

- Chạy benchmark BM25 search trên port `8001`.
- Kết quả ban đầu:

```text
Actual QPS: 57.86
Error rate: 0.00%
P50: 498.39 ms
P95: 865.88 ms
P99: 1391.82 ms
Max: 1531.66 ms
```

- Đánh giá:
  - Reliability đạt vì không có lỗi request.
  - Throughput đạt vì QPS > 50.
  - Latency chưa đạt production SLO.

- Kết quả được ghi vào:

```text
docs/Le Hoang Dat/baseline_latency_report.md
```

## 11/06/2026 - Tách SLO Target Và Baseline Report

- Cập nhật `docs/Le Hoang Dat/slo_defination.md` để chỉ còn định nghĩa SLO target, không trộn kết quả đo.
- Tạo file report riêng:

```text
docs/Le Hoang Dat/baseline_latency_report.md
```

- Target production cho BM25-only search:

```text
P50 <= 250 ms
P95 <= 500 ms
P99 <= 1000 ms
Error rate <= 0.1%
Sustained QPS >= 50
```

## 11/06/2026 - Tối Ưu BM25 Query Và Runtime

Các quick wins đã thực hiện:

- Thêm `track_total_hits=false` vào BM25 query để tránh chi phí đếm total hits chính xác khi không cần.
- Giảm `_source` trả về, không fetch full `description`.
- Giữ `size=10`.
- Tăng OpenSearch client pool:

```python
OpenSearch(OPENSEARCH_URL, maxsize=25)
```

- Cập nhật `docker-compose.yml` để OpenSearch dùng heap `1g` khi container được recreate:

```text
OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
```

Kết quả benchmark sau quick wins:

```text
Actual QPS: 62.78
Error rate: 0.00%
P50: 449.76 ms
P95: 770.51 ms
P99: 949.98 ms
```

Đánh giá:

- P99 đã đạt target.
- P50 và P95 vẫn chưa đạt production SLO.
- Cần điều tra tiếp scheduler benchmark và bottleneck API/OpenSearch.

## 11/06/2026 - Chuẩn Hóa Benchmark Scheduler

- Phát hiện script `scripts/benchmark_search.py` tạo burst request không đúng với ý nghĩa `--qps` và `--concurrency`.
- Sửa scheduler để:
  - Phát request đều theo target QPS.
  - Dùng semaphore để giới hạn concurrency thật.
  - Tránh burst làm phình P50/P95/P99 không phản ánh đúng tải mục tiêu.

Smoke test 10 giây sau khi sửa scheduler:

```text
Actual QPS: 49.60
P50: 68.00 ms
P95: 109.86 ms
P99: 371.09 ms
Error rate: 0.00%
```

## 11/06/2026 - Đạt BM25-only Production SLO

Benchmark chính thức sau khi chuẩn hóa scheduler:

```powershell
venv\Scripts\python.exe scripts\benchmark_search.py --target http://localhost:8001 --qps 55 --duration 60 --concurrency 10
```

Kết quả:

```text
Total requests: 3300
Successful: 3300
Errors: 0
Error rate: 0.00%
Actual duration: 60.08s
Actual QPS: 54.93
P50: 60.37 ms
P95: 108.13 ms
P99: 142.04 ms
Max: 484.19 ms
```

Đánh giá theo production SLO:

| SLO | Target | Kết quả | Trạng thái |
| :--- | ---: | ---: | :--- |
| Sustained QPS | >= 50 | 54.93 | Đạt |
| Error rate | <= 0.1% | 0.00% | Đạt |
| P50 | <= 250 ms | 60.37 ms | Đạt |
| P95 | <= 500 ms | 108.13 ms | Đạt |
| P99 | <= 1000 ms | 142.04 ms | Đạt |

Kết luận:

```text
BM25-only Search SLO: ĐẠT
```

Kết quả đã được cập nhật vào:

```text
docs/Le Hoang Dat/baseline_latency_report.md
```

## 11/06/2026 - Test Và Verification

- Chạy compile các file liên quan:

```powershell
venv\Scripts\python.exe -m py_compile scripts\benchmark_search.py api\main.py retrieval\lexical_search\service.py
```

- Chạy test liên quan:

```powershell
venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_retrieval.py tests\test_bm25_indexer.py
```

- Kết quả:

```text
9 passed
```

- Full test suite trước đó còn 2 lỗi ngoài phạm vi ở `tests/test_chunking.py`.

## Tài Liệu Đã Tạo/Cập Nhật

- `docs/Le Hoang Dat/opensearch_index_run_guide.md`
- `docs/Le Hoang Dat/keyword_search_implementation_guide.md`
- `docs/Le Hoang Dat/slo_defination.md`
- `docs/Le Hoang Dat/baseline_latency_report.md`
- `docs/Le Hoang Dat/versioning.md`
- `docs/Le Hoang Dat/sprint2_note.md`

## Ghi Chú Cho Bước Tiếp Theo

- Chạy lại benchmark ít nhất 3 lần nếu cần xác nhận độ ổn định production SLO.
- Theo dõi thêm OpenSearch heap, CPU, search thread pool và API latency histogram.
- Khi thêm vector search, hybrid fusion hoặc reranking, cần định nghĩa SLO riêng cho hybrid retrieval.
- Tiếp tục xử lý lỗi còn lại trong `tests/test_chunking.py` nếu thuộc phạm vi Sprint 2.

