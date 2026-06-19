# Báo cáo 07 — Monitoring & Observability

Lớp observability (`observability/`) cho phép vận hành "nhìn thấy" hệ thống: **metrics** (Prometheus/Grafana), **structured logging** (JSON), **deep health** (probe phụ thuộc), và **golden evaluation** đẩy lên dashboard. Tất cả gom vào **một registry chung** và một endpoint `/metrics` duy nhất.

---

## 1. Kiến trúc tổng thể

```
API (FastAPI, uvicorn trên host)
  ├─ middleware đo mọi request → da10_http_*
  ├─ /metrics  → generate_latest(REGISTRY)  (gộp da10_* + search_bm25_*)
  ├─ /health        → liveness đơn giản
  ├─ /health/deep   → probe OpenSearch + Qdrant + Postgres
  └─ logs/da10.jsonl (structured JSON)
        ▲ scrape
Prometheus (docker, :9090)  →  Grafana (docker, :3000, anonymous Admin)
```

`docker-compose.yml`: Prometheus dùng `extra_hosts: host.docker.internal:host-gateway` để scrape API chạy trên host (uvicorn ngoài Docker). Grafana auto-provision datasource + dashboard.

---

## 2. Metrics (`observability/metrics/__init__.py`)

### 2.1 Registry chung — tránh duplicate

Toàn bộ collector đăng ký trên **`REGISTRY`** (một `CollectorRegistry` riêng, không phải global). Nhờ vậy `/metrics` gộp cả `da10_*` (observability mới) lẫn `search_bm25_*` (baseline cũ) trong **một** `generate_latest(REGISTRY)`. Nguyên tắc: **không tạo metric object ở nơi khác** → tránh lỗi duplicate registration.

### 2.2 Bộ metric (§6.2 monitoring_plan)

| Metric | Loại | Label | Đo gì |
|---|---|---|---|
| `da10_http_requests_total` | Counter | endpoint, method, status | tổng request |
| `da10_http_request_duration_seconds` | Histogram | endpoint | latency HTTP (buckets 50ms→5s) |
| `da10_search_zero_results_total` | Counter | search_mode | search trả 0 kết quả |
| `da10_context_build_duration_seconds` | Histogram | — | thời gian build context (→120s) |
| `da10_stage_duration_seconds` | Histogram | stage | latency từng node pipeline |
| `da10_eval_metric` | Gauge | name, k | recall/precision/hit/mrr/ndcg lần chạy gần nhất |
| `da10_eval_queries_total` | Gauge | — | số câu golden đã chạy |
| `da10_eval_duration_seconds` | Histogram | — | thời gian chạy golden |
| `da10_dependency_up` | Gauge | dependency | 1=up / 0=down |
| `da10_dependency_probe_duration_seconds` | Histogram | dependency | latency probe |
| `search_bm25_request_duration_seconds` | Histogram | endpoint | latency BM25 (baseline) |
| `search_bm25_requests_total` / `_errors_total` | Counter | endpoint | đếm request/lỗi BM25 |

### 2.3 Thu thập tự động

Middleware HTTP trong `api/main.py` đo **mọi** request:
- Dùng **route path template** làm label `endpoint` (vd `/hybrid_search`) thay vì URL thật → **tránh nổ cardinality**.
- Ghi `da10_http_request_duration_seconds` + `da10_http_requests_total{endpoint,method,status}`.

Mỗi endpoint nghiệp vụ (`/search`, `/hybrid_search`, `/context`, `/eval/golden`) cũng đếm requests/errors/latency riêng (search_bm25_*).

---

## 3. Structured logging (`observability/logging/__init__.py`)

- **JSON one-line per event** → stdout + `logs/da10.jsonl`.
- Timestamp **giờ VN (+07:00)** (`_VnJsonFormatter`).
- Dùng `logger.info("", extra={"event": "search_completed", "request_id": rid, ...})` → mọi field trong `extra` được merge vào JSON (lọc bỏ field nội bộ của LogRecord).
- `ensure_ascii=False` → tiếng Việt đọc được trực tiếp trong log.
- Singleton (`get_logger`), `propagate=False` → không nhân đôi log.

Log JSON cho phép truy vết theo `request_id`, query, intent, số candidate, rerank_method, latency từng stage — phục vụ debug và phân tích chất lượng tìm kiếm.

---

## 4. Deep health (`observability/health.py`)

`GET /health/deep` probe trực tiếp 3 phụ thuộc qua biến môi trường (không phụ thuộc config nội bộ):

| Dependency | Probe |
|---|---|
| OpenSearch | `OpenSearch(url).ping()` |
| Qdrant | `QdrantClient(url).get_collections()` |
| Postgres | `SELECT 1` |

Mỗi probe (`_probe`):
- đo latency, cập nhật gauge `da10_dependency_up` (1/0) + histogram `da10_dependency_probe_duration_seconds`.
- **nuốt mọi lỗi** để luôn trả status (không làm endpoint vỡ).

`deep_health()` trả `(body, all_ok)`:
- `body` = `{status, checks{dep:{status, latency_ms|message}}, index_opensearch, index_qdrant}`.
- `all_ok=True` chỉ khi **tất cả** deps `ok` → API trả **HTTP 503** nếu bất kỳ dep nào down (cho load balancer/k8s biết).

`GET /health` (liveness) thì luôn `{"status":"ok"}` — phân biệt liveness (process sống) vs readiness (deps sẵn).

---

## 5. Golden evaluation → dashboard

Endpoint `GET /eval/golden` (`api/main.py`) chạy golden dataset on-demand:
- Tham số: `k` (top-K), `limit` (số câu), `use_services` (full vector+BM25 vs candidate-only).
- Trả summary (Recall/Precision/Hit/MRR/nDCG) + per-query + duration + mode.
- **Đẩy lên Prometheus**: cập nhật gauge `da10_eval_metric{name,k}`, `da10_eval_queries_total`, `da10_eval_duration_seconds` → Grafana hiển thị chất lượng retrieval lần chạy gần nhất.

UI (`evaluation_dashboard.html`) gọi endpoint này để theo dõi metric theo thời gian.

---

## 6. Grafana (`observability/grafana/`)

- **Auto-provisioning**: `provisioning/datasources/datasource.yml` (Prometheus), `provisioning/dashboards/provider.yml` (load dashboard).
- **Dashboard**: `dashboards/da10_api.json` — panel cho latency, throughput, error rate, dependency health, eval metric.
- Grafana bật anonymous Admin (`GF_AUTH_ANONYMOUS_ENABLED=true`) → mở `localhost:3000` xem ngay, không cần login (demo).

---

## 7. SLO

Hệ thống có `SLO_GUIDELINE.md` ở root định nghĩa mục tiêu (latency, error budget). Các metric ở trên (`da10_http_request_duration_seconds`, `_errors_total`, `da10_dependency_up`) là cơ sở để tính SLI và cảnh báo.

---

## 8. Khởi động & truy cập

```bash
# Hạ tầng + monitoring stack
docker compose up -d prometheus grafana opensearch qdrant postgres

# API trên host (để Prometheus scrape qua host.docker.internal)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Truy cập
curl localhost:8000/metrics          # Prometheus exposition
curl localhost:8000/health/deep      # deep health (503 nếu dep down)
open  localhost:9090                  # Prometheus
open  localhost:3000                  # Grafana (anonymous Admin)
open  localhost:8000/eval/golden?limit=10   # chạy golden eval
```

---

## 9. Tóm tắt nguyên tắc thiết kế

- **Một registry, một `/metrics`** — gộp metric cũ + mới, không duplicate.
- **Cardinality an toàn** — label theo route template, không theo URL thật.
- **Probe nuốt lỗi** — health luôn trả status, không tự vỡ.
- **Liveness ≠ readiness** — `/health` vs `/health/deep`.
- **Eval là first-class** — chất lượng retrieval cũng là metric vận hành, đẩy thẳng lên Grafana.
