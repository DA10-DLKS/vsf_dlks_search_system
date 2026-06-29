"""Tests for retrieval (Layer 6)."""

from retrieval.lexical_search import BM25SearchService


class FakeOpenSearchClient:
    def __init__(self):
        self.calls = []

    def search(self, index, body):
        self.calls.append({"index": index, "body": body})
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_score": 12.5,
                        "_source": {
                            "id": 123,
                            "name": "Test Hotel",
                            "accommodation_type": "hotel",
                            "star_rating": 5,
                            "review_score": 9.1,
                            "address": "Ha Long",
                            "city": "ha long",
                            "description": "Khach san gan bien",
                        },
                    }
                ],
            }
        }


def test_bm25_search_service_builds_query_and_maps_results():
    client = FakeOpenSearchClient()
    service = BM25SearchService(client=client, index_name="travel_bm25")

    response = service.search("khach san gan bien")

    assert client.calls[0]["index"] == "travel_bm25"
    assert client.calls[0]["body"]["size"] == 10
    # V16: _source phải gồm description + field hiển thị (trước thiếu → GET /search trả null).
    src = client.calls[0]["body"]["_source"]
    for f in ("id", "name", "description", "amenities", "images", "review_count"):
        assert f in src, f"V16: _source phải gồm '{f}'"
    assert client.calls[0]["body"]["query"]["multi_match"] == {
        "query": "khach san gan bien",
        "fields": ["name", "description^2", "city", "address", "amenities"],
    }
    assert client.calls[0]["body"]["track_total_hits"] is False
    assert response["query"] == "khach san gan bien"
    assert response["total_hits"] == 1
    # V16: description không null (đây là bug audit phát hiện)
    r = response["results"][0]
    assert r["id"] == 123 and r["name"] == "Test Hotel"
    assert r["description"] == "Khach san gan bien"
    assert r["score"] == 12.5
