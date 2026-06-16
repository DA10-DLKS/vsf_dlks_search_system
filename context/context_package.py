"""context_package.py — Contract ContextPackage + dựng context cho LLM (Node 7C output -> Node 8).

ContextPackage là gói ngữ cảnh chuẩn mà tầng retrieval bàn giao cho tầng sinh câu trả lời.
Tương đương shared_contracts.context_package trong file pipeline tham chiếu (repo này chưa có
nên định nghĩa tại đây). Gồm chunk đã chọn + metadata + citation index.

Cũng chứa Node 8: build_context_string + build_prompt (dựng prompt RAG có trích dẫn).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextChunk:
    chunk_id: str
    hotel_id: Any
    hotel_name: str | None
    text: str
    score: float
    citation_index: int
    source_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextPackage:
    query: str
    chunks: list[ContextChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "hotel_id": c.hotel_id,
                    "hotel_name": c.hotel_name,
                    "text": c.text,
                    "score": c.score,
                    "citation_index": c.citation_index,
                    "source_type": c.source_type,
                }
                for c in self.chunks
            ],
            "metadata": self.metadata,
        }


def build_context_package(
    query: str,
    ranked_hotels: list[dict[str, Any]],
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> ContextPackage:
    """Node 7C -> ContextPackage: list hotel đã rerank/aggregate -> chunk có citation index."""
    chunks: list[ContextChunk] = []
    for idx, doc in enumerate(ranked_hotels, start=1):
        md = doc.get("metadata") or {}
        chunks.append(
            ContextChunk(
                chunk_id=str(doc.get("chunk_id") or idx),
                hotel_id=doc.get("hotel_id"),
                hotel_name=md.get("hotel_name") or md.get("name"),
                text=doc.get("text") or "",
                score=float(doc.get("final_score", doc.get("business_score", 0.0))),
                citation_index=idx,
                source_type=doc.get("source_type"),
                metadata={
                    "matched_chunks": doc.get("matched_chunks"),
                    "ontology_concepts": md.get("ontology_concepts"),
                    "ke_review_score": md.get("ke_review_score") or md.get("review_score"),
                    "ke_star_rating": md.get("ke_star_rating") or md.get("star_rating"),
                    "city": md.get("city"),
                },
            )
        )
    return ContextPackage(
        query=query,
        chunks=chunks,
        metadata={"total_hotels": len(ranked_hotels), **(extra_metadata or {})},
    )


def build_context_string(pkg: ContextPackage, max_chunks: int = 5) -> str:
    """Node 8: ghép chunk thành context có đánh số [i] để LLM trích dẫn."""
    parts = []
    for c in pkg.chunks[:max_chunks]:
        meta = c.metadata
        head = f"[{c.citation_index}] {c.hotel_name or 'Khách sạn'} "
        extra = []
        if meta.get("city"):
            extra.append(f"tại {meta['city']}")
        if meta.get("ke_star_rating"):
            extra.append(f"{meta['ke_star_rating']}★")
        if meta.get("ke_review_score"):
            extra.append(f"điểm {meta['ke_review_score']}/10")
        if extra:
            head += "(" + ", ".join(str(e) for e in extra) + ")"
        parts.append(f"{head}\nNội dung: {c.text}")
    return "\n\n".join(parts)


PROMPT_TEMPLATE = """Bạn là trợ lý tư vấn du lịch của DA10 Travel Assistant. Trả lời câu hỏi DỰA TRÊN \
thông tin ngữ cảnh dưới đây.

Ngữ cảnh:
---
{context}
---

Yêu cầu:
1. Chỉ dùng thông tin trong ngữ cảnh (không bịa).
2. Nếu thiếu thông tin, nói rõ "Tôi không tìm thấy thông tin cụ thể trong dữ liệu".
3. Khi nhắc một khách sạn, trích dẫn nguồn [i] tương ứng.

Câu hỏi: "{query}"
"""


def build_prompt(pkg: ContextPackage, max_chunks: int = 5) -> str:
    """Node 8: dựng prompt RAG hoàn chỉnh từ ContextPackage."""
    return PROMPT_TEMPLATE.format(
        context=build_context_string(pkg, max_chunks=max_chunks),
        query=pkg.query,
    )
