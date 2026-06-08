"""absa.py — Aspect-Based Sentiment Analysis cho review (Sprint 2, Bước 5.3).

Owner: Trương Anh Long (KE, DA10). Mỗi review tiếng Việt -> trích cặp (khía cạnh, cảm xúc, span)
bằng LLM (qua llm.py đa-provider). Bổ sung cho SEED (5.2): thêm SPAN dẫn chứng + concept STYLE_*
ngoài 7 aspect mà aggregate Agoda không có.

NGUYÊN TẮC (mục 0.5 + 2.4):
  - concept TRUNG TÍNH: "hơi ồn" -> {STYLE_QUIET, negative}, KHÔNG tạo STYLE_NOT_QUIET.
  - aspect CHỈ trong 7 ASPECT_* (ràng buộc vocabulary). style chỉ trong tập cho phép.
  - mỗi review tối đa 1 phiếu/concept (dedupe ở aggregate 5.4).
  - LLM chỉ chạy review (ca khó/giàu thông tin); KHÔNG sửa ontology.

Chạy mẫu:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.absa --hotel 805030 --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from knowledge_engineering.enrichment.llm import complete_json, active_config

REVIEWS_DIR = "data/raw/reviews"

# Vocabulary cho phép (ràng buộc LLM chỉ chọn trong đây)
ASPECTS = ["ASPECT_CLEANLINESS", "ASPECT_SERVICE", "ASPECT_LOCATION", "ASPECT_ROOM",
           "ASPECT_FOOD", "ASPECT_VALUE", "ASPECT_FACILITIES"]
STYLES = ["STYLE_QUIET", "STYLE_LIVELY", "STYLE_RELAXING", "STYLE_MODERN",
          "STYLE_ROMANTIC", "STYLE_LUXURY", "STYLE_ECO"]

SYSTEM = f"""Bạn trích cảm xúc theo khía cạnh (ABSA) từ review du lịch tiếng Việt.

aspect CHỈ chọn trong: {ASPECTS}
style (cảm nhận phong cách, tùy chọn) CHỈ chọn trong: {STYLES}

Quy tắc:
- Mỗi khía cạnh/phong cách được NHẮC tới -> 1 mục {{concept, sentiment, span}}.
- sentiment: positive | negative | neutral | mixed.
- span: trích NGUYÊN VĂN đoạn ngắn trong review làm bằng chứng.
- TRUNG TÍNH: "hơi ồn" -> {{"concept":"STYLE_QUIET","sentiment":"negative"}} (KHÔNG tạo NOT_QUIET).
- Không bịa khía cạnh review không nhắc tới. Không nhắc gì -> mảng rỗng.

CHỈ trả JSON đúng dạng:
{{"overall_sentiment":"positive|negative|neutral|mixed",
  "items":[{{"concept":"ASPECT_... hoặc STYLE_...","sentiment":"...","span":"..."}}]}}"""


def analyze_review(text: str) -> dict:
    """Trả {overall_sentiment, items:[{concept, sentiment, span}]}. Lọc concept ngoài vocab."""
    if not text or not text.strip():
        return {"overall_sentiment": "neutral", "items": []}
    out = complete_json(SYSTEM, text.strip()[:2000], temperature=0)
    allowed = set(ASPECTS) | set(STYLES)
    items = []
    for it in out.get("items", []) or []:
        if isinstance(it, dict) and it.get("concept") in allowed:
            items.append({
                "concept": it["concept"],
                "sentiment": it.get("sentiment", "neutral"),
                "span": (it.get("span") or "")[:200],
            })
    return {"overall_sentiment": out.get("overall_sentiment", "neutral"), "items": items}


def analyze_hotel(hotel_id: int, limit: int | None = None) -> list[dict]:
    """Chạy ABSA cho review của 1 hotel. Trả list evidence per-review."""
    f = Path(REVIEWS_DIR) / f"hotel_{hotel_id}_reviews.json"
    if not f.exists():
        raise FileNotFoundError(f"Không có file review: {f}")
    data = json.loads(f.read_text(encoding="utf-8"))
    reviews = data.get("reviews", [])
    if limit:
        reviews = reviews[:limit]
    out = []
    for r in reviews:
        text = r.get("text") or ""
        # ghép positives/negatives nếu có (Agoda tách)
        extra = " ".join(filter(None, [r.get("positives"), r.get("negatives")]))
        full = (text + " " + extra).strip()
        res = analyze_review(full)
        out.append({
            "review_id": r.get("review_id"),
            "hotel_id": hotel_id,
            "rating": r.get("rating"),
            "overall_sentiment": res["overall_sentiment"],
            "items": res["items"],
        })
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hotel", type=int, required=True)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    print(f"LLM: {active_config()['provider']}/{active_config()['model']}")
    print(f"ABSA hotel {args.hotel}, {args.limit} review (mẫu nghiệm thu)...\n")
    ev = analyze_hotel(args.hotel, args.limit)

    # tóm tắt
    from collections import Counter
    concept_sent = Counter()
    n_items = 0
    for e in ev:
        for it in e["items"]:
            concept_sent[(it["concept"], it["sentiment"])] += 1
            n_items += 1
    print(f"Đã phân tích {len(ev)} review -> {n_items} cặp (concept, sentiment).\n")
    print("Phân bố (concept, sentiment):")
    for (c, s), n in concept_sent.most_common(20):
        print(f"  {n:3d}  {c:22s} {s}")
    # vài span mẫu
    print("\nVí dụ span dẫn chứng:")
    shown = 0
    for e in ev:
        for it in e["items"]:
            if it["span"]:
                print(f"  [{it['concept']}/{it['sentiment']}] \"{it['span'][:70]}\"")
                shown += 1
        if shown >= 6:
            break
