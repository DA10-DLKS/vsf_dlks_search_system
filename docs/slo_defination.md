# Sprint 1 — BM25 Search SLO Definition

Tài liệu này định nghĩa Service Level Indicators (SLIs), Service Level Objectives (SLOs) và Error Budgets cho dịch vụ tìm kiếm BM25 (Sprint 1 baseline) của hệ thống tìm kiếm VSF DLKS. Các chỉ số này được xây dựng dựa trên kết quả chạy load benchmark thực tế ngày 04/06/2026.

---

## 1. Kết quả Load Benchmark Baseline (Sprint 1)

Các số liệu đo đạc từ kịch bản tải thực tế:
- **Thời gian chạy**: 60.31 giây
- **Tổng số request**: 3,650
- **Lưu lượng (Actual QPS)**: 60.52 requests/sec (Mục tiêu: 50 QPS)
- **Concurrency**: 10
- **Tỉ lệ lỗi (Error Rate)**: 0.00% (3,650 thành công, 0 lỗi)

### Phân bố Latency (Thời gian phản hồi)

| Đo lường | Client-side (Đo bởi benchmark client) | Server-side (Đo bởi API/Prometheus) |
| :--- | :--- | :--- |
| **Minimum** | 111.45 ms | < 25.00 ms |
| **P50 (Median)** | 486.39 ms | ~ 45.00 ms |
| **P95** | **812.31 ms** | **~ 73.00 ms** |
| **P99** | 909.95 ms | ~ 98.00 ms |
| **Maximum** | 1082.55 ms | ~ 240.00 ms |
| **Average (Mean)** | 485.66 ms | ~ 55.00 ms |

> [!NOTE]
> **Sự chênh lệch giữa Client-side và Server-side Latency:**
> Do API server sử dụng cơ chế xử lý đồng bộ (synchronous handler thread pool) và OpenSearch driver chặn block thread, khi client gửi dồn dập (QPS cao), các request phải xếp hàng ở hàng đợi socket/uvicorn threadpool.
> Điều này làm tăng độ trễ xếp hàng ở phía Client (P95 = 812.31ms), trong khi thời gian thực thi nghiệp vụ đo tại Server vẫn rất tốt (P95 = 73ms).

---

## 2. Định nghĩa SLI & SLO

Dựa trên kết quả đo lường baseline, chúng tôi thiết lập mục tiêu chất lượng dịch vụ (SLOs) cho Sprint 1 như sau:

### 2.1. Độ tin cậy (Availability)

- **Service Level Indicator (SLI)**:
  Tỉ lệ phần trăm các yêu cầu tìm kiếm `/search` trả về mã trạng thái HTTP thành công (200 OK) so với tổng số yêu cầu gửi tới.
  $$\text{Availability SLI} = \frac{\text{Tổng request thành công (HTTP 200)}}{\text{Tổng request nhận được}} \times 100\%$$
  - *Metric Prometheus*: `sum(rate(search_bm25_requests_total[5m]))` và `sum(rate(search_bm25_errors_total[5m]))`
- **Service Level Objective (SLO)**:
  $$\ge 99.9\% \text{ tổng số request trong vòng 30 ngày}$$
- **Error Budget (Ngân sách lỗi)**:
  **0.1%** tổng số request được phép bị lỗi trong chu kỳ 30 ngày (tương đương tối đa ~1,300 request lỗi với lưu lượng trung bình 50 QPS liên tục).

### 2.2. Hiệu năng (Latency - Độ trễ)

Chúng tôi định nghĩa hai mức SLO để theo dõi cả hiệu năng nội bộ hệ thống và trải nghiệm thực tế của người dùng:

#### Mức 1: Server-side Latency (Đo tại API Gateway / API Server)
- **Service Level Indicator (SLI)**:
  Tỉ lệ phần trăm các request tìm kiếm có thời gian xử lý nội bộ tại server $\le 150\text{ ms}$.
  $$\text{Server Latency SLI} = \frac{\text{Số request xử lý } \le 150\text{ms}}{\text{Tổng số request nhận được}} \times 100\%$$
  - *Metric Prometheus*: `search_bm25_request_duration_seconds_bucket{le="0.15"}` / `search_bm25_request_duration_seconds_count`
- **Service Level Objective (SLO)**:
  $$\ge 95.0\% \text{ tổng số request phản hồi } \le 150\text{ ms (trong 30 ngày)}$$
- **Error Budget**: **5.0%** số request được phép vượt quá 150ms.

#### Mức 2: End-to-End Client Latency (Đo tại phía Client / Consumer)
- **Service Level Indicator (SLI)**:
  Tỉ lệ phần trăm các request tìm kiếm nhận kết quả $\le 900\text{ ms}$ (bao gồm cả độ trễ mạng và độ trễ xếp hàng).
- **Service Level Objective (SLO)**:
  $$\ge 95.0\% \text{ tổng số request phản hồi } \le 900\text{ ms dưới mức tải tiêu chuẩn 50 QPS}$$
- **Error Budget**: **5.0%** số request được phép vượt quá 900ms.

---

## 3. Kế hoạch Duy trì và Cải thiện SLO

Để cải thiện độ trễ phía client (giảm hiện tượng nghẽn hàng đợi uvicorn thread pool) trong các Sprint tiếp theo:
1. **Asynchronous API Client**: Chuyển đổi OpenSearch client trong FastAPI sang phiên bản bất đồng bộ (`AsyncOpenSearch`) và đổi hàm endpoint `/search` sang `async def` để tối ưu luồng xử lý I/O không bị block.
2. **Connection Pooling**: Tối ưu hóa kích thước connection pool của OpenSearch client để tránh thắt nút cổ chai kết nối.
3. **Caching**: Áp dụng phân lớp cache (Redis / In-memory) cho các truy vấn phổ biến.
