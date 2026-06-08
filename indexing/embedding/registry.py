"""Embedding model registry."""

from __future__ import annotations

from .base import EmbeddingModel
from .models import BGE_M3_MODEL_NAME, HashEmbeddingModel, SentenceTransformerEmbeddingModel


def get_embedding_model(name: str = "bge-m3", *, offline: bool = False) -> EmbeddingModel:
    if offline:
        return HashEmbeddingModel()
    normalized = name.lower()
    if normalized in {"bge-m3", "bge_m3", BGE_M3_MODEL_NAME.lower()}:
        return SentenceTransformerEmbeddingModel(model_name=BGE_M3_MODEL_NAME)
    raise ValueError(f"Unsupported embedding model: {name}")
