"""audit_relations.py — Bước 1 roadmap: AUDIT relation legacy + query_expansion hiện tại.

Read-only. Quét mọi cạnh `related/broader/narrower` trong ontology/core/*.yaml, parse
ontology/query_expansion.yaml, đối chiếu, đánh dấu cạnh nguy hiểm, và chụp BASELINE
(số concept khóa + số cạnh) để MVP 2 so sánh khi sinh candidate.

Sinh ra: docs/reports/ontology/relation_audit.md

Chạy:
    .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.audit_relations
"""

from __future__ import annotations

import glob
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CORE_GLOB = str(ROOT / "ontology/core/*.yaml")
EXPANSION_YAML = ROOT / "ontology/query_expansion.yaml"
LOCATION_SETTING_GEN = ROOT / "ontology/core/location_setting.generated.yaml"
NEAR_GEN = ROOT / "ontology/relations_near.generated.yaml"
OUT_MD = ROOT / "docs/reports/ontology/relation_audit.md"

# Facet quá rộng để làm source/target an toàn (cạnh dễ kéo nhiễu nếu dùng filter).
BROAD_CONCEPTS = {"OBJ_HOTEL"}
LEGACY_KEYS = ("related", "broader", "narrower")


def load_concepts() -> tuple[dict[str, str], dict[str, str]]:
    """Trả (facets: cid->facet, origin: cid->filename). Gồm cả file generated."""
    facets: dict[str, str] = {}
    origin: dict[str, str] = {}
    for f in sorted(glob.glob(CORE_GLOB)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            if isinstance(v, dict):
                facets[cid] = v.get("facet", "")
                origin.setdefault(cid, Path(f).name)
    return facets, origin


def collect_legacy_edges() -> list[dict]:
    """Mọi cạnh related/broader/narrower trong file core KHÔNG generated."""
    edges: list[dict] = []
    for f in sorted(glob.glob(CORE_GLOB)):
        if "generated" in Path(f).name:
            continue
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            if not isinstance(v, dict):
                continue
            for key in LEGACY_KEYS:
                r = v.get(key)
                if not r:
                    continue
                for tgt in (r if isinstance(r, list) else [r]):
                    if tgt != cid:
                        edges.append(
                            {"source": cid, "target": tgt, "key": key, "file": Path(f).name}
                        )
    return edges


def load_expansion() -> dict:
    if not EXPANSION_YAML.exists():
        return {}
    return yaml.safe_load(EXPANSION_YAML.read_text(encoding="utf-8")) or {}


def suggest_type(src_facet: str, tgt_facet: str, key: str) -> str:
    """Gợi ý relation `type` mới cho cạnh legacy dựa trên facet."""
    if key == "broader":
        return "broader"
    if key == "narrower":
        return "narrower"
    if src_facet == "location" and tgt_facet == "setting":
        return "implies"
    if src_facet == "purpose" and tgt_facet in {"amenity", "style"}:
        return "evidence_for"
    if src_facet == "amenity" and tgt_facet == "purpose":
        return "evidence_for"
    if src_facet == tgt_facet:
        return "similar_to"
    return "cooccurs_with"


def suggest_use_as(rel_type: str) -> str:
    return {
        "implies": "filter",
        "located_in": "filter",
        "supports_setting": "filter",
        "evidence_for": "boost",
        "broader": "boost",
        "narrower": "boost",
        "similar_to": "suggestion",
        "cooccurs_with": "suggestion",
    }.get(rel_type, "suggestion")


def flag_edge(edge: dict, facets: dict[str, str]) -> list[str]:
    """Đánh dấu cạnh nguy hiểm. Trả list flag (rỗng nếu sạch)."""
    flags: list[str] = []
    s, t = edge["source"], edge["target"]
    if t not in facets:
        flags.append("target_missing")
    if s in BROAD_CONCEPTS or t in BROAD_CONCEPTS:
        flags.append("too_broad")
    fs, ft = facets.get(s, ""), facets.get(t, "")
    if fs == "price_tier" and ft == "style":
        flags.append("price_to_style")
    if fs and fs == ft and edge["key"] == "related":
        flags.append("same_facet_unclear")
    return flags


def build_report() -> str:
    facets, origin = load_concepts()
    legacy = collect_legacy_edges()
    expansion = load_expansion()
    rules = expansion.get("rules", {}) or {}

    # --- BASELINE query_expansion ---
    n_keys = len(rules)
    n_edges = sum(len((r or {}).get("expands_to", []) or []) for r in rules.values())
    # nguồn từng cạnh expansion (ontology_relation vs cooccurrence)
    src_kind = Counter()
    for r in rules.values():
        for ev in (r or {}).get("evidence", {}).values():
            src_kind["cooccurrence" if str(ev).startswith("cooccurrence") else "ontology_relation"] += 1

    # set cạnh đang có trong query_expansion để đối chiếu legacy
    expansion_pairs: set[tuple[str, str]] = set()
    for s, r in rules.items():
        for t in (r or {}).get("expands_to", []) or []:
            expansion_pairs.add((s, t))

    # --- phân loại legacy edges ---
    by_facetpair = Counter()
    flagged: list[tuple[dict, list[str]]] = []
    rows: list[dict] = []
    for e in legacy:
        fs, ft = facets.get(e["source"], "?"), facets.get(e["target"], "?")
        by_facetpair[f"{fs} -> {ft}"] += 1
        flags = flag_edge(e, facets)
        if flags:
            flagged.append((e, flags))
        rel_type = suggest_type(fs, ft, e["key"])
        rows.append(
            {
                **e,
                "src_facet": fs,
                "tgt_facet": ft,
                "in_expansion": (e["source"], e["target"]) in expansion_pairs,
                "suggest_type": rel_type,
                "suggest_use_as": suggest_use_as(rel_type),
                "flags": flags,
            }
        )

    # cạnh có trong expansion nhưng KHÔNG phải từ legacy related (tức cooccurrence-sinh)
    legacy_pairs = {(e["source"], e["target"]) for e in legacy}
    cooc_only_pairs = sorted(expansion_pairs - legacy_pairs)

    # location.generated bị build_expansion skip
    loc_setting = yaml.safe_load(LOCATION_SETTING_GEN.read_text(encoding="utf-8")) or {}
    loc_setting_map = loc_setting.get("location_setting", {}) or {}
    near = yaml.safe_load(NEAR_GEN.read_text(encoding="utf-8")) or {}
    n_near = len(near.get("relations", []) or [])

    # --- render markdown ---
    L: list[str] = []
    L.append("# Relation Audit (Bước 1 roadmap)")
    L.append("")
    L.append(f"> Sinh tự động bởi `knowledge_engineering/governance/audit_relations.py`. Read-only.")
    L.append(f"> Ngày: {date.today().isoformat()}.")
    L.append("")
    L.append("## 0. Baseline (chụp để MVP 2 so sánh)")
    L.append("")
    L.append("| Chỉ số | Giá trị |")
    L.append("|---|---|")
    L.append(f"| Tổng concept ontology (gồm location) | {len(facets)} |")
    L.append(f"| Cạnh legacy `related/broader/narrower` | {len(legacy)} |")
    L.append(f"| Concept khóa trong `query_expansion.yaml` | {n_keys} |")
    L.append(f"| Tổng cạnh expansion (`expands_to`) | {n_edges} |")
    L.append(f"| └ từ `ontology_relation` | {src_kind['ontology_relation']} |")
    L.append(f"| └ từ `cooccurrence` | {src_kind['cooccurrence']} |")
    L.append(f"| Relation `near` (relations_near.generated) | {n_near} |")
    L.append(f"| Location có SETTING suy ra (location_setting.generated) | {len(loc_setting_map)} |")
    L.append("")
    L.append("## 1. Legacy edges theo cặp facet")
    L.append("")
    L.append("| Cặp facet (source -> target) | số cạnh |")
    L.append("|---|---|")
    for pair, c in sorted(by_facetpair.items(), key=lambda x: -x[1]):
        L.append(f"| `{pair}` | {c} |")
    L.append("")
    L.append("## 2. Cạnh nguy hiểm cần soát tay")
    L.append("")
    if not flagged:
        L.append("Không có cạnh nguy hiểm (không target thiếu / không quá rộng / không price->style).")
    else:
        L.append("| source | target | key | flags |")
        L.append("|---|---|---|---|")
        for e, flags in flagged:
            L.append(f"| `{e['source']}` | `{e['target']}` | {e['key']} | {', '.join(flags)} |")
    L.append("")
    L.append("## 3. Toàn bộ legacy edges + đề xuất type/use_as")
    L.append("")
    L.append("| source | target | facet→facet | key | trong expansion? | suggest type | suggest use_as |")
    L.append("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x["src_facet"], x["source"], x["target"])):
        L.append(
            f"| `{r['source']}` | `{r['target']}` | {r['src_facet']}→{r['tgt_facet']} | "
            f"{r['key']} | {'✅' if r['in_expansion'] else '—'} | "
            f"`{r['suggest_type']}` | `{r['suggest_use_as']}` |"
        )
    L.append("")
    L.append("## 4. Cạnh trong query_expansion KHÔNG từ legacy (cooccurrence-sinh)")
    L.append("")
    L.append("> Đây là cạnh data-driven `build_expansion.py` tự sinh. Khi migrate sang relation graph,")
    L.append("> các cạnh này nên thành `source_type: generated_lift`, vào `candidates.yaml`, KHÔNG verified ngay.")
    L.append("")
    if not cooc_only_pairs:
        L.append("Không có (mọi cạnh expansion đều khớp legacy).")
    else:
        L.append("| source | target |")
        L.append("|---|---|")
        for s, t in cooc_only_pairs:
            L.append(f"| `{s}` | `{t}` |")
    L.append("")
    L.append("## 5. Location relation bị bỏ khỏi query_expansion")
    L.append("")
    L.append("`build_expansion.py` skip mọi file `*generated*` ở nguồn 1, nên:")
    L.append("")
    L.append(f"- `location_setting.generated.yaml`: {len(loc_setting_map)} location có SETTING suy ra,")
    L.append("  KHÔNG vào `query_expansion.yaml`. Đây là ứng viên relation `LOC_* implies SETTING_*`")
    L.append("  (`source_type: generated_location`, `use_as: filter` sau khi QC).")
    L.append(f"- `relations_near.generated.yaml`: {n_near} cạnh `near` hotel→landmark, là quan hệ object-level")
    L.append("  (không phải concept→concept), giữ riêng cho ranking theo km — KHÔNG đưa vào expansion concept.")
    L.append("")
    L.append("## 6. Khuyến nghị migrate đầu tiên (vào curated.yaml)")
    L.append("")
    L.append("Ưu tiên cạnh có `suggest type` deterministic và facet rõ:")
    L.append("")
    first_migrate = [
        r for r in rows
        if not r["flags"] and r["suggest_type"] in {"implies", "evidence_for", "broader", "narrower"}
    ]
    L.append("| source | target | suggest type | suggest use_as |")
    L.append("|---|---|---|---|")
    for r in sorted(first_migrate, key=lambda x: (x["suggest_use_as"], x["source"])):
        L.append(f"| `{r['source']}` | `{r['target']}` | `{r['suggest_type']}` | `{r['suggest_use_as']}` |")
    L.append("")
    L.append(f"_Tổng cạnh đề xuất migrate đợt đầu: {len(first_migrate)}._")
    L.append("")
    return "\n".join(L)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = build_report()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(report, encoding="utf-8")
    print(f"Đã sinh audit -> {OUT_MD.relative_to(ROOT)}")
    # in baseline ngắn ra stdout
    for line in report.splitlines():
        if line.startswith("| ") and ("|" in line) and any(
            k in line for k in ("concept", "Cạnh", "expansion", "near", "Location", "SETTING")
        ):
            print("  " + line)


if __name__ == "__main__":
    main()
