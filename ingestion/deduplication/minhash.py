"""Phát hiện tài liệu gần trùng lặp (Layer 2 — deduplication).

Dùng MinHash + LSH (Locality-Sensitive Hashing) để gom nhóm các tài liệu
có nội dung gần giống nhau (near-duplicate), tiết kiệm chi phí so với
tính Jaccard exact giữa mọi cặp.

Ngưỡng mặc định: jaccard >= 0.85 coi là trùng.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Sequence

# TODO(hieudm): Cân nhắc dùng thư viện `datasketch` (pip install khi cần)
# hoặc tự cài đặt MinHash nếu muốn tránh thêm dependency.
# TODO(hieudm): Chuẩn hóa text trước khi shingle (lowercase, bỏ dấu?) — quy ước
# phải thống nhất với text_normalizer.normalize_text().

DEFAULT_THRESHOLD: float = 0.85
DEFAULT_NUM_PERM: int = 128
DEFAULT_NGRAM_SIZE: int = 5


@dataclass
class DuplicateGroup:
    """Một nhóm tài liệu được cho là gần trùng lặp."""

    document_ids: list[str]
    similarity: float


def shingle(text: str, n: int = DEFAULT_NGRAM_SIZE) -> set[str]:
    """Tạo tập n-gram ký tự từ text."""
    # TODO(hieudm): implement
    raise NotImplementedError("shingle not implemented")


def minhash_signature(text: str, num_perm: int = DEFAULT_NUM_PERM) -> list[int]:
    """Tính MinHash signature cho 1 text."""
    # TODO(hieudm): implement
    raise NotImplementedError("minhash_signature not implemented")


def find_duplicates(
    docs: Iterable[tuple[str, str]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    num_perm: int = DEFAULT_NUM_PERM,
) -> list[DuplicateGroup]:
    """Tìm các nhóm near-duplicate.

    Args:
        docs: Iterable (doc_id, text) của từng tài liệu.
        threshold: Ngưỡng Jaccard similarity coi là trùng.
        num_perm: Số permutation cho MinHash.

    Returns:
        Danh sách DuplicateGroup (mỗi nhóm >= 2 doc).
    """
    # TODO(hieudm): implement (MinHash + LSH banding)
    raise NotImplementedError("find_duplicates not implemented")


def dedup_documents(
    docs: Sequence[dict],
    *,
    text_field: str = "content",
    id_field: str = "id",
) -> tuple[list[dict], list[DuplicateGroup]]:
    """Tiện ích: trả về (docs_sau_khi_loại_trùng, các_nhóm_trùng).

    Mỗi nhóm DuplicateGroup giữ lại 1 doc đầu tiên, loại bỏ phần còn lại.
    """
    # TODO(hieudm): implement
    raise NotImplementedError("dedup_documents not implemented")


__all__ = [
    "DEFAULT_THRESHOLD",
    "DEFAULT_NUM_PERM",
    "DEFAULT_NGRAM_SIZE",
    "DuplicateGroup",
    "shingle",
    "minhash_signature",
    "find_duplicates",
    "dedup_documents",
]
