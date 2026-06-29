# BM25 Search SLO Definition

Tài liệu này chỉ định nghĩa các Service Level Indicators (SLIs), Service Level Objectives (SLOs) và error budget cho BM25-only search trong hệ thống VSF DLKS. Kết quả benchmark thực tế được lưu riêng trong `baseline_latency_report.md`.

## 1. Phạm Vi Áp Dụng

SLO này áp dụng cho BM25-only retrieval:

- Endpoint hiện tại: `GET /search`
- Backend: OpenSearch/Elasticsearch
- Runtime index alias: `vsf_hotels_bm25_current`
- Retrieval mode: keyword/BM25-only
- Chưa bao gồm vector search, hybrid fusion, reranking, context building hoặc LLM generation.

BM25-only search là một thành phần trong pipeline RAG retrieval. Vì vậy latency của BM25 cần đủ thấp để còn ngân sách cho vector retrieval, fusion, reranking và Context API ở các phase sau.

## 2. Service Level Indicators

### Availability SLI

```text
Availability = số request /search thành công / tổng số request /search
```

Request thành công là request trả HTTP `2xx` và có response hợp lệ.

Prometheus metrics liên quan:

```text
search_bm25_requests_total
search_bm25_errors_total
```

### Latency SLI

Latency được đo theo end-to-end client-side latency của request `/search`, bao gồm:

- Thời gian request từ client tới API.
- Thời gian API gọi OpenSearch.
- Thời gian OpenSearch query/fetch.
- Thời gian API serialize response.
- Thời gian client nhận response.

Các percentile cần theo dõi:

```text
P50
P95
P99
```

### Throughput SLI

```text
Sustained QPS = số request thành công / thời gian benchmark hoặc cửa sổ đo
```

Sustained QPS dùng để xác nhận hệ thống duy trì tải mục tiêu mà không tăng error rate hoặc tail latency quá ngưỡng.

## 3. Target SLO Cho BM25-only Search

Target production-oriented cho BM25-only retrieval:

```text
P50 latency <= 250 ms
P95 latency <= 500 ms
P99 latency <= 1000 ms
Error rate <= 0.1%
Sustained QPS >= 50
```

Diễn giải:

- `P50 <= 250 ms`: request thông thường phải phản hồi nhanh để đảm bảo UX tốt.
- `P95 <= 500 ms`: phần lớn request phải nằm dưới nửa giây, đủ tốt cho retrieval trong RAG.
- `P99 <= 1000 ms`: tail latency không nên vượt 1 giây vì pipeline RAG còn nhiều bước phía sau.
- `Error rate <= 0.1%`: search backend phải ổn định, không được thường xuyên timeout hoặc trả lỗi.
- `Sustained QPS >= 50`: hệ thống phải giữ được tối thiểu 50 request/giây trong benchmark chuẩn.

## 4. Error Budget

### Error Rate Budget

```text
Tối đa 0.1% request được phép lỗi trong chu kỳ đo.
```

Ví dụ với 100,000 request:

```text
Tối đa 100 request lỗi.
```

### Latency Budget

Theo SLO `P95 <= 500 ms`, tối đa 5% request được phép vượt quá 500 ms.

Theo SLO `P99 <= 1000 ms`, tối đa 1% request được phép vượt quá 1000 ms.

## 5. Điều Kiện Benchmark Chuẩn

Khi benchmark để đánh giá SLO, cần ghi rõ:

- Target URL và port API.
- Target QPS.
- Actual QPS.
- Duration.
- Concurrency.
- Query file hoặc danh sách query.
- Runtime index alias.
- OpenSearch index version alias đang trỏ tới.
- API có chạy `--reload` hay không.
- OpenSearch heap/container resources.

Benchmark chuẩn khuyến nghị:

```powershell
venv\Scripts\python.exe scripts\benchmark_search.py --target http://localhost:8001 --qps 50 --duration 60 --concurrency 10
```

Khi báo cáo SLO, không chỉ ghi target QPS; phải ghi cả `Actual QPS`.

## 6. Ngưỡng Đánh Giá

| Mức | Điều kiện |
| :--- | :--- |
| Đạt production target | P50 <= 250 ms, P95 <= 500 ms, P99 <= 1000 ms, error rate <= 0.1%, QPS >= 50 |
| Đạt staging/baseline | P95 <= 700 ms, P99 <= 1200 ms, error rate <= 1%, QPS >= 50 |
| Chưa đạt | P95 > 700 ms hoặc P99 > 1200 ms hoặc error rate > 1% |

## 7. Ghi Chú Vận Hành

- SLO này chỉ áp dụng cho BM25-only. Khi có hybrid search, cần định nghĩa SLO riêng cho hybrid retrieval.
- Không dùng kết quả benchmark đơn lẻ làm cam kết production. Nên chạy ít nhất 3 lần và lấy xu hướng ổn định.
- Nếu benchmark chạy với `--reload`, kết quả không đại diện cho production.
- Nếu response trả full `description` hoặc payload lớn, latency client-side có thể cao hơn latency OpenSearch thực tế.
