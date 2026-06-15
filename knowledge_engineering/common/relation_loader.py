"""relation_loader.py — Bước 4 roadmap: đọc + validate + normalize relation graph.

Một nơi duy nhất để load relation từ MỌI nguồn về cùng schema:
  - ontology/relations/curated.yaml      (source_type giữ nguyên, thường 'curated')
  - ontology/relations/rejected.yaml     (status=rejected)
  - ontology/relations/candidates.yaml   (status=candidate)
  - ontology/core/*.yaml related/broader/narrower  (legacy -> source_type='legacy_related')

Validate sớm (fail loud): source/target tồn tại, enum hợp lệ, confidence 0-1,
use_as=filter chỉ cho verified, generated_* không được verified trực tiếp.

Dedup theo precedence: curated > rejected > candidates > legacy_related.

API:
    load_relations(status={"verified"}, use_as=None) -> list[Relation]

Chạy nhanh (in summary):
    .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.relation_loader
"""

from __future__ import annotations

import glob
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]
CORE_GLOB = str(ROOT / "ontology/core/*.yaml")
REL_DIR = ROOT / "ontology/relations"
CURATED = REL_DIR / "curated.yaml"
CANDIDATES = REL_DIR / "candidates.yaml"
REJECTED = REL_DIR / "rejected.yaml"

VALID_TYPE = {
    "implies", "evidence_for", "cooccurs_with", "broader", "narrower",
    "located_in", "near", "supports_setting", "supports_purpose",
    "similar_to", "conflicts_with", "avoid_with",
}
VALID_SOURCE_TYPE = {
    "curated", "legacy_related", "generated_lift", "generated_location",
    "generated_near", "llm_suggested",
}
VALID_USE_AS = {"filter", "boost", "suggestion", "explanation", "avoid"}
# pending/approved = từ vựng HÀNG ĐỢI candidate (giống luồng STYLE: pending->approved/rejected).
#   pending : chờ người duyệt.   approved : người đã duyệt, CHỜ apply (chưa vào curated).
# verified/deprecated = từ vựng GRAPH nội bộ (curated.yaml). apply dịch approved -> verified.
VALID_STATUS = {"pending", "approved", "candidate", "verified", "rejected", "deprecated"}
# status chưa dùng được cho query layer (chỉ verified mới được dùng).
NOT_LIVE_STATUS = {"pending", "approved", "candidate"}
GENERATED_SOURCE_TYPES = {"generated_lift", "generated_location", "generated_near", "llm_suggested"}

# precedence cao -> thấp khi cùng (source, target)
PRECEDENCE = ["curated", "rejected", "candidates", "legacy"]
LEGACY_KEYS = ("related", "broader", "narrower")


class RelationError(ValueError):
    """Relation vi phạm contract — fail sớm."""


@dataclass
class Relation:
    source: str
    target: str
    type: str
    source_type: str
    confidence: float
    use_as: str
    status: str
    origin: str  # nguồn file ('curated','candidates','rejected','legacy') để dedup
    support: int | None = None
    probability: float | None = None
    lift: float | None = None
    direction: str = "directed"
    evidence: str | None = None
    note: str | None = None
    reject_reason: str | None = None
    provenance: str | None = None  # 'tags' | 'profile' | 'tags+profile' (cho generated_lift)
    extra: dict = field(default_factory=dict)

    def key(self) -> tuple[str, str]:
        return (self.source, self.target)


def load_concept_ids() -> set[str]:
    ids: set[str] = set()
    for f in sorted(glob.glob(CORE_GLOB)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            if isinstance(v, dict):
                ids.add(cid)
    return ids


def _validate(rel: Relation, concept_ids: set[str]) -> None:
    if rel.source not in concept_ids:
        raise RelationError(f"source không tồn tại: {rel.source} ({rel.origin})")
    if rel.target not in concept_ids:
        raise RelationError(f"target không tồn tại: {rel.target} (từ {rel.source}, {rel.origin})")
    if rel.type not in VALID_TYPE:
        raise RelationError(f"type không hợp lệ: {rel.type} ({rel.source}->{rel.target})")
    if rel.source_type not in VALID_SOURCE_TYPE:
        raise RelationError(f"source_type không hợp lệ: {rel.source_type} ({rel.source}->{rel.target})")
    if rel.use_as not in VALID_USE_AS:
        raise RelationError(f"use_as không hợp lệ: {rel.use_as} ({rel.source}->{rel.target})")
    if rel.status not in VALID_STATUS:
        raise RelationError(f"status không hợp lệ: {rel.status} ({rel.source}->{rel.target})")
    if not (0.0 <= float(rel.confidence) <= 1.0):
        raise RelationError(f"confidence ngoài [0,1]: {rel.confidence} ({rel.source}->{rel.target})")
    # rule 3: use_as=filter chỉ cho verified
    if rel.use_as == "filter" and rel.status != "verified":
        raise RelationError(
            f"use_as=filter chỉ cho status=verified: {rel.source}->{rel.target} (status={rel.status})"
        )
    # rule 4: generated_* không được verified trực tiếp
    if rel.source_type in GENERATED_SOURCE_TYPES and rel.status == "verified":
        raise RelationError(
            f"source_type={rel.source_type} không được status=verified trực tiếp (phải qua candidate): "
            f"{rel.source}->{rel.target}"
        )
    # rule 5: rejected phải có reject_reason
    if rel.status == "rejected" and not rel.reject_reason:
        raise RelationError(f"status=rejected thiếu reject_reason: {rel.source}->{rel.target}")


def _row_to_relation(row: dict, origin: str, default_source_type: str) -> Relation:
    known = {
        "source", "target", "type", "source_type", "confidence", "use_as", "status",
        "support", "probability", "lift", "direction", "evidence", "note", "reject_reason",
        "provenance",
    }
    extra = {k: v for k, v in row.items() if k not in known}
    return Relation(
        source=row["source"],
        target=row["target"],
        type=row.get("type", "cooccurs_with"),
        source_type=row.get("source_type", default_source_type),
        confidence=float(row.get("confidence", 0.5)),
        use_as=row.get("use_as", "suggestion"),
        status=row.get("status", "candidate"),
        origin=origin,
        support=row.get("support"),
        probability=row.get("probability"),
        lift=row.get("lift"),
        direction=row.get("direction", "directed"),
        evidence=row.get("evidence"),
        note=row.get("note"),
        reject_reason=row.get("reject_reason"),
        provenance=row.get("provenance"),
        extra=extra,
    )


def _load_yaml_relations(path: Path, origin: str, default_source_type: str) -> list[Relation]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: list[Relation] = []
    for row in data.get("relations", []) or []:
        if not isinstance(row, dict) or "source" not in row or "target" not in row:
            raise RelationError(f"relation thiếu source/target trong {path.name}: {row!r}")
        out.append(_row_to_relation(row, origin, default_source_type))
    return out


def _load_legacy() -> list[Relation]:
    """related/broader/narrower trong core (không generated) -> Relation legacy."""
    out: list[Relation] = []
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
                rel_type = {"broader": "broader", "narrower": "narrower"}.get(key, "cooccurs_with")
                use_as = "boost" if key in ("broader", "narrower") else "suggestion"
                for tgt in (r if isinstance(r, list) else [r]):
                    if tgt == cid:
                        continue
                    out.append(
                        Relation(
                            source=cid, target=tgt, type=rel_type,
                            source_type="legacy_related", confidence=0.6,
                            use_as=use_as, status="candidate", origin="legacy",
                        )
                    )
    return out


def _dedup(relations: list[Relation]) -> list[Relation]:
    """Khi cùng (source,target), giữ relation từ origin có precedence cao nhất."""
    rank = {o: i for i, o in enumerate(PRECEDENCE)}
    best: dict[tuple[str, str], Relation] = {}
    for rel in relations:
        k = rel.key()
        cur = best.get(k)
        if cur is None or rank.get(rel.origin, 99) < rank.get(cur.origin, 99):
            best[k] = rel
    return list(best.values())


def load_all_relations(concept_ids: set[str] | None = None, validate: bool = True) -> list[Relation]:
    """Load + validate + dedup mọi relation. Trả list đã chuẩn hóa."""
    if concept_ids is None:
        concept_ids = load_concept_ids()
    raw: list[Relation] = []
    raw += _load_yaml_relations(CURATED, "curated", "curated")
    raw += _load_yaml_relations(REJECTED, "rejected", "generated_lift")
    raw += _load_yaml_relations(CANDIDATES, "candidates", "generated_lift")
    raw += _load_legacy()
    if validate:
        for rel in raw:
            _validate(rel, concept_ids)
    return _dedup(raw)


def load_relations(
    status: Iterable[str] | None = ("verified",),
    use_as: Iterable[str] | None = None,
    concept_ids: set[str] | None = None,
) -> list[Relation]:
    """Lọc relation theo status/use_as. Mặc định chỉ verified (dùng cho query layer)."""
    rels = load_all_relations(concept_ids=concept_ids)
    status_set = set(status) if status is not None else None
    use_set = set(use_as) if use_as is not None else None
    out = []
    for r in rels:
        if status_set is not None and r.status not in status_set:
            continue
        if use_set is not None and r.use_as not in use_set:
            continue
        out.append(r)
    return out


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rels = load_all_relations()
    by_status = Counter(r.status for r in rels)
    by_origin = Counter(r.origin for r in rels)
    by_use = Counter(r.use_as for r in rels)
    print(f"Tổng relation (sau dedup): {len(rels)}")
    print(f"  theo status: {dict(by_status)}")
    print(f"  theo origin: {dict(by_origin)}")
    print(f"  theo use_as: {dict(by_use)}")
    verified = load_relations(status={"verified"})
    print(f"  verified (query layer dùng): {len(verified)}")
    filters = load_relations(status={"verified"}, use_as={"filter"})
    print(f"  verified + filter: {len(filters)} -> {[(r.source, r.target) for r in filters]}")


if __name__ == "__main__":
    main()
