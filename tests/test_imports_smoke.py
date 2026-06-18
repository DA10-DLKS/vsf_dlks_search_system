"""test_imports_smoke.py — V17: smoke test import mọi entrypoint chính.

Bắt sớm lỗi "thiếu dependency" (underthesea/torch/numpy... clone mới không chạy nổi) — rẻ, chạy
nhanh, không cần service. Nếu một import vỡ vì thiếu package → fail ngay ở CI thay vì lúc runtime.
"""

from __future__ import annotations

import importlib

import pytest

ENTRYPOINTS = [
    "api.main",
    "api.frontend_adapter",
    "retrieval.hybrid_search.pipeline",
    "retrieval.query_processing.intent_parser",
    "retrieval.filtering.concept_index",
    "retrieval.filtering.hard_filter",
    "retrieval.reranking.fusion",
    "retrieval.vector_search.qdrant_service",
    "retrieval.lexical_search.service",
    "indexing.embedding.models",
    "knowledge_engineering.common.normalize",
    "evaluation.retrieval_metrics.eval_golden",
    "context",
]


@pytest.mark.parametrize("module", ENTRYPOINTS)
def test_entrypoint_imports(module):
    """Mỗi entrypoint phải import được (đủ dependency)."""
    importlib.import_module(module)
