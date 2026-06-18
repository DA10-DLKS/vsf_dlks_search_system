"""ke_labels.py — Cầu nối KE -> tầng index. Đọc knowledge_objects.json (output enrichment)
và trả nhãn ontology theo hotel_id, để indexer (pgvector / BM25) ĐÍNH nhãn vào payload chunk.

Lý do tồn tại (đứt gãy Nhóm 0): tầng index chunk text phong phú từ data/cleaned, nhưng cleaned
KHÔNG có nhãn ontology đã enrich (amenity/setting/style/aspect/landmark...). File này JOIN nhãn
đó vào theo hotel_id. Một nguồn nhãn DUY NHẤT cho cả 2 indexer (tránh lệch).

Quy ước: knowledge_objects.json là dict, key dạng "acc_<id>"; ta map về hotel_id dạng int.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

KO_JSON_DEFAULT = "knowledge_engineering/enrichment/knowledge_objects.json"

# Ngưỡng để coi một concept CẢM NHẬN (style/aspect) là "đủ mạnh" -> đưa vào danh sách concept
# phẳng cho filter/boost. Giữ ĐỒNG BỘ với query_demo.FEEL_MIN (tầng test) để index và query
# hiểu nhãn như nhau. Profile score < ngưỡng vẫn giữ ở semantic_profile (dùng cho rerank).
FEEL_MIN = 0.6


def _hotel_id_from_key(key: str) -> int | None:
    """ "acc_1015998" -> 1015998. Trả None nếu không parse được."""
    try:
        return int(key.replace("acc_", ""))
    except (ValueError, AttributeError):
        return None


def _flat_concepts(obj: dict[str, Any]) -> list[str]:
    """Gom MỌI concept HARD trong semantic_metadata thành 1 list phẳng (amenity/setting/
    object_type/purpose/price_tier/style/location/nearby_landmark). Dùng cho inverted index
    + filter concept ở tầng retrieval (Node 3)."""
    out: set[str] = set()
    sm = obj.get("semantic_metadata") or {}
    for v in sm.values():
        if isinstance(v, list):
            out.update(c for c in v if isinstance(c, str))
        elif isinstance(v, str) and v:
            out.add(v)
    return sorted(out)


def _strong_feel_concepts(obj: dict[str, Any]) -> list[str]:
    """STYLE_/ASPECT_ có profile score >= FEEL_MIN -> coi như 'có' (đưa vào concept phẳng).
    Tách riêng vì semantic_metadata.style chỉ giữ style mạnh; aspect không nằm ở metadata."""
    out: set[str] = set()
    for cid, val in (obj.get("semantic_profile") or {}).items():
        if (val or {}).get("score", 0) >= FEEL_MIN and cid.startswith(("STYLE_", "ASPECT_")):
            out.add(cid)
    return sorted(out)


@lru_cache(maxsize=1)
def load_ke_labels(ko_json: str = KO_JSON_DEFAULT) -> dict[int, dict[str, Any]]:
    """hotel_id(int) -> nhãn KE để đính vào payload chunk:

        {
          "ontology_concepts": [...],        # HARD concept phẳng (filter/inverted index)
          "strong_feel_concepts": [...],     # STYLE/ASPECT đạt ngưỡng (filter mềm)
          "semantic_profile": {cid: {score,...}},  # đầy đủ điểm (rerank)
          "negative_style_profile": {...},
          "range_filters": {star_rating, review_score, price_min_vnd, price_capped},
          "nearby_landmarks": [{concept, distance_km}],
          "location_concept": "LOC_...",     # concept location đã resolve
        }

    Trả {} nếu file không tồn tại (indexer vẫn chạy, chỉ thiếu nhãn — không vỡ pipeline).
    """
    if not os.path.exists(ko_json):
        return {}
    with open(ko_json, encoding="utf-8") as fh:
        objs = json.load(fh)

    labels: dict[int, dict[str, Any]] = {}
    for key, obj in objs.items():
        hid = _hotel_id_from_key(key) or _hotel_id_from_key(str(obj.get("id", "")))
        if hid is None:
            continue
        sm = obj.get("semantic_metadata") or {}
        loc = obj.get("location") or {}
        labels[hid] = {
            "ontology_concepts": _flat_concepts(obj),
            "strong_feel_concepts": _strong_feel_concepts(obj),
            "semantic_profile": obj.get("semantic_profile") or {},
            "negative_style_profile": obj.get("negative_style_profile") or {},
            "range_filters": obj.get("range_filters") or {},
            "nearby_landmarks": obj.get("nearby_landmarks") or [],
            "location_concept": sm.get("location"),
            "city": loc.get("city"),
            "province": loc.get("province"),
            "title": obj.get("title"),
        }
    return labels


def labels_for(hotel_id: Any, ko_json: str = KO_JSON_DEFAULT) -> dict[str, Any]:
    """Nhãn KE cho 1 hotel_id (chấp nhận int/str/'acc_...'). {} nếu không có."""
    if isinstance(hotel_id, str):
        hotel_id = _hotel_id_from_key(hotel_id) if hotel_id.startswith("acc_") else hotel_id
    try:
        hid = int(hotel_id)
    except (ValueError, TypeError):
        return {}
    return load_ke_labels(ko_json).get(hid, {})
