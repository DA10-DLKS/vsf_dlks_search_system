"""frontend_adapter.py — Map kết quả pipeline (run_hybrid_search) sang schema FRONTEND.

Frontend (frontend/src/types/searchTypes.js) có contract CỐ ĐỊNH:
  /search  -> {query, results[], total}; result = {id,title,snippet,score,metadata,citations,
               source_documents, context_chunks}
  /context -> {result_id, llm_context, citations, source_documents, context_chunks}

Backend không bắt frontend đổi — adapter này dịch shape pipeline -> shape frontend. Lấy thêm
metadata hiển thị (location/amenities/price_level/best_for) từ ke_labels + knowledge_objects.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Any

import httpx

from knowledge_engineering.common.ke_labels import labels_for

KO_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"

_log = logging.getLogger(__name__)

# API OTA (Supabase) trả full hotel object đúng schema frontend (hotel2.json). /search chỉ lo
# RANKING (pipeline) còn DỮ LIỆU hiển thị lấy từ đây theo hotel_id. Key/timeout cấu hình qua env.
OTA_API_BASE = os.getenv("OTA_API_BASE", "https://supabase-ota-travel.onrender.com").rstrip("/")
OTA_API_KEY = os.getenv("OTA_API_KEY", "ota_sk_7f3d9b2e1a4c8f6e5d3a")
OTA_API_TIMEOUT = float(os.getenv("OTA_API_TIMEOUT", "30"))

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
# Nhãn aspect (ABSA) tiếng Việt — dùng dựng evidence grounding cho /context (V6).
_ASPECT_VI = {
    "ASPECT_SERVICE": "Dịch vụ", "ASPECT_VALUE": "Đáng tiền", "ASPECT_CLEANLINESS": "Sạch sẽ",
    "ASPECT_FACILITIES": "Cơ sở vật chất", "ASPECT_LOCATION": "Vị trí", "ASPECT_ROOM": "Phòng",
    "ASPECT_FOOD": "Đồ ăn", "STYLE_QUIET": "Yên tĩnh", "STYLE_LIVELY": "Sôi động",
    "STYLE_NEW": "Mới/hiện đại", "STYLE_LUXURY": "Sang trọng", "STYLE_COZY": "Ấm cúng",
}


def _concept_vi(concept: str) -> str:
    """Nhãn tiếng Việt cho 1 concept, gộp mọi nhóm (aspect/purpose/amenity); fallback = raw."""
    return _ASPECT_VI.get(concept) or _PURPOSE_VI.get(concept) or _AMEN_VI.get(concept) or concept


def _grounded_evidence(
    hotel_id: Any, max_pos: int = 5, query_concepts: set[str] | None = None
) -> dict[str, Any]:
    """V6: rút bằng chứng THẬT từ ABSA (semantic_profile + negative_style_profile) thay vì chỉ
    dùng content marketing. Trả mặt mạnh (aspect score cao, có evidence_count) + mặt yếu (negative
    span review thật) để câu trả lời CÂN BẰNG, không tâng bốc, không bịa.

    V7 (#4-A): nếu có query_concepts (từ parse_intent), ƯU TIÊN aspect KHỚP query lên đầu ở CẢ hai
    chiều pos/neg và đánh dấu `matched=True`. Soi cả negative để KHÔNG tâng bốc sai: hotel điểm
    positive thấp nhưng negative cao về cùng aspect (vd 'yên tĩnh') sẽ nổi lên ở mặt hạn chế."""
    ke = labels_for(hotel_id)
    sp = ke.get("semantic_profile") or {}
    neg = ke.get("negative_style_profile") or {}
    qc = query_concepts or set()

    # Ưu tiên: aspect khớp query trước (matched), trong mỗi nhóm vẫn sort theo score giảm dần.
    def _pos_key(item):
        c, v = item
        return (0 if c in qc else 1, -(v.get("score") or 0))

    positives = []
    for c, v in sorted(sp.items(), key=_pos_key):
        if (v.get("evidence_count") or 0) < 1:
            continue
        positives.append({
            "concept": c,
            "aspect": _concept_vi(c),
            "score": round(float(v.get("score") or 0), 2),
            "evidence_count": int(v.get("evidence_count") or 0),
            "matched": c in qc,
        })
        if len(positives) >= max_pos:
            break

    def _neg_key(item):
        c, v = item
        return (0 if c in qc else 1, -(v.get("negative_score") or 0))

    negatives = []
    for c, v in sorted(neg.items(), key=_neg_key):
        spans = [s for s in (v.get("top_spans") or []) if s][:2]
        negatives.append({
            "concept": c,
            "aspect": _concept_vi(c),
            "negative_score": round(float(v.get("negative_score") or 0), 2),
            "spans": spans,
            "matched": c in qc,
        })

    return {"positives": positives, "negatives": negatives}


def _evidence_text(title: str, content: str, evidence: dict[str, Any]) -> str:
    """Gộp content + evidence ABSA thành 1 đoạn ngữ cảnh có dẫn chứng cho LLM.

    V7: nêu RÕ aspect khớp nhu cầu query (matched) ở phần đầu — gồm CẢ chiều tích cực lẫn tiêu cực —
    để LLM trả lời trung thực: hotel mạnh/yếu đúng tiêu chí user hỏi, không tâng bốc."""
    parts = []
    if content:
        parts.append(content[:600])

    pos = evidence.get("positives") or []
    neg = evidence.get("negatives") or []

    # Phần khớp nhu cầu user: gom cả pos+neg của các aspect matched để LLM cân nhắc 2 chiều.
    matched_pos = [p for p in pos if p.get("matched")]
    matched_neg = [n for n in neg if n.get("matched")]
    for p in matched_pos:
        parts.append(
            f"Về tiêu chí '{p['aspect']}' (khách hỏi): điểm tích cực {p['score']} "
            f"từ {p['evidence_count']} lượt đánh giá."
        )
    for n in matched_neg:
        line = f"Về tiêu chí '{n['aspect']}' (khách hỏi): có phản hồi tiêu cực (điểm {n['negative_score']})."
        if n.get("spans"):
            line += " Trích review: " + " | ".join(n["spans"])
        parts.append(line)

    other_pos = [p for p in pos if not p.get("matched")]
    if other_pos:
        parts.append("Điểm mạnh nổi bật khác (từ review thật): " + "; ".join(
            f"{p['aspect']} ({p['score']}, {p['evidence_count']} lượt)" for p in other_pos
        ))
    for n in neg:
        if not n.get("matched") and n.get("spans"):
            parts.append(f"Lưu ý mặt hạn chế — {n['aspect']}: " + " | ".join(n["spans"]))
    return "\n".join(parts) or "Không có mô tả chi tiết."


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


async def _fetch_hotel(client: httpx.AsyncClient, hotel_id: Any) -> dict[str, Any] | None:
    """Lấy full hotel object từ API OTA. Trả None nếu lỗi/không tồn tại -> hotel sẽ bị BỎ QUA."""
    try:
        r = await client.get(f"{OTA_API_BASE}/api/hotels/{hotel_id}")
        r.raise_for_status()
        obj = r.json()
        return obj if isinstance(obj, dict) else None
    except Exception as exc:  # noqa: BLE001 — 1 hotel lỗi không được làm hỏng cả request
        _log.warning("OTA fetch hotel_id=%s lỗi: %s", hotel_id, exc)
        return None


async def _fetch_hotels(pairs: list[tuple[Any, float]]) -> dict[Any, dict[str, Any]]:
    """Gọi API OTA cho tất cả hotel_id ĐỒNG THỜI (render.com cold-start chậm nếu gọi tuần tự)."""
    async with httpx.AsyncClient(
        timeout=OTA_API_TIMEOUT, headers={"X-API-Key": OTA_API_KEY}
    ) as client:
        objs = await asyncio.gather(*(_fetch_hotel(client, hid) for hid, _ in pairs))
    return {hid: obj for (hid, _), obj in zip(pairs, objs) if obj is not None}


def to_search_response(query: str, pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """pipeline run_hybrid_search -> {query, results[], total} cho frontend /search.

    Mỗi result là full hotel object (schema hotel2.json) lấy từ API OTA theo hotel_id, chèn thêm
    `score` = final_score của pipeline (làm tròn 4). Pipeline lo RANKING, API OTA lo DỮ LIỆU hiển thị.
    Hotel nào fetch lỗi thì bỏ qua; giữ nguyên thứ tự rank của pipeline."""
    # Gom (hotel_id, score) theo thứ tự rank, bỏ trùng (1 hotel có thể có nhiều chunk).
    pairs: list[tuple[Any, float]] = []
    seen: set[Any] = set()
    for c in pipeline_result.get("context_package", {}).get("chunks", []):
        hid = c.get("hotel_id")
        if hid is None or hid in seen:
            continue
        seen.add(hid)
        pairs.append((hid, round(float(c.get("score", 0)), 4)))

    fetched = asyncio.run(_fetch_hotels(pairs)) if pairs else {}

    results = []
    for hid, score in pairs:
        obj = fetched.get(hid)
        if obj is None:
            continue
        # Chèn `score` ngay sau `id` để khớp thứ tự field trong schema hotel2.json.
        merged: dict[str, Any] = {}
        for k, v in obj.items():
            merged[k] = v
            if k == "id":
                merged["score"] = score
        if "score" not in merged:  # phòng khi object không có `id`
            merged["score"] = score
        results.append(merged)
    return {"query": query, "results": results, "total": len(results)}


def build_hotel_context(result_id: str, query: str | None = None) -> dict[str, Any]:
    """Dựng context cho 1 hotel ĐƯỢC CHỌN (result_id='hotel_<id>') -> Node 9 sinh llm_context.

    KHÔNG search lại — lấy thẳng knowledge_object của hotel đó làm ngữ cảnh, để LLM giải thích
    đúng hotel user click (tránh trả 'không tìm thấy' khi search theo tên không khớp).

    V6: grounding theo BẰNG CHỨNG THẬT (ABSA: aspect mạnh + mặt yếu từ review), không chỉ content
    marketing → câu trả lời cân bằng, đáng tin. Truyền query gốc của user nếu có (thay câu hard-code)."""
    from context import ContextChunk, ContextPackage, generate_answer

    hotel_id = result_id.replace("hotel_", "")
    obj = _obj(hotel_id)
    title = obj.get("title") or result_id
    md = _hotel_metadata(hotel_id)
    content = (obj.get("content") or "").strip()

    # #4-A: trích concept từ query gốc để ƯU TIÊN evidence khớp nhu cầu user (cả pos lẫn neg).
    query_concepts: set[str] = set()
    q_clean = (query or "").strip()
    if q_clean:
        try:
            from retrieval.query_processing.intent_parser import parse_intent
            query_concepts = set(parse_intent(q_clean).concepts)
        except Exception:
            query_concepts = set()
    evidence = _grounded_evidence(hotel_id, query_concepts=query_concepts)
    grounded_text = _evidence_text(title, content, evidence)
    rf = labels_for(hotel_id).get("range_filters") or {}

    # #3-B: vẫn truyền query gốc (đã được nới prompt trong context_package) để câu trả lời bám nhu cầu;
    # nếu không có query thì hỏi giới thiệu chung hotel.
    pkg = ContextPackage(
        query=q_clean or f"Vì sao {title} phù hợp? Giới thiệu ngắn gọn.",
        chunks=[ContextChunk(
            chunk_id=f"chunk_{hotel_id}",
            hotel_id=hotel_id,
            hotel_name=title,
            text=grounded_text,
            score=1.0,
            citation_index=1,
            metadata={
                "city": md["location"], "ke_star_rating": rf.get("star_rating"),
                "ke_review_score": rf.get("review_score"),
                "absa_positives": evidence["positives"], "absa_negatives": evidence["negatives"],
            },
        )],
        metadata={"hotel_id": hotel_id, "grounded": True},
    )
    ans = generate_answer(pkg)

    # #1-B: tách evidence ABSA đã có thành NHIỀU chunk hiển thị (matched lên đầu), thay vì 1 chunk gộp.
    display_chunks = _evidence_chunks(hotel_id, title, content, evidence, md)
    return {
        "result_id": result_id,
        "llm_context": ans.get("answer", ""),
        # #2: trả OBJECT thật (không phải string id) để frontend render đúng text + metadata.
        "citations": [{
            "id": f"cit_{hotel_id}",
            "source_document_id": f"doc_{hotel_id}",
            "label": title,
            "url": (obj.get("provenance") or {}).get("source_url", ""),
            "quote": (content[:160] or grounded_text[:160]),
        }],
        "source_documents": [{
            "id": f"doc_{hotel_id}",
            "title": title,
            "type": "hotel_detail",
            "url": (obj.get("provenance") or {}).get("source_url", ""),
        }],
        "context_chunks": display_chunks,
        "evidence": evidence,
    }


def _evidence_chunks(
    hotel_id: Any, title: str, content: str, evidence: dict[str, Any], md: dict[str, Any]
) -> list[dict[str, Any]]:
    """#1-B: dựng NHIỀU chunk hiển thị từ ABSA đã enrich (không search lại).

    Thứ tự: (1) chunk tổng quan từ content; (2) các aspect KHỚP query (matched) — cả mặt mạnh lẫn
    mặt hạn chế có span review thật; (3) các điểm mạnh/hạn chế nổi bật khác. Positive chỉ có
    score+count (data không lưu span positive); negative có top_spans = câu review nguyên văn."""
    chunks: list[dict[str, Any]] = []

    if content:
        chunks.append({
            "chunk_id": f"chunk_{hotel_id}_overview",
            "hotel_name": title,
            "source_type": "hotel_content",
            "text": content[:400],
            "score": None,
            "metadata": {"location": md.get("location")},
        })

    pos = evidence.get("positives") or []
    neg = evidence.get("negatives") or []
    # matched trước, trong nhóm giữ nguyên thứ tự đã sort ở _grounded_evidence.
    ordered_pos = [p for p in pos if p.get("matched")] + [p for p in pos if not p.get("matched")]
    ordered_neg = [n for n in neg if n.get("matched")] + [n for n in neg if not n.get("matched")]

    for p in ordered_pos:
        tag = " (khớp nhu cầu)" if p.get("matched") else ""
        chunks.append({
            "chunk_id": f"chunk_{hotel_id}_pos_{p['concept']}",
            "hotel_name": title,
            "source_type": "absa_positive",
            "text": f"Điểm mạnh{tag}: {p['aspect']} — đánh giá tích cực {p['score']} "
                    f"từ {p['evidence_count']} lượt review.",
            "score": p["score"],
            "metadata": {"concept": p["concept"], "evidence_count": p["evidence_count"],
                         "matched": p["matched"]},
        })

    for n in ordered_neg:
        if not n.get("spans"):
            continue
        tag = " (khớp nhu cầu)" if n.get("matched") else ""
        chunks.append({
            "chunk_id": f"chunk_{hotel_id}_neg_{n['concept']}",
            "hotel_name": title,
            "source_type": "absa_negative",
            "text": f"Mặt hạn chế{tag}: {n['aspect']} (điểm tiêu cực {n['negative_score']}). "
                    f"Trích review thật: " + " | ".join(n["spans"]),
            "score": n["negative_score"],
            "metadata": {"concept": n["concept"], "matched": n["matched"], "spans": n["spans"]},
        })

    return chunks
