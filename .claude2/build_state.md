# Project State

## Goal
Cải thiện lớp Monitoring/Observability của DA10 Search để metric/log/health phản ánh ĐÚNG thực tế vận hành: làm sống 3 metric chết, thêm observability cho LLM + degraded mode, probe dependency định kỳ, vệ sinh logging (request_id, rotation), và bổ sung alert rules. Bám 7 mục ưu tiên trong đánh giá.

## Current Plan
Thực thi tuần tự 5 phase (Phase 0 + 4 phase sửa). Plan chi tiết: `~/.claude/plans/quiet-stirring-breeze.md`.
**Trạng thái: HOÀN TẤT toàn bộ 5 phase — cả 7 mục ưu tiên đã xong & MASTER verify OK.** Chờ MASTER quyết có commit không.

## Phase Progress
* [x] Phase 0 - Khởi tạo Build Journal
* [x] Phase 1 - Làm sống metrics (STAGE/ZERO/CONTEXT) + LLM metric + degraded + rerank_method + method label *(chờ MASTER verify)*
* [x] Phase 2 - Background task probe dependency định kỳ *(chờ MASTER verify)*
* [x] Phase 3 - Vệ sinh logging (request_id, hạ debug SCHEMA, log rotation) — **MASTER đã verify OK** (metrics/log/header đạt; vá thêm bỏ field `taskName`)
* [x] Phase 4 - Grafana dashboard + alert rules + sửa docs — **MASTER đã verify OK** (Prometheus nạp 5 rule không lỗi; Grafana hiện đủ panel mới có data)
* [x] Phase 5 - Truy vết request chậm: log per-request (query + stage_ms) + endpoint + trang UI HTML *(chờ MASTER verify)*

## Completed
- Đã tạo `.claude2/build_state.md` nhằm theo dõi trạng thái dự án (Single Source of Truth).
- **Phase 1** — sửa `observability/metrics/__init__.py` (thêm `method` label cho HTTP_DURATION; thêm SEARCH_DEGRADED, RERANK_METHOD, LLM_DURATION, LLM_REQUESTS); `retrieval/hybrid_search/pipeline.py` (instrument STAGE_DURATION 6 stage + đếm degraded + rerank_method); `context/answer_generator.py` (đo LLM latency + ok/error); `api/main.py` (SEARCH_ZERO_RESULTS, CONTEXT_DURATION, middleware method label + try/finally). Mục đích: làm sống metric chết + thêm observability LLM/degraded.
- **Phase 2** — `api/main.py`: thêm background asyncio task `_dep_probe_loop` chạy `deep_health()` mỗi `DEP_PROBE_INTERVAL` (mặc định 30s) để gauge `da10_dependency_up` luôn tươi khi Prometheus scrape.
- **Phase 3** — `observability/logging/__init__.py` (request_id contextvar + inject vào JSON formatter; đổi sang RotatingFileHandler 10MB×5); `api/main.py` (middleware sinh/propagate `X-Request-ID`; hạ log `[SCHEMA]` xuống DEBUG, bật lại qua `SCHEMA_DEBUG=1`; thêm log sự kiện `search_completed`/`hybrid_search_completed`/`context_completed`).
- Yêu cầu MASTER chạy uvicorn + curl `/metrics` + bắn vài request nhằm xác minh Acceptance Phase 1–3 → **ĐÃ verify OK**.
- **Phase 1–3 fix bổ sung**: `observability/logging/__init__.py` thêm `taskName` vào skip set (Python 3.12 LogRecord) để log sạch field thừa.
- **Phase 4** — `observability/grafana/dashboards/da10_api.json` (Search p95 lọc method=POST; Context p95 đổi sang da10_context_build_duration_seconds; thêm 4 panel: LLM latency, LLM error ratio, degraded rate, rerank method); tạo `observability/alerts.yml` (5 rule); `observability/prometheus.yml` (+rule_files); `docker-compose.yml` (mount alerts.yml); `docs/reports/project_report/07_monitoring.md` (bảng metric + logging + health probe nền + dashboard + mục Alerting/SLO, sửa dẫn sai SLO_GUIDELINE → `docs/Le Hoang Dat/slo_defination.md`). Mục đích: dashboard/alert/docs phản ánh đúng metric mới.

- **Phase 5** — `retrieval/hybrid_search/pipeline.py` (gom stage timing per-request qua `contextvars` → `out["stage_ms"]`); `api/main.py` (log thêm `query`+`stage_ms` vào event hoàn tất; endpoint `GET /observability/slow_requests` đọc `logs/da10.jsonl`); `frontend/slow_requests.html` (trang UI bảng request chậm + breakdown stage, mở tại `/ui/slow_requests.html`); `docs/.../07_monitoring.md` (mục 6b per-request tracing). Mục đích: truy vết "request chậm có query gì + chậm ở stage nào" mà không cần Loki/OTel.
  - **Cập nhật sắp xếp** (theo yêu cầu MASTER): `/observability/slow_requests` trả theo **thời gian giảm dần (mới nhất lên đầu)** thay vì latency giảm dần; `limit` lấy N request gần nhất khớp ngưỡng. UI vẫn tô màu latency + tô đỏ stage chậm nhất để dễ nhận diện request chậm.

## Architecture Decisions
- **Metric LLM**: chỉ đo latency + ok/error, instrument tại `context/answer_generator.py` (chokepoint Node 9). KHÔNG sửa `knowledge_engineering/enrichment/llm.py` (dùng chung ABSA), không lấy token. Lý do: tránh rủi ro cho module đồng đội KE.
- **Alerting**: chỉ alert rules trong Prometheus (`observability/alerts.yml`), không thêm Alertmanager. Lý do: đủ cho demo/đồ án, không cần kênh thông báo ngoài.
- **Probe deps**: background asyncio task trong FastAPI startup, không thêm container blackbox exporter. Lý do: đơn giản, gauge `da10_dependency_up` luôn tươi khi Prometheus scrape `/metrics`.
- **Không OpenTelemetry/tracing**: dùng `request_id` + `STAGE_DURATION` thay thế cho hệ 1-service. Lý do: tránh over-engineer.
- Tất cả metric tiếp tục đăng ký trên `REGISTRY` chung (không tạo metric ngoài `observability/metrics`).

## Issues
- (chưa có)

## Next Step
* [ ] Step 0 - **MASTER verify Phase 5**: restart uvicorn → bắn vài request → mở `localhost:8000/ui/slow_requests.html` xem bảng request chậm + breakdown stage; hoặc `curl /observability/slow_requests`.
* [ ] Step 1 - (Tùy MASTER) Commit thay đổi observability. Mình KHÔNG tự git theo rule.md — chờ MASTER yêu cầu.
