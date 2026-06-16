"""reset_backfill_mark.py — gỡ dấu backfilled_versions[concept] ở review chứa surface_form MỚI.

Bối cảnh: backfill_concepts skip review đã có backfilled_versions[concept] == version hiện tại.
Version dựa trên DANH SÁCH CONCEPT_ID, KHÔNG đổi khi ta chỉ thêm surface_form vào ontology.
=> Sau khi bổ sung surface_form cho 1 concept, các review đã backfill lần trước sẽ bị SKIP oan
   (form mới mở ra review mới NHƯNG nếu review đó từng được xét cho form cũ thì đã đánh dấu).

Giải: gỡ dấu backfilled_versions[concept] CHỈ ở review chứa form MỚI -> lần backfill sau chạy lại
đúng phần đó (không tốn tiền cho review không liên quan). KHÔNG xóa items đã có (chỉ xóa dấu).

Chạy:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.reset_backfill_mark \
      --concept STYLE_RELAXING --forms "nghỉ dưỡng" "nghỉ ngơi" relaxation retreat
  (thêm --dry-run để chỉ đếm, không sửa)
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

from knowledge_engineering.common.normalize import normalize as _norm

REVIEWS_DIR = "data/raw/reviews"
EVIDENCE_DIR = Path("knowledge_engineering/enrichment/review_evidence")


def _review_text(r: dict) -> str:
    text = r.get("text") or ""
    extra = " ".join(filter(None, [r.get("positives"), r.get("negatives")]))
    return (text + " " + extra).strip()


def reset_marks(concept: str, forms: list[str], dry_run: bool = False) -> tuple[int, int]:
    """Gỡ backfilled_versions[concept] ở review chứa 1 trong `forms` (đã fold).
    Trả (số review gỡ dấu, số hotel chạm)."""
    folded = [_norm(f, fold=True) for f in forms]
    n_reset = n_hotels = 0
    for evf in glob.glob(str(EVIDENCE_DIR / "hotel_*.json")):
        hid = re.search(r"hotel_(\d+)", evf).group(1)
        rf = Path(REVIEWS_DIR) / f"hotel_{hid}_reviews.json"
        if not rf.exists():
            continue
        store = json.loads(Path(evf).read_text(encoding="utf-8"))
        revs = {str(r.get("review_id")): r for r in
                json.loads(rf.read_text(encoding="utf-8")).get("reviews", [])}
        changed = 0
        for rid, e in store.items():
            bv = e.get("backfilled_versions")
            if not bv or concept not in bv:
                continue
            r = revs.get(rid)
            if not r:
                continue
            blob = _norm(_review_text(r), fold=True)
            if any(f in blob for f in folded):
                if not dry_run:
                    del bv[concept]              # gỡ dấu -> backfill lần sau xét lại review này
                changed += 1
        if changed:
            n_reset += changed
            n_hotels += 1
            if not dry_run:
                Path(evf).write_text(json.dumps(store, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return n_reset, n_hotels


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gỡ dấu backfilled_versions[concept] ở review nhắc form mới.")
    ap.add_argument("--concept", required=True, help="concept_id (vd STYLE_RELAXING)")
    ap.add_argument("--forms", nargs="+", required=True, help="các surface_form MỚI thêm (chưa fold cũng được)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ đếm, không sửa file")
    args = ap.parse_args()
    n, h = reset_marks(args.concept, args.forms, dry_run=args.dry_run)
    tag = "[dry-run] " if args.dry_run else ""
    print(f"{tag}{args.concept}: gỡ dấu {n} review / {h} hotel (chứa form {args.forms}).")
    if not args.dry_run:
        print("-> chạy lại: absa.py --backfill " + args.concept)
