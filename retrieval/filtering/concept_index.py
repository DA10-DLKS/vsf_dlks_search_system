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

from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from knowledge_engineering.common.ke_labels import load_ke_labels


@dataclass
class ConceptLookupResult:
    hotel_ids: list[int] = field(default_factory=list)
    match_count: dict[int, int] = field(default_factory=dict)   # hotel_id -> số concept khớp


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

    match_count: dict[int, int] = defaultdict(int)
    for s in live:
        for hid in s:
            match_count[hid] += 1

    if require_all:
        hotel_ids = set.intersection(*live) if live else set()
    else:
        hotel_ids = set().union(*live)

    ranked = sorted(hotel_ids, key=lambda h: -match_count[h])
    return ConceptLookupResult(hotel_ids=ranked, match_count=dict(match_count))
