"""Phát hiện & loại bỏ gần trùng lặp (Layer 2 — deduplication)."""

from ingestion.deduplication.minhash import (
    DEFAULT_NGRAM_SIZE,
    DEFAULT_NUM_PERM,
    DEFAULT_THRESHOLD,
    DuplicateGroup,
    dedup_documents,
    find_duplicates,
    minhash_signature,
    shingle,
)

__all__ = [
    "DEFAULT_NGRAM_SIZE",
    "DEFAULT_NUM_PERM",
    "DEFAULT_THRESHOLD",
    "DuplicateGroup",
    "dedup_documents",
    "find_duplicates",
    "minhash_signature",
    "shingle",
]
