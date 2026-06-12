# Supabase pgvector Run Guide

Tài liệu này hướng dẫn cài đặt vector index và vector search service dùng Supabase Cloud PostgreSQL + pgvector. Kế hoạch hiện tại không dùng Qdrant cho vector search.

## 1. Thành Phần Đã Thêm

- Schema SQL: `sql/supabase_vector_schema.sql`
- Vector indexer: `indexing/vector_index/pgvector_index.py`
- Vector search service: `retrieval/vector_search/service.py`

Không dùng `db/models.py` cho phần này vì database thật nằm trên Supabase Cloud và model local đã outdate.

## 2. Cấu Hình Môi Trường

`.env` cần có:

```env
DATABASE_URL=postgresql://<user>:<password>@<supabase-host>:5432/postgres
VECTOR_STORE=pgvector
VECTOR_INDEX_TABLE=text_chunks
VECTOR_EMBEDDING_MODEL=BAAI/bge-m3
VECTOR_DIMENSION=1024
VECTOR_TOP_K=10
VECTOR_INDEX_BATCH_SIZE=32
CLEANED_DATA_DIR=data/cleaned
```

`QDRANT_URL` và `QDRANT_COLLECTION` là legacy, không dùng cho vector path mới.

## 3. Tạo Schema Trên Supabase

Chạy nội dung file sau trong Supabase SQL Editor:

```text
sql/supabase_vector_schema.sql
```

Schema tạo:

- Extension `vector`
- Bảng `text_chunks`
- HNSW cosine index cho cột `embedding vector(1024)`
- Index phụ cho `hotel_id`, `source_type`, `metadata`

Kiểm tra nhanh:

```sql
SELECT count(*) FROM text_chunks;
```

## 4. Chạy Vector Indexer

Indexer đọc JSON sạch, chunk, embed bằng BGE-M3 và upsert vào Supabase.

```powershell
$env:DATABASE_URL="postgresql://<user>:<password>@<supabase-host>:5432/postgres"
$env:VECTOR_INDEX_TABLE="text_chunks"
$env:VECTOR_EMBEDDING_MODEL="BAAI/bge-m3"
$env:VECTOR_DIMENSION="1024"
$env:VECTOR_INDEX_BATCH_SIZE="32"
$env:CLEANED_DATA_DIR="data/cleaned"

venv\Scripts\python.exe -m indexing.vector_index.pgvector_index
```

Kết quả mong đợi:

```text
Indexed <n> vector chunks into text_chunks.
```

## 5. Test Vector Search Service

Service chưa có public API. Có thể smoke test trong Python:

```python
import os
import psycopg2
from indexing.embedding import get_embedding_model
from retrieval.vector_search import PgVectorSearchService

conn = psycopg2.connect(os.environ["DATABASE_URL"])
model = get_embedding_model("BAAI/bge-m3")
service = PgVectorSearchService(conn, model)

result = service.search("khach san gan bien", top_k=5)
print(result)
```

## 6. Ghi Chú Vận Hành

- Supabase Cloud là source of truth cho vector DB.
- Docker PostgreSQL local và `db/models.py` không dùng cho vector search implementation.
- BGE-M3 tạo embedding 1024 chiều, khớp schema `VECTOR(1024)`.
- Nếu đổi embedding model hoặc dimension, cần tạo schema/index version mới.
- Public `POST /search` sẽ thuộc phase hybrid search sau này.

