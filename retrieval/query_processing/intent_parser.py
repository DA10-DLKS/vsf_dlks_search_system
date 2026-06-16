"""intent_parser.py — Node 1: câu hỏi tiếng Việt -> intent có cấu trúc.

Tầng retrieval (Node 2 SQL filter, Node 3 concept lookup, Node 6 text retrieval) cần một
intent đã parse. Module này là phiên bản PRODUCTION của logic parse trong
knowledge_engineering/enrichment/query_demo.py (vốn là công cụ test tay) — TÁCH phần parse
thuần (không kéo theo loading knowledge_objects/search).

Nguồn concept DUY NHẤT: ontology/synonym_dictionary.yaml (sinh bởi build_synonym_index từ
core/*.yaml). KHÔNG tự build synonym riêng -> tránh lệch với tầng KE.

Trả ParsedIntent gồm:
  - concepts: tất cả concept_id parse được (sorted)
  - hard_concepts: AMEN_/SETTING_ (filter cứng)
  - feel_concepts: STYLE_/ASPECT_ (rerank, filter mềm)
  - object_types / purposes / price_tiers / landmarks / location_concepts: tách theo prefix
  - city: địa danh thô (text) cho SQL filter
  - range: {price_min, price_max, score_min, star_eq}
  - implicit: {concept_id: bằng-chứng} từ mô tả hoàn cảnh
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from knowledge_engineering.common.implicit_intent import parse_implicit_intent
from knowledge_engineering.common.normalize import normalize

SYN_YAML_DEFAULT = "ontology/synonym_dictionary.yaml"

# Thành phố hay gặp (cho SQL filter text). Đồng bộ với query_demo.parse_location_text.
_CITIES = [
    "đà nẵng", "nha trang", "hà nội", "hồ chí minh", "sài gòn", "phú quốc",
    "đà lạt", "hội an", "huế", "hạ long", "vũng tàu", "sầm sơn", "quy nhơn",
    "phan thiết", "sa pa", "ninh bình", "cát bà", "côn đảo",
]


@dataclass
class ParsedIntent:
    query: str
    concepts: list[str] = field(default_factory=list)
    hard_concepts: list[str] = field(default_factory=list)
    feel_concepts: list[str] = field(default_factory=list)
    object_types: list[str] = field(default_factory=list)
    purposes: list[str] = field(default_factory=list)
    price_tiers: list[str] = field(default_factory=list)
    landmarks: list[str] = field(default_factory=list)
    location_concepts: list[str] = field(default_factory=list)
    city: str | None = None
    range: dict[str, Any] = field(default_factory=dict)
    implicit: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "concepts": self.concepts,
            "hard_concepts": self.hard_concepts,
            "feel_concepts": self.feel_concepts,
            "object_types": self.object_types,
            "purposes": self.purposes,
            "price_tiers": self.price_tiers,
            "landmarks": self.landmarks,
            "location_concepts": self.location_concepts,
            "city": self.city,
            "range": self.range,
            "implicit": self.implicit,
        }


@lru_cache(maxsize=1)
def _load_synonyms(syn_yaml: str = SYN_YAML_DEFAULT) -> dict[str, list[str]]:
    return yaml.safe_load(open(syn_yaml, encoding="utf-8"))["synonyms"]


@lru_cache(maxsize=1)
def _max_gram(syn_yaml: str = SYN_YAML_DEFAULT) -> int:
    """Cửa sổ n-gram lớn nhất khi tra surface form (địa danh/landmark tên dài tới 8-10 từ)."""
    syn = _load_synonyms(syn_yaml)
    return max((len(k.split()) for k in syn), default=4)


def _lookup_concepts(q: str, syn: dict[str, list[str]], max_gram: int) -> set[str]:
    """Tra concept qua surface form, xử lý xung đột span LMK đè SETTING (port từ query_demo).

    "gần núi" -> SETTING_MOUNTAIN, nhưng nếu nằm trong "gần núi trường lệ" (LMK) thì là tên
    riêng -> bỏ setting. SETTING bị bỏ chỉ khi MỌI text (norm + fold) đều bị LMK phủ.
    """
    found: set[str] = set()
    setting_covered: set[str] | None = None
    for text in (normalize(q), normalize(q, fold=True)):
        toks = text.split()
        text_matches: list[tuple[str, int, int]] = []
        for n in range(max_gram, 0, -1):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                if len(gram) < 3:
                    continue
                if gram in syn:
                    cs = syn[gram]
                    found.update(cs)
                    for c in cs:
                        text_matches.append((c, i, i + n))
        lmk_spans = [(s, e) for c, s, e in text_matches if c.startswith("LMK_")]
        settings = {c for c, _, _ in text_matches if c.startswith("SETTING_")}
        covered = {
            c for c in settings
            if all(any(s < le and ls < e for ls, le in lmk_spans)
                   for cc, s, e in text_matches if cc == c)
        }
        setting_covered = covered if setting_covered is None else (setting_covered & covered)
    for c in setting_covered or set():
        found.discard(c)
    return found


def parse_range(q: str) -> dict[str, Any]:
    """Bắt range filter phổ biến: giá (tầm/dưới X triệu), điểm, sao. Port từ query_demo."""
    rf: dict[str, Any] = {}
    ql = q.lower()
    m = re.search(r"(tầm|khoảng|tầm khoảng|cỡ|xấp xỉ)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        x = float(m.group(2).replace(",", ".")) * 1_000_000
        rf["price_min"] = int(x * 0.7)
        rf["price_max"] = int(x * 1.3)
    m = re.search(r"(dưới|<|không quá|tối đa)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        rf["price_max"] = int(float(m.group(2).replace(",", ".")) * 1_000_000)
        rf.pop("price_min", None)
    # "không quá X nghìn/k" — giá rẻ dạng nghìn đồng
    m = re.search(r"(dưới|<|không quá|tối đa)\s*([\d.,]+)\s*(nghìn|nghin|k)\b", ql)
    if m and "price_max" not in rf:
        rf["price_max"] = int(float(m.group(2).replace(",", ".")) * 1_000)
    m = re.search(r"(trên|>|từ)\s*([\d.,]+)\s*điểm", ql)
    if m:
        rf["score_min"] = float(m.group(2).replace(",", "."))
    m = re.search(r"(\d)\s*sao", ql)
    if m:
        rf["star_eq"] = int(m.group(1))
    return rf


def parse_city(q: str) -> str | None:
    """Bắt địa danh thô (text) cho SQL filter. Port từ query_demo.parse_location_text."""
    ql = normalize(q, fold=True)
    ql_nospace = ql.replace(" ", "")
    for c in _CITIES:
        cf = normalize(c, fold=True)
        if cf in ql or cf.replace(" ", "") in ql_nospace:
            return c
    return None


def parse_intent(q: str, syn_yaml: str = SYN_YAML_DEFAULT) -> ParsedIntent:
    """Câu hỏi VN -> ParsedIntent. Rule-based, dùng synonym_dictionary của KE."""
    syn = _load_synonyms(syn_yaml)
    found = _lookup_concepts(q, syn, _max_gram(syn_yaml))

    implicit = parse_implicit_intent(q)
    found.update(implicit)

    rng = parse_range(q)

    # Suppress PRICE_BUDGET khi "ngân sách/budget" đi kèm SỐ TIỀN (là khai báo ngân sách, không
    # phải phân khúc giá rẻ). Port từ query_demo.
    if "PRICE_BUDGET" in found and re.search(
        r"(budget|ngân sách|ngan sach)\D{0,6}[\d.,]+\s*(triệu|tr|trieu|k|nghìn|nghin|đồng|dong)",
        normalize(q, fold=True),
    ):
        found.discard("PRICE_BUDGET")

    concepts = sorted(found)
    return ParsedIntent(
        query=q,
        concepts=concepts,
        hard_concepts=[c for c in concepts if c.startswith(("AMEN_", "SETTING_"))],
        feel_concepts=[c for c in concepts if c.startswith(("STYLE_", "ASPECT_"))],
        object_types=[c for c in concepts if c.startswith("OBJ_")],
        purposes=[c for c in concepts if c.startswith("PURPOSE_")],
        price_tiers=[c for c in concepts if c.startswith("PRICE_")],
        landmarks=[c for c in concepts if c.startswith("LMK_")],
        location_concepts=[c for c in concepts if c.startswith("LOC_")],
        city=parse_city(q),
        range=rng,
        implicit=implicit,
    )
