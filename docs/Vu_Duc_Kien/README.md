# Tài liệu bàn giao — Vũ Đức Kiên

Bộ tài liệu cho 2 phần mình phụ trách trong hệ thống DA10, viết để người tiếp nhận có thể tiếp
tục maintain khi mình vắng:
1. **API** — folder [`api/`](../../api/) (tầng Platform Services / Layer 8).
2. **Monitoring & Logging** — folder [`observability/`](../../observability/) + tích hợp trong `api/main.py`.

> **Phạm vi API:** [`api/main.py`](../../api/main.py) + [`api/frontend_adapter.py`](../../api/frontend_adapter.py)
> (các folder `api/app`, `api/routes`, `api/schemas` hiện là scaffolding **rỗng**).

## Phần A — API (đọc theo thứ tự)

| # | Tài liệu | Nội dung |
|---|----------|----------|
| 1 | [01_API_Overview_Architecture.md](01_API_Overview_Architecture.md) | Sơ đồ tổng quan, luồng request→response, quan hệ giữa các file/module |
| 2 | [02_API_Reference.md](02_API_Reference.md) | Từng endpoint: method, path, tham số, schema, mã lỗi, ví dụ thực tế |
| 3 | [03_Setup_and_Run.md](03_Setup_and_Run.md) | Cài đặt, `.env`, chạy local, dependencies, port |
| 4 | [04_Business_Logic_Decision_Notes.md](04_Business_Logic_Decision_Notes.md) | Quy tắc nghiệp vụ hardcode (parse giá, lọc phòng, ngưỡng…), lý do thiết kế, nợ kỹ thuật |

## Phần B — Monitoring & Logging

| # | Tài liệu | Nội dung |
|---|----------|----------|
| 5 | [05_Monitoring_Architecture.md](05_Monitoring_Architecture.md) | Đo cái gì, Prometheus/Grafana, danh mục metric, dashboard, cách truy cập |
| 6 | [06_Logging_Guide.md](06_Logging_Guide.md) | Log format JSON, level, vị trí log, trace request theo `request_id`, debug |
| 7 | [07_Alerting_and_Runbook.md](07_Alerting_and_Runbook.md) | 5 alert đang có, ngưỡng, quy trình xử lý sự cố, lệnh restart |

## Tài liệu tham chiếu (cũ)

- [VuDucKien_api_schema_proposal.md](VuDucKien_api_schema_proposal.md) — ⚠️ bản **đề xuất** schema
  ban đầu (`/api/v1/...`). **Không khớp** code đang chạy; chỉ giữ làm lịch sử thiết kế.

## Tóm tắt 30 giây

**API:**
- 10 endpoint, tất cả trong `main.py`. Chia 2 nhóm: **GET** (debug, shape pipeline) và **POST**
  `/search` + `/context` (frontend, đi qua `frontend_adapter.py`).
- API là lớp mỏng: định tuyến + đo đạc + dịch shape. "Bộ não" tìm kiếm ở `retrieval/`.
- Chạy: `uvicorn api.main:app --port 8000 --reload`.
- Điểm nghiệp vụ then chốt: parse giá "trên/dưới X triệu" (intent parser), map hạng giá →
  ngưỡng VND (`PRICE_BUDGET`≤800k, `PRICE_LUXURY`≥2tr), lọc phòng theo dải giá, tách search
  (không LLM) khỏi context (có LLM). Xem tài liệu 04.

**Monitoring & Logging:**
- Metric `prometheus_client` → `GET /metrics` (1 `REGISTRY` chung, gộp `da10_*` + `search_bm25_*`).
- **Prometheus** (:9090) scrape 15s + chạy alert; **Grafana** (:3000) dashboard `DA10 API`.
- Log JSON (stdout + `logs/da10.jsonl`, xoay vòng ~60MB), trace bằng `request_id` (header `X-Request-ID`).
- 5 alert (chỉ hiển thị, **chưa** có Alertmanager): error 5xx, latency search, dependency down,
  search degraded, LLM errors. Xem tài liệu 07.
