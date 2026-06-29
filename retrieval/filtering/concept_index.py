"""concept_index.py — Node 3: inverted index concept_id -> {hotel_id}.

Production-hóa phần "lọc theo concept" của query_demo. Thay vì quét tuyến tính mọi hotel,
build sẵn inverted index từ knowledge_objects.json (qua ke_labels) -> lookup O(1) theo concept.

Hard concept (AMEN_/SETTING_/OBJ_/PRICE_/LOC_): tra trực tiếp.
Feel concept (STYLE_/ASPECT_): dùng strong_feel_concepts (đã lọc ngưỡng 0.6 ở ke_labels).
Landmark (LMK_): từ nearby_landmarks.

Lookup trả candidate theo 2 chế độ:
  - require_all=True  -> giao (AND) mọi concept (lọc cứng).
  - require_all=False -> hợp (OR) + đếm match_count mỗi hotel (cho ranking/soft).
"""

from __future__ import annotations

import glob
import math
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from knowledge_engineering.common.ke_labels import load_ke_labels

LOC_GLOB = "ontology/core/location*.yaml"


@lru_cache(maxsize=1)
def _loc_parent() -> dict[str, str]:
    """LOC_* -> parent LOC_* (từ core location). Cho hierarchy match (Phú Quốc bao Gành Dầu)."""
    out: dict[str, str] = {}
    for f in glob.glob(LOC_GLOB):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            p = (v or {}).get("parent") or (v or {}).get("located_in")
            if p:
                out[cid] = p
    return out


def _is_same_or_child(child: str | None, parent: str) -> bool:
    """child == parent HOẶC child là hậu duệ của parent (đi ngược chuỗi parent)."""
    cur, par = child, _loc_parent()
    seen = 0
    while cur and seen < 50:
        if cur == parent:
            return True
        cur = par.get(cur)
        seen += 1
    return False


@lru_cache(maxsize=64)
def hotels_in_location(loc_concept: str) -> frozenset[int]:
    """Mọi hotel có location_concept == loc HOẶC thuộc loc (hậu duệ). Hierarchy-aware: query
    'Phú Quốc' (LOC_PHU_QUOC) nhặt cả hotel ở 'Gành Dầu' (LOC_GANH_DAU, con của Phú Quốc).
    Trước đây concept index chỉ khớp ĐÚNG loc -> hotel ở xã con bị loại oan."""
    labels = load_ke_labels()
    return frozenset(
        hid for hid, ke in labels.items()
        if _is_same_or_child(ke.get("location_concept"), loc_concept)
    )


@dataclass
class ConceptLookupResult:
    hotel_ids: list[int] = field(default_factory=list)
    match_count: dict[int, int] = field(default_factory=dict)   # hotel_id -> số concept khớp
    idf_score: dict[int, float] = field(default_factory=dict)   # hotel_id -> tổng IDF concept khớp (V5)


@lru_cache(maxsize=1)
def build_concept_index() -> dict[str, set[int]]:
    """concept_id -> set(hotel_id). Gom hard + strong_feel + landmark từ ke_labels."""
    labels = load_ke_labels()
    index: dict[str, set[int]] = defaultdict(set)
    for hid, ke in labels.items():
        for c in ke.get("ontology_concepts", []):
            index[c].add(hid)
        for c in ke.get("strong_feel_concepts", []):
            index[c].add(hid)
        for lm in ke.get("nearby_landmarks", []):
            cid = lm.get("concept")
            if cid:
                index[cid].add(hid)
        loc = ke.get("location_concept")
        if loc:
            index[loc].add(hid)
    return dict(index)


def lookup_hotels_by_concepts(
    concepts: list[str],
    *,
    require_all: bool = False,
    index: dict[str, set[int]] | None = None,
) -> ConceptLookupResult:
    """Tra hotel theo danh sách concept. Bỏ qua concept không có hotel nào (tránh AND ra rỗng giả
    — cùng tinh thần _LIVE_CONCEPTS của query_demo)."""
    if index is None:
        index = build_concept_index()
    if not concepts:
        return ConceptLookupResult()

    sets = [index.get(c, set()) for c in concepts]
    live = [s for s in sets if s]            # concept thực sự có hotel
    if not live:
        return ConceptLookupResult()

    # V5: tổng số hotel để tính IDF. Concept hiếm (vd STYLE_LIVELY 1/520) đặc trưng hơn nhiều
    # concept phổ thông (OBJ_HOTEL 393/520) → trọng số IDF = log(N/df) cao hơn hẳn.
    n_total = len(load_ke_labels())
    match_count: dict[int, int] = defaultdict(int)
    idf_score: dict[int, float] = defaultdict(float)
    for s in live:
        idf = math.log((n_total + 1) / (len(s) + 1)) + 1.0   # smoothed IDF, luôn > 0
        for hid in s:
            match_count[hid] += 1
            idf_score[hid] += idf

    if require_all:
        hotel_ids = set.intersection(*live) if live else set()
    else:
        hotel_ids = set().union(*live)

    # sort theo IDF (sát query theo concept ĐẶC TRƯNG), tiebreak match_count
    ranked = sorted(hotel_ids, key=lambda h: (-idf_score[h], -match_count[h]))
    return ConceptLookupResult(
        hotel_ids=ranked, match_count=dict(match_count), idf_score=dict(idf_score)
    )
