# Sprint 1 - BM25 Search SLO Definition

Tài liệu này định nghĩa Service Level Indicators (SLIs), Service Level Objectives (SLOs) và Error Budgets cho dịch vụ tìm kiếm BM25 của hệ thống VSF DLKS trong Sprint 1.

Kết quả dưới đây được cập nhật từ benchmark chạy ngày 09/06/2026 trên môi trường local:

```powershell
python scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10
```

## 1. Kết Quả Load Benchmark Baseline

### Điều kiện đo

- Endpoint: `GET /search`
- Target QPS: `50`
- Actual QPS: `99.78`
- Duration cấu hình: `60s`
- Actual duration: `60.13s`
- Concurrency: `10`
- Error count: `0`
- Error rate: `0.00%`
- Search backend: OpenSearch BM25 index `travel_bm25`

Lưu ý: benchmark hiện ghi nhận `Actual QPS = 99.78`, cao hơn target `50 QPS`. Vì vậy kết quả này có thể xem là baseline ở mức tải gần `100 QPS`, không phải đúng `50 QPS`.

### Phân Bố Latency

| Đo lường | Client-side latency |
| :--- | ---: |
| Minimum | 104.08 ms |
| Maximum | 672.07 ms |
| Mean | 272.95 ms |
| Median | 267.95 ms |
| P50 | 267.95 ms |
| P95 | 440.18 ms |
| P99 | 495.77 ms |
| StdDev | 104.34 ms |

### Đánh giá kết quả

Kết quả benchmark đạt tốt cho baseline Sprint 1:

- Không có lỗi request: `0.00%`.
- P95 dưới `500 ms` dù actual throughput gần `100 QPS`.
- P99 dưới `500 ms`, vẫn nằm trong vùng chấp nhận được cho baseline BM25 local.
- Chưa cần tối ưu OpenSearch ngay nếu mục tiêu Sprint 1 là xác lập baseline ổn định.

Điểm cần lưu ý là script benchmark đang tạo tải cao hơn target. Trước khi dùng số liệu này làm cam kết chính thức, cần chuẩn hóa lại benchmark để `Actual QPS` bám sát `Target QPS`.

## 2. Định Nghĩa SLI Và SLO

### 2.1. Availability

Service Level Indicator:

```text
Availability SLI = số request /search thành công / tổng số request /search
```

Prometheus metrics liên quan:

```text
search_bm25_requests_total
search_bm25_errors_total
```

Service Level Objective:

```text
Availability >= 99.9% trong chu kỳ 30 ngày
```

Error Budget:

```text
Tối đa 0.1% request được phép lỗi trong chu kỳ 30 ngày
```

### 2.2. End-to-End Client Latency

Service Level Indicator:

```text
Tỷ lệ request /search có client-side latency <= 500 ms
```

Service Level Objective đề xuất cho Sprint 1:

```text
P95 latency <= 500 ms
```

Điều kiện áp dụng:

- Môi trường local Docker.
- OpenSearch single-node.
- Index `travel_bm25`.
- Endpoint `GET /search`.
- Duration benchmark `60s`.
- Concurrency `10`.
- Target load tối thiểu `50 QPS`.

Error Budget:

```text
Tối đa 5% request được phép vượt quá 500 ms
```

Với kết quả hiện tại:

```text
P95 = 440.18 ms
Error rate = 0.00%
```

SLO latency `P95 <= 500 ms` đang đạt.

### 2.3. Tail Latency

Service Level Indicator:

```text
P99 latency của request /search
```

Service Level Objective đề xuất:

```text
P99 latency <= 800 ms
```

Với kết quả hiện tại:

```text
P99 = 495.77 ms
```

SLO tail latency `P99 <= 800 ms` đang đạt.

## 3. Kết Luận Sprint 1

Baseline BM25 hiện tại đạt yêu cầu SLO đề xuất:

| SLO | Mục tiêu | Kết quả đo | Trạng thái |
| :--- | :--- | :--- | :--- |
| Availability | >= 99.9% | 100.00% | Đạt |
| Error rate | <= 1.0% | 0.00% | Đạt |
| P95 latency | <= 500 ms | 440.18 ms | Đạt |
| P99 latency | <= 800 ms | 495.77 ms | Đạt |

Chưa cần tối ưu backend ngay ở Sprint 1. Việc nên ưu tiên trước là chuẩn hóa script benchmark để `Actual QPS` gần với `Target QPS`, sau đó chạy lại 2-3 lần để xác nhận độ ổn định của P95/P99.

## 4. Kế Hoạch Duy Trì Và Cải Thiện

Các hướng cải thiện nên cân nhắc ở sprint sau nếu latency tăng hoặc throughput yêu cầu cao hơn:

1. Chuẩn hóa benchmark để kiểm soát chính xác QPS.
2. Giới hạn số field trả về từ OpenSearch bằng `_source` filtering nếu response quá lớn.
3. Thêm `size` mặc định hợp lý cho query search, ví dụ `size=10`.
4. Tối ưu connection pool của OpenSearch client.
5. Cân nhắc dùng `AsyncOpenSearch` nếu API chịu tải đồng thời cao.
6. Thêm cache cho các truy vấn phổ biến nếu workload có tính lặp lại.
