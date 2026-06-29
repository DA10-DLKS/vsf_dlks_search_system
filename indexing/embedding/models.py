"""Embedding model implementations.

Production default is BAAI/bge-m3, as required by the chunking/embedding
architecture. HashEmbeddingModel exists only for offline tests and smoke runs.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from .base import EmbeddingResult, l2_normalize

BGE_M3_MODEL_NAME = "BAAI/bge-m3"


def _default_batch_size() -> int:
    """batch_size mặc định cho encode. Override qua env EMBEDDING_BATCH_SIZE.

    Nâng 32->128: với chunk dài, batch nhỏ -> nhiều batch -> nhiều padding-pass -> chậm. batch lớn
    giảm số forward (đo thật: 32->128 nhanh ~41% trên CPU). KHÔNG đổi vector (đã verify max diff=0;
    encode chia batch nội bộ, kết quả từng text độc lập). Chỉ đổi TỐC ĐỘ, không đổi embedding."""
    import os
    try:
        return int(os.environ.get("EMBEDDING_BATCH_SIZE", "128"))
    except ValueError:
        return 128


@dataclass
class SentenceTransformerEmbeddingModel:
    model_name: str = BGE_M3_MODEL_NAME
    normalize: bool = True
    batch_size: int = field(default_factory=_default_batch_size)

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for BAAI/bge-m3 embeddings. "
                "Install requirements.txt before running the production embedding pipeline."
            ) from exc
        import os

        import torch
        # V15: ưu tiên CUDA (máy Windows có GPU NVIDIA trước đây luôn rơi về CPU vì chỉ check mps).
        # Cho override qua env EMBEDDING_DEVICE.
        device = os.environ.get("EMBEDDING_DEVICE")
        if not device:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        if device in ("mps", "cuda"):
            self.batch_size = max(self.batch_size, 64)
        self._model = SentenceTransformer(self.model_name, device=device, trust_remote_code=True)

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        import torch
        with torch.no_grad():
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
