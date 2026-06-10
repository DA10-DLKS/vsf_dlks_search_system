"""Tests for the API (Layer 8)."""

from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_search_uses_keyword_search_service(monkeypatch):
    class FakeKeywordSearchService:
        def search(self, query):
            return {
                "query": query,
                "results": [
                    {
                        "id": 123,
                        "name": "Test Hotel",
                        "accommodation_type": "hotel",
                        "star_rating": 5,
                        "review_score": 9.1,
                        "address": "Ha Long",
                        "city": "ha long",
                        "description": "Khach san gan bien",
                        "score": 12.5,
                    }
                ],
                "took_ms": 7,
                "total_hits": 1,
            }

    monkeypatch.setattr(api_main, "keyword_search_service", FakeKeywordSearchService())

    resp = client.get("/search", params={"q": "khach san gan bien"})

    assert resp.status_code == 200
    assert resp.json()["query"] == "khach san gan bien"
    assert resp.json()["total_hits"] == 1
    assert resp.json()["results"][0]["name"] == "Test Hotel"
