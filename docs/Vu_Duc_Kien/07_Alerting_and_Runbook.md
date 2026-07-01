# 07 — Alerting & Runbook

> **Người phụ trách:** Vũ Đức Kiên
> **Nguồn sự thật:** [`observability/alerts.yml`](../../observability/alerts.yml) +
> [`observability/prometheus.yml`](../../observability/prometheus.yml) + [`docker-compose.yml`](../../docker-compose.yml).

---

## 1. Alert hoạt động thế nào

- Rule định nghĩa trong [`alerts.yml`](../../observability/alerts.yml), nạp vào Prometheus qua
  `rule_files` trong [`prometheus.yml`](../../observability/prometheus.yml) (`evaluation_interval: 15s`).
- **CHƯA cấu hình Alertmanager** → alert **chỉ hiển thị** ở tab **Alerts** của Prometheus
  (`http://localhost:9090/alerts`) và trong Grafana. **Không** có email/Slack/telegram.
  → Muốn được thông báo chủ động phải tự thêm Alertmanager. Hiện tại là **giám sát thủ công**:
  người trực mở dashboard/Prometheus để thấy alert chuyển sang `FIRING`.
- Ngưỡng đặt "vừa phải cho môi trường demo" — **chỉnh theo SLO thật** khi lên production.

**Trạng thái một alert:** `inactive` → `pending` (điều kiện đúng nhưng chưa đủ thời gian `for:`)
→ `firing` (đã đủ `for:`).

---

## 2. Bảng alert hiện có

| # | Alert | Điều kiện (expr rút gọn) | `for` | Severity |
|---|-------|--------------------------|-------|----------|
| 1 | `HighErrorRate` | tỉ lệ 5xx / tổng request > **5%** | 5m | warning |
| 2 | `HighSearchLatency` | p95 `POST /search` > **1.5s** | 10m | warning |
| 3 | `DependencyDown` | `da10_dependency_up == 0` | 1m | **critical** |
| 4 | `SearchDegraded` | `rate(da10_search_degraded_total[5m]) > 0` | 5m | warning |
| 5 | `LLMErrors` | tỉ lệ LLM `status="error"` > **20%** | 10m | warning |

Biểu thức đầy đủ (copy từ code) ở mục 4.

---

## 3. Nguyên tắc xử lý chung (đọc trước)

1. **Xác định phạm vi:** mở Grafana `DA10 API` xem panel liên quan + Prometheus *Status → Targets*
   xem API còn được scrape (`UP`) không.
2. **Soi log theo request_id** (xem [06_Logging_Guide.md](06_Logging_Guide.md)) hoặc
   `GET /observability/slow_requests`.
3. **Kiểm tra dependency:** `GET /health/deep`.
4. **Chỉ restart khi cần** và theo đúng lệnh ở mục 5. Restart API **không** mất dữ liệu (API
   stateless); restart OpenSearch/Qdrant/Postgres dùng volume nên dữ liệu vẫn còn.
5. **Ghi lại** `request_id` / thời điểm / panel để hậu kiểm.

---

## 4. Runbook theo từng alert

### 4.1 `HighErrorRate` — 5xx > 5% (warning)
```promql
sum(rate(da10_http_requests_total{status=~"5.."}[5m]))
/ clamp_min(sum(rate(da10_http_requests_total[5m])), 1e-9) > 0.05
```
**Nghĩa:** API trả nhiều lỗi 5xx (thường `500` từ pipeline/adapter/LLM, hoặc `503` backend).

**Chẩn đoán:**
1. Panel *Error Rate (5xx req/s)* xem endpoint nào lỗi.
2. `Get-Content logs\da10.jsonl -Tail 100` tìm exception / `detail=`.
3. `GET /health/deep` — nếu có dep down → nhảy sang [4.3](#43-dependencydown--dependency-down-critical).

**Nguyên nhân thường gặp → xử lý:**
- OpenSearch/Qdrant down → `503` ở `/search`, `/hotel/{id}/ask` → khởi động lại dep (mục 5).
- Lỗi LLM ở `/context` → xem [4.5](#45-llmerrors--llm-lỗi--20-warning).
- Bug code sau deploy → xem commit gần nhất, rollback nếu cần.

---

### 4.2 `HighSearchLatency` — p95 POST /search > 1.5s (warning)
```promql
histogram_quantile(0.95,
  rate(da10_http_request_duration_seconds_bucket{endpoint="/search",method="POST"}[5m])
) > 1.5
```
**Chẩn đoán — tìm stage nghẽn** (panel *Stage p95 Latency* hoặc `da10_stage_duration_seconds`):
| Stage cao | Nghĩa | Hướng xử lý |
|-----------|-------|-------------|
| `text_retrieval` | OpenSearch/Qdrant chậm | Kiểm tra tải/health 2 service; xem index có sẵn |
| `rerank` | Cross-encoder bật | Cân nhắc tắt `USE_RERANKER` (mặc định off) |
| `context` | LLM chậm | Bình thường nếu có sinh answer; `POST /search` **không** gọi LLM nên stage này thường nhỏ |
| `filter`/`fusion` | Xử lý in-memory | Hiếm; kiểm tra kích thước candidate pool |

**Ghi chú:** đã biết client-side p95 (~800ms) cao hơn server-side (~73ms baseline BM25) do
OpenSearch sync block nghẽn threadpool uvicorn (xem `SLO_GUIDELINE.md`). Nếu latency toàn cục cao
đều, nghi ngờ nghẽn threadpool hơn là 1 stage.

---

### 4.3 `DependencyDown` — dependency down (**critical**)
```promql
da10_dependency_up == 0    # for 1m
```
Nhãn `{{ $labels.dependency }}` cho biết cái nào: `opensearch` / `qdrant` / `postgres`.

**Xử lý:**
1. Xác nhận: `GET /health/deep` (xem `checks.<dep>.message`).
2. Kiểm tra container: `docker compose ps`.
3. Restart đúng service (mục 5). Chờ ~30s (probe nền chu kỳ `DEP_PROBE_INTERVAL=30s` sẽ cập nhật
   lại gauge — alert tự `inactive` khi `da10_dependency_up == 1`).
4. Nếu không lên: xem log container `docker compose logs <service> --tail 100`.

**Tác động khi từng dep down:**
- `opensearch` → `GET /search` trả `503`; hybrid tụt degraded (candidate-only) — API vẫn `200`.
- `qdrant` → `GET /hotel/{id}/ask` trả `503`; hybrid mất nguồn vector (degraded).
- `postgres` → chỉ ảnh hưởng phần dùng DB (không phải luồng search chính, vốn đọc file cache).

---

### 4.4 `SearchDegraded` — thiếu nguồn retrieval (warning)
```promql
sum(rate(da10_search_degraded_total[5m])) > 0    # for 5m
```
**Nghĩa:** search đang chạy **thiếu BM25 và/hoặc vector** → tụt "candidate-only", chất lượng
kết quả giảm nhưng API vẫn `200` (không lỗi). Nhãn `source` = `bm25` / `vector` / `both`.

**Xử lý:** thực chất là hệ quả của dep down / index chưa sẵn:
1. `GET /health/deep` + panel *Degraded Search Rate* / *Dependency Up*.
2. Nếu OpenSearch up nhưng vẫn degraded `bm25` → **index BM25 chưa tồn tại** (`_get_bm25_service`
   trả `None` khi index vắng). Kiểm tra `BM25_INDEX` và nạp index (xem phần indexing).
3. Nếu `vector` → Qdrant/model bge-m3 chưa sẵn → kiểm tra Qdrant + log startup warmup.

---

### 4.5 `LLMErrors` — LLM lỗi > 20% (warning)
```promql
sum(rate(da10_llm_requests_total{status="error"}[15m]))
/ clamp_min(sum(rate(da10_llm_requests_total[15m])), 1e-9) > 0.2
```
**Nghĩa:** Node 9 sinh câu trả lời lỗi nhiều → `llm_context` có thể rỗng ở `POST /context`.
`error` = thiếu API key / hết quota / mạng / parse lỗi.

**Xử lý:**
1. Panel *LLM Error Ratio* + log event `context_completed` có `has_answer=false`.
2. Kiểm tra cấu hình LLM (`.env`): `LLM_PROVIDER`, `LLM_MODEL`, `*_API_KEY` tương ứng
   (xem [03_Setup_and_Run.md §5](03_Setup_and_Run.md)).
3. Kiểm tra quota/mạng của provider. Có thể tạm đổi provider (vd `ollama` chạy offline) mà
   **không sửa code** — chỉ đổi `.env` rồi restart API.
4. Lưu ý: lỗi LLM **không** làm hỏng search — chỉ ảnh hưởng phần answer ở `/context`.

---

## 5. Lệnh vận hành (restart / kiểm tra)

> Chạy từ thư mục gốc dự án. Dịch vụ dùng Docker Compose ([`docker-compose.yml`](../../docker-compose.yml)).

```powershell
# Trạng thái + log
docker compose ps
docker compose logs opensearch --tail 100
docker compose logs qdrant --tail 100
docker compose logs prometheus --tail 50

# Restart từng dependency (dữ liệu giữ nguyên nhờ volume)
docker compose restart opensearch
docker compose restart qdrant
docker compose restart postgres

# Restart Prometheus/Grafana (nếu dashboard/scrape lỗi)
docker compose restart prometheus grafana

# API chạy trên host (uvicorn) — restart = Ctrl+C rồi chạy lại:
.venv\Scripts\python.exe -X utf8 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Kiểm tra nhanh sau restart:**
```powershell
Invoke-RestMethod http://localhost:8000/health          # {"status":"ok"}
Invoke-RestMethod http://localhost:8000/health/deep     # từng dep "ok"
start http://localhost:9090/targets                     # da10-api UP?
start http://localhost:9090/alerts                      # alert đã inactive?
```

---

## 6. Ai đụng gì (phân vai gợi ý)

| Loại sự cố | Người xử lý chính | Đụng tới |
|-----------|-------------------|----------|
| Alert / metric / dashboard / log | **Vũ Đức Kiên** (monitoring, logging) + phụ trách API | `observability/`, `api/main.py` |
| OpenSearch / index BM25 | Người phụ trách indexing/lexical | `indexing/`, `retrieval/lexical_search` |
| Qdrant / vector / bge-m3 | Người phụ trách vector search | `retrieval/vector_search` |
| Pipeline retrieval / rerank | Người phụ trách retrieval | `retrieval/hybrid_search` |
| LLM / context / answer | Người phụ trách context/KE | `context/`, `.env` LLM |

> Cập nhật bảng này theo phân công thực tế của team.

---

## 7. Việc còn thiếu / nợ (bàn giao)

1. **Chưa có Alertmanager** → alert không tự gửi. Ưu tiên thêm nếu cần trực 24/7.
2. **Ngưỡng alert là mức demo** — cần chốt lại theo SLO thật (đặc biệt `HighSearchLatency` 1.5s).
3. **Log chỉ local** (stdout + file), chưa tập trung (Loki/ELK).
4. **Không có tracing thật** (OTel) — chỉ `request_id` + `slow_requests`.
5. Prometheus target dùng `host.docker.internal:8000` (Windows/Mac). Trên Linux thuần cần chỉnh
   `prometheus.yml` (vd `extra_hosts` hoặc `network_mode: host`).

---

## 8. Tài liệu liên quan
- [05_Monitoring_Architecture.md](05_Monitoring_Architecture.md) — metric & dashboard.
- [06_Logging_Guide.md](06_Logging_Guide.md) — log & trace request.
- [03_Setup_and_Run.md](03_Setup_and_Run.md) — chạy compose, `.env`, LLM.
