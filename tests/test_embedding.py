from indexing.embedding import BGE_M3_MODEL_NAME, HashEmbeddingModel, get_embedding_model


def test_default_embedding_registry_points_to_bge_m3(monkeypatch):
    created = {}

    class FakeSentenceTransformerModel:
        def __init__(self, model_name):
            created["model_name"] = model_name

        def embed(self, texts):
            return []

    monkeypatch.setattr("indexing.embedding.registry.SentenceTransformerEmbeddingModel", FakeSentenceTransformerModel)

    model = get_embedding_model()

    assert created["model_name"] == BGE_M3_MODEL_NAME
    assert isinstance(model, FakeSentenceTransformerModel)


def test_hash_embedding_is_l2_normalized_for_offline_tests():
    result = HashEmbeddingModel(dimension=8).embed(["xin chao"])[0]

    assert result.dimension == 8
    assert abs(sum(value * value for value in result.vector) - 1.0) < 1e-9
