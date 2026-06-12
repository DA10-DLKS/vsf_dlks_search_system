"""build_objects.py — Ghép tag + metadata thành knowledge_object HARD (Sprint 2, Bước 4).

Owner: Trương Anh Long (KE, DA10). Hợp nhất:
  - tag concept (Bước 2, ontology_mapper -> hotel_tags.json)
  - metadata map/reconcile (Bước 3, metadata_pipeline -> hotel_metadata.json)
-> knowledge_object phần HARD cho cả 520 hotel, theo CONTRACT ontology/metadata_schema.yaml
   + hình dạng docs/.../knowledge_object_SAMPLE.md.

PHẦN HARD: semantic_metadata (object_type/location/amenity/setting/purpose/price_tier),
range_filters, nearby_places, tags(provenance), provenance.
PHẦN SOFT (style/aspect + sentiment từ review) -> Bước 5, gắn sau.

Cardinality (facets.yaml): object_type/price_tier = one (1 id); amenity/setting/purpose = many (list).
Giá: cờ price_capped=true cho hotel giá min=5tr (cap, xem Bước 3) -> tầng search không lọc-giá cứng.

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
"""

from __future__ import annotations

import glob
import json
import re
from collections import defaultdict

import yaml

HOTELS_GLOB = "data/cleaned/hotel_*.json"
TAGS_JSON = "knowledge_engineering/enrichment/hotel_tags.json"
META_JSON = "knowledge_engineering/enrichment/hotel_metadata.json"
PROFILE_JSON = "knowledge_engineering/enrichment/hotel_profiles.json"  # Bước 5 SOFT
CORE_GLOB = "ontology/core/*.yaml"
OUT_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"

# Ngưỡng score để đưa SOFT concept (style) vào semantic_metadata (lọc/boost). Dưới ngưỡng =
# tín hiệu yếu, giữ trong semantic_profile nhưng không đẩy lên metadata lọc.
SOFT_STYLE_MIN_SCORE = 0.6

ONTOLOGY_VERSION = "concepts_v2.0.0"
PRICE_CAP_VND = 5_000_000  # giá min == cap này -> không tin (Bước 3)

# Facet cardinality (khớp ontology/facets.yaml)
ONE_FACETS = {"object_type", "location", "price_tier"}
MANY_FACETS = {"amenity", "setting", "purpose", "style", "aspect"}


LOC_YAML = "ontology/core/location.generated.yaml"
LOC_SETTING_YAML = "ontology/core/location_setting.generated.yaml"


def _location_text_forms(text: str | None) -> list[str]:
    if not text:
        return []
    raw = str(text).strip()
    if not raw:
        return []
    # Agoda sometimes stores city as "Tam Ky (Quang Nam)"; ontology label is "Tam Ky".
    without_parentheses = re.sub(r"\s*\([^)]*\)\s*", " ", raw).strip()
    out = [raw]
    if without_parentheses and without_parentheses != raw:
        out.append(without_parentheses)
    return out


def load_location_index() -> dict:
    """Build a lookup index from location labels/surface forms to LOC_* concept ids."""
    from knowledge_engineering.common.normalize import normalize

    concepts = yaml.safe_load(open(LOC_YAML, encoding="utf-8"))["concepts"]
    index: dict[str, list[str]] = defaultdict(list)

    def add(text: str | None, cid: str) -> None:
        for form in _location_text_forms(text):
            key = normalize(form, fold=True)
            if key and cid not in index[key]:
                index[key].append(cid)

    for cid, data in concepts.items():
        if not cid.startswith("LOC_") or data.get("facet") != "location":
            continue
        label = data.get("label") or {}
        add(label.get("vi"), cid)
        add(label.get("en"), cid)
        for forms in (data.get("surface_forms") or {}).values():
            for form in forms or []:
                add(form, cid)

    depth_cache: dict[str, int] = {}

    def depth(cid: str) -> int:
        if cid in depth_cache:
            return depth_cache[cid]
        parent = concepts.get(cid, {}).get("parent") or concepts.get(cid, {}).get("located_in")
        depth_cache[cid] = 1 + depth(parent) if parent in concepts else 0
        return depth_cache[cid]

    return {"concepts": concepts, "index": dict(index), "depth": depth}


def _is_descendant(cid: str, parent_hint: str | None, concepts: dict) -> bool:
    if not parent_hint:
        return False
    cur = cid
    while cur in concepts:
        parent = concepts[cur].get("parent") or concepts[cur].get("located_in")
        if parent == parent_hint:
            return True
        cur = parent
    return False


def _resolve_location_value(
    value: str | None,
    loc_index: dict,
    parent_hint: str | None = None,
    preferred_kinds: tuple[str, ...] = (),
) -> str | None:
    from knowledge_engineering.common.normalize import normalize

    concepts = loc_index["concepts"]
    index = loc_index["index"]
    depth = loc_index["depth"]
    candidates: list[str] = []
    for form in _location_text_forms(value):
        candidates.extend(index.get(normalize(form, fold=True), []))
    candidates = list(dict.fromkeys(candidates))
    if not candidates:
        return None

    def rank(cid: str) -> tuple[int, int, int]:
        data = concepts.get(cid, {})
        parent_ok = _is_descendant(cid, parent_hint, concepts)
        kind_ok = data.get("kind") in preferred_kinds if preferred_kinds else True
        return (1 if parent_ok else 0, 1 if kind_ok else 0, depth(cid))

    return max(candidates, key=rank)


def resolve_location_concept(location: dict | None, loc_index: dict) -> str | None:
    """Resolve structured hotel location to the most specific LOC_* concept id."""
    if not isinstance(location, dict):
        return None

    country_id = _resolve_location_value(location.get("country"), loc_index, preferred_kinds=("country",))
    province_id = _resolve_location_value(location.get("province"), loc_index, preferred_kinds=("place", "country"))
    city_id = _resolve_location_value(location.get("city"), loc_index, province_id, preferred_kinds=("place",))
    district_id = _resolve_location_value(location.get("district"), loc_index, city_id, preferred_kinds=("area",))
    area_id = _resolve_location_value(location.get("area"), loc_index, city_id, preferred_kinds=("area",))
    return area_id or district_id or city_id or province_id or country_id


def load_facets() -> dict[str, str]:
    out = {}
    for f in sorted(glob.glob(CORE_GLOB)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            out[cid] = v.get("facet", "")
    return out


def load_location_setting() -> dict[str, list[str]]:
    """city text (fold) -> [SETTING_*] từ 2 nguồn: location.related (override) +
    location_setting.generated (suy từ data hotel). Để gắn SETTING cho hotel theo location."""
    import os
    from knowledge_engineering.common.normalize import normalize
    loc = yaml.safe_load(open(LOC_YAML, encoding="utf-8"))["concepts"]
    # loc_id -> set(SETTING) từ related + từ file suy
    by_locid: dict[str, set] = defaultdict(set)
    for cid, v in loc.items():
        for r in (v.get("related") or []):
            if str(r).startswith("SETTING_"):
                by_locid[cid].add(r)
    if os.path.exists(LOC_SETTING_YAML):
        ls = yaml.safe_load(open(LOC_SETTING_YAML, encoding="utf-8")) or {}
        for lid, settings in (ls.get("location_setting") or {}).items():
            by_locid[lid].update(settings.keys())
    # map qua city text (label) -> setting
    out: dict[str, list[str]] = {}
    for cid, v in loc.items():
        if v.get("kind") == "place" and cid in by_locid:
            lab = (v.get("label") or {}).get("vi", "")
            if lab:
                out[normalize(lab, fold=True)] = sorted(by_locid[cid])
    return out


def split_by_facet(tags: list[dict], facets: dict[str, str]) -> dict[str, list[dict]]:
    """Gom tag theo facet (giữ confidence/sources/nature)."""
    by: dict[str, list[dict]] = defaultdict(list)
    for t in tags:
        fct = facets.get(t["concept"], "?")
        by[fct].append(t)
    return by


def build_semantic_metadata(by_facet: dict[str, list[dict]]) -> dict:
    """semantic_metadata: one-facet -> 1 concept_id (conf cao nhất); many -> list concept_id."""
    sm: dict = {}
    # object_type (one)
    obj = by_facet.get("object_type", [])
    sm["object_type"] = max(obj, key=lambda t: t["confidence"])["concept"] if obj else None
    # price_tier (one) — gắn ở build (từ metadata), xử lý riêng ngoài hàm này
    # many facets
    for fct in ("amenity", "setting", "purpose"):
        items = by_facet.get(fct, [])
        # sort theo confidence giảm, khử trùng concept
        seen, out = set(), []
        for t in sorted(items, key=lambda x: -x["confidence"]):
            if t["concept"] not in seen:
                seen.add(t["concept"])
                out.append(t["concept"])
        sm[fct] = out
    return sm


def build_object(hotel: dict, tags: list[dict], meta: dict, profile: dict,
                 facets: dict[str, str], loc_setting: dict[str, list[str]], loc_index: dict) -> dict:
    hid = hotel.get("hotel_id")
    negative_style_profile = profile.get("negative_style_profile", {}) or {}
    concept_profile = {
        c: v for c, v in profile.items()
        if c != "negative_style_profile" and isinstance(v, dict) and "score" in v
    }
    by_facet = split_by_facet(tags, facets)
    sm = build_semantic_metadata(by_facet)
    sm["location"] = resolve_location_concept(meta.get("location"), loc_index)

    # SETTING bổ sung TỪ LOCATION (suy từ data: hotel ở Nha Trang -> COASTAL...). Gộp với
    # setting đã có từ view_types (tag). Khử trùng. -> COASTAL/ISLAND/CITY_CENTER không còn "chết".
    from knowledge_engineering.common.normalize import normalize
    city = (meta.get("location") or {}).get("city") or ""
    extra_setting = loc_setting.get(normalize(city, fold=True), [])
    sm["setting"] = sorted(set(sm.get("setting", [])) | set(extra_setting))

    # price_tier (one) từ metadata reconcile (Bước 3), KHÔNG từ tag
    sm["price_tier"] = meta.get("price_tier")

    # SOFT (Bước 5): style đủ mạnh -> semantic_metadata.style (để lọc/boost);
    #                aspect -> luôn ở semantic_profile (điểm trải nghiệm, không lọc cứng).
    sm["style"] = sorted(
        c for c, v in concept_profile.items()
        if c.startswith("STYLE_") and v["score"] >= SOFT_STYLE_MIN_SCORE
    )

    # range_filters + cờ giá
    rf = dict(meta.get("range_filters", {}))
    price = rf.get("price_min_vnd")
    price_capped = price is not None and price >= PRICE_CAP_VND
    if price_capped:
        rf["price_capped"] = True  # giá min chạm cap 5tr -> không tin, tầng search đừng lọc cứng

    return {
        "id": f"acc_{hid}",
        "type": meta.get("type", "hotel"),
        "title": hotel.get("name"),
        "source": hotel.get("source", "agoda"),
        "ontology_version": ONTOLOGY_VERSION,
        "content": hotel.get("description_short") or hotel.get("description"),
        # semantic_metadata: concept_id theo facet (HARD; SOFT style/aspect để Bước 5)
        "semantic_metadata": sm,
        # tags: provenance từng nhãn (đủ schema.py: concept/confidence/sources)
        "tags": [
            {"concept": t["concept"], "confidence": t["confidence"], "sources": t["sources"]}
            for t in sorted(tags, key=lambda x: (-x["confidence"], x["concept"]))
        ],
        "range_filters": rf,
        "location": meta.get("location"),
        "nearby_places": meta.get("nearby_places", []),
        # semantic_profile (Bước 5): điểm SOFT trải nghiệm/cảm nhận từ review (score/evidence/source).
        # KHÔNG lọc cứng — dùng để rank/boost + giải thích. aspect ở đây, style cũng giữ đầy đủ.
        "semantic_profile": {
            c: {"score": v["score"], "evidence_count": v["evidence_count"], "source": v["source"]}
            for c, v in sorted(concept_profile.items(), key=lambda x: -x[1]["score"])
        },
        # Negative style tách riêng để query/UI biết khách sạn bị chê theo cảm nhận nào
        # (vd STYLE_QUIET negative = bị chê ồn). Không tạo STYLE_NOT_* trong ontology.
        "negative_style_profile": negative_style_profile,
        "provenance": {
            "source": hotel.get("source", "agoda"),
            "source_url": hotel.get("source_url"),
            "crawled_at": hotel.get("crawled_at"),
            "mapper_version": "mapper Tầng0+1 (B2) + metadata (B3) + profile seed (B5.2)",
            "price_note": "price_min capped at 5M (placeholder)" if price_capped else None,
        },
    }


def run() -> dict:
    facets = load_facets()
    tags_all = json.load(open(TAGS_JSON, encoding="utf-8"))
    meta_all = json.load(open(META_JSON, encoding="utf-8"))
    import os
    prof_all = json.load(open(PROFILE_JSON, encoding="utf-8")) if os.path.exists(PROFILE_JSON) else {}
    loc_setting = load_location_setting()
    loc_index = load_location_index()
    objects: dict[str, dict] = {}
    stats = {
        "n": 0,
        "price_capped": 0,
        "no_object_type": 0,
        "with_style": 0,
        "with_location": 0,
        "no_location": 0,
        "tier": defaultdict(int),
    }

    for f in sorted(glob.glob(HOTELS_GLOB)):
        hotel = json.load(open(f, encoding="utf-8"))
        key = f"acc_{hotel.get('hotel_id')}"
        obj = build_object(hotel, tags_all.get(key, []), meta_all.get(key, {}),
                           prof_all.get(key, {}), facets, loc_setting, loc_index)
        objects[key] = obj
        stats["n"] += 1
        if obj["semantic_metadata"].get("style"):
            stats["with_style"] += 1
        if obj["range_filters"].get("price_capped"):
            stats["price_capped"] += 1
        if obj["semantic_metadata"].get("object_type") is None:
            stats["no_object_type"] += 1
        if obj["semantic_metadata"].get("location"):
            stats["with_location"] += 1
        else:
            stats["no_location"] += 1
        stats["tier"][obj["semantic_metadata"].get("price_tier")] += 1

    json.dump(objects, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return stats


if __name__ == "__main__":
    s = run()
    print(f"Objects: {s['n']} -> {OUT_JSON}")
    print(f"location LOC_*: {s['with_location']} | missing: {s['no_location']}")
    print(f"price_capped (giá min=5tr, gắn cờ): {s['price_capped']}")
    print(f"thiếu object_type: {s['no_object_type']}")
    print(f"có style (SOFT từ profile): {s['with_style']}")
    print(f"price_tier: {dict(sorted(s['tier'].items(), key=lambda x: str(x[0])))}")
