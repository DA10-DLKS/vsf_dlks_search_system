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
from knowledge_engineering.common.query_negation import negation_spans

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
    brand: str | None = None      # chuỗi KS user hỏi đích danh ("thuộc Vinpearl") -> filter
    range: dict[str, Any] = field(default_factory=dict)
    implicit: dict[str, str] = field(default_factory=dict)
    exclude_concepts: list[str] = field(default_factory=list)  # concept user KHÔNG muốn (negation)

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
            "brand": self.brand,
            "range": self.range,
            "implicit": self.implicit,
            "exclude_concepts": self.exclude_concepts,
        }


@lru_cache(maxsize=1)
def _load_synonyms(syn_yaml: str = SYN_YAML_DEFAULT) -> dict[str, list[str]]:
    return yaml.safe_load(open(syn_yaml, encoding="utf-8"))["synonyms"]


@lru_cache(maxsize=1)
def _max_gram(syn_yaml: str = SYN_YAML_DEFAULT) -> int:
    """Cửa sổ n-gram lớn nhất khi tra surface form (địa danh/landmark tên dài tới 8-10 từ)."""
    syn = _load_synonyms(syn_yaml)
    return max((len(k.split()) for k in syn), default=4)


def warmup(syn_yaml: str = SYN_YAML_DEFAULT) -> None:
    """V12: nạp sẵn synonym (YAML 177KB) vào lru_cache lúc startup. Nếu không, request ĐẦU của
    MỖI worker bị cold-start ~978ms (parse YAML + max_gram). Gọi 1 lần khi khởi động API."""
    _load_synonyms(syn_yaml)
    _max_gram(syn_yaml)


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


# Đơn vị tiền -> hệ số nhân (nghìn vs triệu). "k"/"nghìn" = 1e3, "tr"/"triệu" = 1e6.
_UNIT_MULT = {"k": 1_000, "nghìn": 1_000, "nghin": 1_000, "tr": 1_000_000, "triệu": 1_000_000}

# "1tr2" = 1 triệu 2 trăm nghìn = 1.200.000 (đơn vị NẰM GIỮA số). Chuẩn hóa "<N>tr<M>" -> "<N>.<M> triệu"
# để regex giá phía sau bắt thống nhất. M là phần trăm-nghìn (1 chữ số): "1tr2"->1.2 triệu, "2tr5"->2.5 triệu.
_TR_INFIX_RE = re.compile(r"(\d+)\s*tr\s*(\d)\b")


def _expand_tr_infix(ql: str) -> str:
    return _TR_INFIX_RE.sub(lambda m: f"{m.group(1)}.{m.group(2)} triệu", ql)


def _money_to_vnd(num: str, unit: str) -> int:
    """Chuỗi số + đơn vị -> VND. Xử lý 'Ntr M' kiểu '1tr2' = 1.200.000 (1 triệu 2 trăm nghìn):
    phần thập phân của 'triệu' tính theo trăm-nghìn ('1.2 triệu' và '1tr2' đều = 1_200_000).
    'k'/'nghìn' nhân thẳng. Trả int VND."""
    num = num.replace(",", ".")
    val = float(num) * _UNIT_MULT.get(unit, 1)
    return int(val)


# Range giá KÉP: "từ 800k đến 1tr2", "800 nghìn - 1.2 triệu". Đơn vị 2 vế có thể KHÁC nhau.
# Nếu vế đầu thiếu đơn vị thì mượn đơn vị vế sau ("1 đến 2 triệu" -> cả hai 'triệu').
_PRICE_RANGE_RE = re.compile(
    r"(?:từ|tầm|khoảng)?\s*([\d.,]+)\s*(triệu|tr|nghìn|nghin|k)?\s*"
    r"(?:đến|tới|-|–|~)\s*([\d.,]+)\s*(triệu|tr|nghìn|nghin|k)"
)


def parse_range(q: str) -> dict[str, Any]:
    """Bắt range filter phổ biến: giá (range kép/tầm/dưới X), superlative, điểm, sao. Port từ query_demo."""
    rf: dict[str, Any] = {}
    ql = _expand_tr_infix(q.lower())  # "1tr2" -> "1.2 triệu" trước khi match giá

    # Range KÉP trước (ưu tiên cao nhất): "800k đến 1tr2" -> price_min + price_max.
    mr = _PRICE_RANGE_RE.search(ql)
    if mr:
        lo_num, lo_unit, hi_num, hi_unit = mr.groups()
        lo_unit = lo_unit or hi_unit  # vế đầu thiếu đơn vị -> mượn vế sau
        rf["price_min"] = _money_to_vnd(lo_num, lo_unit)
        rf["price_max"] = _money_to_vnd(hi_num, hi_unit)

    # Superlative sort theo giá. Lưu vào range để không đổi chữ ký ParsedIntent.
    if re.search(r"rẻ nhất|giá rẻ nhất|rẻ nhất có thể", ql):
        rf["sort"] = "price_asc"
    elif re.search(r"đắt nhất|sang nhất|cao cấp nhất|xịn nhất", ql):
        rf["sort"] = "price_desc"

    if "price_min" in rf:  # range kép đã set -> bỏ qua các pattern đơn dưới đây
        return _parse_range_tail(ql, rf)

    m = re.search(r"(tầm|khoảng|tầm khoảng|cỡ|xấp xỉ)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        x = float(m.group(2).replace(",", ".")) * 1_000_000
        rf["price_min"] = int(x * 0.7)
        rf["price_max"] = int(x * 1.3)
    m = re.search(r"(dưới|<|không quá|tối đa)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        rf["price_max"] = int(float(m.group(2).replace(",", ".")) * 1_000_000)
        rf.pop("price_min", None)

    # "trên X triệu" — min price
    m = re.search(r"(trên|>|hơn|cao hơn)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m and "price_min" not in rf:
        rf["price_min"] = int(float(m.group(2).replace(",", ".")) * 1_000_000)
        rf.pop("price_max", None)

    # "không quá X nghìn/k" — giá rẻ dạng nghìn đồng
    m = re.search(r"(dưới|<|không quá|tối đa)\s*([\d.,]+)\s*(nghìn|nghin|k)\b", ql)
    if m and "price_max" not in rf:
        rf["price_max"] = int(float(m.group(2).replace(",", ".")) * 1_000)

    # "trên X nghìn/k" — min price dạng nghìn
    m = re.search(r"(trên|>|hơn|cao hơn)\s*([\d.,]+)\s*(nghìn|nghin|k)\b", ql)
    if m and "price_min" not in rf:
        rf["price_min"] = int(float(m.group(2).replace(",", ".")) * 1_000)
    return _parse_range_tail(ql, rf)


def _parse_range_tail(ql: str, rf: dict[str, Any]) -> dict[str, Any]:
    """Phần range KHÔNG phải giá (điểm review, số sao). Tách riêng để cả nhánh range-kép và
    nhánh giá-đơn dùng chung."""
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


def parse_brand(q: str) -> str | None:
    """Bắt brand (chuỗi KS) trong câu hỏi. Dùng CHUNG extract_brand với cleaning (1 nguồn bảng
    brand) -> query và data khớp cùng canonical. None nếu câu không nêu brand đã biết."""
    from ingestion.cleaning.brand_normalizer import extract_brand
    return extract_brand(q)


def parse_intent(q: str, syn_yaml: str = SYN_YAML_DEFAULT) -> ParsedIntent:
    """Câu hỏi VN -> ParsedIntent. Rule-based, dùng synonym_dictionary của KE."""
    syn = _load_synonyms(syn_yaml)
    found = _lookup_concepts(q, syn, _max_gram(syn_yaml))

    implicit = parse_implicit_intent(q)
    found.update(implicit)

    # Gia đình ĐÈ lãng mạn: câu có con nhỏ ("2 đứa nhỏ") thì "vợ chồng"/"hai người" KHÔNG còn là
    # tín hiệu romantic (đây là chuyến gia đình). Chỉ giữ ROMANTIC nếu có cue romantic MẠNH
    # (trăng mật/honeymoon/lãng mạn/hẹn hò) — tránh "2 vợ chồng + 2 con" bị gán nhầm romantic.
    if {"PURPOSE_FAMILY", "PURPOSE_ROMANTIC"} <= found:
        qf = normalize(q, fold=True)
        if not re.search(r"trang mat|honeymoon|lang man|hen ho|ky niem (ngay )?cuoi|nguoi yeu", qf):
            found.discard("PURPOSE_ROMANTIC")
            found.discard("STYLE_ROMANTIC")

    rng = parse_range(q)

    # Suppress PRICE_BUDGET khi "ngân sách/budget" đi kèm SỐ TIỀN (là khai báo ngân sách, không
    # phải phân khúc giá rẻ). Port từ query_demo.
    if "PRICE_BUDGET" in found and re.search(
        r"(budget|ngân sách|ngan sach)\D{0,6}[\d.,]+\s*(triệu|tr|trieu|k|nghìn|nghin|đồng|dong)",
        normalize(q, fold=True),
    ):
        found.discard("PRICE_BUDGET")

    # NEGATION: concept nằm trong vế phủ định ("không sát đường", "không có trẻ em") -> exclude.
    # lookup bind sẵn syn+max_gram (1 nguồn surface form). positive = concept ở câu ĐÃ BỎ span phủ
    # định (concept vừa muốn vừa-trong-span-phủ-định, vd "có hồ bơi nhưng không phải hồ bơi chung",
    # KHÔNG bị exclude). exclude bị gỡ khỏi found chính (found gom cả span phủ định trước đó).
    _mg = _max_gram(syn_yaml)
    spans = negation_spans(q)
    exclude: set[str] = set()
    if spans:
        q_wo_neg = q
        for s in spans:
            q_wo_neg = q_wo_neg.replace(s, " ")
        # positive = concept (surface + implicit) ở câu ĐÃ BỎ span phủ định.
        positive = _lookup_concepts(q_wo_neg, syn, _mg) | set(parse_implicit_intent(q_wo_neg))
        for s in spans:
            exclude |= _lookup_concepts(s, syn, _mg) | set(parse_implicit_intent(s))
        exclude -= positive
        found -= exclude

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
        exclude_concepts=sorted(exclude),
        city=parse_city(q),
        brand=parse_brand(q),
        range=rng,
        implicit=implicit,
    )
