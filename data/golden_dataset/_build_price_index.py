# -*- coding: utf-8 -*-
"""
_build_price_index.py — Suy PRICE_TIER (ontology/core/price_tier.yaml) cho moi hotel
tu gia phong (rooms[].price_per_night) trong data/cleaned/*.json.

Tier chia theo PHAN VI (quartile) gia 'price_from' = min(price_per_night) toan corpus:
   PRICE_BUDGET : price_from <= Q1
   PRICE_MID    : Q1 <  price_from <= Q2 (median)
   PRICE_UPSCALE: Q2 <  price_from <= Q3
   PRICE_LUXURY : price_from >  Q3
(In kem star_rating/is_luxury de cross-check.)

Ranking relevance trong tier (theo cuong do tier):
   BUDGET, MID     -> gia TANG dan (re nhat = "binh dan" nhat)
   UPSCALE, LUXURY -> gia GIAM dan (dat nhat = "sang" nhat)

Chay:
    python data/golden_dataset/_build_price_index.py
Output:
    data/golden_dataset/_price_index.json  (global + by_city moi tier)
    + in tom tat ra console.
"""
import json, os, glob, statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
OUT_PATH = os.path.join(HERE, "_price_index.json")

TIER_ORDER = ["PRICE_BUDGET", "PRICE_MID", "PRICE_UPSCALE", "PRICE_LUXURY"]
TIER_LABEL = {"PRICE_BUDGET": "Bình dân", "PRICE_MID": "Tầm trung",
              "PRICE_UPSCALE": "Cao cấp", "PRICE_LUXURY": "Sang trọng"}
TIER_DESC_ASC = {"PRICE_BUDGET": True, "PRICE_MID": True,
                 "PRICE_UPSCALE": False, "PRICE_LUXURY": False}  # True=gia tang dan

def price_from(d):
    vals = []
    for r in (d.get("rooms") or []):
        p = r.get("price_per_night") or r.get("original_price")
        try:
            p = float(p)
        except (TypeError, ValueError):
            continue
        if p and p > 0:
            vals.append(p)
    return min(vals) if vals else None

def main():
    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    hotels = []
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        pf = price_from(d)
        hotels.append({"hotel_id": hid, "price_from": pf, "city": d.get("city"),
                       "star_rating": d.get("star_rating"), "is_luxury": d.get("is_luxury"),
                       "review_score": d.get("review_score") or 0, "name": d.get("name"),
                       "acc_type": d.get("accommodation_type")})

    priced = [h for h in hotels if h["price_from"]]
    no_price = [h for h in hotels if not h["price_from"]]
    prices = sorted(h["price_from"] for h in priced)
    qs = statistics.quantiles(prices, n=4)  # [Q1, Q2, Q3]
    Q1, Q2, Q3 = qs[0], qs[1], qs[2]
    print(f"[i] {len(priced)} hotel co gia, {len(no_price)} khong co gia (bo qua).")
    print(f"[i] Quartile price_from (VND): Q1={Q1:,.0f}  Q2(median)={Q2:,.0f}  Q3={Q3:,.0f}")
    print(f"[i] min={prices[0]:,.0f}  max={prices[-1]:,.0f}")

    def tier_of(pf):
        if pf <= Q1: return "PRICE_BUDGET"
        if pf <= Q2: return "PRICE_MID"
        if pf <= Q3: return "PRICE_UPSCALE"
        return "PRICE_LUXURY"

    by_tier = defaultdict(list)
    for h in priced:
        by_tier[tier_of(h["price_from"])].append(h)

    out = {}
    for t in TIER_ORDER:
        rows = by_tier[t]
        asc = TIER_DESC_ASC[t]
        # tiebreak review_score giam dan (quan trong cho LUXURY vi nhieu hotel dung tran gia)
        rows_sorted = sorted(rows, key=lambda x: (x["price_from"] if asc else -x["price_from"],
                                                  -x["review_score"]))
        by_city = defaultdict(list)
        for h in rows_sorted:
            by_city[h["city"]].append(h)
        by_city = dict(sorted(by_city.items(), key=lambda kv: -len(kv[1])))
        out[t] = {"label": TIER_LABEL[t], "rank_direction": "price_asc" if asc else "price_desc",
                  "count": len(rows_sorted), "global": rows_sorted, "by_city": by_city}

    meta = {"_thresholds_vnd": {"Q1": Q1, "Q2": Q2, "Q3": Q3,
                                "min": prices[0], "max": prices[-1]},
            "_no_price_hotel_ids": [h["hotel_id"] for h in no_price]}
    json.dump({**meta, **out}, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[OK] Ghi -> {os.path.abspath(OUT_PATH)}\n")

    def fmt(h):
        return f"{h['hotel_id']}({h['price_from']/1e6:.2f}tr,{h['star_rating']}*,s{h['review_score']},{h['acc_type']})"
    def resort_line(rows, pad):
        rs = [h for h in rows if (h.get('acc_type') or '').strip().lower() == 'resort']
        if rs:
            print(f"{pad}-> resort-only ({len(rs)}): " + ", ".join(f"{h['hotel_id']}(s={h['review_score']})" for h in rs[:10]))

    print("===== PRICE TIER -> top 10 (global) + city + resort-only =====")
    for t in TIER_ORDER:
        info = out[t]
        print(f"\n# {t} ({info['label']}) [{info['count']} ks, rank={info['rank_direction']}]")
        print("   global top10: " + ", ".join(fmt(h) for h in info["global"][:10]))
        resort_line(info["global"], "      ")
        for city, rows in list(info["by_city"].items())[:6]:
            print(f"      [{len(rows):>2} ks] {city}: " + ", ".join(fmt(h) for h in rows[:10]))
            resort_line(rows, "           ")

if __name__ == "__main__":
    main()
