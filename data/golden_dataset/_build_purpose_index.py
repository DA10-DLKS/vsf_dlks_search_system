# -*- coding: utf-8 -*-
"""
_build_purpose_index.py — Tong hop reviews_detail.demographics cua data/cleaned/*.json,
map traveller-type -> PURPOSE_* (ontology/core/purpose.yaml), nhom theo (purpose, city),
rank hotel theo tong demographic count -> phuc vu build golden query "purpose".

Chay:
    python data/golden_dataset/_build_purpose_index.py
Output:
    data/golden_dataset/_purpose_index.json
    + in: (a) cac ten demographic phan biet (de verify mapping)
          (b) moi purpose: top city + top hotel.

Ranking relevance = tong COUNT cua nhom khach do tai hotel (volume),
tie-break = avg_score (diem nhom khach do cham).
"""
import json, os, glob
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
OUT_PATH = os.path.join(HERE, "_purpose_index.json")

PURPOSE_LABEL = {
    "PURPOSE_FAMILY": "Gia đình", "PURPOSE_ROMANTIC": "Cặp đôi", "PURPOSE_SOLO": "Đi một mình",
    "PURPOSE_GROUP": "Nhóm", "PURPOSE_BUSINESS": "Công tác",
}

def map_purpose(name: str):
    n = (name or "").lower()
    if "gia đình" in n or "gia dinh" in n or "trẻ" in n or "con" in n:
        return "PURPOSE_FAMILY"
    if "công tác" in n or "cong tac" in n or "công vụ" in n or "doanh nhân" in n or "business" in n:
        return "PURPOSE_BUSINESS"
    if "một mình" in n or "mot minh" in n or "solo" in n:
        return "PURPOSE_SOLO"
    if "nhóm" in n or "nhom" in n or "group" in n or "đoàn" in n:
        return "PURPOSE_GROUP"
    if "cặp đôi" in n or "cap doi" in n or "đôi" in n or "couple" in n:
        return "PURPOSE_ROMANTIC"
    return None

def main():
    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    distinct_names = Counter()
    # purpose -> city -> hotel_id -> {count, wscore}
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "wscore": 0.0})))
    hotel_name = {}
    n_with_demo = 0
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        city = d.get("city")
        hotel_name[hid] = d.get("name")
        rd = d.get("reviews_detail") or {}
        demos = rd.get("demographics") if isinstance(rd, dict) else None
        demos = demos or d.get("demographics") or []
        if demos: n_with_demo += 1
        for dm in demos:
            if not isinstance(dm, dict): continue
            name = dm.get("name")
            distinct_names[name] += 1
            p = map_purpose(name)
            if not p: continue
            cnt = dm.get("count") or 0
            sc = dm.get("score") or 0
            rec = agg[p][city][hid]
            rec["count"] += cnt
            rec["wscore"] += cnt * (sc or 0)

    # build output
    out = {}
    for p, label in PURPOSE_LABEL.items():
        by_city = {}
        for city, hotels in agg.get(p, {}).items():
            rows = []
            for hid, rec in hotels.items():
                if rec["count"] <= 0: continue
                avg = round(rec["wscore"] / rec["count"], 2) if rec["count"] else 0
                rows.append({"hotel_id": hid, "name": hotel_name.get(hid),
                             "total_count": rec["count"], "avg_score": avg})
            rows.sort(key=lambda x: (-x["total_count"], -x["avg_score"]))
            if rows:
                by_city[city] = rows
        # sap xep city theo so hotel giam dan
        by_city = dict(sorted(by_city.items(), key=lambda kv: -len(kv[1])))
        out[p] = {"label": label, "by_city": by_city}

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] {n_with_demo} hotel co demographics. Ghi -> {os.path.abspath(OUT_PATH)}\n")

    print("===== TEN DEMOGRAPHIC PHAN BIET (verify mapping) =====")
    for nm, c in distinct_names.most_common():
        print(f"   {c:>4} hotel | {nm!r} -> {map_purpose(nm)}")

    print("\n===== PURPOSE -> CITY (so hotel) -> top hotel =====")
    for p, info in out.items():
        print(f"\n# {p} ({info['label']})")
        for city, rows in list(info["by_city"].items())[:8]:
            ids = ", ".join(f"{r['hotel_id']}(c={r['total_count']},s={r['avg_score']})" for r in rows[:10])
            print(f"   [{len(rows):>2} ks] {city}: {ids}")

if __name__ == "__main__":
    main()
