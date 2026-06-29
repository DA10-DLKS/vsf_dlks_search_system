# -*- coding: utf-8 -*-
"""
_build_amenity_index.py — Match field 'amenities' (list chuoi) cua data/cleaned/*.json
voi surface_forms tung AMEN_* trong ontology/core/amenity.yaml, nhom theo (amenity, city),
rank hotel -> phuc vu build golden query "amenity".

Chay:
    python data/golden_dataset/_build_amenity_index.py
Output:
    data/golden_dataset/_amenity_index.json
    + in: moi amenity -> city (so hotel co tien nghi) -> top hotel.

Ranking relevance trong 1 city (THUAN review_score):
   primary  = review_score, tie-break = review_count, roi match_count
Hotel phai CO tien nghi do (match_count > 0) moi vao danh sach; sau do xep theo
chat luong danh gia (review_score) giam dan.
"""
import json, os, glob, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
ONTO_PATH = os.path.join(HERE, "..", "..", "ontology", "core", "amenity.yaml")
OUT_PATH = os.path.join(HERE, "_amenity_index.json")
MIN_HOTELS_CITY = 5   # chi giu (amenity,city) co >= 5 hotel de du top_k=5 (van xuat het de tham khao)

def load_amenity_ontology():
    """Parse amenity.yaml -> {AMEN_ID: {'label': vi, 'forms': [surface...]}}"""
    res = {}
    cur = None
    in_surface = False
    in_label = False
    with open(ONTO_PATH, "r", encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"^  (AMEN_[A-Z0-9_]+):\s*$", ln)
            if m:
                cur = m.group(1); res[cur] = {"label": "", "forms": []}
                in_surface = in_label = False
                continue
            if not cur:
                continue
            # field key tai 4 space -> reset cac state block
            if re.match(r"^    [a-z_]+:", ln):
                in_surface = ln.strip().startswith("surface_forms:")
                in_label = ln.strip().startswith("label:")
                continue
            if in_label:
                ml = re.match(r"^      vi:\s*(.+)$", ln)
                if ml: res[cur]["label"] = ml.group(1).strip()
                continue
            if in_surface:
                mi = re.match(r"^\s*-\s*(.+)$", ln)
                if mi:
                    form = mi.group(1).strip().lower()
                    if form:
                        res[cur]["forms"].append(form)
    # bo concept khong co form
    return {k: v for k, v in res.items() if v["forms"]}

def main():
    onto = load_amenity_ontology()
    print(f"[i] Parse duoc {len(onto)} AMEN concept tu amenity.yaml")

    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    # amenity -> city -> hotel_id -> {match_count}
    agg = defaultdict(lambda: defaultdict(dict))
    meta = {}
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        city = d.get("city")
        meta[hid] = {"name": d.get("name"), "review_score": d.get("review_score") or 0,
                     "review_count": d.get("review_count") or 0, "city": city,
                     "acc_type": d.get("accommodation_type")}
        ams = [str(a).lower() for a in (d.get("amenities") or []) if a]
        for aid, info in onto.items():
            cnt = 0
            for a in ams:
                if any(form in a for form in info["forms"]):
                    cnt += 1
            if cnt > 0:
                agg[aid][city][hid] = cnt

    out = {}
    for aid, info in onto.items():
        by_city = {}
        for city, hotels in agg.get(aid, {}).items():
            rows = []
            for hid, cnt in hotels.items():
                m = meta[hid]
                rows.append({"hotel_id": hid, "name": m["name"], "match_count": cnt,
                             "review_score": m["review_score"], "review_count": m["review_count"],
                             "acc_type": m["acc_type"]})
            rows.sort(key=lambda x: (-x["review_score"], -x["review_count"], -x["match_count"]))
            by_city[city] = rows
        by_city = dict(sorted(by_city.items(), key=lambda kv: -len(kv[1])))
        out[aid] = {"label": info["label"], "by_city": by_city}

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Ghi -> {os.path.abspath(OUT_PATH)}\n")

    print("===== AMENITY -> CITY (so hotel co tien nghi, >=5) -> top 10 + resort-only =====")
    for aid, info in out.items():
        rich = [(c, r) for c, r in info["by_city"].items() if len(r) >= MIN_HOTELS_CITY]
        if not rich:
            continue
        print(f"\n# {aid} ({info['label']})")
        for city, rows in rich[:8]:
            ids = ", ".join(f"{r['hotel_id']}(s={r['review_score']},{r['acc_type']})" for r in rows[:10])
            print(f"   [{len(rows):>2} ks] {city}: {ids}")
            resorts = [r for r in rows if (r['acc_type'] or '').strip().lower() == 'resort']
            if resorts:
                rids = ", ".join(f"{r['hotel_id']}(s={r['review_score']})" for r in resorts[:10])
                print(f"        -> resort-only ({len(resorts)}): {rids}")

if __name__ == "__main__":
    main()
