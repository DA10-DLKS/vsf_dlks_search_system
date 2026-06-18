"""frontend_adapter.py — Map kết quả pipeline (run_hybrid_search) sang schema FRONTEND.

Frontend (frontend/src/types/searchTypes.js) có contract CỐ ĐỊNH:
  /search  -> {query, results[], total}; result = {id,title,snippet,score,metadata,citations,
               source_documents, context_chunks}
  /context -> {result_id, llm_context, citations, source_documents, context_chunks}

Backend không bắt frontend đổi — adapter này dịch shape pipeline -> shape frontend. Lấy thêm
metadata hiển thị (location/amenities/price_level/best_for) từ ke_labels + knowledge_objects.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from knowledge_engineering.common.ke_labels import labels_for

KO_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"

# Map concept -> nhãn hiển thị tiếng Việt cho amenities/best_for (gọn, dễ đọc trên UI).
_AMEN_VI = {
    "AMEN_POOL": "Hồ bơi", "AMEN_INFINITY_POOL": "Hồ bơi vô cực", "AMEN_PRIVATE_POOL": "Hồ bơi riêng",
    "AMEN_KIDS_POOL": "Hồ bơi trẻ em", "AMEN_BEACHFRONT": "Sát biển", "AMEN_SEA_VIEW": "View biển",
    "AMEN_SPA": "Spa", "AMEN_GYM": "Phòng gym", "AMEN_GOLF": "Sân golf", "AMEN_KIDS_CLUB": "Kids club",
    "AMEN_RESTAURANT": "Nhà hàng", "AMEN_BAR": "Quán bar", "AMEN_WIFI": "Wi-Fi",
    "AMEN_PARKING": "Bãi đỗ xe", "AMEN_MEETING_ROOM": "Phòng họp", "AMEN_AIRPORT_SHUTTLE": "Đưa đón sân bay",
    "AMEN_PET_FRIENDLY": "Cho thú cưng", "AMEN_BABYSITTING": "Trông trẻ", "AMEN_BIKE": "Thuê xe đạp",
    "AMEN_KITCHEN": "Bếp", "AMEN_GARDEN": "Sân vườn", "AMEN_TENNIS": "Sân tennis",
    "AMEN_KARAOKE": "Karaoke", "AMEN_WATERSPORT": "Thể thao nước", "AMEN_HIKING": "Leo núi",
}
_PURPOSE_VI = {
    "PURPOSE_FAMILY": "Gia đình", "PURPOSE_ROMANTIC": "Cặp đôi", "PURPOSE_GROUP": "Nhóm",
    "PURPOSE_SOLO": "Đi một mình", "PURPOSE_BUSINESS": "Công tác", "PURPOSE_WELLNESS": "Nghỉ dưỡng",
}
_PRICE_VI = {
    "PRICE_BUDGET": "Bình dân", "PRICE_MID": "Tầm trung",
    "PRICE_UPSCALE": "Cao cấp", "PRICE_LUXURY": "Sang trọng",
}


@lru_cache(maxsize=1)
def _objs() -> dict:
    return json.load(open(KO_JSON, encoding="utf-8"))


def _obj(hotel_id: Any) -> dict:
    return _objs().get(f"acc_{hotel_id}", {})


def _hotel_metadata(hotel_id: Any) -> dict[str, Any]:
    ke = labels_for(hotel_id)
    obj = _obj(hotel_id)
    loc = obj.get("location") or {}
    concepts = set(ke.get("ontology_concepts") or [])
    amenities = [_AMEN_VI[c] for c in ke.get("ontology_concepts") or [] if c in _AMEN_VI]
    best_for = [_PURPOSE_VI[c] for c in concepts if c in _PURPOSE_VI]
    price_level = next((_PRICE_VI[c] for c in concepts if c in _PRICE_VI), "Unknown")
    rf = ke.get("range_filters") or {}
    star = rf.get("star_rating")
    score = rf.get("review_score")
    rank_bits = []
    if star:
        rank_bits.append(f"{star:g}★")
    if score:
        rank_bits.append(f"điểm {score:g}/10")
    # location: bỏ trùng city==province (data nhiều nơi city=province)
    parts = [loc.get("city")]
    if loc.get("province") and loc.get("province") != loc.get("city"):
        parts.append(loc.get("province"))
    return {
        "location": ", ".join(p for p in parts if p) or "Unknown location",
        "category": (obj.get("semantic_metadata") or {}).get("object_type", "OBJ_HOTEL").replace("OBJ_", "").title(),
        "amenities": amenities[:8],
        "ranking_info": " · ".join(rank_bits) or "No ranking information",
        "price_level": price_level,
        "best_for": best_for[:3],   # giới hạn 3 nhóm chính, tránh nhiễu UI
    }


def _snippet(hotel_id: Any, chunk_text: str | None) -> str:
    if chunk_text:
        return chunk_text[:200]
    content = (_obj(hotel_id).get("content") or "").strip()
    return content[:200] or "Không có mô tả."


def to_search_response(query: str, pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """pipeline run_hybrid_search -> {query, results[], total} cho frontend /search."""
    results = []
    for c in pipeline_result.get("context_package", {}).get("chunks", []):
        hid = c.get("hotel_id")
        results.append({
            "id": f"hotel_{hid}",
            "title": c.get("hotel_name") or f"hotel_{hid}",
            "snippet": _snippet(hid, c.get("text")),
            "score": round(float(c.get("score", 0)), 4),
            "metadata": _hotel_metadata(hid),
            "citations": [{
                "id": f"cit_{hid}",
                "source_document_id": f"doc_{hid}",
                "chunk_id": str(c.get("chunk_id", "")),
                "label": c.get("hotel_name") or "Hotel detail",
                "url": (_obj(hid).get("provenance") or {}).get("source_url", ""),
                "quote": _snippet(hid, c.get("text"))[:120],
            }],
            "source_documents": [{
                "id": f"doc_{hid}",
                "title": c.get("hotel_name") or f"hotel_{hid}",
                "type": "hotel_detail",
                "url": (_obj(hid).get("provenance") or {}).get("source_url", ""),
            }],
            "context_chunks": [{
                "id": str(c.get("chunk_id", f"chunk_{hid}")),
                "source_document_id": f"doc_{hid}",
                "text": c.get("text") or _snippet(hid, None),
                "rank": c.get("citation_index", 1),
            }],
        })
    return {"query": query, "results": results, "total": len(results)}


def build_hotel_context(result_id: str) -> dict[str, Any]:
    """Dựng context cho 1 hotel ĐƯỢC CHỌN (result_id='hotel_<id>') -> Node 9 sinh llm_context.

    KHÔNG search lại — lấy thẳng knowledge_object của hotel đó làm ngữ cảnh, để LLM giải thích
    đúng hotel user click (tránh trả 'không tìm thấy' khi search theo tên không khớp)."""
    from context import ContextChunk, ContextPackage, generate_answer

    hotel_id = result_id.replace("hotel_", "")
    obj = _obj(hotel_id)
    title = obj.get("title") or result_id
    md = _hotel_metadata(hotel_id)
    content = (obj.get("content") or "").strip()

    pkg = ContextPackage(
        query=f"Vì sao {title} phù hợp? Giới thiệu ngắn gọn.",
        chunks=[ContextChunk(
            chunk_id=f"chunk_{hotel_id}",
            hotel_id=hotel_id,
            hotel_name=title,
            text=content or "Không có mô tả chi tiết.",
            score=1.0,
            citation_index=1,
            metadata={"city": md["location"], "ke_star_rating": None, "ke_review_score": None},
        )],
        metadata={"hotel_id": hotel_id},
    )
    ans = generate_answer(pkg)
    return {
        "result_id": result_id,
        "llm_context": ans.get("answer", ""),
        "citations": [f"cit_{hotel_id}"],
        "source_documents": [f"doc_{hotel_id}"],
        "context_chunks": [f"chunk_{hotel_id}"],
    }
