"""relation_quality.py — Bước 10 roadmap: report sức khỏe relation graph.

Read-only. Đọc toàn bộ relation (qua relation_loader) + candidates thô, sinh report để
người duyệt biết duyệt gì trước và phát hiện relation graph có phình thành mạng nhiễu không.

Sinh: docs/reports/ontology/relation_quality.md

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.relation_quality
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

from knowledge_engineering.common.relation_loader import (
    load_all_relations, load_concept_ids,
)

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "ontology/relations/candidates.yaml"
OUT_MD = ROOT / "docs/reports/ontology/relation_quality.md"
POPULAR_THRESHOLD = 6  # concept làm source của > N cạnh -> coi là "phổ biến", soát kỹ


def load_candidate_rows() -> list[dict]:
    if not CANDIDATES.exists():
        return []
    d = yaml.safe_load(CANDIDATES.read_text(encoding="utf-8")) or {}
    return [r for r in (d.get("relations") or []) if r.get("status") == "candidate"]


def build() -> str:
    concept_ids = load_concept_ids()
    rels = load_all_relations(concept_ids=concept_ids)
    candidates = load_candidate_rows()

    by_status = Counter(r.status for r in rels)
    by_source_type = Counter(r.source_type for r in rels)
    by_use_as = Counter(r.use_as for r in rels)
    src_fanout = Counter(r.source for r in rels if r.status == "verified")

    L: list[str] = []
    L.append("# Relation Quality Report (Bước 10 roadmap)")
    L.append("")
    L.append("> Sinh bởi `knowledge_engineering/governance/relation_quality.py`. Read-only.")
    L.append(f"> Ngày: {date.today().isoformat()}. Tổng relation (sau dedup): {len(rels)}.")
    L.append("")
    L.append("## 1. Theo status")
    L.append("")
    L.append("| status | số |")
    L.append("|---|---|")
    for k, v in sorted(by_status.items()):
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 2. Theo source_type")
    L.append("")
    L.append("| source_type | số |")
    L.append("|---|---|")
    for k, v in sorted(by_source_type.items()):
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 3. Theo use_as")
    L.append("")
    L.append("| use_as | số |")
    L.append("|---|---|")
    for k, v in sorted(by_use_as.items()):
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## 4. Relation dùng FILTER (verified, cần deterministic)")
    L.append("")
    filters = [r for r in rels if r.use_as == "filter" and r.status == "verified"]
    if not filters:
        L.append("Không có.")
    else:
        L.append("| source | target | type | confidence | note |")
        L.append("|---|---|---|---|---|")
        for r in filters:
            L.append(f"| `{r.source}` | `{r.target}` | {r.type} | {r.confidence} | {r.evidence or r.note or ''} |")
        L.append("")
        L.append("> ⚠ Filter là lọc cứng — chỉ giữ khi quan hệ gần như tất định "
                 "(vd location -> setting địa lý). Nếu evaluator báo noise cho cạnh filter, "
                 "kiểm tra xem noise có phải artifact của golden set không trước khi hạ.")
    L.append("")
    L.append("## 5. Top candidate theo lift (duyệt trước)")
    L.append("")
    cand_sorted = sorted(candidates, key=lambda r: -(r.get("lift") or 0))
    if not cand_sorted:
        L.append("Không có candidate chờ duyệt.")
    else:
        L.append("| source | target | support | probability | lift | confidence |")
        L.append("|---|---|---|---|---|---|")
        for r in cand_sorted[:20]:
            L.append(f"| `{r['source']}` | `{r['target']}` | {r.get('support','')} | "
                     f"{r.get('probability','')} | {r.get('lift','')} | {r.get('confidence','')} |")
    L.append("")
    L.append("## 6. Relation đã reject")
    L.append("")
    rejected = [r for r in rels if r.status == "rejected"]
    if not rejected:
        L.append("Không có.")
    else:
        L.append("| source | target | reject_reason |")
        L.append("|---|---|---|")
        for r in rejected:
            L.append(f"| `{r.source}` | `{r.target}` | {r.reject_reason or ''} |")
    L.append("")
    L.append("## 7. Source/target không tồn tại trong ontology")
    L.append("")
    bad = [r for r in rels if r.source not in concept_ids or r.target not in concept_ids]
    if not bad:
        L.append("Không có (mọi source/target hợp lệ).")
    else:
        for r in bad:
            L.append(f"- `{r.source}` -> `{r.target}` ({r.origin})")
    L.append("")
    L.append("## 8. Concept phổ biến làm source nhiều cạnh verified")
    L.append("")
    popular = [(s, c) for s, c in src_fanout.most_common() if c > POPULAR_THRESHOLD]
    if not popular:
        L.append(f"Không có concept nào làm source > {POPULAR_THRESHOLD} cạnh verified "
                 "(graph chưa phình).")
    else:
        L.append("| source | số cạnh verified |")
        L.append("|---|---|")
        for s, c in popular:
            L.append(f"| `{s}` | {c} |")
        L.append("")
        L.append("> Concept fan-out cao dễ kéo expansion rộng -> soát xem có cạnh nào nên hạ use_as.")
    L.append("")
    return "\n".join(L)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(build(), encoding="utf-8")
    print(f"Đã ghi -> {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
