# Sprint 1 — BM25 Baseline: Runbook & Ghi chú

## Mục tiêu
Cài đặt phiên bản baseline BM25-only, lập chỉ mục (index) dữ liệu từ thư mục `data/cleaned/` vào index `travel_bm25` của OpenSearch, đo lường độ trễ (P95 latency) để xác định chỉ số SLO baseline.

---

## Các File Được Thêm/Thay Đổi

- [indexing/bm25_index/index_bm25.py](file:///c:/dat/vsf_dlks_search_system/indexing/bm25_index/index_bm25.py) — Script lập chỉ mục dữ liệu khách sạn sạch từ JSON vào OpenSearch (đã căn chỉnh mapping chặt chẽ và chuẩn hóa giá phòng).
- [api/main.py](file:///c:/dat/vsf_dlks_search_system/api/main.py) — API dịch vụ (sử dụng FastAPI) đã được tích hợp tìm kiếm thực tế với OpenSearch và đo đạc Prometheus metrics (metrics: `search_bm25_request_duration_seconds`, `search_bm25_requests_total`, `search_bm25_errors_total`).
- [scripts/benchmark_search.py](file:///c:/dat/vsf_dlks_search_system/scripts/benchmark_search.py) — Công cụ tạo tải giả lập (load generator) và thu thập thống kê độ trễ (P50, P95, P99).

---

## Điều Kiện Tiền Đề (Prerequisites)

1. **Dịch vụ bổ trợ (Docker Containers)**:
   Đảm bảo OpenSearch và Qdrant đang chạy. Khởi động bằng Docker Compose:
   ```bash
   docker-compose up -d opensearch qdrant
   ```
   *Lưu ý: Không khởi động container `api` từ docker-compose để tránh xung đột cổng 8000 khi chạy API cục bộ phục vụ đo benchmark.*

2. **Thư viện Python (Virtual Environment)**:
   Kích hoạt virtual environment và cài đặt đầy đủ các thư viện phụ thuộc:
   ```bash
   # Kích hoạt venv (trên Windows PowerShell)
   .\venv\Scripts\Activate.ps1

   # Cài đặt thư viện
   pip install -r requirements.txt
   ```

---

## Các Bước Thực Hiện Chi Tiết (Step-by-Step Runbook)

### Bước 1: Tạo Index trên OpenSearch với Mapping Chuẩn
Sử dụng công cụ `curl.exe` gửi yêu cầu tạo index với định nghĩa cấu hình schema mapping:
```powershell
curl.exe -X PUT "http://localhost:9200/travel_bm25" -H "Content-Type: application/json" -d "@indexing/bm25_index/index_mapping.json"
```
*Lưu ý: Cần sử dụng chính xác lệnh `curl.exe` trên Windows PowerShell thay vì viết ngắn `curl` (để tránh bị PowerShell hiểu nhầm thành alias cho `Invoke-WebRequest`).*

### Bước 2: Chạy Indexing Dữ Liệu
Đặt các biến môi trường và chạy script để đưa toàn bộ tệp tin khách sạn sạch vào OpenSearch:
```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="travel_bm25"
$env:CLEANED_DATA_DIR="data/cleaned"
python indexing/bm25_index/index_bm25.py
```
Màn hình sẽ hiển thị kết quả đồng bộ thành công: `Indexed: 27 successfully. Failed: 0`.

### Bước 3: Khởi Chạy API Server
Khởi động API Gateway cục bộ trên cổng `8000`:
```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="travel_bm25"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Kiểm tra phản hồi sức khỏe dịch vụ:
```powershell
curl.exe http://localhost:8000/health
# Trả về: {"status":"ok"}
```

### Bước 4: Chạy Benchmark Đo Lường Tải (Đo SLO)
Giả lập tải với lưu lượng mong muốn để đo các phân vị độ trễ (latency percentiles):
```powershell
python scripts/benchmark_search.py --target http://localhost:8000 --qps 50 --duration 60 --concurrency 10
```
Các tham số cấu hình:
- `--target`: Đường dẫn API cần đo (mặc định: `http://localhost:8000`).
- `--qps`: Tần suất truy vấn mục tiêu trên giây (mặc định: `50`).
- `--duration`: Thời gian giả lập tải tính bằng giây (mặc định: `60`).
- `--concurrency`: Số luồng xử lý đồng thời tối đa (mặc định: `10`).

Khi chạy xong, script sẽ kết xuất kết quả chi tiết bao gồm tỉ lệ lỗi và độ trễ P50, P95, P99.

### Bước 5: Thu Thập Metrics Prometheus
Sau khi tiến hành benchmark, quét lấy các thông số giám sát từ API:
```powershell
curl.exe http://localhost:8000/metrics
```
Dữ liệu trả về chứa thông tin phân bố tần suất độ trễ dạng histogram, giúp chúng ta tính toán SLO phía Server.

---

## Ghi chú & Bài Học Kinh Nghiệm

- **Độ trễ Xếp Hàng (Queueing Latency)**: Đo lường thực tế cho thấy độ trễ đo ở phía Client (P95 ~ 800ms) lớn hơn nhiều so với Server-side xử lý trong mã nguồn (P95 ~ 73ms). Điều này xảy ra do cơ chế đồng bộ (sync block) của kết nối OpenSearch làm nghẽn luồng xử lý uvicorn thread pool khi nhận đồng thời nhiều request.
- **Tiến trình tiếp theo**:
  - Chuyển đổi mã nguồn kết nối OpenSearch sang dạng bất đồng bộ (`AsyncOpenSearch`) trong các sprint tiếp theo để tối ưu hóa hàng đợi.
  - Sử dụng các định nghĩa SLO đã chốt tại tệp [slo_defination.md](file:///c:/dat/vsf_dlks_search_system/docs/slo_defination.md) làm chuẩn đối sánh cho Sprint 2 (Vector Search).
