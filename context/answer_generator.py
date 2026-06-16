"""answer_generator.py — Node 9: sinh câu trả lời cuối từ ContextPackage.

Dùng LLM client đa-provider của KE (knowledge_engineering.enrichment.llm.complete_text),
provider/model theo .env (LLM_PROVIDER/LLM_MODEL). Prompt RAG dựng ở context.build_prompt
(Node 8). Trả answer + danh sách citation (hotel được trích).

Tách khỏi pipeline retrieval: chỉ chạy khi cần câu trả lời ngôn ngữ (API có thể trả
ContextPackage thô cho client tự render, hoặc gọi node này để có answer sẵn).
"""

from __future__ import annotations

from typing import Any

from context.context_package import ContextPackage, build_prompt

SYSTEM_PROMPT = (
    "Bạn là trợ lý tư vấn du lịch tiếng Việt, trả lời ngắn gọn, chính xác, có trích dẫn nguồn. "
    "Tuyệt đối không bịa thông tin ngoài ngữ cảnh."
)


def generate_answer(
    pkg: ContextPackage,
    *,
    max_chunks: int = 5,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Node 9: gọi LLM sinh câu trả lời từ ContextPackage. Trả {answer, citations, model}.

    Nếu LLM lỗi (thiếu key/mạng), trả answer rỗng + error để API không vỡ — client vẫn nhận
    được citations/context.
    """
    from knowledge_engineering.enrichment.llm import active_config, complete_text

    prompt = build_prompt(pkg, max_chunks=max_chunks)
    citations = [
        {
            "index": c.citation_index,
            "hotel_id": c.hotel_id,
            "hotel_name": c.hotel_name,
            "score": round(c.score, 4),
        }
        for c in pkg.chunks[:max_chunks]
    ]
    cfg = active_config()
    try:
        answer = complete_text(system=SYSTEM_PROMPT, user=prompt, temperature=temperature)
        return {"answer": answer, "citations": citations,
                "model": f"{cfg['provider']}/{cfg['model']}", "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"answer": "", "citations": citations,
                "model": f"{cfg['provider']}/{cfg['model']}", "error": str(exc)}
