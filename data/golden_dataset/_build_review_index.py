# -*- coding: utf-8 -*-
"""
_build_review_index.py — Build ground truth cho 10 golden query MOI (GS-061..GS-070)
dua HOAN TOAN tren REVIEW (reviews_detail.grades), KHONG dung amenities,
KHONG dung bat ky STYLE_* nao trong ontology/core/style.yaml.

reviews_detail.grades la list[{name, score}] — diem con (sub-score) tu review cho
tung khia canh: "Do sach se", "Co so vat chat", "Vi tri",
"Su thoai mai va chat luong phong", "Dich vu", "Dang tien".

Voi moi query (city + grade aspect, co the rang buoc resort):
  - Loc hotel cung city (va accommodation_type=Resort neu resort_only=True)
    co grade aspect do.
  - Rank: grade_score DESC -> tiebreak review_score DESC -> review_count DESC.
  - Lay top 10 (neu khong du 10 thi lay het).

Chay:
    python data/golden_dataset/_build_review_index.py
Output:
    data/golden_dataset/_review_index.json
    + in tom tat ra console (moi query: top 10 hotel + diem grade).
"""
import json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
OUT_PATH = os.path.join(HERE, "_review_index.json")

# ---- 10 query spec: (query_id, city_exact, grade_name, resort_only) ----
SPECS = [
    ("GS-061", "Đà Nẵng",       "Dịch vụ",                            False),
    ("GS-062", "Hà Nội",        "Độ sạch sẽ",                         False),
    ("GS-063", "Hồ Chí Minh",   "Đáng tiền",                          False),
    ("GS-064", "Đà Lạt",        "Vị trí",                             False),
    ("GS-065", "Hạ Long",       "Cơ sở vật chất",                     False),
    ("GS-066", "Vũng Tàu",      "Sự thoải mái và chất lượng phòng",   False),
    ("GS-067", "Hội An",        "Dịch vụ",                            False),
    ("GS-068", "Nha Trang",     "Độ sạch sẽ",                         False),
    ("GS-069", "Đảo Phú Quốc",  "Đáng tiền",                          True),   # RESORT only
    ("GS-070", "Nha Trang",     "Dịch vụ",                            True),   # RESORT only
]
TOP_K = 10


def grades_dict(rd):
    """reviews_detail.grades (list[{name,score}]) -> {name: score}."""
    out = {}
    if not isinstance(rd, dict):
        return out
    for g in (rd.get("grades") or []):
        if isinstance(g, dict) and g.get("name") is not None and g.get("score") is not None:
            out[g["name"]] = g["score"]
    return out


def main():
    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    print(f"[i] {len(files)} hotel files")

    hotels = []
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None:
            continue
        rd = d.get("reviews_detail")
        hotels.append({
            "hotel_id": hid,
            "name": d.get("name"),
            "city": d.get("city"),
            "accommodation_type": d.get("accommodation_type"),
            "review_score": d.get("review_score"),
            "review_count": d.get("review_count"),
            "grades": grades_dict(rd),
        })

    out = {}
    for qid, city, grade, resort_only in SPECS:
        pool = [h for h in hotels if h["city"] == city and grade in h["grades"]]
        if resort_only:
            pool = [h for h in pool if (h["accommodation_type"] or "").strip().lower() == "resort"]
        pool.sort(key=lambda h: (
            -(h["grades"].get(grade) or 0),
            -(h["review_score"] or 0),
            -(h["review_count"] or 0),
        ))
        top = pool[:TOP_K]
        out[qid] = {
            "city": city, "grade": grade, "resort_only": resort_only,
            "n_pool": len(pool),
            "ranked": [{
                "hotel_id": h["hotel_id"],
                "name": h["name"],
                "accommodation_type": h["accommodation_type"],
                "grade_score": h["grades"].get(grade),
                "review_count": h["review_count"],
                "review_score": h["review_score"],
            } for h in top],
        }

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Ghi -> {os.path.abspath(OUT_PATH)}\n")

    print("===== GROUND TRUTH (review-grade) =====")
    for qid, info in out.items():
        rs = "RESORT-only" if info["resort_only"] else ""
        print(f"\n# {qid} | city={info['city']} | grade='{info['grade']}' {rs} | pool={info['n_pool']}")
        ids = [r["hotel_id"] for r in info["ranked"]]
        print("  relevant_hotel_ids =", ids)
        for r in info["ranked"]:
            print(f"   g={r['grade_score']} | rc={r['review_count']:>6} | s={r['review_score']} "
                  f"| {r['accommodation_type']:<12} | id={r['hotel_id']} | {r['name']}")


if __name__ == "__main__":
    main()
