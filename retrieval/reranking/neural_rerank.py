"""neural_rerank.py — Node 7B: rerank bằng cross-encoder (bge-reranker-v2-m3).

Cross-encoder chấm cặp (query, chunk_text) chính xác hơn bi-encoder. Port từ
test_pipeline_nodes Node 7B, kèm FALLBACK keyword-density khi chưa có model (để pipeline
chạy/verify không cần tải ~2GB model). Đặt giữa fusion (Node 7) và business rerank (Node 7C).
"""

from __future__ import annotations

import math
from typing import Any

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
_MODEL = None


def _load_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import CrossEncoder
        _MODEL = CrossEncoder(RERANKER_MODEL)
    return _MODEL


def neural_rerank(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 10,
    use_model: bool = True,
) -> list[dict[str, Any]]:
    """Rerank candidates theo độ liên quan (query, text). use_model=False -> fallback density."""
    if not candidates:
        return []

    scored = []
    if use_model:
        try:
            model = _load_model()
            pairs = [[query, c.get("text", "")] for c in candidates]
            raw = model.predict(pairs)
            for c, s in zip(candidates, raw):
                item = dict(c)
                item["rerank_score"] = 1.0 / (1.0 + math.exp(-float(s)))  # sigmoid -> [0,1]
                scored.append(item)
        except Exception:
            scored = []   # rơi xuống fallback

    if not scored:
        qwords = set(query.lower().split())
        for c in candidates:
            text = (c.get("text") or "").lower()
            density = sum(1 for w in qwords if w in text) / max(len(qwords), 1)
            base = c.get("fused_score", c.get("rrf_score", c.get("score", 0.0)))
            item = dict(c)
            item["rerank_score"] = float(max(0.0, min(1.0, 0.4 * base * 30 + 0.6 * density)))
            scored.append(item)

    scored.sort(key=lambda d: -d["rerank_score"])
    return scored[:top_k]
