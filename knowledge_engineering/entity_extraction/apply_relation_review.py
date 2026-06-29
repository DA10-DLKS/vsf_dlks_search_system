"""apply_relation_review.py — Áp quyết định duyệt từ candidates.yaml (luồng giống STYLE).

KHÔNG có quyết định trong code. Người duyệt chỉ sửa `status` NGAY trong
ontology/relations/candidates.yaml:
    status: pending   -> chờ duyệt (để nguyên)
    status: approved  -> đồng ý  -> script chuyển sang curated.yaml (verified, boost-only)
    status: rejected  -> từ chối -> script chuyển sang rejected.yaml (cần reject_reason)

Rồi chạy script này. Nó di chuyển các cạnh đã quyết, giữ lại pending để duyệt vòng sau.

Chạy:
    .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.apply_relation_review
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REL_DIR = ROOT / "ontology/relations"
CANDIDATES = REL_DIR / "candidates.yaml"
CURATED = REL_DIR / "curated.yaml"
REJECTED = REL_DIR / "rejected.yaml"

CANDIDATES_HEADER = (
    "# candidates.yaml — Relation CHỜ DUYỆT (hàng đợi). Do build_relation_candidates.py sinh.\n"
    "# DUYỆT TAY (giống luồng STYLE): đổi `status: pending` -> `approved` hoặc `rejected`\n"
    "#   (rejected thì thêm dòng `reject_reason: \"...\"`), rồi chạy:\n"
    "#   python -m knowledge_engineering.entity_extraction.apply_relation_review\n"
    "# Relation đã approved/rejected được GIỮ NGUYÊN khi chạy lại generator (không ghi đè quyết định).\n"
)
CURATED_HEADER = "# curated.yaml — Relation đã DUYỆT (verified). Source of truth. Xem ontology/relations/README.md\n"
REJECTED_HEADER = "# rejected.yaml — Relation đã TỪ CHỐI (giữ để generator không đề xuất lại). Mỗi cái có reject_reason.\n"


def load(path: Path) -> dict:
    if not path.exists():
        return {"version": "1.0.0", "relations": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"version": "1.0.0", "relations": []}


def dump(path: Path, data: dict, header: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cand = load(CANDIDATES)
    curated = load(CURATED)
    rejected = load(REJECTED)
    cand_rels = cand.get("relations") or []

    cur_pairs = {(r["source"], r["target"]) for r in curated["relations"]}
    rej_pairs = {(r["source"], r["target"]) for r in rejected["relations"]}

    still_pending, approved, rejected_now, errors = [], [], [], []

    for r in cand_rels:
        status = r.get("status", "pending")
        key = (r.get("source"), r.get("target"))
        if status == "pending":
            still_pending.append(r)
            continue
        if status == "approved":
            if key in cur_pairs:
                continue  # đã có trong curated
            # approve = quyết định người -> source_type thành 'curated' (README rule 4:
            # generated_* không được verified trực tiếp). Giữ vết gốc + lift trong note.
            orig = r.get("source_type", "generated_lift")
            lift = r.get("lift")
            curated["relations"].append({
                "source": r["source"], "target": r["target"],
                "type": r.get("type", "cooccurs_with"),
                "source_type": "curated",
                "confidence": r.get("confidence", 0.6),
                "use_as": "boost", "status": "verified",
                "support": r.get("support"),
                "note": f"approved từ candidate ({orig}, lift={lift}, boost-only)",
            })
            cur_pairs.add(key)
            approved.append(key)
        elif status == "rejected":
            if not r.get("reject_reason"):
                errors.append(f"{key} status=rejected nhưng THIẾU reject_reason -> giữ lại để bạn bổ sung")
                still_pending.append(r)
                continue
            if key not in rej_pairs:
                rejected["relations"].append({
                    "source": r["source"], "target": r["target"],
                    "type": r.get("type", "cooccurs_with"),
                    "source_type": r.get("source_type", "generated_lift"),
                    "status": "rejected", "reject_reason": r["reject_reason"],
                })
                rej_pairs.add(key)
            rejected_now.append(key)
        else:
            errors.append(f"{key} status='{status}' không hợp lệ (pending/approved/rejected) -> giữ lại")
            still_pending.append(r)

    cand["relations"] = still_pending

    dump(CURATED, curated, CURATED_HEADER)
    dump(REJECTED, rejected, REJECTED_HEADER)
    dump(CANDIDATES, cand, CANDIDATES_HEADER)

    print(f"Approved -> curated.yaml : {len(approved)} {approved}")
    print(f"Rejected -> rejected.yaml: {len(rejected_now)} {rejected_now}")
    print(f"Còn pending              : {len(still_pending)}")
    if errors:
        print("\n⚠ Cần xử lý:")
        for e in errors:
            print(f"  - {e}")
    if approved or rejected_now:
        print("\nNhớ chạy tiếp để đẩy ra artifact query layer:")
        print("  python -m knowledge_engineering.common.build_expansion")


if __name__ == "__main__":
    main()
