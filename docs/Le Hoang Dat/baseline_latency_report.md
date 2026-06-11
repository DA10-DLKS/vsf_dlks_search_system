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

