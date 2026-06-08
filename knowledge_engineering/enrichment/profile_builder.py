"""profile_builder.py — Hotel Semantic Profile (Sprint 2, Bước 5.2 SEED + 5.4 aggregate).

Owner: Trương Anh Long (KE, DA10). Xây hotel_semantic_profile: điểm RIÊNG của từng hotel
trên concept (BA THỨ TÁCH BIỆT — Phần 0.5). KHÔNG sửa ontology.

Bước 5.2 (SEED, KHÔNG LLM): từ aggregate Agoda có sẵn:
  - rating_breakdown (7 aspect, điểm /10)        -> ASPECT_* score = điểm/10, nguồn=agoda_grades.
  - reviews_detail.tags (tag, mentioned, pos_pct) -> concept; pos/neg suy từ pos_pct*mentioned,
                                                     score = Wilson lower bound (ít data -> thấp hơn).
Bước 5.3 (ABSA per-review, LLM) sẽ THÊM evidence vào cùng cấu trúc -> aggregate lại (5.4).

Lớp dữ liệu (tách, mục 2.4d): profile = {hotel_id: {concept: {score,pos,neg,evidence_count,source,nature}}}.

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
"""

from __future__ import annotations

import glob
import json
import math
from collections import defaultdict

import yaml

HOTELS_GLOB = "data/cleaned/hotel_*.json"
MAP_YAML = "ontology/review_tag_map.yaml"
OUT_JSON = "knowledge_engineering/enrichment/hotel_profiles.json"

_map = yaml.safe_load(open(MAP_YAML, encoding="utf-8"))
RB_MAP = _map["rating_breakdown"]
TAG_MAP = _map["review_tags"]


def wilson_lower_bound(pos: int, n: int, z: float = 1.96) -> float:
    """Wilson lower bound — ít evidence -> score thấp hơn raw (không overconfident)."""
    if n == 0:
        return 0.0
    phat = pos / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def seed_from_hotel(hotel: dict) -> dict[str, dict]:
    """Seed profile 1 hotel từ aggregate Agoda. concept -> {score,pos,neg,evidence_count,source,nature}."""
    prof: dict[str, dict] = {}
    rd = hotel.get("reviews_detail") or {}

    # (1) rating_breakdown -> ASPECT score = điểm/10 (đã là tổng hợp toàn bộ review)
    n_reviews = rd.get("review_count") or hotel.get("review_count") or 0
    for name, score10 in (hotel.get("rating_breakdown") or {}).items():
        cid = RB_MAP.get(name)
        if cid and isinstance(score10, (int, float)):
            prof[cid] = {
                "score": round(score10 / 10.0, 3),
                "pos": None, "neg": None,
                "evidence_count": n_reviews,
                "source": "agoda_grades",
                "nature": "experience",
            }

    # (2) reviews_detail.tags -> concept; pos/neg từ pos_pct*mentioned; Wilson score
    for t in rd.get("tags", []) or []:
        if not isinstance(t, dict):
            continue
        cid = TAG_MAP.get(t.get("tag"))
        if not cid:
            continue
        mentioned = int(t.get("mentioned") or 0)
        pos_pct = float(t.get("positive_pct") or 0) / 100.0
        pos = round(mentioned * pos_pct)
        neg = mentioned - pos
        score = round(wilson_lower_bound(pos, mentioned), 3)
        # nếu concept đã có từ rating_breakdown (aspect) -> giữ cái grades (mạnh hơn), bổ sung pos/neg
        if cid in prof and prof[cid]["source"] == "agoda_grades":
            prof[cid]["pos"] = pos
            prof[cid]["neg"] = neg
            prof[cid]["evidence_count"] = mentioned
        else:
            nat = "presence" if cid.startswith("AMEN_") or cid.startswith("PURPOSE_") else "experience"
            prof[cid] = {
                "score": score, "pos": pos, "neg": neg,
                "evidence_count": mentioned,
                "source": "agoda_review_tags", "nature": nat,
            }
    return prof


def run() -> dict:
    profiles: dict[str, dict] = {}
    stats = {"n": 0, "with_profile": 0, "concept_hits": defaultdict(int), "no_data": 0}
    for f in sorted(glob.glob(HOTELS_GLOB)):
        hotel = json.load(open(f, encoding="utf-8"))
        key = f"acc_{hotel.get('hotel_id')}"
        prof = seed_from_hotel(hotel)
        profiles[key] = prof
        stats["n"] += 1
        if prof:
            stats["with_profile"] += 1
        else:
            stats["no_data"] += 1
        for c in prof:
            stats["concept_hits"][c] += 1
    json.dump(profiles, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return stats


if __name__ == "__main__":
    s = run()
    print(f"Hotels: {s['n']} | có profile seed: {s['with_profile']} | không data: {s['no_data']}")
    print("Concept phủ (số hotel):")
    for c, n in sorted(s["concept_hits"].items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {c}")
    print(f"-> {OUT_JSON}")
