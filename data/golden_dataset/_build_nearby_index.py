# -*- coding: utf-8 -*-
"""
_build_nearby_index.py  (v2 — cho corpus 520 hotel, top_k=10)

Tong hop nearby_places tren data/cleaned/*.json, CHI giu landmark co trong
ontology/core/location.generated.yaml (kind: landmark, LMK_*), gan city tung hotel,
xac dinh city chu dao, sort hotel theo distance -> phuc vu build golden "Nearby-place".

Chay:
    python data/golden_dataset/_build_nearby_index.py
Output:
    data/golden_dataset/_nearby_index.json
      { LMK_ID: {name, type, dominant_city, n_total, n_in_city,
                 hotels_in_city:[{hotel_id,distance_km,city}],   # sorted distance asc, CUNG city chu dao
                 hotels_all:[...]} }
    + in candidate (landmark co >= MIN_IN_CITY hotel cung city) de chon query.
"""
import json, os, glob, re, unicodedata
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
ONTO_PATH = os.path.join(HERE, "..", "..", "ontology", "core", "location.generated.yaml")
OUT_PATH = os.path.join(HERE, "_nearby_index.json")
MIN_IN_CITY = 5      # chi xuat landmark co >= 5 hotel cung city chu dao (de huong toi top_k=10)

def norm(s):
    s = (s or "").strip().lower()
    return s

# ---------- Load ontology landmarks ----------
def load_landmarks():
    """Tra ve: match_map {surface_or_label_norm -> lmk_id}, info {lmk_id -> {label,type}}"""
    info = {}
    match_map = {}
    cur = None
    block = {}
    in_surface = False
    def flush(cid, b):
        if cid and cid.startswith("LMK_") and b.get("kind") == "landmark":
            label = b.get("label_vi", "")
            info[cid] = {"label": label, "type": b.get("landmark_type", "")}
            if label:
                match_map[norm(label)] = cid
            for sf in b.get("surface_forms", []):
                match_map[norm(sf)] = cid
    with open(ONTO_PATH, "r", encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"^  ([A-Z][A-Z0-9_]+):\s*$", ln)
            if m:
                flush(cur, block)
                cur = m.group(1); block = {}; in_surface = False
                continue
            if not cur:
                continue
            if re.match(r"^    [a-z_]+:", ln):
                in_surface = ln.strip().startswith("surface_forms:")
                ms = re.search(r"kind:\s*(\w+)", ln)
                if ms: block["kind"] = ms.group(1)
                mt = re.search(r"landmark_type:\s*(\w+)", ln)
                if mt: block["landmark_type"] = mt.group(1)
                ml = re.search(r'label:\s*\{vi:\s*"([^"]+)"', ln)
                if ml: block["label_vi"] = ml.group(1)
                continue
            if in_surface:
                # surface_forms: vi: ["a","b", ...]  (inline list)
                items = re.findall(r'"([^"]+)"', ln)
                if items:
                    block.setdefault("surface_forms", []).extend(items)
    flush(cur, block)
    return match_map, info

def main():
    match_map, info = load_landmarks()
    print(f"[i] Ontology: {len(info)} landmark, {len(match_map)} surface/label keys")

    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    print(f"[i] {len(files)} hotel files")

    # lmk_id -> hotel_id -> {distance, city}  (giu distance nho nhat)
    agg = defaultdict(dict)
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        city = d.get("city")
        for np_ in (d.get("nearby_places") or []):
            lid = match_map.get(norm(np_.get("name")))
            if not lid:
                continue
            dist = np_.get("distance_km")
            dist = 99999.0 if dist is None else float(dist)
            rec = agg[lid].get(hid)
            if rec is None or dist < rec["distance_km"]:
                agg[lid][hid] = {"distance_km": (None if dist == 99999 else dist), "city": city}

    out = {}
    for lid, hotels in agg.items():
        rows = [{"hotel_id": h, "distance_km": v["distance_km"], "city": v["city"]}
                for h, v in hotels.items()]
        rows.sort(key=lambda x: (99999 if x["distance_km"] is None else x["distance_km"]))
        city_counts = Counter(r["city"] for r in rows)
        dom_city, n_in_city = city_counts.most_common(1)[0]
        in_city = [r for r in rows if r["city"] == dom_city]
        out[lid] = {"name": info[lid]["label"], "type": info[lid]["type"],
                    "dominant_city": dom_city, "n_total": len(rows), "n_in_city": n_in_city,
                    "hotels_in_city": in_city, "hotels_all": rows}

    out = dict(sorted(out.items(), key=lambda kv: -kv[1]["n_in_city"]))
    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] {len(out)} ontology-landmark co trong data. Ghi -> {os.path.abspath(OUT_PATH)}\n")

    print(f"===== CANDIDATE: landmark co >= {MIN_IN_CITY} hotel CUNG city chu dao =====")
    cands = [(lid, v) for lid, v in out.items() if v["n_in_city"] >= MIN_IN_CITY]
    by_type = defaultdict(list)
    for lid, v in cands:
        by_type[v["type"]].append((lid, v))
    for t in sorted(by_type, key=lambda k: -sum(x[1]["n_in_city"] for x in by_type[k])):
        print(f"\n# type = {t}")
        for lid, v in sorted(by_type[t], key=lambda x: -x[1]["n_in_city"]):
            ids = ", ".join(str(r["hotel_id"]) for r in v["hotels_in_city"][:10])
            print(f"   {v['n_in_city']:>2}/{v['n_total']:>2} ks @ {v['dominant_city']:<28} | {v['name']} [{lid}]")
            print(f"        top10(distance): {ids}")

if __name__ == "__main__":
    main()
