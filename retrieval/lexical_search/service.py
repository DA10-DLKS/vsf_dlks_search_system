"""BM25 lexical search service backed by OpenSearch."""

from __future__ import annotations

import time
from typing import Any

from opensearchpy import OpenSearch


DEFAULT_SEARCH_FIELDS = ["name", "name_alt", "brand", "description^2", "city", "address", "amenities"]
# V16: _map_hit đọc `description` nhưng _source trước đây KHÔNG gồm → GET /search trả description=null
# + thiếu metadata hiển thị. Bổ sung các field _map_hit cần + field UI hữu ích.
DEFAULT_SOURCE_FIELDS = [
    "id",
    "name",
    "accommodation_type",
    "star_rating",
    "review_score",
    "review_count",
    "address",
    "city",
    "description",
    "amenities",
    "images",
    "source_url",
    "latitude",
    "longitude",
]


class BM25SearchService:
    """Thin Layer 6 wrapper for keyword/BM25 search."""

    def __init__(
        self,
        client: OpenSearch,
        index_name: str,
        search_fields: list[str] | None = None,
        source_fields: list[str] | None = None,
        default_size: int = 10,
    ) -> None:
        self.client = client
        self.index_name = index_name
        self.search_fields = search_fields or DEFAULT_SEARCH_FIELDS
        self.source_fields = source_fields or DEFAULT_SOURCE_FIELDS
        self.default_size = default_size

    def search(self, query: str, size: int | None = None) -> dict[str, Any]:
        """Run BM25 keyword search and return the API-compatible payload."""
        limit = size or self.default_size
        start_time = time.time()

        response = self.client.search(
            index=self.index_name,
            body=self._build_query(query=query, size=limit),
        )

        took_ms = int((time.time() - start_time) * 1000)
        hits_container = response.get("hits", {})
        hits = hits_container.get("hits", [])

        return {
            "query": query,
            "results": [self._map_hit(hit) for hit in hits],
            "took_ms": took_ms,
            "total_hits": self._total_hits_value(hits_container.get("total", 0)),
        }

    def _build_query(self, query: str, size: int) -> dict[str, Any]:
        return {
            "size": size,
            "track_total_hits": False,
            "_source": self.source_fields,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": self.search_fields,
                }
            },
        }

    def search_for_fusion(
        self,
        query: str,
        size: int | None = None,
        candidate_hotel_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """BM25 search cho Node 7 fusion: output shape ĐỒNG NHẤT với vector service
        (hotel_id/text/metadata/score/source="bm25"), lọc theo candidate hotel_ids.

        Khác search() (per-hotel doc dùng cho API baseline) — bản này hợp nhất với vector.
        """
        limit = size or self.default_size
        bool_query: dict[str, Any] = {
            "must": [{"multi_match": {"query": query, "fields": self.search_fields}}],
        }
        if candidate_hotel_ids:
            bool_query["filter"] = [{"terms": {"id": list(candidate_hotel_ids)}}]
        body = {
            "size": limit,
            "track_total_hits": False,
            "_source": self.source_fields + ["ontology_concepts", "description"],
            "query": {"bool": bool_query},
        }
        response = self.client.search(index=self.index_name, body=body)
        hits = response.get("hits", {}).get("hits", [])
        return {
            "query": query,
            "results": [
                {
                    "chunk_id": f"bm25_hotel_{h.get('_source', {}).get('id')}",
                    "hotel_id": h.get("_source", {}).get("id"),
                    "text": h.get("_source", {}).get("description") or h.get("_source", {}).get("name") or "",
                    "source_type": "hotel",
                    "metadata": h.get("_source", {}),
                    "score": h.get("_score"),
                    "source": "bm25",
                }
                for h in hits
            ],
        }

    @staticmethod
    def _map_hit(hit: dict[str, Any]) -> dict[str, Any]:
        source = hit.get("_source", {})
        return {
            "id": source.get("id"),
            "name": source.get("name"),
            "accommodation_type": source.get("accommodation_type"),
            "star_rating": source.get("star_rating"),
            "review_score": source.get("review_score"),
            "review_count": source.get("review_count"),
            "address": source.get("address"),
            "city": source.get("city"),
            "description": source.get("description"),
            "amenities": source.get("amenities"),
            "images": source.get("images"),
            "source_url": source.get("source_url"),
            "latitude": source.get("latitude"),
            "longitude": source.get("longitude"),
            "score": hit.get("_score"),
        }

    @staticmethod
    def _total_hits_value(total: Any) -> int:
        if isinstance(total, dict):
            return int(total.get("value", 0))
        return int(total or 0)
