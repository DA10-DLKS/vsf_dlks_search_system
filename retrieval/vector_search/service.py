"""Semantic vector search service backed by Supabase/Postgres pgvector."""

from __future__ import annotations

import os
from typing import Any

from indexing.embedding import get_embedding_model
from indexing.embedding.base import EmbeddingModel
from indexing.vector_index.pgvector_index import DEFAULT_TABLE_NAME, validate_identifier, vector_literal


DEFAULT_TOP_K = 10


class PgVectorSearchService:
    """Layer 6 vector search service for RAG retrieval."""

    def __init__(
        self,
        connection,
        embedding_model: EmbeddingModel,
        table_name: str = DEFAULT_TABLE_NAME,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.connection = connection
        self.embedding_model = embedding_model
        self.table_name = validate_identifier(table_name)
        self.default_top_k = default_top_k

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        limit = top_k or self.default_top_k
        embedding = self.embedding_model.embed([query])[0]
        sql, params = self._build_query(vector_literal(embedding.vector), limit, filters or {})

        with self.connection.cursor(**self._cursor_kwargs()) as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return {
            "query": query,
            "embedding_model": embedding.model_name,
            "top_k": limit,
            "results": [self._map_row(row) for row in rows],
        }

    def _build_query(
        self,
        query_vector: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = [query_vector]

        if filters.get("hotel_id") is not None:
            where_clauses.append("hotel_id = %s")
            params.append(filters["hotel_id"])
        if filters.get("source_type") is not None:
            where_clauses.append("source_type = %s")
            params.append(filters["source_type"])

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        params.append(query_vector)
        params.append(top_k)

        sql = f"""
            SELECT
                chunk_id,
                hotel_id,
                source_type,
                section,
                strategy,
                text,
                metadata,
                embedding_model,
                embedding <=> %s::vector AS distance
            FROM {self.table_name}
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        return sql, params

    @staticmethod
    def _cursor_kwargs() -> dict[str, Any]:
        try:
            from psycopg2.extras import RealDictCursor
        except ImportError:
            return {}
        return {"cursor_factory": RealDictCursor}

    @staticmethod
    def _map_row(row: dict[str, Any]) -> dict[str, Any]:
        distance = float(row["distance"])
        return {
            "chunk_id": row["chunk_id"],
            "hotel_id": row.get("hotel_id"),
            "text": row["text"],
            "source_type": row["source_type"],
            "section": row.get("section"),
            "strategy": row.get("strategy"),
            "metadata": row.get("metadata") or {},
            "embedding_model": row.get("embedding_model"),
            "distance": distance,
            "score": 1.0 - distance,
            "source": "vector",
        }


def create_pgvector_search_service() -> PgVectorSearchService:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for pgvector search.")
    table_name = os.environ.get("VECTOR_INDEX_TABLE", DEFAULT_TABLE_NAME)
    top_k = int(os.environ.get("VECTOR_TOP_K", str(DEFAULT_TOP_K)))
    model_name = os.environ.get("VECTOR_EMBEDDING_MODEL") or os.environ.get("EMBEDDING_MODEL", "bge-m3")
    import psycopg2

    connection = psycopg2.connect(database_url)
    return PgVectorSearchService(
        connection=connection,
        embedding_model=get_embedding_model(model_name),
        table_name=table_name,
        default_top_k=top_k,
    )
