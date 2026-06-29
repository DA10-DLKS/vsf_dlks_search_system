"""build_golden_evidence.py — Bổ sung evidence + expected_answer vào golden (v2.1).

ĐỘC LẬP VỚI KE: đọc review THẬT từ data/raw/reviews/ (không qua ontology/semantic_profile),
trích span review khớp tiêu chí của query, ghi vào golden làm bằng chứng. Tránh "đo hệ thống
bằng nhãn do chính hệ thống sinh".

Cách trích: với mỗi câu, lấy top-K hotel trong relevant_hotel_ids -> đọc review thật -> chấm
mỗi review theo độ khớp soft_signals (keyword + biến thể) -> giữ span điểm cao + cân bằng
pos/neg -> dựng expected_answer tóm tắt CÓ DẪN CHỨNG.

Output: golden_set_v2.1_draft.json (đánh dấu human_review_pending — bạn duyệt rồi promote).

Chạy: PYTHONPATH=. .venv/Scripts/python.exe -X utf8 scripts/build_golden_evidence.py [--limit N]
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

GOLDEN_IN = "data/golden_dataset/golden_set_v2.json"
GOLDEN_OUT = "data/golden_dataset/golden_set_v2.1_draft.json"
REVIEW_DIR = "data/raw/reviews"

TOP_HOTELS_PER_QUERY = 4   # số hotel lấy evidence mỗi câu
EVIDENCE_PER_HOTEL = 2     # span/hotel
MIN_SPAN_LEN = 25


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# từ khóa mở rộng cho soft signal (khớp cả tiếng Việt lẫn Anh, có/không dấu)
SIGNAL_KEYWORDS = {
    "cao cấp": ["luxur", "sang", "cao cap", "premium", "5 star", "5-star", "deluxe", "elegant"],
    "nhóm": ["group", "nhom", "doan", "spacious", "big villa", "large", "2-bedroom", "rong"],
    "gia đình": ["family", "gia dinh", "kid", "children", "tre em", "child"],
    "biển": ["beach", "bien", "sea view", "ocean", "seaview", "beachfront"],
    "yên tĩnh": ["quiet", "yen tinh", "peaceful", "calm", "relax", "tranquil"],
    "sôi động": ["lively", "soi dong", "vibrant", "nightlife", "bar", "party", "buzz"],
    "sạch": ["clean", "sach", "spotless", "tidy", "hygien"],
    "dịch vụ": ["service", "dich vu", "staff", "nhan vien", "friendly", "helpful"],
    "vị trí": ["location", "vi tri", "central", "convenient", "gan", "near"],
    "giá rẻ": ["cheap", "gia re", "budget", "value", "affordable", "worth"],
}


def _load_reviews(hotel_id):
    f = os.path.join(REVIEW_DIR, f"hotel_{hotel_id}_reviews.json")
    if not os.path.exists(f):
        return []
    d = json.load(open(f, encoding="utf-8"))
    return d if isinstance(d, list) else (d.get("reviews") or [])


def _signal_terms(soft_signals):
    """Map soft_signals (gồm cả concept_id) -> tập keyword để khớp review thật."""
    terms = set()
    for s in soft_signals or []:
        sl = _fold(s)
        for label, kws in SIGNAL_KEYWORDS.items():
            if _fold(label) in sl or any(_fold(k) in sl for k in kws):
                terms.update(kws)
        # concept_id (STYLE_/PURPOSE_) -> map qua label gần đúng
        terms.add(sl)
    return [t for t in terms if len(t) >= 3]


def _extract_evidence(hotel_id, terms):
    """Trích tối đa EVIDENCE_PER_HOTEL span review THẬT khớp nhiều term nhất; cân bằng pos/neg."""
    reviews = _load_reviews(hotel_id)
    scored = []
    for r in reviews:
        text = (r.get("text") or "").strip()
        title = (r.get("title") or "").strip()
        blob = _fold(title + " " + text)
        if len(text) < MIN_SPAN_LEN:
            continue
        hits = sum(1 for t in terms if t in blob)
        if hits == 0:
            continue
        rating = r.get("rating")
        scored.append({
            "review_id": r.get("review_id"),
            "rating": rating,
            "polarity": "pos" if (rating or 0) >= 7 else ("neg" if (rating or 0) <= 5 else "mixed"),
            "span": (title + " — " + text)[:280] if title else text[:280],
            "match_count": hits,
        })
    scored.sort(key=lambda x: -x["match_count"])
    # ưu tiên 1 pos + 1 neg để cân bằng (chống tâng bốc)
    pos = [s for s in scored if s["polarity"] == "pos"]
    neg = [s for s in scored if s["polarity"] in ("neg", "mixed")]
    out = (pos[:1] + neg[:1] + scored)[:EVIDENCE_PER_HOTEL]
    # dedupe theo review_id
    seen, dedup = set(), []
    for e in out:
        if e["review_id"] in seen:
            continue
        seen.add(e["review_id"])
        dedup.append(e)
    return dedup[:EVIDENCE_PER_HOTEL]


def _hotel_name(hotel_id):
    f = os.path.join(REVIEW_DIR, f"hotel_{hotel_id}_reviews.json")
    if os.path.exists(f):
        return json.load(open(f, encoding="utf-8")).get("hotel_name", str(hotel_id))
    return str(hotel_id)


def build_entry(e):
    terms = _signal_terms(e.get("soft_signals"))
    evidence = []
    for hid in (e.get("relevant_hotel_ids") or [])[:TOP_HOTELS_PER_QUERY]:
        for ev in _extract_evidence(hid, terms):
            evidence.append({"hotel_id": hid, "hotel_name": _hotel_name(hid),
                             "review_id": ev["review_id"], "rating": ev["rating"],
                             "polarity": ev["polarity"], "span": ev["span"]})
    # answer tóm tắt CÓ DẪN CHỨNG (nêu cả hotel mạnh lẫn lưu ý từ review thật)
    pos = [ev for ev in evidence if ev["polarity"] == "pos"]
    cautions = [ev for ev in evidence if ev["polarity"] in ("neg", "mixed")]
    lines = []
    if pos:
        names = list(dict.fromkeys(ev["hotel_name"][:40] for ev in pos))[:3]
        lines.append("Gợi ý phù hợp (theo review thật): " + ", ".join(names) + ".")
    if cautions:
        c = cautions[0]
        lines.append(f"Lưu ý: một số khách phản ánh về {c['hotel_name'][:40]} — \"{c['span'][:80]}...\"")
    answer = " ".join(lines) or "Chưa đủ review thật khớp tiêu chí để tóm tắt khách quan."
    return {
        "expected_answer": answer,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "answer_labeling": "extracted_from_raw_reviews + human_review_pending",
    }


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    golden = json.load(open(GOLDEN_IN, encoding="utf-8"))
    active = [e for e in golden if e.get("eval_status", "active") == "active"]
    if limit:
        active = active[:limit]

    out = []
    n_with_ev = 0
    for e in golden:
        if e.get("eval_status") != "active" or (limit and e not in active):
            out.append(e)
            continue
        enriched = build_entry(e)
        if enriched["evidence_count"]:
            n_with_ev += 1
        out.append({**e, **enriched})

    json.dump(out, open(GOLDEN_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    total_active = sum(1 for e in out if e.get("eval_status") == "active")
    print(f"Ghi {GOLDEN_OUT}")
    print(f"  {n_with_ev}/{total_active if not limit else len(active)} câu active có evidence từ review thật")
    print(f"  -> review tay file draft này, sửa expected_answer/evidence sai, rồi đổi tên thành golden_set_v2.1.json")


if __name__ == "__main__":
    main()
