# -*- coding: utf-8 -*-
"""
_build_combo_index.py — Tao ground truth cho 10 query TO HOP (GS-051..060):
  Nhom 1 (051-055): PURPOSE (demographics) ∩ STYLE (review) + city
  Nhom 2 (056-060): PRICE_TIER ∩ PURPOSE (demographics) + city

Doc 3 index da sinh san: _purpose_index.json, _style_index.json, _price_index.json
(khong quet lai 520 file). Giao 2 tin hieu trong cung city, rank theo RANK-SUM
(hang o tin hieu A + hang o tin hieu B; nho hon = lien quan hon), lay top 5.
Voi query 'Tim resort' -> chi giu accommodation_type=Resort.

Chay:
    python data/golden_dataset/_build_combo_index.py
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PUR = json.load(open(os.path.join(HERE, "_purpose_index.json"), "r", encoding="utf-8"))
STY = json.load(open(os.path.join(HERE, "_style_index.json"), "r", encoding="utf-8"))
PRI = json.load(open(os.path.join(HERE, "_price_index.json"), "r", encoding="utf-8"))
K = 5

# ---- maps phu tro tu price index: hotel_id -> acc_type ----
ACC = {}
for t, info in PRI.items():
    if not isinstance(info, dict) or "global" not in info:
        continue
    for h in info["global"]:
        ACC[h["hotel_id"]] = h.get("acc_type")

def purpose_rank(purpose, city):
    """hotel_id -> (rank, total_count) trong (purpose, city)."""
    rows = PUR[purpose]["by_city"].get(city, [])
    return {r["hotel_id"]: (i, r["total_count"]) for i, r in enumerate(rows)}

def style_rank(style, city):
    """hotel_id -> (rank, mention) cho hotel thuoc city."""
    rows = [r for r in STY[style]["hotels"] if r.get("city") == city]
    return {r["hotel_id"]: (i, r["mention_reviews"]) for i, r in enumerate(rows)}

def price_rank(tier, city):
    """hotel_id -> (rank, price_from) trong (tier, city)."""
    rows = PRI[tier]["by_city"].get(city, [])
    return {r["hotel_id"]: (i, r["price_from"]) for i, r in enumerate(rows)}

def combine(mapA, mapB, resort_only):
    """Giao 2 map, rank theo rank-sum tang dan."""
    inter = set(mapA) & set(mapB)
    if resort_only:
        inter = {h for h in inter if (ACC.get(h) or "").strip().lower() == "resort"}
    rows = []
    for h in inter:
        ra, va = mapA[h]; rb, vb = mapB[h]
        rows.append((ra + rb, h, va, vb, ACC.get(h)))
    rows.sort(key=lambda x: x[0])
    return rows[:K], len(inter)

GROUP1 = [  # (qid, city, purpose, style, resort_only)
    ("GS-051", "Đà Nẵng",      "PURPOSE_FAMILY",   "STYLE_RELAXING",  False),
    ("GS-052", "Nha Trang",    "PURPOSE_ROMANTIC", "STYLE_LUXURY",    False),
    ("GS-053", "Đà Lạt",       "PURPOSE_GROUP",    "STYLE_AESTHETIC", False),
    ("GS-054", "Hội An",       "PURPOSE_SOLO",     "STYLE_QUIET",     False),
    ("GS-055", "Đảo Phú Quốc", "PURPOSE_ROMANTIC", "STYLE_RELAXING",  True),
]
GROUP2 = [  # (qid, city, tier, purpose, resort_only)
    ("GS-056", "Hồ Chí Minh",  "PRICE_BUDGET",   "PURPOSE_SOLO",     False),
    ("GS-057", "Nha Trang",    "PRICE_LUXURY",   "PURPOSE_FAMILY",   False),
    ("GS-058", "Hà Nội",       "PRICE_MID",      "PURPOSE_BUSINESS", False),
    ("GS-059", "Đà Nẵng",      "PRICE_UPSCALE",  "PURPOSE_GROUP",    False),
    ("GS-060", "Đảo Phú Quốc", "PRICE_LUXURY",   "PURPOSE_ROMANTIC", True),
]

print("========== NHOM 1: PURPOSE ∩ STYLE (GS-051..055) ==========")
for qid, city, purpose, style, ro in GROUP1:
    rows, n = combine(purpose_rank(purpose, city), style_rank(style, city), ro)
    print(f"\n{qid} | {city} | {purpose} ∩ {style}{' [RESORT]' if ro else ''} | giao={n}")
    print("   ids: " + str([r[1] for r in rows]))
    for rs, h, va, vb, acc in rows:
        print(f"      {h}  ranksum={rs}  purpose_count={va}  style_mention={vb}  ({acc})")

print("\n\n========== NHOM 2: PRICE ∩ PURPOSE (GS-056..060) ==========")
for qid, city, tier, purpose, ro in GROUP2:
    rows, n = combine(price_rank(tier, city), purpose_rank(purpose, city), ro)
    print(f"\n{qid} | {city} | {tier} ∩ {purpose}{' [RESORT]' if ro else ''} | giao={n}")
    print("   ids: " + str([r[1] for r in rows]))
    for rs, h, va, vb, acc in rows:
        print(f"      {h}  ranksum={rs}  price_from={va}  purpose_count={vb}  ({acc})")
