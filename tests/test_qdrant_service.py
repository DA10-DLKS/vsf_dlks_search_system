"""test_qdrant_service.py — V13: test backend vector THẬT (Qdrant) mà production dùng.

Trước đây chỉ có test_pgvector_* (backend tham chiếu, KHÔNG phải cái api/main.py dùng) → test xanh
nhưng không bảo vệ code chạy thật. Bộ này test QdrantSearchService với fake client (không cần
Qdrant chạy), bảo vệ cả V11 (chỉ kéo payload cần) lẫn shape output cho fusion.
"""

from __future__ import annotations

from types import SimpleNamespace

from indexing.embedding.base import EmbeddingResult
from retrieval.vector_search.qdrant_service import QdrantSearchService


class _FakeEmbedding:
    model_name = "test-bge"

    def embed(self, texts):
        return [EmbeddingResult(texts[0], [0.1, 0.2, 0.3], self.model_name, 3)]


class _FakeQdrantClient:
    """Ghi lại tham số query_points để khẳng định V11 (payload giới hạn)."""
    def __init__(self, points):
        self._points = points
        self.last_kwargs = None

    def query_points(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(points=self._points)


def _hit(chunk_id, hotel_id, text, score):
    return SimpleNamespace(
        payload={"chunk_id": chunk_id, "hotel_id": hotel_id, "text": text,
                 "source_type": "review", "section": "x"},
        score=score,
    )


def _service(points):
    return QdrantSearchService(
        client=_FakeQdrantClient(points), embedding_model=_FakeEmbedding(), collection="t"
    )


def test_map_hit_shape_for_fusion():
    """Output phải có đúng các key Node 7 fusion cần (chunk_id/hotel_id/text/score/source)."""
    svc = _service([_hit("c1", 11, "chunk text", 0.9)])
    res = svc.search("query", top_k=5)["results"]
    assert len(res) == 1
    r = res[0]
    assert r["chunk_id"] == "c1" and r["hotel_id"] == 11
    assert r["text"] == "chunk text"
    assert r["source"] == "vector"
    assert r["score"] == 0.9


def test_v11_payload_is_limited_not_true():
    """V11: query_points phải dùng with_payload = list field cụ thể, KHÔNG phải True (60+ field)."""
    svc = _service([_hit("c1", 11, "t", 0.5)])
    svc.search("query", top_k=5)
    wp = svc.client.last_kwargs["with_payload"]
    assert wp is not True and isinstance(wp, list)
    assert "chunk_id" in wp and "hotel_id" in wp
    # KHÔNG được kéo field nặng
    assert "image_urls" not in wp and "parent_text" not in wp


def test_candidate_filter_applied():
    """candidate_hotel_ids → query_filter khác None (lọc đúng tập ứng viên)."""
    svc = _service([_hit("c1", 11, "t", 0.5)])
    svc.search("query", top_k=5, candidate_hotel_ids=[11, 12])
    assert svc.client.last_kwargs["query_filter"] is not None
    # không truyền candidate → không lọc
    svc.search("query", top_k=5, candidate_hotel_ids=None)
    assert svc.client.last_kwargs["query_filter"] is None
