"""Tests for Supabase pgvector vector search service."""

from indexing.embedding.base import EmbeddingResult
from retrieval.vector_search import PgVectorSearchService


class FakeEmbeddingModel:
    model_name = "test-model"

    def embed(self, texts):
        return [EmbeddingResult(texts[0], [0.1, 0.2], self.model_name, 2)]


class FakeCursor:
    def __init__(self):
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return [
            {
                "chunk_id": "chunk-1",
                "hotel_id": 123,
                "source_type": "hotel",
                "section": "semantic_profile",
                "strategy": "whole",
                "text": "Khach san gan bien",
                "metadata": {"city": "Nha Trang"},
                "embedding_model": "test-model",
                "distance": 0.2,
            }
        ]


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self, cursor_factory=None):
        return self.cursor_obj


def test_pgvector_search_builds_filtered_query_and_maps_results():
    connection = FakeConnection()
    service = PgVectorSearchService(connection, FakeEmbeddingModel(), table_name="text_chunks")

    response = service.search(
        "khach san gan bien",
        top_k=5,
        filters={"hotel_id": 123, "source_type": "hotel"},
    )

    assert "FROM text_chunks" in connection.cursor_obj.sql
    assert "hotel_id = %s" in connection.cursor_obj.sql
    assert "source_type = %s" in connection.cursor_obj.sql
    assert "ORDER BY embedding <=> %s::vector" in connection.cursor_obj.sql
    assert connection.cursor_obj.params == [
        "[0.1000000000,0.2000000000]",
        123,
        "hotel",
        "[0.1000000000,0.2000000000]",
        5,
    ]
    assert response["embedding_model"] == "test-model"
    assert response["results"][0]["score"] == 0.8
    assert response["results"][0]["source"] == "vector"

