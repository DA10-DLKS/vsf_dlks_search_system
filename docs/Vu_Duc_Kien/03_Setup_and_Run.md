# 03 — Setup & Run guide

> Cách cài đặt, cấu hình `.env`, và chạy tầng API (`api/main.py`) ở local.
> Nguồn: [`requirements.txt`](../../requirements.txt), [`.env.example`](../../.env.example),
> [`Dockerfile`](../../Dockerfile), [`docker-compose.yml`](../../docker-compose.yml).

---

## 1. Yêu cầu môi trường

| Thành phần | Phiên bản / ghi chú |
|-----------|---------------------|
| Python | 3.11 (Docker image dùng `python:3.11-slim`) |
| OS | Chạy được trên Windows / Linux. Team đang dev chính trên **Windows 10** (PowerShell). |
| RAM | Đủ để load model `bge-m3` (embedding) — vài GB. Có thể chạy "candidate-only" nếu thiếu. |
| Dịch vụ ngoài | OpenSearch (:9200), Qdrant (:6333), PostgreSQL (:5432) — **tùy chọn** (xem §6) |

---

## 2. Cài đặt dependencies

Tạo virtualenv rồi cài `requirements.txt`:

```powershell
# Từ thư mục gốc dự án: vsf_dlks_search_system
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Torch:** trong `Dockerfile` torch được cài từ index CPU-only
> (`https://download.pytorch.org/whl/cpu`). Khi cài local, nếu không có GPU nên cài bản CPU để
> nhẹ. `torch` bắt buộc — bge-m3 và cross-encoder cần nó.

Các package chính liên quan API (trích `requirements.txt`):
- **API:** `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`
- **Config:** `pyyaml`, `python-dotenv`
- **Retrieval:** `qdrant-client`, `opensearch-py`, `rank-bm25`
- **Embedding:** `sentence-transformers`, `torch`
- **NLP tiếng Việt:** `underthesea` (bắt buộc — normalize/tách từ, thiếu là pipeline vỡ)
- **Observability:** `prometheus-client`, `structlog`
- **DB:** `psycopg2-binary`, `sqlalchemy`, `alembic`

---

## 3. Biến môi trường (`.env`)

Copy `.env.example` thành `.env` rồi chỉnh:

```powershell
Copy-Item .env.example .env
```

Các biến **API `main.py` thực sự đọc** (qua `os.environ` / `load_dotenv`):

| Biến | Mặc định trong code | Dùng ở đâu / ý nghĩa |
|------|---------------------|----------------------|
| `OPENSEARCH_URL` | `http://localhost:9200` | Kết nối OpenSearch (BM25) |
| `BM25_INDEX` | `vsf_hotels_bm25_current` | Tên index BM25 |
| `USE_RERANKER` | `0` | `1` = bật cross-encoder rerank (nạp model ở startup). Mặc định **off** (đắt, không kéo recall) |
| `DEP_PROBE_INTERVAL` | `30` | Chu kỳ (giây) probe dependency nền → cập nhật gauge `da10_dependency_up` |
| `SCHEMA_DEBUG` | `0` | `1` = hạ log xuống DEBUG, dump cấu trúc `[SCHEMA]` (đối chiếu contract với frontend) |
| `HOTEL_CACHE_PATH` | `data/hotel_detail_cache.json` | Đọc bởi `knowledge_engineering/common/hotel_data.py` (frontend adapter) |
| `LLM_PROVIDER` / `LLM_MODEL` / `*_API_KEY` | `openai` / `gpt-4o-mini` | LLM sinh answer (Node 9) khi gọi `POST /context` hoặc `?answer=true`. Xem §5 |

Các biến khác trong `.env.example` (`DATABASE_URL`, `QDRANT_URL`, `VECTOR_*`, `HYBRID_TOP_K`…)
được **các module tầng dưới** (retrieval/vector, indexing, db) đọc, không phải trực tiếp bởi
`main.py`. Vẫn nên điền đúng để pipeline chạy đủ chức năng.

> 🔎 `PORT` — chỉ dùng trong `Dockerfile` (`--port ${PORT:-8080}`). Khi chạy uvicorn tay,
> port do bạn truyền `--port` (team dùng `8000`, xem §4).

---

## 4. Chạy API ở local

Lệnh chuẩn của team (khớp `SETUP.md`, `QUICKSTART.md`):

```powershell
# Từ thư mục gốc dự án
.venv\Scripts\python.exe -X utf8 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- `-X utf8` — ép UTF-8 (Windows console hay lỗi mã hóa tiếng Việt).
- `--reload` — tự reload khi sửa code (chỉ dùng khi dev).
- App name **`api.main:app`** → chạy từ thư mục gốc dự án (để `api` là package).

**Kiểm tra nhanh:**
```powershell
# Health
Invoke-RestMethod http://localhost:8000/health

# Swagger UI (FastAPI tự sinh)
start http://localhost:8000/docs

# Frontend console tĩnh
start http://localhost:8000/ui
```

- **Swagger/OpenAPI:** `http://localhost:8000/docs` và `/redoc` (FastAPI mặc định).
- **Frontend tĩnh:** mount tại `/ui` (từ folder `frontend/`) — chỉ có nếu folder `frontend/` tồn tại.

> Request đầu tiên sau khi khởi động có thể **hơi lâu** (warmup synonym + load bge-m3 ở startup).
> Đây là cố ý (§ startup ở tài liệu 01) để tránh crash torch trong threadpool.

---

## 5. Cấu hình LLM (cho answer / context)

`POST /context` và `GET /hybrid_search?answer=true`, `GET /...?answer` sẽ gọi LLM qua module
`context/generate_answer`. Provider chọn bằng `.env`, **không sửa code**:

```dotenv
LLM_PROVIDER=openai         # openai | gemini | ollama | claude
LLM_MODEL=gpt-4o-mini       # bỏ trống = mặc định theo provider
OPENAI_API_KEY=sk-...       # chỉ cần key của provider đang dùng
# GOOGLE_API_KEY=...
# ANTHROPIC_API_KEY=...
# OLLAMA_HOST=http://localhost:11434   # chạy offline, miễn phí
```

Nếu không cấu hình LLM: các endpoint search vẫn chạy (chúng không gọi LLM); chỉ `POST /context`
và `answer=true` bị ảnh hưởng.

---

## 6. Chạy dependencies bằng Docker Compose (tùy chọn)

API **vẫn trả `200` khi thiếu OpenSearch/Qdrant** (tụt về candidate-only), nên có thể dev API
mà chưa cần hạ tầng. Nhưng để đủ chức năng hybrid, dựng dịch vụ bằng compose:

```powershell
docker compose up -d postgres opensearch qdrant
# tùy chọn: opensearch-dashboard, prometheus, grafana
docker compose up -d
```

Cổng mapping (`docker-compose.yml`):

| Dịch vụ | Port host | Ghi chú |
|---------|-----------|---------|
| postgres | 5432 | db `da10` / user `da10` / pass `da10` |
| opensearch | 9200 | security plugin **tắt** (dev) |
| opensearch-dashboard | 5601 | |
| qdrant | 6333 | |
| prometheus | 9090 | scrape `/metrics` của API (trỏ `host.docker.internal`) |
| grafana | 3000 | anonymous admin |
| api (image) | 8000 | chỉ khi `docker compose up api` — build từ `Dockerfile` |

> ⚠️ **Chú ý sự khác biệt port:** service `api` trong compose map `8000:8000`, nhưng `Dockerfile`
> `EXPOSE 8080` và `CMD ... --port ${PORT:-8080}`. Nếu chạy container API qua compose mà không set
> `PORT=8000`, cần đảm bảo port trong container khớp mapping. Khi **dev local** thì bỏ qua — ta
> chạy uvicorn tay ở `8000` (§4), thường chỉ dùng compose cho postgres/opensearch/qdrant.

---

## 7. Observability khi chạy

- **Metrics:** `GET http://localhost:8000/metrics` (Prometheus text). Gồm `da10_*` + `search_bm25_*`.
- **Deep health:** `GET /health/deep` → `503` nếu có dependency down.
- **Log JSON:** ghi ra `logs/da10.jsonl` (RotatingFileHandler ~10MB). Xem request chậm qua
  `GET /observability/slow_requests?min_ms=500`.
- **Grafana:** `http://localhost:3000` (nếu bật compose) — dashboard provisioned sẵn trong `observability/`.

---

## 8. Checklist chạy lần đầu

1. `python -m venv .venv` + `pip install -r requirements.txt`
2. `Copy-Item .env.example .env` → điền `OPENSEARCH_URL`, LLM key (nếu cần answer)
3. (tùy chọn) `docker compose up -d postgres opensearch qdrant`
4. Nạp data/index nếu chưa có (ngoài phạm vi `api/` — hỏi phần indexing/ingestion). File
   `data/hotel_detail_cache.json` **phải tồn tại** để `POST /search` trả được data.
5. `uvicorn api.main:app --port 8000 --reload`
6. Mở `/docs` test thử `POST /search` với `{ "query": "resort đà nẵng", "top_n": 5 }`.

> Nếu `POST /search` trả `results: []` → kiểm tra `hotel_detail_cache.json` có tồn tại và index
> retrieval đã nạp chưa; nếu `GET /search` trả `503` → OpenSearch chưa chạy / sai `OPENSEARCH_URL`.
