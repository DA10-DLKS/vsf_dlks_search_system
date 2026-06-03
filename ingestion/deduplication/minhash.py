"""Phát hiện tài liệu gần trùng lặp (Layer 2 — deduplication).

Dùng datasketch (MinHash + LSH) để gom nhóm các tài liệu có nội dung
gần giống nhau (near-duplicate).

Ngưỡng mặc định: jaccard >= 0.85 coi là trùng.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence

from datasketch import MinHash, MinHashLSH
from ingestion.cleaning.text_normalizer import normalize_text

DEFAULT_THRESHOLD: float = 0.85
DEFAULT_NUM_PERM: int = 128
DEFAULT_NGRAM_SIZE: int = 5


@dataclass
class DuplicateGroup:
    document_ids: list[str]
    similarity: float


def _prepare_text(text: str) -> str:
    """Chuẩn hóa trước khi tạo MinHash:
    lowercased + NFC normalized + collapse whitespace."""
    t = normalize_text(text, preserve_case=False)
    return t


def _make_minhash(text: str, num_perm: int = DEFAULT_NUM_PERM) -> MinHash:
    m = MinHash(num_perm=num_perm)
    t = _prepare_text(text)
    for word in t.split():
        m.update(word.encode("utf-8"))
    return m


def compute_jaccard(text_a: str, text_b: str) -> float:
    """Tính Jaccard similarity giữa 2 text (dùng để verify)."""
    m1 = _make_minhash(text_a)
    m2 = _make_minhash(text_b)
    return m1.jaccard(m2)


def find_duplicates(
    docs: Iterable[tuple[str, str]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    num_perm: int = DEFAULT_NUM_PERM,
) -> list[DuplicateGroup]:
    """Tìm các nhóm near-duplicate bằng MinHash LSH.

    Args:
        docs: Iterable (doc_id, text) của từng tài liệu.
        threshold: Ngưỡng Jaccard similarity coi là trùng.
        num_perm: Số permutation cho MinHash.

    Returns:
        Danh sách DuplicateGroup (mỗi nhóm >= 2 doc).
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes: dict[str, MinHash] = {}
    doc_texts: dict[str, str] = {}

    for doc_id, text in docs:
        m = _make_minhash(text, num_perm)
        minhashes[doc_id] = m
        doc_texts[doc_id] = text
        lsh.insert(doc_id, m)

    seen: set[str] = set()
    groups: list[DuplicateGroup] = []

    for doc_id, m in minhashes.items():
        if doc_id in seen:
            continue
        candidates = lsh.query(m)
        # Remove self
        candidates = [c for c in candidates if c != doc_id]
        if not candidates:
            continue

        # Verify by exact Jaccard (LSH là approximate)
        verified = [doc_id]
        for cand in candidates:
            sim = m.jaccard(minhashes[cand])
            if sim >= threshold:
                verified.append(cand)

        if len(verified) >= 2:
            group = list(set(verified))  # deduplicate
            for gid in group:
                seen.add(gid)
            avg_sim = sum(
                minhashes[a].jaccard(minhashes[b])
                for a in group for b in group if a < b
            )
            n_pairs = len(group) * (len(group) - 1) / 2
            groups.append(DuplicateGroup(
                document_ids=group,
                similarity=round(avg_sim / n_pairs, 4) if n_pairs > 0 else 1.0,
            ))

    return groups


def dedup_documents(
    docs: Sequence[dict],
    *,
    text_field: str = "description",
    id_field: str = "id",
) -> tuple[list[dict], list[DuplicateGroup]]:
    """Tiện ích: trả về (docs_sau_khi_loại_trùng, các_nhóm_trùng).

    Mỗi nhóm DuplicateGroup giữ lại 1 doc đầu tiên, loại bỏ phần còn lại.
    """
    id_map: dict[str, dict] = {}
    for doc in docs:
        doc_id = str(doc.get(id_field) or doc.get("hotel_id"))
        text = doc.get(text_field, "") or ""
        id_map[doc_id] = doc

    groups = find_duplicates(
        [(doc_id, id_map[doc_id].get(text_field, "") or "") for doc_id in id_map],
    )

    # Collect IDs to remove
    to_remove: set[str] = set()
    for group in groups:
        for doc_id in group.document_ids[1:]:  # keep first
            to_remove.add(doc_id)

    kept = [doc for doc_id, doc in id_map.items() if doc_id not in to_remove]
    return kept, groups


__all__ = [
    "DEFAULT_THRESHOLD",
    "DEFAULT_NUM_PERM",
    "DEFAULT_NGRAM_SIZE",
    "DuplicateGroup",
    "compute_jaccard",
    "find_duplicates",
    "dedup_documents",
]
