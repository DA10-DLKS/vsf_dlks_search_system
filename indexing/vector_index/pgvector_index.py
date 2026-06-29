"""Index chunk embeddings into Supabase/Postgres pgvector."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from indexing.embedding import get_embedding_model
from indexing.embedding.base import EmbeddingModel
from knowledge_engineering.chunking import Chunk, chunk_document


DEFAULT_TABLE_NAME = "text_chunks"
DEFAULT_DATA_DIR = "data/cleaned"
DEFAULT_BATCH_SIZE = 32
DEFAULT_VECTOR_DIMENSION = 1024


@dataclass(frozen=True)
class VectorChunkRow:
    chunk_id: str
    hotel_id: int | None
    source_type: str
    section: str | None
    strategy: str
    text: str
    raw_text: str
    metadata: dict[str, Any]
    embedding_model: str
    embedding_dimension: int
    embedding: list[float]


def execute_values(cursor, sql, values, template):
    from psycopg2.extras import execute_values as psycopg2_execute_values

    return psycopg2_execute_values(cursor, sql, values, template=template)


def validate_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum() or not identifier[0].isalpha():
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return identifier


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in vector) + "]"


def iter_clean_documents(data_dir: str | Path) -> Iterable[dict[str, Any]]:
    root = Path(data_dir)
    for path in sorted(root.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            try:
                doc = json.load(file)
            except json.JSONDecodeError:
                continue
        if isinstance(doc, dict):
            yield doc


def chunk_to_row(chunk: Chunk, embedding, expected_dimension: int) -> VectorChunkRow:
    if embedding.dimension != expected_dimension:
        raise ValueError(
            f"Embedding dimension {embedding.dimension} does not match expected {expected_dimension}"
        )
    metadata = dict(chunk.metadata)
    section = metadata.get("section")
    return VectorChunkRow(
        chunk_id=chunk.chunk_id,
        hotel_id=metadata.get("hotel_id"),
        source_type=chunk.source_type,
        section=section,
        strategy=chunk.strategy,
        text=chunk.text,
        raw_text=chunk.raw_text,
        metadata=chunk.to_payload(),
        embedding_model=embedding.model_name,
        embedding_dimension=embedding.dimension,
        embedding=embedding.vector,
    )


def build_rows_for_document(
    document: dict[str, Any],
    embedding_model: EmbeddingModel,
    expected_dimension: int = DEFAULT_VECTOR_DIMENSION,
) -> list[VectorChunkRow]:
    chunks = chunk_document(document)
    if not chunks:
        return []
    embeddings = embedding_model.embed([chunk.text for chunk in chunks])
    return [
        chunk_to_row(chunk, embedding, expected_dimension)
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]


def upsert_rows(connection, rows: list[VectorChunkRow], table_name: str = DEFAULT_TABLE_NAME) -> int:
    if not rows:
        return 0

    table = validate_identifier(table_name)
    sql = f"""
        INSERT INTO {table} (
            chunk_id,
            hotel_id,
            source_type,
            section,
            strategy,
            text,
            raw_text,
            metadata,
            embedding_model,
            embedding_dimension,
            embedding
        )
        VALUES %s
        ON CONFLICT (chunk_id) DO UPDATE SET
            hotel_id = EXCLUDED.hotel_id,
            source_type = EXCLUDED.source_type,
            section = EXCLUDED.section,
            strategy = EXCLUDED.strategy,
            text = EXCLUDED.text,
            raw_text = EXCLUDED.raw_text,
            metadata = EXCLUDED.metadata,
            embedding_model = EXCLUDED.embedding_model,
            embedding_dimension = EXCLUDED.embedding_dimension,
            embedding = EXCLUDED.embedding,
            updated_at = NOW()
    """
    values = [
        (
            row.chunk_id,
            row.hotel_id,
            row.source_type,
            row.section,
            row.strategy,
            row.text,
            row.raw_text,
            json.dumps(row.metadata, ensure_ascii=False),
            row.embedding_model,
            row.embedding_dimension,
            vector_literal(row.embedding),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            values,
            template="(%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::vector)",
        )
    connection.commit()
    return len(rows)


def index_documents(
    connection,
    documents: Iterable[dict[str, Any]],
    embedding_model: EmbeddingModel,
    *,
    table_name: str = DEFAULT_TABLE_NAME,
    batch_size: int = DEFAULT_BATCH_SIZE,
    expected_dimension: int = DEFAULT_VECTOR_DIMENSION,
) -> int:
    total = 0
    batch: list[VectorChunkRow] = []
    for document in documents:
        for row in build_rows_for_document(document, embedding_model, expected_dimension):
            batch.append(row)
            if len(batch) >= batch_size:
                total += upsert_rows(connection, batch, table_name)
                batch = []
    total += upsert_rows(connection, batch, table_name)
    return total


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required for Supabase pgvector indexing.")
        return 1

    data_dir = os.environ.get("CLEANED_DATA_DIR", DEFAULT_DATA_DIR)
    table_name = os.environ.get("VECTOR_INDEX_TABLE", DEFAULT_TABLE_NAME)
    batch_size = int(os.environ.get("VECTOR_INDEX_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    expected_dimension = int(os.environ.get("VECTOR_DIMENSION", str(DEFAULT_VECTOR_DIMENSION)))
    model_name = os.environ.get("VECTOR_EMBEDDING_MODEL") or os.environ.get("EMBEDDING_MODEL", "bge-m3")

    embedding_model = get_embedding_model(model_name)
    documents = iter_clean_documents(data_dir)

    import psycopg2

    with psycopg2.connect(database_url) as connection:
        indexed = index_documents(
            connection,
            documents,
            embedding_model,
            table_name=table_name,
            batch_size=batch_size,
            expected_dimension=expected_dimension,
        )
    print(f"Indexed {indexed} vector chunks into {table_name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
