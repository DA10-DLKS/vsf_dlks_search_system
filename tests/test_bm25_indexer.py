"""Tests for the BM25 OpenSearch indexer."""

import importlib
import json

import indexing.bm25_index.index_bm25 as index_bm25


class FakeIndices:
    def __init__(self):
        self.alias_updates = []
        self.aliases = {}

    def exists(self, index):
        return True

    def get_alias(self, name):
        if name not in self.aliases:
            raise index_bm25.NotFoundError(404, "aliases_not_found_exception")
        return self.aliases[name]

    def update_aliases(self, body):
        self.alias_updates.append(body)


class FakeOpenSearchClient:
    def __init__(self):
        self.indices = FakeIndices()


def write_hotel(path, hotel_id=123):
    path.write_text(
        json.dumps(
            {
                "hotel_id": hotel_id,
                "name": "Test Hotel",
                "description": "Khach san gan bien",
            }
        ),
        encoding="utf-8",
    )


def test_iter_docs_uses_target_index(tmp_path):
    write_hotel(tmp_path / "hotel_123.json")

    docs = list(index_bm25.iter_docs(tmp_path, index_name="vsf_hotels_bm25_v1_0_0"))

    assert len(docs) == 1
    assert docs[0]["_index"] == "vsf_hotels_bm25_v1_0_0"
    assert docs[0]["_id"] == "123"


def test_target_index_falls_back_to_runtime_index(monkeypatch):
    monkeypatch.setenv("BM25_INDEX", "vsf_hotels_bm25_current")
    monkeypatch.delenv("BM25_TARGET_INDEX", raising=False)

    reloaded = importlib.reload(index_bm25)

    assert reloaded.TARGET_INDEX_NAME == "vsf_hotels_bm25_current"


def test_run_indexing_does_not_promote_when_flag_false(monkeypatch, tmp_path):
    write_hotel(tmp_path / "hotel_123.json")
    fake_client = FakeOpenSearchClient()

    monkeypatch.setattr(index_bm25, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(index_bm25, "TARGET_INDEX_NAME", "vsf_hotels_bm25_v1_0_0")
    monkeypatch.setattr(index_bm25, "BM25_PROMOTE_ALIAS", False)

    def fake_streaming_bulk(*args, **kwargs):
        yield True, {"index": {"_id": "123"}}

    monkeypatch.setattr(index_bm25.helpers, "streaming_bulk", fake_streaming_bulk)

    exit_code = index_bm25.run_indexing(fake_client)

    assert exit_code == 0
    assert fake_client.indices.alias_updates == []


def test_run_indexing_does_not_promote_when_bulk_has_failures(monkeypatch, tmp_path):
    write_hotel(tmp_path / "hotel_123.json")
    fake_client = FakeOpenSearchClient()

    monkeypatch.setattr(index_bm25, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(index_bm25, "TARGET_INDEX_NAME", "vsf_hotels_bm25_v1_0_0")
    monkeypatch.setattr(index_bm25, "BM25_ALIAS", "vsf_hotels_bm25_current")
    monkeypatch.setattr(index_bm25, "BM25_PROMOTE_ALIAS", True)

    def fake_streaming_bulk(*args, **kwargs):
        yield False, {"index": {"_id": "123", "error": "boom"}}

    monkeypatch.setattr(index_bm25.helpers, "streaming_bulk", fake_streaming_bulk)

    exit_code = index_bm25.run_indexing(fake_client)

    assert exit_code == 0
    assert fake_client.indices.alias_updates == []


def test_run_indexing_promotes_alias_after_success(monkeypatch, tmp_path):
    write_hotel(tmp_path / "hotel_123.json")
    fake_client = FakeOpenSearchClient()

    monkeypatch.setattr(index_bm25, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(index_bm25, "TARGET_INDEX_NAME", "vsf_hotels_bm25_v1_0_0")
    monkeypatch.setattr(index_bm25, "BM25_ALIAS", "vsf_hotels_bm25_current")
    monkeypatch.setattr(index_bm25, "BM25_PROMOTE_ALIAS", True)

    def fake_streaming_bulk(*args, **kwargs):
        yield True, {"index": {"_id": "123"}}

    monkeypatch.setattr(index_bm25.helpers, "streaming_bulk", fake_streaming_bulk)

    exit_code = index_bm25.run_indexing(fake_client)

    assert exit_code == 0
    assert fake_client.indices.alias_updates == [
        {
            "actions": [
                {"add": {"index": "vsf_hotels_bm25_v1_0_0", "alias": "vsf_hotels_bm25_current"}},
            ]
        }
    ]


def test_run_indexing_promotes_alias_by_removing_existing_index(monkeypatch, tmp_path):
    write_hotel(tmp_path / "hotel_123.json")
    fake_client = FakeOpenSearchClient()
    fake_client.indices.aliases = {
        "vsf_hotels_bm25_current": {
            "vsf_hotels_bm25_v0_9_0": {"aliases": {"vsf_hotels_bm25_current": {}}}
        }
    }

    monkeypatch.setattr(index_bm25, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(index_bm25, "TARGET_INDEX_NAME", "vsf_hotels_bm25_v1_0_0")
    monkeypatch.setattr(index_bm25, "BM25_ALIAS", "vsf_hotels_bm25_current")
    monkeypatch.setattr(index_bm25, "BM25_PROMOTE_ALIAS", True)

    def fake_streaming_bulk(*args, **kwargs):
        yield True, {"index": {"_id": "123"}}

    monkeypatch.setattr(index_bm25.helpers, "streaming_bulk", fake_streaming_bulk)

    exit_code = index_bm25.run_indexing(fake_client)

    assert exit_code == 0
    assert fake_client.indices.alias_updates == [
        {
            "actions": [
                {"remove": {"index": "vsf_hotels_bm25_v0_9_0", "alias": "vsf_hotels_bm25_current"}},
                {"add": {"index": "vsf_hotels_bm25_v1_0_0", "alias": "vsf_hotels_bm25_current"}},
            ]
        }
    ]
