# -*- coding: utf-8 -*-
"""
_build_nearby_pairs.py — Tim cap (landmark_chinh, dieu_kien_phu) de moi query nearby
dat du ~5 hotel, co ranking theo so dieu kien thoa man.

Y tuong:
  - Dieu kien CHINH luon la landmark co trong ontology (LMK_*).
  - Dieu kien PHU la 1 nearby place CO THAT khac, CUNG CITY, sao cho union hotel lon nhat
    (uu tien <=5) va giao >= 1 (de co hotel "thoa 2 dieu kien" rank cao hon).
  - Ranking union:
        tier 2 (gan ca 2 landmark)  -> sort theo (d1 + d2) tang dan  -> xep trcn
        tier 1 (chi gan 1 landmark) -> sort theo distance cua landmark do tang dan
    Lay top 5.

Chay:
    python data/golden_dataset/_build_nearby_pairs.py
Output:
    data/golden_dataset/_nearby_pairs.json   (de Claude doc va viet golden set)
    + in goi y ra console.
"""
import json, os, glob, re
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
ONTO_PATH = os.path.join(HERE, "..", "..", "ontology", "core", "location.generated.yaml")
OUT_PATH = os.path.join(HERE, "_nearby_pairs.json")
TARGET = 5  # so hotel mong muon moi query

# ---------- 1. Load ontology landmarks (kind: landmark) ----------
def load_ontology_landmarks():
    """Tra ve dict: label_vi -> {lmk_id, type}. Parse don gian theo dong."""
    res = {}
    cur_id = None
    cur_type = None
    with open(ONTO_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    block_id = None
    block = {}
    def flush(bid, b):
        if bid and bid.startswith("LMK_") and b.get("kind") == "landmark" and b.get("label_vi"):
            res[b["label_vi"]] = {"lmk_id": bid, "type": b.get("landmark_type", "")}
    for ln in lines:
        m = re.match(r"^  ([A-Z][A-Z0-9_]+):\s*$", ln)
        if m:
            flush(block_id, block)
            block_id = m.group(1)
            block = {}
            continue
        if block_id:
            ms = re.search(r"kind:\s*(\w+)", ln)
            if ms: block["kind"] = ms.group(1)
            mt = re.search(r"landmark_type:\s*(\w+)", ln)
            if mt: block["landmark_type"] = mt.group(1)
            ml = re.search(r'label:\s*\{vi:\s*"([^"]+)"', ln)
            if ml: block["label_vi"] = ml.group(1)
    flush(block_id, block)
    return res

# ---------- 2. Load hotels + nearby ----------
def load_hotels():
    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    hotel_city = {}
    # place -> {hotel_id: distance}
    place_hotels = defaultdict(dict)
    place_type = defaultdict(Counter)
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        hotel_city[hid] = d.get("city")
        for np_ in (d.get("nearby_places") or []):
            name = (np_.get("name") or "").strip()
            if not name: continue
            dist = np_.get("distance_km")
            dist = 9999.0 if dist is None else float(dist)
            if hid not in place_hotels[name] or dist < place_hotels[name][hid]:
                place_hotels[name][hid] = dist
            place_type[name][(np_.get("type") or "").strip()] += 1
    return hotel_city, place_hotels, place_type

def place_city(hotels, hotel_city):
    c = Counter(hotel_city.get(h) for h in hotels)
    return c.most_common(1)[0][0] if c else None

def main():
    onto = load_ontology_landmarks()
    hotel_city, place_hotels, place_type = load_hotels()
    print(f"[i] Ontology landmarks: {len(onto)} | places trong data: {len(place_hotels)}")

    # city -> list of place names (place co >=2 hotel)
    places = {n: h for n, h in place_hotels.items() if len(h) >= 2}
    pcity = {n: place_city(h, hotel_city) for n, h in places.items()}

    results = []
    # Primary = place vua co trong ontology vua co trong data
    primaries = [n for n in places if n in onto]
    for p1 in primaries:
        city = pcity[p1]
        h1 = places[p1]                      # {hid: dist}
        # tim secondary tot nhat cung city
        best = None
        for p2, h2 in places.items():
            if p2 == p1 or pcity[p2] != city: continue
            inter = set(h1) & set(h2)
            if not inter: continue           # phai co hotel thoa ca 2
            union = set(h1) | set(h2)
            is_lmk2 = p2 in onto
            # uu tien: union lon (cap TARGET), giao lon, secondary la LMK
            score = (min(len(union), TARGET), len(inter), 1 if is_lmk2 else 0, len(union))
            if best is None or score > best[0]:
                best = (score, p2, h2, inter, union, is_lmk2)
        if not best:
            # khong ghep duoc -> de primary mot minh
            ranked = sorted(({"hotel_id": h, "tiers": 1, "primary_km": d, "secondary_km": None}
                             for h, d in h1.items()), key=lambda x: x["primary_km"])[:TARGET]
            results.append({
                "primary": {"name": p1, "lmk_id": onto[p1]["lmk_id"], "type": onto[p1]["type"], "city": city},
                "secondary": None,
                "union_size": len(h1), "intersection_size": 0,
                "ranked_top5_hotel_ids": [r["hotel_id"] for r in ranked],
                "ranked_detail": ranked,
            })
            continue
        _, p2, h2, inter, union, is_lmk2 = best
        # build ranked
        rows = []
        for h in union:
            d1 = h1.get(h); d2 = h2.get(h)
            tiers = (1 if d1 is not None else 0) + (1 if d2 is not None else 0)
            keyd = (d1 if d1 is not None else 9999) + (d2 if d2 is not None else 9999) if tiers == 2 \
                   else (d1 if d1 is not None else d2)
            rows.append({"hotel_id": h, "tiers": tiers,
                         "primary_km": d1, "secondary_km": d2, "_sort": (-tiers, keyd)})
        rows.sort(key=lambda x: x["_sort"])
        for r in rows: r.pop("_sort")
        top = rows[:TARGET]
        results.append({
            "primary": {"name": p1, "lmk_id": onto[p1]["lmk_id"], "type": onto[p1]["type"], "city": city},
            "secondary": {"name": p2, "is_ontology_lmk": is_lmk2,
                          "lmk_id": onto[p2]["lmk_id"] if is_lmk2 else None,
                          "type": (onto[p2]["type"] if is_lmk2 else place_type[p2].most_common(1)[0][0])},
            "union_size": len(union), "intersection_size": len(inter),
            "ranked_top5_hotel_ids": [r["hotel_id"] for r in top],
            "ranked_detail": top,
        })

    # sap xep: uu tien union dat 5 truoc
    results.sort(key=lambda r: (-(min(r["union_size"], TARGET)), -r["intersection_size"]))
    json.dump(results, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Ghi {len(results)} primary-landmark combos -> {os.path.abspath(OUT_PATH)}\n")

    print("===== GOI Y CAP DIEU KIEN (primary LMK + secondary) =====")
    for r in results:
        p = r["primary"]; s = r["secondary"]
        sec = "(khong ghep duoc)" if not s else f"+ '{s['name']}'" + (" [LMK]" if s["is_ontology_lmk"] else " [non-LMK]")
        print(f"\n# {p['name']} [{p['type']}] @ {p['city']}  {sec}")
        print(f"   union={r['union_size']} inter={r['intersection_size']}  top5={r['ranked_top5_hotel_ids']}")
        for d in r["ranked_detail"]:
            print(f"     hid={d['hotel_id']:>8}  thoa {d['tiers']} dk  p={d['primary_km']}  s={d['secondary_km']}")

if __name__ == "__main__":
    main()
