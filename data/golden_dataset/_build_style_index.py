# -*- coding: utf-8 -*-
"""
_build_style_index.py — Quet sample_comments (review) cua data/cleaned/*.json,
match surface_forms cua tung STYLE_* trong ontology/core/style.yaml,
dem so review mention va trich snippet -> phuc vu build golden query "style".

Chay:
    python data/golden_dataset/_build_style_index.py
Output:
    data/golden_dataset/_style_index.json
    + in tom tat ra console (moi style: hotel xep theo so review mention giam dan).

Ghi chu:
  - Chi match tren cac truong mang tinh tich cuc/mo ta: title, text, positives.
    (BO QUA 'negatives' de tranh dem diem style trong phan che.)
  - Co co 'maybe_negated' khi truoc cum tu match co tu phu dinh (khong/ko/chua/chang)
    -> Claude se loc tay khi viet ground truth.
  - match_count = so REVIEW (khong phai so lan) co mention style do.
"""
import json, os, glob, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(HERE, "..", "cleaned")
OUT_PATH = os.path.join(HERE, "_style_index.json")
MAX_SNIPPETS = 4          # so snippet luu moi hotel/style
SNIPPET_PAD = 45          # so ky tu lay quanh cho match

# ---- surface_forms (vi + en) lay tu ontology/core/style.yaml ----
STYLES = {
    "STYLE_QUIET": ("Yên tĩnh", ["yên tĩnh","tĩnh lặng","không ồn ào","im ắng","thanh bình","yên bình",
                                  "ít ồn","riêng tư yên tĩnh","yên tĩnh","không gian yên tĩnh","cách âm tốt",
                                  "quiet","peaceful","calm"]),
    "STYLE_LIVELY": ("Sôi động", ["sôi động","náo nhiệt","nhộn nhịp","vui nhộn","đông vui","nhiều hoạt động",
                                   "có chỗ vui chơi","gần chỗ ăn chơi","lively","vibrant","bustling"]),
    "STYLE_RELAXING": ("Thư giãn", ["thư giãn","thoải mái","dễ chịu","thư thái","relaxing","soothing","restful"]),
    "STYLE_MODERN": ("Hiện đại", ["hiện đại","tiện nghi hiện đại","thiết kế hiện đại","tân tiến","trẻ trung",
                                   "modern","contemporary"]),
    "STYLE_ROMANTIC": ("Lãng mạn", ["lãng mạn","lãng mạn riêng tư","không gian lãng mạn","tình tứ","hẹn hò",
                                     "tuần trăng mật","romantic","intimate"]),
    "STYLE_LUXURY": ("Đẳng cấp", ["đẳng cấp","sang trọng","xa hoa","fancy","xịn sò","hoành tráng","sang xịn",
                                   "đẳng cấp sang trọng","cao sang","lộng lẫy","luxurious","opulent","exclusive"]),
    "STYLE_ECO": ("Thân thiện môi trường", ["thân thiện môi trường","sinh thái","eco-friendly","sustainable","green"]),
    "STYLE_EUROPEAN_JAPANESE": ("Phong cách châu Âu và Nhật", ["phong cách châu âu","thiết kế châu âu","kiến trúc châu âu",
                                   "nội thất châu âu","phong cách nhật","phong cách nhật bản","thiết kế kiểu nhật",
                                   "kiến trúc nhật bản","european style","japanese style","european design",
                                   "japanese design"]),
    "STYLE_NEW": ("Mới", ["khách sạn mới xây","khách sạn mới mở","khách sạn mới khai trương","mới xây dựng",
                          "mới khai trương","cơ sở vật chất mới tinh","phòng mới tinh","mới tinh","còn mới",
                          "new hotel","brand-new","newly opened","newly built"]),
    "STYLE_VINTAGE": ("Phong cách cổ điển", ["vintage","phong cách vintage","phong cách cổ điển","thiết kế cổ điển",
                                  "kiến trúc cổ điển","nội thất cổ điển","phong cách retro","classic style","retro"]),
    "STYLE_AESTHETIC": ("Thẩm mỹ", ["phong cách thẩm mỹ","thiết kế thẩm mỹ","decor thẩm mỹ","trang trí thẩm mỹ",
                                     "thiết kế đẹp mắt","đẹp mắt","aesthetic"]),
    "STYLE_BOUTIQUE": ("Khách sạn boutique", ["khách sạn boutique","boutique hotel","phong cách boutique",
                                   "thiết kế boutique","boutique resort","boutique"]),
    "STYLE_MINIMALIST": ("Phong cách tối giản", ["tối giản","phong cách tối giản","thiết kế tối giản",
                                   "minimalist","minimalist style","minimalist design"]),
}
NEGATORS = ["không", "ko ", "ko.", "chưa", "chẳng", "chả ", "thiếu"]

def find_matches(textfields):
    """textfields: list[(field_name, text)]. Tra ve list match dict."""
    hits = []
    for fname, txt in textfields:
        if not txt: continue
        low = txt.lower()
        for sid, (label, forms) in STYLES.items():
            for form in forms:
                idx = low.find(form)
                if idx == -1: continue
                pre = low[max(0, idx-15):idx]
                negated = any(n in pre for n in NEGATORS)
                s = max(0, idx-SNIPPET_PAD); e = min(len(txt), idx+len(form)+SNIPPET_PAD)
                snip = txt[s:e].replace("\n", " ").strip()
                hits.append({"style": sid, "field": fname, "form": form,
                             "maybe_negated": negated, "snippet": snip})
                break  # 1 style match/field la du
    return hits

def main():
    files = sorted(glob.glob(os.path.join(CLEANED_DIR, "hotel_*.json")))
    # style -> hotel_id -> {count, city, name, matches[]}
    idx = defaultdict(lambda: defaultdict(lambda: {"count": 0, "matches": []}))
    hotel_meta = {}
    for fp in files:
        try:
            d = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print("[!]", fp, e); continue
        hid = d.get("hotel_id")
        if hid is None: continue
        hotel_meta[hid] = {"city": d.get("city"), "name": d.get("name"),
                           "review_score": d.get("review_score")}
        reviews = (((d.get("reviews_detail") or {}) if isinstance(d.get("reviews_detail"), dict) else {})
                   .get("sample_comments")) or d.get("sample_comments") or []
        # sample_comments co the nam trong reviews_detail hoac top-level
        if not reviews:
            rd = d.get("reviews_detail")
            if isinstance(rd, dict):
                reviews = rd.get("sample_comments") or []
        seen_style_this_hotel = defaultdict(int)
        for rv in reviews:
            if not isinstance(rv, dict): continue
            fields = [("title", rv.get("title")), ("text", rv.get("text")),
                      ("positives", rv.get("positives"))]
            hits = find_matches(fields)
            styles_in_review = set()
            for h in hits:
                if h["maybe_negated"]:
                    # van luu nhung danh dau, KHONG tinh vao count chinh
                    pass
                styles_in_review.add(h["style"])
            for sid in styles_in_review:
                rec = idx[sid][hid]
                # count = so review co mention (uu tien review khong negated)
                pos_hits = [h for h in hits if h["style"] == sid and not h["maybe_negated"]]
                if pos_hits:
                    rec["count"] += 1
                if len(rec["matches"]) < MAX_SNIPPETS:
                    for h in (pos_hits or [h for h in hits if h["style"] == sid]):
                        if len(rec["matches"]) >= MAX_SNIPPETS: break
                        rec["matches"].append({"rating": rv.get("rating"), "field": h["field"],
                                               "form": h["form"], "maybe_negated": h["maybe_negated"],
                                               "snippet": h["snippet"]})

    # build output sorted
    out = {}
    for sid, (label, _) in STYLES.items():
        hotels = []
        for hid, rec in idx.get(sid, {}).items():
            if rec["count"] <= 0:  # bo hotel chi co match negated
                continue
            m = hotel_meta.get(hid, {})
            hotels.append({"hotel_id": hid, "city": m.get("city"), "name": m.get("name"),
                           "review_score": m.get("review_score"),
                           "mention_reviews": rec["count"], "matches": rec["matches"]})
        hotels.sort(key=lambda x: (-x["mention_reviews"], -(x["review_score"] or 0)))
        out[sid] = {"label": label, "hotel_count": len(hotels), "hotels": hotels}

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Ghi -> {os.path.abspath(OUT_PATH)}\n")
    print("===== STYLE -> so hotel co review mention (positive) =====")
    for sid, info in sorted(out.items(), key=lambda kv: -kv[1]["hotel_count"]):
        print(f"\n# {sid} ({info['label']}) : {info['hotel_count']} hotel")
        for h in info["hotels"][:10]:
            print(f"   {h['mention_reviews']} review | id={h['hotel_id']:>8} | {h['city']} | score={h['review_score']}")

if __name__ == "__main__":
    main()
