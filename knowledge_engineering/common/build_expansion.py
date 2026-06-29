"""build_expansion.py — COMPILER: relation graph (verified) -> query_expansion.yaml.

Sau Bước 8 roadmap, file này KHÔNG còn tự tính co-occurrence. Việc đào co-occurrence đã
chuyển sang knowledge_engineering/entity_extraction/build_relation_candidates.py (sinh candidate,
chờ duyệt). build_expansion giờ chỉ COMPILE relation đã verified thành artifact cho query layer.

Nguồn: relation_loader.load_relations(status={"verified"})
  gồm: curated.yaml (đã duyệt) + cạnh legacy được giữ.
Output: ontology/query_expansion.yaml — backward-compatible:
  - expands_to: list target (code cũ đọc được)
  - evidence  : dict target -> "source_type/type/use_as" (đọc nhanh)
  - expansions: list typed {target, relation_type, source_type, use_as, weight, confidence, status}

KHÔNG sửa tay query_expansion.yaml để duyệt — sửa curated/rejected/candidates rồi chạy lại.

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.build_expansion
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

from knowledge_engineering.common.relation_loader import load_relations

ROOT = Path(__file__).resolve().parents[2]
OUT_YAML = ROOT / "ontology/query_expansion.yaml"

# weight gợi ý theo use_as (query layer có thể override)
USE_AS_WEIGHT = {"filter": 1.0, "boost": 0.8, "suggestion": 0.5, "explanation": 0.2}


def build() -> dict:
    """Compile relation verified thành rules cho query layer."""
    # chỉ lấy verified, và chỉ use_as ảnh hưởng retrieval (filter/boost/suggestion)
    rels = load_relations(status={"verified"}, use_as={"filter", "boost", "suggestion"})
    by_src: dict[str, list] = defaultdict(list)
    for r in rels:
        by_src[r.source].append(r)

    rules: dict[str, dict] = {}
    for src in sorted(by_src):
        edges = sorted(by_src[src], key=lambda r: (-r.confidence, r.target))
        expansions = []
        evidence = {}
        for r in edges:
            expansions.append({
                "target": r.target,
                "relation_type": r.type,
                "source_type": r.source_type,
                "use_as": r.use_as,
                "weight": USE_AS_WEIGHT.get(r.use_as, 0.5),
                "confidence": round(float(r.confidence), 2),
                "status": r.status,
            })
            evidence[r.target] = f"{r.source_type}/{r.type}/use_as={r.use_as}"
        rules[src] = {
            "expands_to": sorted({e["target"] for e in expansions}),
            "evidence": evidence,
            "status": "verified",
            "expansions": expansions,
        }
    return rules


def write() -> tuple[int, int]:
    rules = build()
    n_edges = sum(len(r["expands_to"]) for r in rules.values())
    header = (
        "# AUTO-GENERATED — KHÔNG sửa tay. COMPILER: "
        "knowledge_engineering/common/build_expansion.py\n"
        "# Nguồn: relation graph verified (ontology/relations/curated.yaml + legacy giữ lại).\n"
        "# Duyệt relation ở curated/candidates/rejected, KHÔNG sửa file này.\n"
        "# Backward-compatible: expands_to (cũ) + expansions typed (mới: relation_type/use_as/weight).\n"
    )
    with open(OUT_YAML, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(
            {"version": "4.0.0", "status": "compiled_from_relation_graph",
             "default_weight": 0.5, "rules": rules},
            fh, allow_unicode=True, sort_keys=False,
        )
    return len(rules), n_edges


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    n_rules, n_edges = write()
    print(f"Compiled {n_rules} concept khóa, {n_edges} cạnh expansion (verified) -> {OUT_YAML.name}")


if __name__ == "__main__":
    main()
