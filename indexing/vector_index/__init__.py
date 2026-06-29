"""Vector indexing package backed by Supabase/Postgres pgvector."""

from indexing.vector_index.pgvector_index import (
    VectorChunkRow,
    build_rows_for_document,
    chunk_to_row,
    index_documents,
    upsert_rows,
    vector_literal,
)

__all__ = [
    "VectorChunkRow",
    "build_rows_for_document",
    "chunk_to_row",
    "index_documents",
    "upsert_rows",
    "vector_literal",
]
