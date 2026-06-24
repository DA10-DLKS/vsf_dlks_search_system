"""frontend_adapter.py — Map pipeline -> frontend hotel2.json schema.

Replaces the OTA (Supabase) API with a local 6.6MB hotel_detail_cache.json
built from cleaned data (520 hotels). No external HTTP calls needed for
hotel detail — faster, no cold-start, no Render.com dependency.

Response schema matches frontend/src/types/searchTypes.js (HotelMetadata).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from knowledge_engineering.common.ke_labels import labels_for
from knowledge_engineering.common.hotel_data import filter_rooms, get_hotel, get_rooms

KO_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"

_log = logging.getLogger(__name__)

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
_ASPECT_VI = {
    "ASPECT_SERVICE": "Dịch vụ", "ASPECT_VALUE": "Đáng tiền", "ASPECT_CLEANLINESS": "Sạch sẽ",
    "ASPECT_FACILITIES": "Cơ sở vật chất", "ASPECT_LOCATION": "Vị trí", "ASPECT_ROOM": "Phòng",
    "ASPECT_FOOD": "Đồ ăn", "STYLE_QUIET": "Yên tĩnh", "STYLE_LIVELY": "Sôi động",
    "STYLE_NEW": "Mới/hiện đại", "STYLE_LUXURY": "Sang trọng", "STYLE_COZY": "Ấm cúng",
}


def _concept_vi(concept: str) -> str:
    return _ASPECT_VI.get(concept) or _PURPOSE_VI.get(concept) or _AMEN_VI.get(concept) or concept


def _grounded_evidence(
    hotel_id: Any, max_pos: int = 5, query_concepts: set[str] | None = None
) -> dict[str, Any]:
    """V6: real evidence from ABSA (semantic_profile + negative_style_profile)."""
    ke = labels_for(hotel_id)
    sp = ke.get("semantic_profile") or {}
    neg = ke.get("negative_style_profile") or {}
    qc = query_concepts or set()

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
    parts = []
    if content:
        parts.append(content[:600])

    pos = evidence.get("positives") or []
    neg = evidence.get("negatives") or []

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
    parts = [loc.get("city")]
    if loc.get("province") and loc.get("province") != loc.get("city"):
        parts.append(loc.get("province"))
    return {
        "location": ", ".join(p for p in parts if p) or "Unknown location",
        "category": (obj.get("semantic_metadata") or {}).get("object_type", "OBJ_HOTEL").replace("OBJ_", "").title(),
        "amenities": amenities[:8],
        "ranking_info": " · ".join(rank_bits) or "No ranking information",
        "price_level": price_level,
        "best_for": best_for[:3],
    }


def to_search_response(query: str, pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """pipeline -> {query, results[], total} for frontend /search.

    Reads full hotel detail from local hotel_detail_cache.json (no OTA API).
    Each result includes `rooms_matching[]` — rooms that fall within the
    price range the user specified in their query.
    """
    pairs: list[tuple[Any, float]] = []
    seen: set[Any] = set()
    for c in pipeline_result.get("context_package", {}).get("chunks", []):
        hid = c.get("hotel_id")
        if hid is None or hid in seen:
            continue
        seen.add(hid)
        pairs.append((hid, round(float(c.get("score", 0)), 4)))

    if not pairs:
        return {"query": query, "results": [], "total": 0}

    # Extract price filter from intent (numeric range or price tier)
    intent = pipeline_result.get("intent") or {}
    intent_range = intent.get("range") or {}
    price_min = intent_range.get("price_min")
    price_max = intent_range.get("price_max")

    # Map price_tiers to numeric range when no explicit min/max
    if price_min is None and price_max is None:
        tiers = set(intent.get("price_tiers") or [])
        if "PRICE_BUDGET" in tiers:
            price_max = 800000
        elif "PRICE_LUXURY" in tiers:
            price_min = 2000000

    results = []
    for hid, score in pairs:
        obj = get_hotel(hid)
        if obj is None:
            _log.warning("hotel_id=%s not found in local cache, skipping", hid)
            continue

        merged: dict[str, Any] = {}
        for k, v in obj.items():
            merged[k] = v
            if k == "hotel_id":
                merged["score"] = score
        if "score" not in merged:
            merged["score"] = score

        # Override rooms with price-filtered list so frontend only sees matching rooms
        if price_min is not None or price_max is not None:
            merged["rooms"] = filter_rooms(hid, min_price=price_min, max_price=price_max)
            prices = [r["price_per_night"] for r in merged["rooms"] if r.get("price_per_night")]
            merged["price_from"] = min(prices) if prices else None
        else:
            merged["rooms"] = get_rooms(hid)
        merged["rooms_matching"] = merged["rooms"]

        results.append(merged)

    return {"query": query, "results": results, "total": len(results)}


def build_hotel_context(result_id: str, query: str | None = None) -> dict[str, Any]:
    """Build /context response for a single selected hotel.

    Uses hotel_detail_cache.json for data (not OTA API).
    """
    from context import ContextChunk, ContextPackage, generate_answer

    hotel_id = result_id.replace("hotel_", "")
    obj = _obj(hotel_id)
    title = obj.get("title") or result_id
    md = _hotel_metadata(hotel_id)
    content = (obj.get("content") or "").strip()

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

    display_chunks = _evidence_chunks(hotel_id, title, content, evidence, md)
    return {
        "result_id": result_id,
        "llm_context": ans.get("answer", ""),
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
