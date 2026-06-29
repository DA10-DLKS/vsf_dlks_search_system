# vector_index

Trình dựng chỉ mục vector bằng Supabase PostgreSQL + pgvector (Layer 4).

Qdrant là hướng legacy và không còn là vector store mục tiêu cho pipeline mới.

Các thành phần chính:

- `pgvector_index.py`: đọc data sạch, chunk, embed bằng BGE-M3 và upsert vào bảng `text_chunks`.
- Schema Supabase: `sql/supabase_vector_schema.sql`.
