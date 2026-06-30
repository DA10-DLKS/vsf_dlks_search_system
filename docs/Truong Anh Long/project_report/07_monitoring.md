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
| `da10_http_request_duration_seconds` | Histogram | endpoint, **method** | latency HTTP (buckets 50ms→5s) — `method` tách GET vs POST `/search` |
| `da10_search_zero_results_total` | Counter | search_mode | search trả 0 kết quả (`hybrid`/`frontend`) |
| `da10_context_build_duration_seconds` | Histogram | — | thời gian build context `/context` (buckets →120s) |
| `da10_stage_duration_seconds` | Histogram | stage | latency từng nhóm node pipeline (intent/filter/text_retrieval/fusion/rerank/context) |
| `da10_search_degraded_total` | Counter | source | search chạy thiếu nguồn retrieval (`bm25`/`vector`/`both`) → tụt candidate-only |
| `da10_rerank_method_total` | Counter | method | rerank thực tế (`cross-encoder`/`density-fallback`) — theo dõi tỉ lệ reranker neural chạy thật |
| `da10_llm_duration_seconds` | Histogram | — | latency gọi LLM Node 9 (buckets →60s) |
| `da10_llm_requests_total` | Counter | status | đếm LLM `ok`/`error` |
| `da10_eval_metric` | Gauge | name, k | recall/precision/hit/mrr/ndcg lần chạy gần nhất |
| `da10_eval_queries_total` | Gauge | — | số câu golden đã chạy |
| `da10_eval_duration_seconds` | Histogram | — | thời gian chạy golden |
| `da10_dependency_up` | Gauge | dependency | 1=up / 0=down (cập nhật bởi **probe nền định kỳ**) |
| `da10_dependency_probe_duration_seconds` | Histogram | dependency | latency probe |
| `search_bm25_request_duration_seconds` | Histogram | endpoint | latency BM25 (baseline) |
| `search_bm25_requests_total` / `_errors_total` | Counter | endpoint | đếm request/lỗi BM25 |

### 2.3 Thu thập tự động

Middleware HTTP trong `api/main.py` đo **mọi** request:
- Dùng **route path template** làm label `endpoint` (vd `/hybrid_search`) thay vì URL thật → **tránh nổ cardinality**.
- Thêm label `method` → tách `GET /search` (BM25 baseline, ~70ms) khỏi `POST /search` (hybrid, nhiều giây) vốn cùng route path.
- Bọc `try/finally` → request ném exception vẫn được đo + đếm (status mặc định 500).
- Ghi `da10_http_request_duration_seconds{endpoint,method}` + `da10_http_requests_total{endpoint,method,status}`.

**Instrument trong pipeline** (`retrieval/hybrid_search/pipeline.py`): mỗi nhóm node bọc context-manager `_stage(name)` ghi `da10_stage_duration_seconds`; đếm `da10_search_degraded_total` khi thiếu service text retrieval; đếm `da10_rerank_method_total` theo phương pháp rerank thực chạy.

**Instrument LLM** (`context/answer_generator.py` — chokepoint Node 9, phủ cả `/context` lẫn `/hybrid_search?answer=true`): đo `da10_llm_duration_seconds` + đếm `da10_llm_requests_total{status}`. **Không** sửa `knowledge_engineering/enrichment/llm.py` (module dùng chung ABSA) → không lấy token usage.

Mỗi endpoint nghiệp vụ (`/search`, `/hybrid_search`, `/context`, `/eval/golden`) cũng đếm requests/errors/latency riêng (search_bm25_*).

---

## 3. Structured logging (`observability/logging/__init__.py`)

- **JSON one-line per event** → stdout + `logs/da10.jsonl` (qua `RotatingFileHandler` 10MB × 5 file → chặn log phình vô hạn).
- Timestamp **giờ VN (+07:00)** (`_VnJsonFormatter`).
- **`request_id`**: middleware sinh `uuid4().hex[:12]` (hoặc nhận header `X-Request-ID` từ client/proxy), lưu vào `contextvars.ContextVar` → formatter **tự chèn `request_id` vào MỌI dòng log** trong cùng request, và trả lại header `X-Request-ID`. Nhờ vậy truy được toàn bộ log của 1 request.
- Mỗi endpoint nghiệp vụ log 1 dòng sự kiện hoàn tất: `event=search_completed`/`hybrid_search_completed`/`context_completed` kèm `latency_ms`, `n_results`, `rerank_method`.
- Debug dump cấu trúc response (`[SCHEMA]`) đã **hạ xuống mức DEBUG** (mặc định im, tránh ô nhiễm log); bật lại khi cần đối chiếu contract bằng `SCHEMA_DEBUG=1`.
- `ensure_ascii=False` → tiếng Việt đọc được trực tiếp; singleton (`get_logger`), `propagate=False` → không nhân đôi log.

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

**Probe nền định kỳ**: Prometheus scrape `/metrics` chứ **không** gọi `/health/deep`, nên nếu chỉ cập nhật gauge khi gọi tay endpoint thì `da10_dependency_up` sẽ cũ/chết. Một **background asyncio task** (khởi động ở `startup`, `api/main.py`) chạy `deep_health()` mỗi `DEP_PROBE_INTERVAL` giây (mặc định 30s, qua threadpool vì probe blocking) → gauge **luôn tươi** khi scrape. Probe 1 lần ngay lúc startup để có giá trị tức thì.

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
- **Dashboard**: `dashboards/da10_api.json` — panel cho:
  - Search p95/p50 (`POST /search`, tách khỏi GET BM25 nhờ label `method`).
  - Context p95/p50 (dùng `da10_context_build_duration_seconds` buckets →120s, **không** bão hòa như histogram HTTP cap 5s).
  - Request rate, error rate (5xx), zero-result rate, stage p95 breakdown, dependency up.
  - **LLM p95/p50 latency**, **LLM error ratio**, **degraded search rate**, **rerank method distribution**.
  - Golden eval (Recall/Precision/Hit/MRR/nDCG lần chạy gần nhất).
- Grafana bật anonymous Admin (`GF_AUTH_ANONYMOUS_ENABLED=true`) → mở `localhost:3000` xem ngay, không cần login (demo).

---

## 6b. Truy vết request chậm (per-request tracing nhẹ)

Metrics chỉ cho biết stage nào chậm **ở mức tổng hợp**. Để biết **một request cụ thể có query gì và chậm ở stage nào**, hệ thống dùng "poor man's tracing" qua log thay vì Loki/OpenTelemetry:

- `pipeline.py` gom thời gian từng stage của **chính request đó** vào `out["stage_ms"]` (qua `contextvars`, song song với histogram Prometheus).
- Mỗi endpoint log sự kiện hoàn tất kèm `request_id` + `query` + `stage_ms{...}` + `latency_ms` vào `logs/da10.jsonl`.
- Endpoint `GET /observability/slow_requests?min_ms=&limit=` đọc log, trả các request đã hoàn tất, sắp theo latency giảm dần.
- **Trang UI** `frontend/slow_requests.html` (mở `localhost:8000/ui/slow_requests.html`): bảng request chậm + thanh breakdown từng stage, tô đỏ stage chậm nhất, có ngưỡng lọc + auto-refresh.

Truy nhanh bằng dòng lệnh (cần `jq`):
```bash
cat logs/da10.jsonl | jq -c 'select(.event=="search_completed" and .latency_ms>1000) | {request_id, query, latency_ms, stage_ms}'
```

---

## 7. Alerting & SLO

**Alert rules** (`observability/alerts.yml`, nạp vào Prometheus qua `rule_files`, mount trong `docker-compose.yml`): xem ở tab **Alerts** của Prometheus/Grafana — *chưa* gắn Alertmanager nên không gửi thông báo ngoài (đủ cho demo).

| Alert | Điều kiện | Mức |
|---|---|---|
| `HighErrorRate` | tỉ lệ 5xx > 5% trong 5m | warning |
| `HighSearchLatency` | p95 `POST /search` > 1.5s trong 10m | warning |
| `DependencyDown` | `da10_dependency_up == 0` trong 1m | critical |
| `SearchDegraded` | có request degraded (thiếu BM25/vector) trong 5m | warning |
| `LLMErrors` | tỉ lệ lỗi LLM > 20% trong 15m | warning |

**SLO**: định nghĩa mục tiêu SLO thật ở `docs/Le Hoang Dat/slo_defination.md`. (Lưu ý: `SLO_GUIDELINE.md` ở root **không** phải định nghĩa SLO — đó là *runbook BM25 Sprint 1*.) Các metric `da10_http_request_duration_seconds`, `da10_http_requests_total{status}`, `da10_dependency_up` là cơ sở tính SLI và alert ở trên.

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
