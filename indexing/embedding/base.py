"""Embedding interfaces for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: list[float]
    model_name: str
    dimension: int


class EmbeddingModel(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        ...


def l2_normalize(vector: list[float]) -> list[float]:
    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        return vector
    return [value / norm for value in vector]
