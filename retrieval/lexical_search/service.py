"""BM25 lexical search service backed by OpenSearch."""

from __future__ import annotations

import time
from typing import Any

from opensearchpy import OpenSearch


DEFAULT_SEARCH_FIELDS = ["name", "description^2", "city", "address", "amenities"]
DEFAULT_SOURCE_FIELDS = [
    "id",
    "name",
    "accommodation_type",
    "star_rating",
    "review_score",
    "address",
    "city",
    "description",
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
            "_source": self.source_fields,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": self.search_fields,
                }
            },
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
            "address": source.get("address"),
            "city": source.get("city"),
            "description": source.get("description"),
            "score": hit.get("_score"),
        }

    @staticmethod
    def _total_hits_value(total: Any) -> int:
        if isinstance(total, dict):
            return int(total.get("value", 0))
        return int(total or 0)

