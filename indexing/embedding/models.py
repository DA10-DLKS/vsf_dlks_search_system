"""Embedding model implementations.

Production default is BAAI/bge-m3, as required by the chunking/embedding
architecture. HashEmbeddingModel exists only for offline tests and smoke runs.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from .base import EmbeddingResult, l2_normalize

BGE_M3_MODEL_NAME = "BAAI/bge-m3"


@dataclass
class SentenceTransformerEmbeddingModel:
    model_name: str = BGE_M3_MODEL_NAME
    normalize: bool = True
    batch_size: int = 32

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for BAAI/bge-m3 embeddings. "
                "Install requirements.txt before running the production embedding pipeline."
            ) from exc
        self._model = SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        )
        return [
            EmbeddingResult(
                text=text,
                vector=[float(value) for value in vector],
                model_name=self.model_name,
                dimension=len(vector),
            )
            for text, vector in zip(texts, vectors, strict=True)
        ]


@dataclass
class HashEmbeddingModel:
    """Deterministic offline embedding for tests; not used by default."""

    model_name: str = "offline/hash-test"
    dimension: int = 32

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        results: list[EmbeddingResult] = []
        for text in texts:
            seed = int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:16], 16)
            rng = random.Random(seed)
            vector = l2_normalize([rng.uniform(-1.0, 1.0) for _ in range(self.dimension)])
            results.append(
                EmbeddingResult(
                    text=text,
                    vector=vector,
                    model_name=self.model_name,
                    dimension=self.dimension,
                )
            )
        return results
