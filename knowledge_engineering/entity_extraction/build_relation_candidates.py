"""build_relation_candidates.py — Bước 5+6 roadmap.

TÁCH logic co-occurrence ra khỏi build_expansion.py: generator này sinh CANDIDATE relation
(chưa verified) từ corpus, ghi ra generated.cooccurrence.yaml + merge vào candidates.yaml.
KHÔNG ghi thẳng vào query_expansion.yaml (artifact) -> candidate phải qua người duyệt trước.

Ngưỡng PER-FACET theo mục 8.3 roadmap (nguồn chân lý duy nhất), KHÔNG ngưỡng phẳng.

Nguồn data = knowledge_objects.json (KHÔNG dùng hotel_tags.json nữa — file đó thiếu LMK/LOC/ASPECT/
price_tier và gần như không có style; knowledge_objects đầy đủ hơn). Hai loại tín hiệu, ghi provenance:
    --source=metadata   semantic_metadata (nhãn có/không, đã loại LMK/LOC)
    --source=profile    semantic_profile score>=0.6 (cảm nhận review — giàu style/aspect)
    --source=both       (MẶC ĐỊNH) gộp cả hai; cùng cặp xuất hiện ở cả hai -> provenance=metadata+profile

LMK_*/LOC_* bị loại: là quan hệ object-level (hotel gần landmark / ở location), không phải
concept<->concept; đi đường generated_near/generated_location riêng.

Chạy:
    .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_relation_candidates
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CORE_GLOB = str(ROOT / "ontology/core/*.yaml")
OBJECTS_JSON = ROOT / "knowledge_engineering/enrichment/knowledge_objects.json"
REL_DIR = ROOT / "ontology/relations"
OUT_GENERATED = REL_DIR / "generated.cooccurrence.yaml"
OUT_CANDIDATES = REL_DIR / "candidates.yaml"

PROFILE_MIN_SCORE = 0.6  # ngưỡng lấy concept từ semantic_profile
MAX_EDGES_PER_SOURCE = 5

# Concept prefix BỎ khỏi co-occurrence: LMK/LOC là quan hệ OBJECT-LEVEL (hotel gần landmark/ở
# location), KHÔNG phải quan hệ concept<->concept. Đi đường generated_near/generated_location riêng.
# (Bảng FACET_THRESHOLDS cũng đã không có cặp landmark/location, nhưng loại tường minh cho rõ ý đồ.)
SKIP_PREFIXES = ("LMK_", "LOC_")

# Candidate sinh ra ở trạng thái "pending" (chờ người duyệt), giống luồng STYLE.
DEFAULT_STATUS = "pending"

# Bảng ngưỡng per-facet — mục 8.3 roadmap. (support, probability, lift).
# None = cặp facet bị BLOCK (không sinh candidate). location->setting đi đường generated_location riêng.
FACET_THRESHOLDS: dict[tuple[str, str], dict | None] = {
    ("purpose", "amenity"): {"support": 5, "prob": 0.35, "lift": 1.3},
    ("object_type", "amenity"): {"support": 8, "prob": 0.35, "lift": 1.5},
    ("setting", "amenity"): {"support": 8, "prob": 0.35, "lift": 1.5},
    ("style", "amenity"): {"support": 3, "prob": 0.35, "lift": 1.3},
    ("style", "style"): {"support": 3, "prob": 0.35, "lift": 1.3},
    ("location", "setting"): None,    # dùng generated_location riêng
    ("price_tier", "style"): None,    # block, chỉ manual curated
}

BROAD_CONCEPTS = {"OBJ_HOTEL"}


def load_concept_facets() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted(glob.glob(CORE_GLOB)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            if isinstance(v, dict):
                out[cid] = v.get("facet", "")
    return out


def _keep(cid: str) -> bool:
    """Bỏ LMK/LOC (object-level) khỏi co-occurrence concept."""
    return isinstance(cid, str) and not cid.startswith(SKIP_PREFIXES)


def hotels_concepts_from_metadata() -> list[set[str]]:
    """Nhãn 'có/không' từ semantic_metadata (amenity/object_type/purpose/setting/style/price_tier).

    Đầy đủ hơn hotel_tags.json. Đã loại LMK/LOC.
    """
    objs = json.loads(OBJECTS_JSON.read_text(encoding="utf-8"))
    out: list[set[str]] = []
    for o in objs.values():
        s: set[str] = set()
        for facet_val in (o.get("semantic_metadata", {}) or {}).values():
            if isinstance(facet_val, list):
                s.update(x for x in facet_val if _keep(x))
            elif isinstance(facet_val, str) and _keep(facet_val):
                s.add(facet_val)
        out.append(s)
    return out


def hotels_concepts_from_profile() -> list[set[str]]:
    """CẢM NHẬN từ review: semantic_profile score>=0.6 (aspect/style/amenity...). Tín hiệu giàu nhất."""
    objs = json.loads(OBJECTS_JSON.read_text(encoding="utf-8"))
    out: list[set[str]] = []
    for o in objs.values():
        s = {cid for cid, info in (o.get("semantic_profile", {}) or {}).items()
             if isinstance(info, dict) and info.get("score", 0) >= PROFILE_MIN_SCORE and _keep(cid)}
        out.append(s)
    return out


def existing_pairs() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Trả (curated_pairs, rejected_pairs) để không đề xuất lại."""
    def pairs(path: Path) -> set[tuple[str, str]]:
        if not path.exists():
            return set()
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {(r["source"], r["target"]) for r in (d.get("relations") or []) if "source" in r}
    return pairs(REL_DIR / "curated.yaml"), pairs(REL_DIR / "rejected.yaml")


def mine(hotels: list[set[str]], facets: dict[str, str], provenance: str) -> list[dict]:
    """Đào cặp co-occurrence từ một nguồn. provenance = 'tags' | 'profile' (ghi vết nguồn)."""
    cnt: dict[str, int] = defaultdict(int)
    co: dict[tuple[str, str], int] = defaultdict(int)
    for concepts in hotels:
        for a in concepts:
            cnt[a] += 1
        for a in concepts:
            for b in concepts:
                if a != b:
                    co[(a, b)] += 1
    n_hotels = len(hotels)
    curated_pairs, rejected_pairs = existing_pairs()

    by_source: dict[str, list[dict]] = defaultdict(list)
    for (a, b), n_ab in co.items():
        if a in BROAD_CONCEPTS or b in BROAD_CONCEPTS:
            continue
        if (a, b) in curated_pairs or (a, b) in rejected_pairs:
            continue
        fa, fb = facets.get(a, ""), facets.get(b, "")
        th = FACET_THRESHOLDS.get((fa, fb), "BLOCK")
        if th is None or th == "BLOCK":
            continue  # cặp facet không có trong bảng -> block
        prob = n_ab / cnt[a]
        base = cnt[b] / n_hotels if n_hotels else 0
        lift = prob / base if base > 0 else 0
        if cnt[a] < th["support"] or prob < th["prob"] or lift < th["lift"]:
            continue
        by_source[a].append({
            "source": a, "target": b, "type": "cooccurs_with",
            "source_type": "generated_lift", "provenance": provenance,
            "support": cnt[a], "probability": round(prob, 2), "lift": round(lift, 2),
            "confidence": round(min(0.7, 0.3 + 0.1 * lift), 2),
            "use_as": "boost", "status": DEFAULT_STATUS,
            "created_by": "build_relation_candidates.py", "created_at": date.today().isoformat(),
        })
    # top theo lift, tối đa N cạnh/source
    out: list[dict] = []
    for a, edges in by_source.items():
        edges.sort(key=lambda x: -x["lift"])
        out.extend(edges[:MAX_EDGES_PER_SOURCE])
    out.sort(key=lambda x: (x["source"], -x["lift"]))
    return out


def merge_sources(*candidate_lists: list[dict]) -> list[dict]:
    """Gộp candidate từ nhiều nguồn. Cùng (source,target): giữ bản lift cao hơn, ghi provenance cả hai."""
    best: dict[tuple[str, str], dict] = {}
    for lst in candidate_lists:
        for c in lst:
            k = (c["source"], c["target"])
            cur = best.get(k)
            if cur is None:
                best[k] = dict(c)
            else:
                # gộp provenance, giữ chỉ số của bản lift cao hơn
                provs = {cur.get("provenance"), c.get("provenance")}
                keep = c if c["lift"] > cur["lift"] else cur
                merged = dict(keep)
                merged["provenance"] = "+".join(sorted(p for p in provs if p))
                best[k] = merged
    out = list(best.values())
    out.sort(key=lambda x: (x["source"], -x["lift"]))
    return out


def write_yaml(path: Path, relations: list[dict], header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(
            {"version": "1.0.0", "relations": relations},
            fh, allow_unicode=True, sort_keys=False,
        )


def merge_into_candidates(generated: list[dict]) -> int:
    """Merge generated candidate vào candidates.yaml.

    GIỮ NGUYÊN mọi relation người đã đụng vào (status approved/rejected) — không ghi đè quyết định.
    Chỉ làm mới phần pending. Cạnh generated mới mà người đã quyết (approved/rejected) hoặc đã
    duyệt sang curated/rejected file thì KHÔNG thêm lại.
    """
    existing = []
    if OUT_CANDIDATES.exists():
        d = yaml.safe_load(OUT_CANDIDATES.read_text(encoding="utf-8")) or {}
        existing = d.get("relations") or []
    # giữ relation người đã quyết (approved/rejected) — chờ apply hoặc đã ghi chú reject
    kept = [r for r in existing if r.get("status") in ("approved", "rejected")]
    kept_pairs = {(r["source"], r["target"]) for r in kept}
    merged = kept + [g for g in generated if (g["source"], g["target"]) not in kept_pairs]
    header = (
        "# candidates.yaml — Relation CHỜ DUYỆT (hàng đợi). Do build_relation_candidates.py sinh.\n"
        "# DUYỆT TAY (giống luồng STYLE): đổi `status: pending` -> `approved` hoặc `rejected`\n"
        "#   (rejected thì thêm dòng `reject_reason: \"...\"`), rồi chạy:\n"
        "#   python -m knowledge_engineering.entity_extraction.apply_relation_review\n"
        "# Relation đã approved/rejected được GIỮ NGUYÊN khi chạy lại generator (không ghi đè quyết định).\n"
    )
    write_yaml(OUT_CANDIDATES, merged, header)
    return len(merged)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["both", "metadata", "profile"], default="both",
                    help="both=gộp metadata+profile (mặc định); metadata=semantic_metadata; "
                         "profile=semantic_profile. Tất cả đọc từ knowledge_objects.json.")
    args = ap.parse_args()

    facets = load_concept_facets()
    parts = []
    if args.source in ("both", "metadata"):
        parts.append(mine(hotels_concepts_from_metadata(), facets, "metadata"))
    if args.source in ("both", "profile"):
        parts.append(mine(hotels_concepts_from_profile(), facets, "profile"))
    generated = merge_sources(*parts)

    header = (
        f"# AUTO-GENERATED bởi build_relation_candidates.py (--source={args.source}). "
        "Nguồn: knowledge_objects.json.\n"
        "# Ngưỡng per-facet mục 8.3 roadmap. provenance=metadata|profile|metadata+profile (cạnh từ nguồn nào).\n"
        "# LMK/LOC bị loại (object-level). Candidate THÔ — input cho candidates.yaml. KHÔNG verified.\n"
    )
    write_yaml(OUT_GENERATED, generated, header)
    n_cand = merge_into_candidates(generated)

    by_facet = Counter()
    by_prov = Counter()
    for g in generated:
        by_facet[f"{facets.get(g['source'],'?')}->{facets.get(g['target'],'?')}"] += 1
        by_prov[g.get("provenance", "?")] += 1
    print(f"Sinh {len(generated)} candidate (source={args.source})")
    print(f"  theo cặp facet: {dict(by_facet)}")
    print(f"  theo provenance: {dict(by_prov)}")
    print(f"  -> {OUT_GENERATED.relative_to(ROOT)}")
    print(f"  candidates.yaml giờ có {n_cand} relation")


if __name__ == "__main__":
    main()
