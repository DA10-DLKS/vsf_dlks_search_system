# SETUP — Chạy hệ thống sau khi pull về

Hướng dẫn cho đồng nghiệp: pull nhánh này về → chạy được backend search.

**Đã có sẵn trong repo (KHÔNG phải tạo lại):**
- `data/cleaned/*.json` — 520 khách sạn đã clean (tên/brand/nearby chuẩn hóa).
- `knowledge_engineering/enrichment/knowledge_objects.json` + KE output — nhãn ontology đã enrich.
- `.docker_volumes/qdrant_storage/` — **Qdrant vector index đã embed sẵn (520 hotel)**. KHÔNG cần re-embed (re-embed mất nhiều giờ trên CPU).

**Phải tự dựng lại 1 lần (nhanh):**
- BM25 / OpenSearch index (~520 doc, vài phút) — KHÔNG commit vì nhạy version.

---

## Yêu cầu
- Docker Desktop
- Python 3.11 + venv (đã có `requirements.txt`)

## Các bước

### 1. Cài Python deps
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Bật Docker (Qdrant + OpenSearch)
```powershell
docker compose up -d qdrant opensearch
```
- **Qdrant** lên với data đã embed sẵn (520 hotel) — không cần làm gì thêm.
- **OpenSearch** lên trống — bước 3 sẽ build index.

> Lưu ý: KHÔNG cần `postgres` cho luồng search (backend chỉ dùng Qdrant + OpenSearch).

### 3. Build BM25 index (OpenSearch) — chỉ làm 1 lần
```powershell
.venv\Scripts\python.exe -X utf8 -m indexing.bm25_index.create_index --recreate
.venv\Scripts\python.exe -X utf8 -m indexing.bm25_index.index_bm25
```
- `index_bm25` đọc `data/cleaned` → đẩy vào OpenSearch. Xong khi báo `Indexed: 520 ... Failed: 0`.
- Nếu vài doc `ConnectionTimeout`: chạy lại `index_bm25` lần nữa (idempotent, bù phần thiếu).

### 4. Bật backend
```powershell
.venv\Scripts\python.exe -X utf8 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
→ Mở `http://localhost:8000/docs` (Swagger) hoặc `http://localhost:8000/ui` (console).

---

## Kiểm tra nhanh
```powershell
# Qdrant đủ 520 hotel?
.venv\Scripts\python.exe -X utf8 -c "from qdrant_client import QdrantClient; print(QdrantClient(url='http://localhost:6333').get_collection('vsf_travel'))"

# thử query
curl "http://localhost:8000/hybrid_search?q=khách sạn vinpearl ở phú quốc&top_n=5"
```

## Nếu Qdrant không lên / lỗi
- KHÔNG xóa `.docker_volumes/qdrant_storage` (đó là vector đã embed).
- `docker compose restart qdrant` rồi đợi vài phút (optimizer chạy).
- Nếu vẫn lỗi: re-embed lại (chậm) — `.venv\Scripts\python.exe -X utf8 -m indexing.vector_index.qdrant_index` (đọc data/cleaned, có checkpoint resume).
