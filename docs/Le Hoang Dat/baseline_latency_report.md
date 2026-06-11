# Baseline Latency Report

Tài liệu này lưu các kết quả benchmark latency thực tế cho BM25-only search. SLO target chính thức được định nghĩa trong `slo_defination.md`.

## 1. Benchmark Ngày 10/06/2026 - Port 8001

Lệnh chạy:

```powershell
venv\Scripts\python.exe scripts\benchmark_search.py --target http://localhost:8001 --qps 50 --duration 60 --concurrency 10
```

Kết quả tổng quan:

```text
Total requests: 3500
Successful: 3500
Errors: 0
Error rate: 0.00%
Actual duration: 60.50s
Actual QPS: 57.86
```

Latency:

| Metric | Value |
| :--- | ---: |
| Min | 133.93 ms |
| Max | 1531.66 ms |
| Mean | 509.21 ms |
| Median | 498.39 ms |
| P50 | 498.39 ms |
| P95 | 865.88 ms |
| P99 | 1391.82 ms |
| StdDev | 234.05 ms |

Đánh giá theo target hiện tại:

| SLO | Target | Kết quả | Trạng thái |
| :--- | ---: | ---: | :--- |
| Sustained QPS | >= 50 | 57.86 | Đạt |
| Error rate | <= 0.1% | 0.00% | Đạt |
| P50 | <= 250 ms | 498.39 ms | Không đạt |
| P95 | <= 500 ms | 865.88 ms | Không đạt |
| P99 | <= 1000 ms | 1391.82 ms | Không đạt |

Kết luận:

- Reliability đạt: không có lỗi request.
- Throughput đạt: actual QPS lớn hơn 50.
- Latency chưa đạt target BM25-only production.
- Tail latency cao, đặc biệt `P95` và `P99`.

## 2. Nhận Định Production Engineering

Benchmark port 8001 cho thấy hệ thống đang ở mức:

```text
Functional baseline / staging candidate
```

Chưa nên xem là production-ready cho RAG retrieval vì BM25-only đã có `P95 = 865.88 ms`. Khi thêm vector retrieval, hybrid fusion, reranking và context building, latency tổng sẽ còn tăng.

Các bottleneck cần điều tra trước:

1. API có đang chạy với `--reload` hay không.
2. Response payload có trả full `description` quá lớn hay không.
3. OpenSearch query có dùng `_source` filtering và `size=10` chưa.
4. Query có cần `track_total_hits=false` để giảm chi phí đếm total hits không.
5. OpenSearch local Docker có đủ heap/CPU/RAM không.
6. API/OpenSearch client có nghẽn connection pool hoặc thread pool không.

## 3. Hướng Tối Ưu Ưu Tiên

Quick wins:

- Chạy API benchmark không dùng `--reload`.
- Thêm `track_total_hits=false` vào query BM25 nếu không cần total hits chính xác.
- Giới hạn `_source`, tránh trả full `description` trong benchmark latency.
- Đảm bảo `size=10`.
- Warm up trước benchmark.

Medium effort:

- Tăng OpenSearch heap từ `512m` lên `1g` nếu máy đủ RAM.
- Tăng `maxsize` connection pool của OpenSearch client.
- Benchmark từng field set để tìm field làm query chậm.
- Dùng `_profile` để phân biệt query phase và fetch phase.

Hard optimization:

- Chuyển sang `AsyncOpenSearch` hoặc chạy nhiều API worker nếu concurrency cao.
- Thiết kế cache cho query lặp lại.
- Tối ưu mapping/analyzer sau khi có query profiling.
- Thiết kế latency budget riêng cho hybrid retrieval.

## 4. Benchmark Ngày 11/06/2026 - Port 8001 Sau Quick Wins

Các tối ưu đã áp dụng trước lần đo này:

- API chạy trên port `8001`, không dùng `--reload`.
- Thêm `track_total_hits=false` vào BM25 query.
- Giảm `_source` trả về, không fetch full `description`.
- Giữ `size=10`.
- Tăng OpenSearch client pool lên `maxsize=25`.
- Cập nhật cấu hình Docker Compose cho OpenSearch heap `1g` khi container được recreate.

Lệnh chạy:

```powershell
venv\Scripts\python.exe scripts\benchmark_search.py --target http://localhost:8001 --qps 50 --duration 60 --concurrency 10
```

Kết quả tổng quan:

```text
Total requests: 3800
Successful: 3800
Errors: 0
Error rate: 0.00%
Actual duration: 60.53s
Actual QPS: 62.78
```

Latency:

| Metric | Value |
| :--- | ---: |
| Min | 115.57 ms |
| Max | 1082.68 ms |
| Mean | 458.80 ms |
| Median | 449.76 ms |
| P50 | 449.76 ms |
| P95 | 770.51 ms |
| P99 | 949.98 ms |
| StdDev | 198.62 ms |

Đánh giá theo target hiện tại:

| SLO | Target | Kết quả | Trạng thái |
| :--- | ---: | ---: | :--- |
| Sustained QPS | >= 50 | 62.78 | Đạt |
| Error rate | <= 0.1% | 0.00% | Đạt |
| P50 | <= 250 ms | 449.76 ms | Không đạt |
| P95 | <= 500 ms | 770.51 ms | Không đạt |
| P99 | <= 1000 ms | 949.98 ms | Đạt |

So với lần đo ngày 10/06/2026:

| Metric | Trước tối ưu | Sau quick wins | Thay đổi |
| :--- | ---: | ---: | ---: |
| Actual QPS | 57.86 | 62.78 | +8.5% |
| Mean | 509.21 ms | 458.80 ms | -9.9% |
| P50 | 498.39 ms | 449.76 ms | -9.8% |
| P95 | 865.88 ms | 770.51 ms | -11.0% |
| P99 | 1391.82 ms | 949.98 ms | -31.7% |

Kết luận:

- Quick wins cải thiện tail latency rõ rệt, đặc biệt P99.
- Hệ thống vẫn chưa đạt production SLO vì P50 và P95 còn cao.
- Bước tiếp theo cần tách đo direct OpenSearch latency và API latency để xác định bottleneck chính.

## 5. Benchmark Ngày 11/06/2026 - Sau Khi Chuẩn Hóa Benchmark Scheduler

Thay đổi trước lần đo này:

- Sửa `scripts/benchmark_search.py` để phát request đều theo target QPS.
- Dùng semaphore để giới hạn concurrency thật theo tham số `--concurrency`.
- Tránh burst 50 request đồng thời mỗi vòng như scheduler cũ.
- Giữ các quick wins đã áp dụng:
  - `track_total_hits=false`
  - `_source` filtering không fetch full `description`
  - `size=10`
  - OpenSearch client pool `maxsize=25`

Lệnh chạy:

```powershell
venv\Scripts\python.exe scripts\benchmark_search.py --target http://localhost:8001 --qps 55 --duration 60 --concurrency 10
```

Kết quả tổng quan:

```text
Total requests: 3300
Successful: 3300
Errors: 0
Error rate: 0.00%
Actual duration: 60.08s
Actual QPS: 54.93
```

Latency:

| Metric | Value |
| :--- | ---: |
| Min | 30.45 ms |
| Max | 484.19 ms |
| Mean | 68.10 ms |
| Median | 60.37 ms |
| P50 | 60.37 ms |
| P95 | 108.13 ms |
| P99 | 142.04 ms |
| StdDev | 30.22 ms |

Đánh giá theo production target:

| SLO | Target | Kết quả | Trạng thái |
| :--- | ---: | ---: | :--- |
| Sustained QPS | >= 50 | 54.93 | Đạt |
| Error rate | <= 0.1% | 0.00% | Đạt |
| P50 | <= 250 ms | 60.37 ms | Đạt |
| P95 | <= 500 ms | 108.13 ms | Đạt |
| P99 | <= 1000 ms | 142.04 ms | Đạt |

Kết luận:

- BM25-only search đã đạt toàn bộ production SLO hiện tại.
- Nguyên nhân chính làm benchmark cũ xấu là scheduler tạo burst request quá lớn so với concurrency mong muốn.
- Sau khi chuẩn hóa scheduler, kết quả phù hợp hơn với direct OpenSearch latency đã đo được.
- Quick wins query vẫn nên giữ vì giảm payload và tránh chi phí đếm total hits không cần thiết.

## 6. Trạng Thái Hiện Tại

Trạng thái sau lần đo mới nhất:

```text
BM25-only Search SLO: ĐẠT
```

Điều kiện đã đạt:

- `P50 <= 250 ms`: đạt, hiện `60.37 ms`
- `P95 <= 500 ms`: đạt, hiện `108.13 ms`
- `P99 <= 1000 ms`: đạt, hiện `142.04 ms`
- `Error rate <= 0.1%`: đạt, hiện `0.00%`
- `Sustained QPS >= 50`: đạt, hiện `54.93`

Các bước tiếp theo nếu tiếp tục hardening:

- Chạy lại benchmark ít nhất 3 lần để xác nhận độ ổn định.
- Theo dõi OpenSearch heap, CPU, search thread pool và API latency histogram khi chạy lâu hơn.
- Khi thêm vector/hybrid/rerank, tạo SLO riêng cho hybrid retrieval thay vì dùng lại SLO BM25-only.
