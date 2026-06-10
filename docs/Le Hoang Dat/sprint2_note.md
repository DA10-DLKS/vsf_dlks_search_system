# Sprint 2 - Ghi Chú Công Việc Trong Tuần

Tài liệu này tổng hợp các nhiệm vụ đã thực hiện trong tuần cho phần OpenSearch, BM25 indexing, keyword search và SLO.

## 1. Cấu Hình OpenSearch Dashboard

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

## 2. Hoàn Thiện Quy Trình Index Data Vào OpenSearch

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

- Tạo tài liệu hướng dẫn chạy index:

```text
docs/Le Hoang Dat/opensearch_index_run_guide.md
```

## 3. Chuẩn Hóa Tên Và Version BM25 Index

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

## 4. Tách Keyword Search Sang Layer 6

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

## 5. Cập Nhật Tài Liệu Keyword Search

- Tạo tài liệu:

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

## 6. Đo Và Cập Nhật SLO Latency

- Đánh giá kết quả benchmark BM25 search.
- Kết quả đo:

```text
Actual QPS: 99.78
Error rate: 0.00%
P50: 267.95 ms
P95: 440.18 ms
P99: 495.77 ms
Max: 672.07 ms
```

- Kết luận:
  - Baseline BM25 đạt SLO đề xuất `P95 <= 500 ms`.
  - Chưa cần tối ưu backend ngay ở Sprint 2.
  - Cần lưu ý benchmark đang tạo actual QPS cao hơn target QPS.

- Cập nhật tài liệu:

```text
docs/Le Hoang Dat/slo_defination.md
```

## 7. Test Và Verification

- Thêm test cho keyword search service và API:

```text
tests/test_api.py
tests/test_retrieval.py
```

- Thêm test cho BM25 indexer:

```text
tests/test_bm25_indexer.py
```

- Các case đã test:
  - API `GET /search` dùng keyword search service.
  - BM25 service build query đúng.
  - Indexer dùng `BM25_TARGET_INDEX`.
  - Fallback sang `BM25_INDEX` nếu thiếu target index.
  - Không promote alias khi flag false.
  - Không promote alias khi bulk có failed docs.
  - Promote alias khi indexing thành công.

- Kết quả test liên quan:

```text
9 passed
```

- Full test suite còn 2 lỗi ngoài phạm vi ở `tests/test_chunking.py`.

## 8. Tài Liệu Đã Tạo/Cập Nhật

- `docs/Le Hoang Dat/opensearch_index_run_guide.md`
- `docs/Le Hoang Dat/keyword_search_implementation_guide.md`
- `docs/Le Hoang Dat/slo_defination.md`
- `docs/Le Hoang Dat/versioning.md`
- `docs/Le Hoang Dat/sprint2_note.md`

## 9. Ghi Chú Cho Tuần Tiếp Theo

- Chuẩn hóa benchmark để `Actual QPS` bám sát `Target QPS`.
- Xử lý lỗi còn lại trong `tests/test_chunking.py` nếu thuộc phạm vi Sprint 2.
- Sau khi hybrid search sẵn sàng, thiết kế `POST /search` làm input cho Context API.
- Cân nhắc thêm filter/ranking metadata cho BM25 nếu cần phục vụ demo hoặc evaluation.
