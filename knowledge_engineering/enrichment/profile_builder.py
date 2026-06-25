"""profile_builder.py — Hotel Semantic Profile (Sprint 2, Bước 5.2 SEED + 5.4 aggregate).

Owner: Trương Anh Long (KE, DA10). Xây hotel_semantic_profile: điểm RIÊNG của từng hotel
trên concept (BA THỨ TÁCH BIỆT — Phần 0.5). KHÔNG sửa ontology.

Bước 5.2 (SEED, KHÔNG LLM): từ aggregate Agoda có sẵn:
  - rating_breakdown (7 aspect, điểm /10)        -> ASPECT_* score = điểm/10, nguồn=agoda_grades.
  - reviews_detail.tags (tag, mentioned, pos_pct) -> concept; pos/neg suy từ pos_pct*mentioned,
                                                     score = Wilson lower bound (ít data -> thấp hơn).
Bước 5.3 (ABSA per-review, LLM) sẽ THÊM evidence vào cùng cấu trúc -> aggregate lại (5.4).

Lớp dữ liệu (tách, mục 2.4d): profile = {hotel_id: {concept: {score,pos,neg,evidence_count,source,nature}}}.

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
"""

from __future__ import annotations

import glob
import json
import math
from collections import defaultdict

import yaml

HOTELS_GLOB = "data/cleaned/hotel_*.json"
MAP_YAML = "ontology/review_tag_map.yaml"
OUT_JSON = "knowledge_engineering/enrichment/hotel_profiles.json"
EVIDENCE_DIR = "knowledge_engineering/enrichment/review_evidence"

_map = yaml.safe_load(open(MAP_YAML, encoding="utf-8"))
RB_MAP = _map["rating_breakdown"]
TAG_MAP = _map["review_tags"]

# ── PURPOSE score (2026-06-25): suitable_for loãng (450/520 hotel đủ 5 purpose -> không phân
#    biệt). Lấy ĐIỂM PHÂN BIỆT từ reviews_detail.demographics (score/10 + count per nhóm khách).
#    Fallback chain mỗi purpose: demographics > review_tag (cũ) > derived(related) > presence-only.
# (1) demographics nhóm Agoda -> PURPOSE_*. 2 nhóm gia đình GỘP vào FAMILY (cộng count, score
#     trọng số theo count).
DEMO_MAP = {
    "Khách du lịch một mình": "PURPOSE_SOLO",
    "Cặp đôi": "PURPOSE_ROMANTIC",
    "Nhóm du khách": "PURPOSE_GROUP",
    "Gia đình có trẻ nhỏ": "PURPOSE_FAMILY",
    "Gia đình có thanh thiếu niên": "PURPOSE_FAMILY",
    "Khách đi công tác": "PURPOSE_BUSINESS",
}
DEMO_PRIOR = 0.86   # mean điểm demographics toàn corpus (8.6/10) — kéo về khi ít review
DEMO_K = 20         # ngưỡng shrinkage: count<<K -> về prior; count>>K -> tin score thật
# (3) derived: purpose KHÔNG có nhóm demographics (vd WELLNESS) suy từ related concepts đã khai
#     báo trong ontology. Map purpose -> [(concept, loại)]. loại: "presence"(amenity có=1.0) |
#     "score"(lấy score SOFT từ profile). Purpose mới chỉ cần thêm dòng ở đây, KHÔNG sửa logic.
DERIVED_RELATED = {
    "PURPOSE_WELLNESS": [("AMEN_SPA", "presence"), ("STYLE_QUIET", "score")],
}
DERIVED_DISCOUNT = 0.8   # điểm gián tiếp -> nhân 0.8 (tin thấp hơn nguồn trực tiếp)

# Phân vai 2 nguồn (sau khi đo: review crawl thiên-thấp -> ABSA mẫu lệch tiêu cực):
#   - ASPECT score  : LẤY TỪ SEED (rating_breakdown = toàn bộ review Agoda, cân bằng).
#                     KHÔNG đè bằng ABSA (mẫu crawl không đại diện tỷ lệ pos/neg).
#   - STYLE + span  : LẤY TỪ ABSA (seed/Agoda không có tag style). Chỉ cần sự HIỆN DIỆN,
#                     không cần tỷ lệ cân bằng -> mẫu crawl dùng được.
ABSA_MIN_EVIDENCE = 3   # cần >=3 review nhắc style mới đưa vào profile (tránh 1 review lẻ)
NEG_STYLE_MIN_EVIDENCE = 3  # cần >=3 review chê để expose negative_style_profile
NEG_STYLE_MAX_SPANS = 5


def wilson_lower_bound(pos: int, n: int, z: float = 1.96) -> float:
    """Wilson lower bound — ít evidence -> score thấp hơn raw (không overconfident)."""
    if n == 0:
        return 0.0
    phat = pos / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def _demographics_purpose(rd: dict) -> dict[str, dict]:
    """reviews_detail.demographics (score/10 + count per nhóm) -> PURPOSE_* score.
    Shrinkage Bayesian: count nhỏ -> kéo về prior (đỡ overconfident, đúng tinh thần Wilson).
    2 nhóm gia đình GỘP (cộng count, score trung bình trọng số count)."""
    agg: dict[str, dict] = defaultdict(lambda: {"wsum": 0.0, "count": 0})
    for d in rd.get("demographics", []) or []:
        if not isinstance(d, dict):
            continue
        cid = DEMO_MAP.get(d.get("name"))
        score10, count = d.get("score"), int(d.get("count") or 0)
        if not cid or not isinstance(score10, (int, float)) or count <= 0:
            continue
        agg[cid]["wsum"] += (score10 / 10.0) * count
        agg[cid]["count"] += count
    out: dict[str, dict] = {}
    for cid, a in agg.items():
        cnt = a["count"]
        raw = a["wsum"] / cnt                                   # điểm thật (trọng số count)
        score = (cnt * raw + DEMO_K * DEMO_PRIOR) / (cnt + DEMO_K)   # kéo về prior khi ít review
        out[cid] = {
            "score": round(score, 3),
            "score_source": "agoda_demographics(shrunk)",
            "evidence_count": cnt,
            "source": "agoda_demographics", "nature": "presence",
        }
    return out


def derive_purpose(prof: dict[str, dict], amenities: set[str]) -> None:
    """Purpose KHÔNG có nhóm demographics (WELLNESS...) -> suy điểm từ related concepts đã
    khai báo (DERIVED_RELATED). Chỉ gán nếu hotel có >=1 related. Đánh dấu source=derived."""
    for cid, rels in DERIVED_RELATED.items():
        if cid in prof:                       # đã có điểm từ nguồn mạnh hơn -> không đè
            continue
        vals = []
        for concept, kind in rels:
            if kind == "presence":
                if concept in amenities:
                    vals.append(1.0)
            elif kind == "score":
                s = prof.get(concept, {}).get("score")
                if s is not None:
                    vals.append(s)
        if not vals:
            continue
        prof[cid] = {
            "score": round(sum(vals) / len(vals) * DERIVED_DISCOUNT, 3),
            "score_source": "derived(related)",
            "evidence_count": len(vals),
            "source": "derived",
            "nature": "presence",
            "derived_from": [c for c, _ in rels],
        }


def seed_from_hotel(hotel: dict) -> dict[str, dict]:
    """Seed profile 1 hotel từ aggregate Agoda. concept -> {score,pos,neg,evidence_count,source,nature}."""
    prof: dict[str, dict] = {}
    rd = hotel.get("reviews_detail") or {}

    # (1) rating_breakdown -> ASPECT score = điểm/10 (tổng hợp TOÀN BỘ review).
    #     score_source ghi rõ nguồn của SCORE (tách khỏi mention bên dưới).
    n_reviews = rd.get("review_count") or hotel.get("review_count") or 0
    for name, score10 in (hotel.get("rating_breakdown") or {}).items():
        cid = RB_MAP.get(name)
        if cid and isinstance(score10, (int, float)):
            prof[cid] = {
                "score": round(score10 / 10.0, 3),
                "score_source": "agoda_grades(all reviews)",
                "evidence_count": n_reviews,
                "source": "agoda_grades",
                "nature": "experience",
            }

    # (1b) demographics -> PURPOSE_* score (nguồn PHÂN BIỆT, thay suitable_for loãng). Đặt TRƯỚC
    #      review_tags để purpose lấy score demographics làm chính, review_tag chỉ thêm mention.
    prof.update(_demographics_purpose(rd))

    # (2) reviews_detail.tags -> mention pos/neg. LƯU Ý 2 NGUỒN KHÁC NHAU:
    #     score (trên) = grades toàn bộ; mention_pos/neg (dưới) = SỐ REVIEW NHẮC TỚI aspect
    #     (Agoda chỉ trích vài trăm review tiêu biểu, KHÔNG phải toàn bộ). 2 số đo việc khác
    #     nhau -> KHÔNG đá nhau, đánh dấu rõ mention_source để người đọc không hiểu nhầm.
    for t in rd.get("tags", []) or []:
        if not isinstance(t, dict):
            continue
        cid = TAG_MAP.get(t.get("tag"))
        if not cid:
            continue
        mentioned = int(t.get("mentioned") or 0)
        pos = round(mentioned * float(t.get("positive_pct") or 0) / 100.0)
        neg = mentioned - pos
        if cid in prof and prof[cid].get("source") in ("agoda_grades", "agoda_demographics"):
            # đã có score mạnh hơn (grades cho aspect / demographics cho purpose) -> CHỈ thêm
            # mention (nguồn riêng), KHÔNG đè score.
            prof[cid]["mention_pos"] = pos
            prof[cid]["mention_neg"] = neg
            prof[cid]["mention_source"] = "agoda_tags(mentioned)"
        else:
            nat = "presence" if cid.startswith(("AMEN_", "PURPOSE_")) else "experience"
            prof[cid] = {
                "score": round(wilson_lower_bound(pos, mentioned), 3),
                "score_source": "agoda_tags(mentioned)",
                "pos": pos, "neg": neg,
                "evidence_count": mentioned,
                "source": "agoda_review_tags", "nature": nat,
            }
    return prof


def merge_absa(hotel_id: int, prof: dict[str, dict]) -> None:
    """Bổ sung từ ABSA evidence (nếu có file). 2 vai theo điểm mạnh nguồn:

      - ASPECT_* : score GIỮ TỪ SEED (Agoda toàn bộ review, cân bằng). ABSA chỉ THÊM
                   SPAN dẫn chứng tích cực (để DA09 giải thích "vì sao sạch").
      - STYLE_*  : nếu seed CHƯA có -> ABSA đóng góp cả score (Wilson) + span. Nếu seed
                   đã có -> chỉ thêm span (mẫu crawl thiên-thấp không đủ tin đè score).
    Span lấy review TÍCH CỰC (vì aspect score = % khen -> dẫn chứng nên là khen).
    """
    import os
    p = os.path.join(EVIDENCE_DIR, f"hotel_{hotel_id}.json")
    if not os.path.exists(p):
        return
    ev = json.load(open(p, encoding="utf-8"))
    pos: dict[str, int] = {}
    neg: dict[str, int] = {}
    span: dict[str, str] = {}     # span TÍCH CỰC (ưu tiên) làm dẫn chứng
    neg_spans: dict[str, list[str]] = defaultdict(list)
    for e in ev.values():
        seen = set()
        for it in e.get("items", []):
            c = it.get("concept", "")
            if not c.startswith(("ASPECT_", "STYLE_")) or c in seen:
                continue
            seen.add(c)
            if it.get("sentiment") == "positive":
                pos[c] = pos.get(c, 0) + 1
                span.setdefault(c, it.get("span", ""))
            elif it.get("sentiment") == "negative":
                neg[c] = neg.get(c, 0) + 1
                if c.startswith("STYLE_") and it.get("span") and len(neg_spans[c]) < NEG_STYLE_MAX_SPANS:
                    neg_spans[c].append(it["span"])

    negative_style_profile = {}
    for c, n_neg in neg.items():
        if not c.startswith("STYLE_") or n_neg < NEG_STYLE_MIN_EVIDENCE:
            continue
        n_pos = pos.get(c, 0)
        n_total = n_pos + n_neg
        negative_style_profile[c] = {
            "negative_score": round(wilson_lower_bound(n_neg, n_total), 3),
            "neg": n_neg,
            "pos": n_pos,
            "evidence_count": n_total,
            "top_spans": neg_spans.get(c, []),
            "source": "absa",
        }
    if negative_style_profile:
        prof["negative_style_profile"] = negative_style_profile

    for c in set(pos) | set(neg) | set(span):
        # ASPECT: chỉ thêm span (nếu seed có concept đó), KHÔNG đụng score.
        if c.startswith("ASPECT_"):
            if c in prof and span.get(c):
                prof[c]["span"] = span[c]
            continue
        # STYLE: là cặp ĐỐI NGHĨA (sôi động↔yên tĩnh), KHÔNG phải thang tốt↔xấu như aspect.
        # "chê ồn" (neg cho LIVELY) KHÔNG có nghĩa "hotel kém sôi động" -> nếu tính cả neg thì
        # ra STYLE_LIVELY=0.02 vô nghĩa. GIẢI: score style = sự HIỆN DIỆN TÍCH CỰC ('hotel này
        # CÓ phong cách X'); chỉ đếm positive, bỏ negative. Concept toàn negative -> LOẠI.
        #
        # HỢP NHẤT 2 NGUỒN: seed Agoda (tag map -> STYLE) và ABSA đo CÙNG sự hiện diện style,
        # nên GỘP pos/neg của cả hai rồi tính 1 Wilson chung. Nếu KHÔNG gộp (trước đây seed độc
        # quyền giữ score) thì 1 tag Agoda thiểu số toàn-chê (vd "Cách âm" 3 chê) khóa cứng
        # STYLE_QUIET=0.0 và vô hiệu hàng chục phiếu KHEN của ABSA — 57 hotel từng dính lỗi này.
        seed = prof.get(c) if (c in prof and prof[c].get("source") in
                               ("agoda_review_tags", "agoda_grades")) else None
        seed_pos = int(seed.get("pos", 0)) if seed else 0
        seed_neg = int(seed.get("neg", 0)) if seed else 0
        p = pos.get(c, 0) + seed_pos       # tổng KHEN: ABSA + seed Agoda
        if p < ABSA_MIN_EVIDENCE:          # cần >=3 phiếu KHEN (gộp) mới công nhận phong cách này
            continue
        n_neg = neg.get(c, 0) + seed_neg   # tổng CHÊ (chỉ để biết mẫu số, KHÔNG kéo score xuống 0)
        n = p + n_neg
        prof[c] = {
            "score": round(wilson_lower_bound(p, n), 3),
            "pos": p, "neg": n_neg,
            "evidence_count": n,
            "span": span.get(c, "") or (seed.get("span", "") if seed else ""),
            "source": "absa+agoda_review_tags" if seed else "absa",
            "nature": "experience",
        }


def run() -> dict:
    profiles: dict[str, dict] = {}
    stats = {"n": 0, "with_profile": 0, "concept_hits": defaultdict(int), "no_data": 0}
    for f in sorted(glob.glob(HOTELS_GLOB)):
        hotel = json.load(open(f, encoding="utf-8"))
        hid = hotel.get("hotel_id")
        key = f"acc_{hid}"
        prof = seed_from_hotel(hotel)
        merge_absa(hid, prof)              # ASPECT: thêm span; STYLE: score+span từ ABSA
        profiles[key] = prof
        stats["n"] += 1
        if prof:
            stats["with_profile"] += 1
        else:
            stats["no_data"] += 1
        for c in prof:
            if c == "negative_style_profile":
                continue
            stats["concept_hits"][c] += 1
    json.dump(profiles, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return stats


if __name__ == "__main__":
    s = run()
    print(f"Hotels: {s['n']} | có profile seed: {s['with_profile']} | không data: {s['no_data']}")
    print("Concept phủ (số hotel):")
    for c, n in sorted(s["concept_hits"].items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {c}")
    print(f"-> {OUT_JSON}")
