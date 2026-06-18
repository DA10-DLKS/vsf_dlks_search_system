"""qdrant_service.py — Node 6B: semantic vector search trên Qdrant.

Đối ứng của indexing/vector_index/qdrant_index.py. Repo có PgVectorSearchService làm tham
chiếu nhưng dự án dùng Qdrant (.env). Output shape GIỐNG pgvector service (chunk_id/hotel_id/
text/metadata/score/source="vector") để Node 7 fusion hợp nhất chung với BM25.

Filter theo candidate hotel_ids (thu từ Node 4) — chỉ tìm vector trong tập ứng viên đã lọc.
"""

from __future__ import annotations

import os
from typing import Any

from indexing.embedding import get_embedding_model
from indexing.embedding.base import EmbeddingModel

QDRANT_URL_DEFAULT = "http://localhost:6333"
COLLECTION_DEFAULT = "vsf_travel"
DEFAULT_TOP_K = 10


class QdrantSearchService:
    """Node 6B vector search service (Qdrant backend)."""

    def __init__(
        self,
        client,
        embedding_model: EmbeddingModel,
        collection: str = COLLECTION_DEFAULT,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.client = client
        self.embedding_model = embedding_model
        self.collection = collection
        self.default_top_k = default_top_k

    def _candidate_filter(self, hotel_ids: list[int] | None):
        """Qdrant Filter: payload.hotel_id ∈ candidate. None nếu không lọc."""
        if not hotel_ids:
            return None
        from qdrant_client.models import FieldCondition, Filter, MatchAny

        return Filter(
            must=[FieldCondition(key="hotel_id", match=MatchAny(any=list(hotel_ids)))]
        )

    # V11 (SLA): chỉ kéo field downstream THỰC SỰ dùng. with_payload=True kéo cả 60+ field
    # (image_urls/parent_text/...) → Qdrant ~244ms vs ~30ms (chậm 8×). Không downstream nào
    # đọc các field nặng đó từ vector hit (đã verify). Đo: ~840ms → ~290ms/query.
    _PAYLOAD_FIELDS = ["chunk_id", "hotel_id", "text", "raw_text", "source_type", "section"]

    def search(
        self,
        query: str,
        top_k: int | None = None,
        candidate_hotel_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        limit = top_k or self.default_top_k
        embedding = self.embedding_model.embed([query])[0]
        # Qdrant >=1.10: query_points (search() đã bỏ). Trả QueryResponse.points.
        response = self.client.query_points(
            collection_name=self.collection,
            query=embedding.vector,
            query_filter=self._candidate_filter(candidate_hotel_ids),
            limit=limit,
            with_payload=self._PAYLOAD_FIELDS,
        )
        return {
            "query": query,
            "embedding_model": embedding.model_name,
            "top_k": limit,
            "results": [self._map_hit(h) for h in response.points],
        }

    @staticmethod
    def _map_hit(hit) -> dict[str, Any]:
        payload = hit.payload or {}
        return {
            "chunk_id": payload.get("chunk_id"),
            "hotel_id": payload.get("hotel_id"),
            "text": payload.get("text") or payload.get("raw_text") or "",
            "source_type": payload.get("source_type"),
            "section": payload.get("section"),
            "metadata": payload,
            "score": float(hit.score),   # Qdrant COSINE: cao = gần
            "source": "vector",
        }


def create_qdrant_search_service(offline: bool = False) -> QdrantSearchService:
    from qdrant_client import QdrantClient

    url = os.environ.get("QDRANT_URL", QDRANT_URL_DEFAULT)
    collection = os.environ.get("QDRANT_COLLECTION", COLLECTION_DEFAULT)
    top_k = int(os.environ.get("VECTOR_TOP_K", str(DEFAULT_TOP_K)))
    model = get_embedding_model("bge-m3", offline=offline)
    return QdrantSearchService(
        client=QdrantClient(url=url),
        embedding_model=model,
        collection=collection,
        default_top_k=top_k,
    )
