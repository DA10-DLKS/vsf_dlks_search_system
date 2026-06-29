"""Tests for Supabase pgvector indexing."""

import pytest

from indexing.embedding.base import EmbeddingResult
from indexing.vector_index.pgvector_index import chunk_to_row, upsert_rows, vector_literal
from knowledge_engineering.chunking.base import Chunk


class FakeCursor:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


def test_vector_literal_formats_pgvector_value():
    assert vector_literal([0.1, -0.25, 1.0]) == "[0.1000000000,-0.2500000000,1.0000000000]"


def test_chunk_to_row_maps_payload_and_embedding():
    chunk = Chunk(
        chunk_id="chunk-1",
        text="Khach san gan bien",
        raw_text="gan bien",
        source_type="hotel",
        strategy="whole",
        metadata={"hotel_id": 123, "section": "semantic_profile"},
    )
    embedding = EmbeddingResult(
        text=chunk.text,
        vector=[0.1, 0.2],
        model_name="test-model",
        dimension=2,
    )

    row = chunk_to_row(chunk, embedding, expected_dimension=2)

    assert row.chunk_id == "chunk-1"
    assert row.hotel_id == 123
    assert row.section == "semantic_profile"
    assert row.embedding_model == "test-model"
    assert row.embedding == [0.1, 0.2]
    assert row.metadata["chunk_id"] == "chunk-1"


def test_chunk_to_row_rejects_wrong_dimension():
    chunk = Chunk("chunk-1", "text", "text", "hotel", "whole", {})
    embedding = EmbeddingResult("text", [0.1], "test-model", 1)

    with pytest.raises(ValueError):
        chunk_to_row(chunk, embedding, expected_dimension=2)


def test_upsert_rows_uses_vector_cast(monkeypatch):
    captured = {}

    def fake_execute_values(cursor, sql, values, template):
        captured["sql"] = sql
        captured["values"] = values
        captured["template"] = template

    monkeypatch.setattr("indexing.vector_index.pgvector_index.execute_values", fake_execute_values)

    chunk = Chunk(
        chunk_id="chunk-1",
        text="Khach san gan bien",
        raw_text="gan bien",
        source_type="hotel",
        strategy="whole",
        metadata={"hotel_id": 123, "section": "semantic_profile"},
    )
    embedding = EmbeddingResult(chunk.text, [0.1, 0.2], "test-model", 2)
    row = chunk_to_row(chunk, embedding, expected_dimension=2)
    connection = FakeConnection()

    count = upsert_rows(connection, [row], table_name="text_chunks")

    assert count == 1
    assert connection.commits == 1
    assert "ON CONFLICT (chunk_id) DO UPDATE" in captured["sql"]
    assert "%s::vector" in captured["template"]
    assert captured["values"][0][-1] == "[0.1000000000,0.2000000000]"

