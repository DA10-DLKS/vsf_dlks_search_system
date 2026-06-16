"""build_golden_v2.py — Dựng lại golden dataset theo chuẩn IR khách quan (v2).

ĐỘNG CƠ (đánh giá MLOps golden v1):
  v1 định nghĩa relevant = TOP-N hotel SORT theo MỘT metric đơn (đếm review 'yên tĩnh',
  distance_km, grade_score...). Đây là CIRCULAR: đo hệ thống bằng chính heuristic hệ thống
  có thể dùng -> metric đẹp giả, không đo "đúng/sai" thực.

CÁCH v2 (multi-signal binary relevance):
  relevant(hotel) = NHỊ PHÂN, = 1 nếu hotel thỏa ĐIỀU KIỆN CỨNG của câu (đúng city + đúng
  concept) VÀ được xác nhận bởi ÍT NHẤT tín hiệu ĐỘC LẬP. Không sort-để-định-nghĩa-relevant.
  Thứ tự (ordering) tách riêng — chỉ dùng cho graded/tie-break, KHÔNG quyết định nhãn.

  3 nguồn tín hiệu ĐỘC LẬP nhau (giảm circular):
    A. Structured (Agoda): amenity thật, star_rating, price — KHÔNG từ review.
    B. Review aspect: semantic_profile (score>=0.6) / grades.
    C. Demographics: nhóm khách thực tế đã ở (count) — độc lập review text.

  Một câu PURPOSE_FAMILY: relevant = đúng city + (có amenity gia đình A) HOẶC (demographics
  'Gia đình' đủ lớn C). Không cần "rank theo count" -> hết circular.

Output: golden_set_v2.json — giữ query/intent, thêm relevant_hotel_ids (nhị phân, set),
labeling_method='multi_signal_binary', signals dùng. KHÔNG ghi đè v1.

Chạy: .venv/Scripts/python.exe -X utf8 -m evaluation.test_queries.build_golden_v2
"""

from __future__ import annotations

import json
from collections import Counter

KO = "knowledge_engineering/enrichment/knowledge_objects.json"
CLEANED = "data/cleaned/hotel_{}.json"
GOLDEN_V1 = "data/golden_dataset/golden_set_v1.json"
OUT = "data/golden_dataset/golden_set_v2.json"

_objs = json.load(open(KO, encoding="utf-8"))


def _hid(key: str) -> int:
    return int(key.replace("acc_", ""))


def _by_hotel() -> dict[int, dict]:
    return {_hid(k): v for k, v in _objs.items()}


_H = _by_hotel()


def _cleaned(hid: int) -> dict:
    try:
        return json.load(open(CLEANED.format(hid), encoding="utf-8"))
    except Exception:
        return {}


def _city_match(obj: dict, city: str) -> bool:
    loc = (obj.get("location") or {})
    blob = f"{loc.get('city','')} {loc.get('province','')}".lower()
    return city.lower() in blob or any(t in blob for t in city.lower().split() if len(t) > 2)


def _has_amenity(obj: dict, amens: set[str]) -> bool:
    return bool(set((obj.get("semantic_metadata") or {}).get("amenity") or []) & amens)


def _profile_ok(obj: dict, concept: str, thr: float = 0.6) -> bool:
    return (obj.get("semantic_profile") or {}).get(concept, {}).get("score", 0) >= thr


def _grade(hid: int, name_substr: str) -> float:
    for g in (_cleaned(hid).get("reviews_detail") or {}).get("grades") or []:
        if name_substr.lower() in (g.get("name") or "").lower():
            return g.get("score") or 0
    return 0


def _demographic(hid: int, name_substr: str) -> int:
    for d in (_cleaned(hid).get("reviews_detail") or {}).get("demographics") or []:
        if name_substr.lower() in (d.get("name") or "").lower():
            return d.get("count") or 0
    return 0


def _demographic_share(hid: int, name_substr: str) -> float:
    """Tỷ lệ nhóm khách này / tổng các nhóm (demographics). Chặt hơn count tuyệt đối: một
    hotel 'hợp gia đình' phải có TỶ LỆ khách gia đình cao, không chỉ nhiều review tổng."""
    demos = (_cleaned(hid).get("reviews_detail") or {}).get("demographics") or []
    total = sum(d.get("count") or 0 for d in demos)
    if not total:
        return 0.0
    grp = sum(d.get("count") or 0 for d in demos if name_substr.lower() in (d.get("name") or "").lower())
    return grp / total


def _landmark_near(obj: dict, lmk: str) -> float | None:
    for x in obj.get("nearby_landmarks") or []:
        if x.get("concept") == lmk:
            return x.get("distance_km")
    return None


# ---------------------------------------------------------------------------
# Predicate relevant NHỊ PHÂN cho từng họ câu (multi-signal, không sort-để-định-nghĩa)
# ---------------------------------------------------------------------------
def relevant_for(q: dict) -> tuple[list[int], dict]:
    """Trả (relevant_hotel_ids nhị phân, mô tả tín hiệu dùng)."""
    sig = [s for s in q.get("soft_signals", []) if s.isupper() and "_" in s]
    cid = sig[-1] if sig else ""
    city = (q.get("hard_filters") or {}).get("city")
    out: list[int] = []
    meta: dict = {"concept": cid, "signals": []}

    for hid, obj in _H.items():
        if city and not _city_match(obj, city):
            continue
        ok = False

        if cid.startswith("LMK_"):
            ok = _landmark_near(obj, cid) is not None
            meta["signals"] = ["nearby_landmark (structured)"]

        elif cid.startswith("AMEN_"):
            ok = _has_amenity(obj, {cid})
            meta["signals"] = ["amenity (structured Agoda)"]

        elif cid.startswith("STYLE_") or cid.startswith("ASPECT_"):
            # 2 nguồn ĐỘC LẬP: review-profile HOẶC grade tương ứng (nếu map được)
            grade_map = {
                "ASPECT_CLEANLINESS": "sạch", "ASPECT_SERVICE": "dịch vụ",
                "ASPECT_LOCATION": "vị trí", "ASPECT_FOOD": "ăn uống",
                "ASPECT_ROOM": "phòng", "ASPECT_VALUE": "đáng tiền",
                "ASPECT_FACILITIES": "cơ sở vật chất",
            }
            ok = _profile_ok(obj, cid)
            if cid in grade_map:
                ok = ok or _grade(hid, grade_map[cid]) >= 8.5
            meta["signals"] = ["semantic_profile>=0.6 OR grade>=8.5 (review, độc lập)"]

        elif cid.startswith("PURPOSE_"):
            demo_map = {
                "PURPOSE_FAMILY": "Gia đình", "PURPOSE_ROMANTIC": "Cặp đôi",
                "PURPOSE_SOLO": "một mình", "PURPOSE_GROUP": "Nhóm",
                "PURPOSE_BUSINESS": "công tác",
            }
            amen_map = {
                "PURPOSE_FAMILY": {"AMEN_KIDS_CLUB", "AMEN_KIDS_POOL", "AMEN_BABYSITTING"},
                "PURPOSE_BUSINESS": {"AMEN_MEETING_ROOM"},
            }
            # ĐỘC LẬP: demographics nhóm khách phải TRỘI (share>=25% + count>=50 đủ mẫu) HOẶC
            # amenity minh chứng. Dùng SHARE (không chỉ count) -> hotel thật sự "hợp nhóm này",
            # tránh mọi hotel đông review đều lọt -> tập relevant chọn lọc hơn.
            name = demo_map.get(cid, "")
            demo_ok = bool(name) and _demographic(hid, name) >= 50 and _demographic_share(hid, name) >= 0.25
            ok = demo_ok
            if cid in amen_map:
                ok = ok or _has_amenity(obj, amen_map[cid])
            meta["signals"] = ["demographics share>=25% & count>=50 OR amenity minh chứng (độc lập)"]

        elif cid.startswith("PRICE_"):
            rf = obj.get("range_filters") or {}
            star = rf.get("star_rating") or 0
            score = rf.get("review_score") or 0
            # PRICE tier xác nhận bằng STAR (structured) — giá là placeholder nên KHÔNG dùng giá.
            # Tier CAO (upscale/luxury) thêm điều kiện review_score>=8.5: "sang" phải được xác
            # nhận chất lượng, nếu không star=5 ra 149 hotel -> quá rộng, không phân biệt được.
            tier_star = {"PRICE_BUDGET": (1, 2), "PRICE_MID": (3, 3),
                         "PRICE_UPSCALE": (4, 4), "PRICE_LUXURY": (5, 5)}
            lo, hi = tier_star.get(cid, (0, 5))
            ok = lo <= star <= hi
            if cid in ("PRICE_UPSCALE", "PRICE_LUXURY"):
                ok = ok and score >= 8.5
            meta["signals"] = ["star_rating tier + (tier cao: review_score>=8.5); giá placeholder loại"]

        elif cid.startswith("GRADE_"):
            gmap = {
                "GRADE_DICH_VU": "dịch vụ", "GRADE_DO_SACH_SE": "sạch",
                "GRADE_DANG_TIEN": "đáng tiền", "GRADE_VI_TRI": "vị trí",
                "GRADE_CO_SO_VAT_CHAT": "cơ sở vật chất",
                "GRADE_CHAT_LUONG_PHONG": "phòng",
            }
            ok = _grade(hid, gmap.get(cid, "")) >= 8.5
            meta["signals"] = ["grade>=8.5 (review category, độc lập ontology)"]

        if ok:
            out.append(hid)
    return sorted(out), meta


# Ngưỡng kiểm soát chất lượng nhãn (MLOps): câu không đủ tin cậy -> đánh dấu excluded, KHÔNG
# để nhãn rác làm sai metric. Minh bạch "chưa eval được" tốt hơn số đẹp/xấu giả.
CORPUS_N = len(_H)
# too_broad theo SỐ TUYỆT ĐỐI, không theo % corpus: eval top-k (k<=10) cần tập relevant đủ
# CHỌN LỌC. >40 relevant -> hầu như mọi top-10 đều "trúng" -> không phân biệt hệ thống tốt/kém.
# Câu 1-tiêu-chí toàn quốc ("khách sạn tầm trung/yên tĩnh") rơi vào đây -> exclude.
TOO_BROAD_ABS = 40
MIN_RELEVANT = 1


def build() -> list[dict]:
    v1 = json.load(open(GOLDEN_V1, encoding="utf-8"))
    v2 = []
    for q in v1:
        rel, meta = relevant_for(q)
        n = len(rel)
        excluded = None
        if n < MIN_RELEVANT:
            excluded = "no_signal: enrichment chưa đủ data tạo nhãn khách quan (vd STYLE review thưa)"
        elif n > TOO_BROAD_ABS:
            excluded = f"too_broad: relevant {n}/{CORPUS_N} (>{TOO_BROAD_ABS}) — câu 1-tiêu-chí quá rộng, không phân biệt ranking"
        v2.append({
            "query_id": q["query_id"],
            "query": q["query"],
            "intent_type": q.get("intent_type", "hotel_search"),
            "hard_filters": q.get("hard_filters", {}),
            "soft_signals": q.get("soft_signals", []),
            "relevant_hotel_ids": rel,
            "relevant_chunk_ids": [],   # điền sau khi index xong (script riêng)
            "labeling_method": "multi_signal_binary",
            "relevance_signals": meta["signals"],
            "eval_status": "excluded" if excluded else "active",
            "exclude_reason": excluded,
            "labeler": q.get("labeler", "Kiên") + " + multi_signal_rebuild",
            "notes_v1": q.get("notes", "")[:120],
        })
    return v2


if __name__ == "__main__":
    v2 = build()
    json.dump(v2, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    active = [q for q in v2 if q["eval_status"] == "active"]
    excluded = [q for q in v2 if q["eval_status"] == "excluded"]
    print(f"Đã ghi {len(v2)} câu -> {OUT}")
    print(f"  active (eval được): {len(active)} | excluded (nhãn không đủ tin cậy): {len(excluded)}")
    if excluded:
        print("\nCâu EXCLUDED (minh bạch — không tính vào metric):")
        for q in excluded:
            print(f"  [{q['query_id']}] {q['query'][:45]} | {q['exclude_reason']}")
    import statistics
    rels = [len(q["relevant_hotel_ids"]) for q in active]
    print(f"\nactive relevant/câu: min={min(rels)} max={max(rels)} median={statistics.median(rels):.0f}")
