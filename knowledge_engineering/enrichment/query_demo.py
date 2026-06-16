"""query_demo.py — CÔNG CỤ TEST TAY (KHÔNG phải search engine production).

Mục đích: kiểm CHẤT LƯỢNG NHÃN HARD đã gắn ở Bước 4. Mô phỏng phần "filter theo concept +
range" mà tầng search (Anh Tài/Đạt) sẽ làm — KHÔNG có vector/BM25/ranking.

Luồng (giống tầng search sẽ làm):
  câu hỏi tiếng Việt
   -> normalize + tra synonym_dictionary  => tập concept + facet
   -> bắt range filter đơn giản (dưới X triệu / trên X điểm / N sao)
   -> lọc knowledge_objects.json theo concept (AND) + range + LOC_* hierarchy/fallback text
   -> in hotel khớp.

Chạy:  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.query_demo "câu hỏi"
"""

from __future__ import annotations

import json
import re
import sys

import yaml

from knowledge_engineering.common.implicit_intent import parse_implicit_intent
from knowledge_engineering.common.normalize import normalize

# PURPOSE -> amenity "minh chứng" cho mục đích đó. Khi suy ra PURPOSE (từ surface form HOẶC
# intent ngầm), hotel có các amenity này được ƯU TIÊN lên top (không lọc cứng — soft fact).
#
# Bước 11 roadmap: nguồn boost giờ là RELATION GRAPH verified (use_as=boost) thay vì hard-code.
# Fallback giữ bảng tĩnh nếu loader lỗi (query_demo là tool hay chạy, không được vỡ).
# Giai đoạn 1: CHỈ dùng use_as=boost (không filter bằng generated relation).
_PURPOSE_EVIDENCE_FALLBACK = {
    "PURPOSE_FAMILY": {"AMEN_KIDS_CLUB", "AMEN_KIDS_POOL", "AMEN_BABYSITTING"},
    "PURPOSE_ROMANTIC": {"AMEN_SEA_VIEW", "AMEN_PRIVATE_POOL", "STYLE_ROMANTIC"},
    "PURPOSE_BUSINESS": {"AMEN_MEETING_ROOM", "AMEN_WIFI"},
    "PURPOSE_WELLNESS": {"AMEN_SPA", "STYLE_QUIET"},
    "PURPOSE_GROUP": {"AMEN_KARAOKE", "AMEN_GAME_ROOM", "AMEN_MEETING_ROOM"},
}


def _load_boost_relations() -> dict[str, list]:
    """Load cạnh boost verified từ relation graph: {source: [Relation,...]}. Fallback nếu lỗi."""
    try:
        from knowledge_engineering.common.relation_loader import load_relations
        rels = load_relations(status={"verified"}, use_as={"boost"})
        out: dict[str, list] = {}
        for r in rels:
            out.setdefault(r.source, []).append(r)
        return out
    except Exception:
        return {}


_BOOST_RELATIONS = _load_boost_relations()


def _purpose_evidence() -> dict[str, set]:
    """PURPOSE_* -> set target từ relation graph (boost), fallback bảng tĩnh khi rỗng."""
    if not _BOOST_RELATIONS:
        return _PURPOSE_EVIDENCE_FALLBACK
    out: dict[str, set] = {}
    for src, rels in _BOOST_RELATIONS.items():
        if src.startswith("PURPOSE_"):
            out[src] = {r.target for r in rels}
    return out or _PURPOSE_EVIDENCE_FALLBACK


PURPOSE_EVIDENCE = _purpose_evidence()

OBJ_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"
SYN_YAML = "ontology/synonym_dictionary.yaml"
LOC_YAML = "ontology/core/location.generated.yaml"

_objs = json.load(open(OBJ_JSON, encoding="utf-8"))
_syn = yaml.safe_load(open(SYN_YAML, encoding="utf-8"))["synonyms"]
_loc_concepts = yaml.safe_load(open(LOC_YAML, encoding="utf-8"))["concepts"]

# Cửa sổ n-gram lớn nhất khi tra surface form. Nhiều địa danh/bảo tàng có TÊN DÀI
# ("khu vui chơi giải trí sun world hạ long" = 8 từ, "quần thể di tích..." = 10 từ).
# Nếu cố định max=4 thì 300+ surface form ≥5 từ KHÔNG BAO GIỜ khớp -> mất concept (vd
# LMK_*). Lấy theo key dài nhất thực tế trong dictionary để tự đúng khi dictionary lớn lên.
_MAX_GRAM = max((len(k.split()) for k in _syn), default=4)


# ---------------------------------------------------------------------------
# Parse câu hỏi -> concept + range + location
# ---------------------------------------------------------------------------
def parse_concepts(q: str) -> tuple[list[str], dict[str, str]]:
    """Suy concept từ câu bằng HAI cơ chế bổ sung nhau:

      1. LOOKUP surface form: tra mọi cụm con (1-4 từ) qua synonym_dictionary. Bắt cách nói
         CỐ ĐỊNH ("gia đình", "ven biển"...).
      2. PATTERN intent ngầm (implicit_intent): bắt MÔ TẢ HOÀN CẢNH có biến số mà lookup không
         kham nổi ("nhà tôi có 2 con" -> PURPOSE_FAMILY).

    Trả (sorted concept_ids, {concept_id: bằng-chứng}) — bằng chứng chỉ có cho concept từ
    cơ chế 2 (để in ra giải thích "vì sao gán"); concept từ lookup không cần bằng chứng.
    """
    norm = normalize(q)
    normf = normalize(q, fold=True)
    found: set[str] = set()
    # Thu THÊM span (vị trí token) của mỗi match để xử lý xung đột "tên riêng đè thuộc tính chung":
    # cụm "gần núi" sinh SETTING_MOUNTAIN nhưng nếu nó NẰM TRONG cụm "gần núi trường lệ" (= LMK),
    # thì người dùng đang nói TÊN RIÊNG, không phải setting -> bỏ setting. So span theo token-index
    # TRONG CÙNG một text (norm vs fold tách token khác nhau, không so chéo được).
    # Một SETTING_* CHỈ bị bỏ nếu trong MỌI text nó xuất hiện đều bị một LMK_* phủ (giữ khi có
    # cách hiểu setting độc lập ở đâu đó). Gom theo từng text rồi giao kết quả.
    setting_covered: set[str] | None = None    # giao dần: setting bị phủ ở mọi text đã xét
    for text in (norm, normf):
        toks = text.split()
        text_matches: list[tuple[str, int, int]] = []   # (concept, start_tok, end_tok)
        for n in range(_MAX_GRAM, 0, -1):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                if len(gram) < 3:
                    continue
                if gram in _syn:
                    cs = _syn[gram]
                    found.update(cs)
                    for c in cs:
                        text_matches.append((c, i, i + n))
        # XUNG ĐỘT SPAN (cùng text): SETTING_* coi như "bị phủ" nếu MỌI lần nó khớp đều GIAO span một
        # LMK_*. Tín hiệu là token địa hình ("núi") bị DÙNG CHUNG: "gần núi"[5:7] giao "núi trường
        # lệ"[6:8] ở token "núi" -> đó là tên riêng landmark, không phải setting -> bỏ setting. Dùng
        # GIAO (không đòi lồng kín) vì giới từ "gần/view" của setting luôn lòi ra ngoài span LMK.
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
    implicit = parse_implicit_intent(q)
    found.update(implicit)
    # NGỮ CẢNH "ngân sách": "budget/ngân sách" + một SỐ TIỀN ("budget 10 triệu") là khai báo
    # NGÂN SÁCH (-> range filter), KHÔNG phải phân khúc giá rẻ. Surface "budget" (en) khớp
    # PRICE_BUDGET ở bước lookup -> suppress khi đi kèm số tiền. Giữ "budget hotel" (không số) là
    # giá rẻ như cũ. parse_range lo phần range; ở đây chỉ gỡ concept hiểu sai.
    if "PRICE_BUDGET" in found and re.search(
        r"(budget|ngân sách|ngan sach)\D{0,6}[\d.,]+\s*(triệu|tr|trieu|k|nghìn|nghin|đồng|dong)",
        normalize(q, fold=True),
    ):
        found.discard("PRICE_BUDGET")
    return sorted(found), implicit


def parse_range(q: str) -> dict:
    """Bắt vài range filter phổ biến từ câu (giá triệu / điểm / sao)."""
    rf: dict = {}
    ql = q.lower()
    # tầm/khoảng X triệu -> dải quanh X (±30%)
    m = re.search(r"(tầm|khoảng|tầm khoảng|cỡ|xấp xỉ)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        x = float(m.group(2).replace(",", ".")) * 1_000_000
        rf["price_min"] = int(x * 0.7)
        rf["price_max"] = int(x * 1.3)
    # dưới X triệu / tối đa
    m = re.search(r"(dưới|<|không quá|tối đa)\s*([\d.,]+)\s*(triệu|tr)", ql)
    if m:
        rf["price_max"] = int(float(m.group(2).replace(",", ".")) * 1_000_000)
        rf.pop("price_min", None)  # "dưới X" thì không có sàn
    # trên X điểm
    m = re.search(r"(trên|>|từ)\s*([\d.,]+)\s*điểm", ql)
    if m:
        rf["score_min"] = float(m.group(2).replace(",", "."))
    # N sao
    m = re.search(r"(\d)\s*sao", ql)
    if m:
        rf["star_eq"] = int(m.group(1))
    return rf


def parse_location_text(q: str) -> str | None:
    """Bắt địa danh thô (dùng để lọc theo text city/area — đơn giản, không qua LOC concept)."""
    # các thành phố hay gặp; mở rộng tùy ý
    cities = ["đà nẵng", "nha trang", "hà nội", "hồ chí minh", "sài gòn", "phú quốc",
              "đà lạt", "hội an", "huế", "hạ long", "vũng tàu", "sầm sơn", "quy nhơn",
              "phan thiết", "sa pa", "ninh bình", "cát bà", "côn đảo"]
    ql = normalize(q, fold=True)
    ql_nospace = ql.replace(" ", "")          # bắt cả dạng gõ liền: "danang", "nhatrang", "phuquoc"
    for c in cities:
        cf = normalize(c, fold=True)
        if cf in ql or cf.replace(" ", "") in ql_nospace:
            return c
    return None


# ---------------------------------------------------------------------------
# Lọc object
# ---------------------------------------------------------------------------
def _all_concepts(obj: dict) -> set[str]:
    sm = obj["semantic_metadata"]
    out: set[str] = set()
    for k, v in sm.items():
        if v is None:
            continue
        out.update(v if isinstance(v, list) else [v])
    return out


def _location_parent(cid: str | None) -> str | None:
    if not cid:
        return None
    data = _loc_concepts.get(cid) or {}
    return data.get("parent") or data.get("located_in")


def _is_same_or_child_location(child: str | None, parent: str) -> bool:
    cur = child
    while cur:
        if cur == parent:
            return True
        cur = _location_parent(cur)
    return False


def _prune_location_concepts(concepts: list[str]) -> list[str]:
    """If both a city and its area are parsed, keep the more specific area."""
    locs = [c for c in concepts if c.startswith("LOC_") and c in _loc_concepts]
    return [
        c for c in locs
        if not any(other != c and _is_same_or_child_location(other, c) for other in locs)
    ]


def _matches_location_concepts(obj: dict, wanted: list[str]) -> bool:
    if not wanted:
        return True
    obj_loc = (obj.get("semantic_metadata") or {}).get("location")
    return any(_is_same_or_child_location(obj_loc, loc) for loc in wanted)


# Tập concept THỰC SỰ có mặt trên ít nhất 1 hotel trong corpus. Dùng để bỏ qua các hard
# concept "chết" khi lọc: vd SETTING_COASTAL/SETTING_CITY_CENTER/SETTING_ISLAND hiện 0 hotel
# (Bước 4 chưa suy ra setting) -> nếu một surface form ("ven biển") kéo theo concept rỗng đó
# rồi đưa vào AND lọc cứng thì LUÔN ra 0 kết quả GIẢ. Cùng tinh thần "giá fake -> không lọc
# cứng". Khi Bước 4 gắn được setting, concept tự "sống" lại, không cần sửa code.
_LIVE_CONCEPTS: set[str] = set()
for _o in _objs.values():
    _LIVE_CONCEPTS |= _all_concepts(_o)

FEEL_MIN = 0.6  # hotel phải đạt profile score >= ngưỡng cho concept cảm nhận mới tính "khớp"
# Negative style không lọc cứng để tránh loại hotel mixed-signal; chỉ trừ ranking.
NEG_STYLE_PENALTY_WEIGHT = 0.5

# Tập concept CẢM NHẬN có ít nhất 1 hotel đạt ngưỡng FEEL_MIN. Nhiều STYLE_* (LUXURY,
# ROMANTIC, MODERN...) chưa hotel nào đạt -> nếu đưa vào lọc feel thì LUÔN 0 kết quả giả
# (giống _LIVE_CONCEPTS cho hard). Concept feel "chết" -> không lọc, chỉ để ranking
# (score() đã cộng feel_score nên hotel điểm thấp tự xuống cuối).
_LIVE_FEEL: set[str] = set()
for _o in _objs.values():
    for _c, _v in (_o.get("semantic_profile") or {}).items():
        if (_v or {}).get("score", 0) >= FEEL_MIN:
            _LIVE_FEEL.add(_c)


def _feel_scores(obj: dict, concepts: list[str]) -> tuple[float, float, float]:
    """(positive, negative_penalty, adjusted) cho concept cảm nhận trong query."""
    prof = obj.get("semantic_profile", {})
    neg_prof = obj.get("negative_style_profile", {})
    positive = sum(prof.get(c, {}).get("score", 0) for c in concepts)
    negative = sum(
        neg_prof.get(c, {}).get("negative_score", 0)
        for c in concepts
        if c.startswith("STYLE_")
    )
    adjusted = positive - NEG_STYLE_PENALTY_WEIGHT * negative
    return positive, negative, adjusted


def search(q: str, limit: int = 15) -> dict:
    concepts, implicit = parse_concepts(q)
    rng = parse_range(q)
    loc = parse_location_text(q)
    loc_concepts = _prune_location_concepts(concepts)
    # Phân loại concept giống tầng search thật:
    #   - HARD filter (AND bắt buộc): amenity + setting. Đây là "có/không" rõ ràng.
    #   - NỚI LỎNG (không lọc cứng): object_type ("khách sạn"=mọi lưu trú, xem golden Q1-01),
    #     purpose/style (cảm tính), price_tier (đã có range giá lo). Location dùng LOC_* hierarchy
    #     nếu synonym bắt được, fallback text chỉ để demo không kẹt khi thiếu alias.
    hard_all = [c for c in concepts if c.startswith(("AMEN_", "SETTING_"))]
    # Bỏ qua hard concept "chết" (0 hotel) khỏi AND -> tránh 0-kết-quả-giả (xem _LIVE_CONCEPTS).
    hard = [c for c in hard_all if c in _LIVE_CONCEPTS]
    hard_skipped = [c for c in hard_all if c not in _LIVE_CONCEPTS]
    soft = [c for c in concepts if c.startswith(("PURPOSE_", "OBJ_", "PRICE_"))]
    # CẢM NHẬN từ review (Bước 5 profile): style/aspect -> lọc theo semantic_profile score.
    feel_all = [c for c in concepts if c.startswith(("STYLE_", "ASPECT_"))]
    # Bỏ qua feel concept "chết" (0 hotel đạt ngưỡng) khỏi lọc -> tránh 0-kết-quả-giả; vẫn
    # góp vào ranking (xem _LIVE_FEEL). vd STYLE_LUXURY/STYLE_ROMANTIC chưa hotel nào đạt.
    feel = [c for c in feel_all if c in _LIVE_FEEL]
    feel_skipped = [c for c in feel_all if c not in _LIVE_FEEL]
    # ĐỊA DANH GẦN (LMK_*): SOFT — không lọc cứng (landmark chỉ ở vài hotel; lọc cứng dễ ra
    # "0 kết quả giả", cùng tinh thần giá/setting). Hotel khớp được ưu tiên lên top, gần hơn (km
    # nhỏ) xếp trên. Object mang LMK ở semantic_metadata.nearby_landmark + km ở nearby_landmarks.
    lmk = [c for c in concepts if c.startswith("LMK_")]

    hits = []
    for obj in _objs.values():
        oc = _all_concepts(obj)
        prof = obj.get("semantic_profile", {})
        # AND mọi concept HARD (amenity/setting)
        if not all(c in oc for c in hard):
            continue
        # CẢM NHẬN: hotel phải có profile score đủ cao cho MỌI concept feel yêu cầu
        if not all((prof.get(c, {}).get("score", 0) >= FEEL_MIN) for c in feel):
            continue
        # object_type: nếu câu nói loại hình cụ thể (resort/villa...) thì lọc, trừ OBJ_HOTEL (hiểu rộng).
        # NHƯNG nếu câu có CẢ OBJ_HOTEL ("khách sạn") lẫn loại cụ thể -> người dùng nói "khách sạn HOẶC
        # resort" = MỞ RỘNG (chấp nhận mọi lưu trú), KHÔNG lọc cứng. Chỉ lọc khi câu CHỈ nêu loại cụ thể.
        want_obj = [c for c in soft if c.startswith("OBJ_") and c != "OBJ_HOTEL"]
        if want_obj and "OBJ_HOTEL" not in concepts and oc.isdisjoint(want_obj):
            continue
        # location concept: LOC city/place matches its area descendants; text is fallback only.
        if loc_concepts:
            if not _matches_location_concepts(obj, loc_concepts):
                continue
        elif loc:
            locblob = " ".join(
                str(obj["location"].get(k) or "") for k in ("city", "area", "province", "district")
            )
            if normalize(loc, fold=True) not in normalize(locblob, fold=True):
                continue
        rf = obj["range_filters"]
        # GIÁ: toàn bộ giá là placeholder (fake) -> KHÔNG loại cứng theo giá (tránh "0 kết quả"
        # giả). Chỉ dùng để SORT ưu tiên (xem score()). star/score thì lọc thật.
        if "score_min" in rng and (rf.get("review_score") or 0) < rng["score_min"]:
            continue
        if "star_eq" in rng and rf.get("star_rating") != rng["star_eq"]:
            continue
        hits.append(obj)

    # PURPOSE (vd PURPOSE_FAMILY) là SOFT -> KHÔNG lọc, chỉ ƯU TIÊN ranking: hotel có amenity
    # minh chứng cho mục đích đó (kids club/babysitting cho family...) được đẩy lên top.
    purposes = [c for c in concepts if c.startswith("PURPOSE_")]
    purpose_amen = set()
    for p in purposes:
        purpose_amen |= PURPOSE_EVIDENCE.get(p, set())

    # EXPANSION TRACE (Bước 11/8.6 roadmap): cạnh boost relation graph áp cho concept trong câu.
    # Chỉ giải thích/debug — không lọc cứng. Mọi concept parse được, không chỉ purpose.
    expansion_trace = []
    for c in concepts:
        for r in _BOOST_RELATIONS.get(c, []):
            expansion_trace.append(
                f"{r.source} -> {r.target} [{r.source_type}/{r.type}/use_as={r.use_as}/conf={r.confidence}]"
            )

    # sort: ưu tiên hotel khớp nhiều concept SOFT + có amenity minh chứng PURPOSE; nếu câu có
    #       mức giá -> ưu tiên hotel giá GẦN mức đó (dù giá fake, vẫn là proxy); rồi review_score.
    target_price = rng.get("price_max") or rng.get("price_min")

    def lmk_match(o: dict):
        """Trả (số LMK yêu cầu khớp, km tới LMK gần nhất trong số khớp)."""
        if not lmk:
            return 0, 10**12
        want = set(lmk)
        dists = [x.get("distance_km") for x in o.get("nearby_landmarks", [])
                 if x.get("concept") in want and x.get("distance_km") is not None]
        n_hit = sum(1 for x in o.get("nearby_landmarks", []) if x.get("concept") in want)
        return n_hit, (min(dists) if dists else 10**12)

    def score(o: dict):
        oc = _all_concepts(o)
        soft_hit = sum(1 for c in soft if c in oc)
        # ĐỊA DANH: hotel khớp nhiều LMK yêu cầu lên trước; trong cùng mức, gần (km nhỏ) lên trước.
        lmk_hit, lmk_km = lmk_match(o)
        purpose_hit = len(purpose_amen & oc)  # số amenity khớp mục đích chuyến đi
        # Tổng điểm cảm nhận (kể cả feel skip), đã trừ nhẹ negative_style_profile để hotel bị chê
        # cùng STYLE (vd "không yên tĩnh") tụt hạng thay vì bị loại cứng.
        _, _, feel_score = _feel_scores(o, feel_all)
        rf = o["range_filters"]
        p = rf.get("price_min_vnd")
        if target_price and p and not rf.get("price_capped"):
            price_gap = abs(p - target_price)
        else:
            price_gap = 10**12
        # LMK đứng ĐẦU khóa sort khi câu nêu địa danh: khớp nhiều LMK + gần hơn lên top.
        return (-lmk_hit, lmk_km, -soft_hit, -purpose_hit, -feel_score, price_gap,
                -(rf.get("review_score") or 0))
    hits.sort(key=score)
    return {"concepts": concepts, "implicit": implicit, "hard": hard, "soft": soft, "feel": feel,
            "hard_skipped": hard_skipped, "feel_skipped": feel_skipped,
            "loc_concepts": loc_concepts, "lmk": lmk,
            "purpose_amen": sorted(purpose_amen), "expansion_trace": expansion_trace,
            "range": rng, "location": loc, "n": len(hits), "hits": hits[:limit]}


# ---------------------------------------------------------------------------
# Intent "tìm ĐỊA ĐIỂM" (không phải tìm hotel) — trả lời từ nearby_places
# ---------------------------------------------------------------------------
HOTEL_INTENT_KW = ["khách sạn", "khach san", "hotel", "resort", "villa", "homestay",
                   "nơi lưu trú", "noi luu tru", "chỗ ở", "cho o"]
PLACE_INTENT_KW = ["khu vui chơi", "vui chơi", "chơi gì", "tham quan", "địa điểm",
                   "điểm đến", "giải trí", "đi đâu", "có gì chơi", "thắng cảnh"]
# loại nearby (category) coi là "vui chơi/giải trí"
FUN_CATEGORIES = ["giải trí", "công viên", "vui chơi", "thể thao", "bãi biển",
                  "vườn", "thú", "cắm trại", "chợ"]


def is_place_intent(q: str) -> bool:
    ql = normalize(q, fold=True)
    return any(normalize(k, fold=True) in ql for k in PLACE_INTENT_KW)


def is_hotel_intent(q: str) -> bool:
    ql = normalize(q, fold=True)
    return any(normalize(k, fold=True) in ql for k in HOTEL_INTENT_KW)


def search_places(q: str, limit: int = 20) -> list[tuple]:
    """Gom nearby_places (loại vui chơi/giải trí) của hotel trong location -> địa điểm + tần suất."""
    loc = parse_location_text(q)
    loc_concepts = _prune_location_concepts(parse_concepts(q)[0])
    from collections import Counter
    seen: dict[str, dict] = {}
    freq: Counter = Counter()
    for obj in _objs.values():
        if loc_concepts:
            if not _matches_location_concepts(obj, loc_concepts):
                continue
        elif loc:
            blob = " ".join(str(obj["location"].get(k) or "") for k in ("city", "area", "province"))
            if normalize(loc, fold=True) not in normalize(blob, fold=True):
                continue
        for p in obj["nearby_places"]:
            nm, cat = p.get("name"), (p.get("category") or "")
            if not nm:
                continue
            if any(normalize(fc, fold=True) in normalize(cat, fold=True) for fc in FUN_CATEGORIES):
                freq[nm] += 1
                seen[nm] = {"name": nm, "category": cat}
    return [(seen[nm], n) for nm, n in freq.most_common(limit)]


def show(q: str) -> None:
    # nếu hỏi ĐỊA ĐIỂM -> trả địa điểm, không phải hotel
    if is_place_intent(q) and not is_hotel_intent(q):
        loc = parse_location_text(q)
        loc_concepts = _prune_location_concepts(parse_concepts(q)[0])
        places = search_places(q)
        print(f"\n❓ {q}")
        loc_label = loc_concepts or loc or "—"
        print(f"   → intent: TÌM ĐỊA ĐIỂM (không phải hotel) | location: {loc_label}")
        print(f"   → {len(places)} địa điểm vui chơi/giải trí (từ nearby_places của hotel quanh đó):")
        for pl, n in places:
            print(f"      • {pl['name'][:46]:46s} | {pl['category']}  (gần {n} hotel)")
        return

    r = search(q)
    print(f"\n❓ {q}")
    print(f"   → concept hiểu được: {r['concepts']}")
    if r["implicit"]:
        impl = ", ".join(f"{cid} (từ '{ev}')" for cid, ev in r["implicit"].items())
        print(f"   → intent NGẦM suy ra (từ mô tả hoàn cảnh): {impl}")
    if r["purpose_amen"]:
        print(f"   → ưu tiên hotel có tiện ích hợp mục đích: {r['purpose_amen']}")
    if r.get("expansion_trace"):
        print("   → expansion boost (relation graph verified, chỉ ưu tiên ranking, KHÔNG lọc cứng):")
        for line in r["expansion_trace"]:
            print(f"        ↳ {line}")
    print(f"   → lọc CỨNG (amenity/setting): {r['hard'] or '—'} | nới lỏng: {r['soft'] or '—'}")
    if r["hard_skipped"]:
        print(f"   ⚠ bỏ qua hard concept 0 hotel (Bước 4 chưa gắn nhãn): {r['hard_skipped']}")
    if r["feel_skipped"]:
        print(f"   ⚠ bỏ qua feel concept 0 hotel đạt ngưỡng (Bước 5 chưa đủ profile): {r['feel_skipped']}")
    print(f"   → CẢM NHẬN (từ review, lọc theo profile≥0.6): {r['feel'] or '—'}")
    loc_label = r["loc_concepts"] or r["location"] or "—"
    print(f"   → range: {r['range'] or '—'} | location: {loc_label}")
    if r.get("lmk"):
        print(f"   → ĐỊA DANH gần (ưu tiên, gần hơn lên top): {r['lmk']}")
    if "price_max" in r["range"] or "price_min" in r["range"]:
        print("   ⚠ GIÁ là placeholder (fake) — KHÔNG lọc cứng theo giá, chỉ ưu tiên hotel giá gần mức yêu cầu.")
    print(f"   → {r['n']} hotel khớp. Top (ưu tiên khớp nhiều tiêu chí + gần giá + điểm cao; trừ nhẹ negative style):")
    for o in r["hits"]:
        rf = o["range_filters"]
        cap = " [giá~cap5tr]" if rf.get("price_capped") else ""
        price = f"từ {rf.get('price_min_vnd', 0):,}đ/đêm" if rf.get("price_min_vnd") else "giá ?"
        score = f"{rf.get('review_score')}/10" if rf.get("review_score") else "—"
        star = f"{rf.get('star_rating')}★" if rf.get("star_rating") else "?★"
        # điểm cảm nhận của hotel cho các concept feel trong câu
        prof = o.get("semantic_profile", {})
        neg_prof = o.get("negative_style_profile", {})
        feel_parts = []
        for c in r["feel"]:
            name = c.split("_", 1)[1].lower()
            feel_parts.append(f"{name}={prof.get(c, {}).get('score', 0):.2f}")
            neg_score = neg_prof.get(c, {}).get("negative_score", 0)
            if neg_score:
                feel_parts.append(f"neg_{name}={neg_score:.2f}")
        feel_str = " ".join(feel_parts)
        feel_str = f" | {feel_str}" if feel_str else ""
        # đánh dấu hotel có tiện ích hợp mục đích chuyến đi (lý do được ưu tiên lên top)
        matched = sorted(set(r["purpose_amen"]) & _all_concepts(o))
        purpose_str = f" | ✓hợp mục đích: {', '.join(c.split('_', 1)[1].lower() for c in matched)}" if matched else ""
        # khoảng cách tới (các) địa danh yêu cầu — lý do hotel được đẩy lên top
        lmk_str = ""
        if r.get("lmk"):
            want = set(r["lmk"])
            near = sorted(
                ((x["concept"], x.get("distance_km")) for x in o.get("nearby_landmarks", [])
                 if x["concept"] in want),
                key=lambda t: (t[1] is None, t[1] or 0),
            )
            if near:
                lmk_str = " | 📍" + ", ".join(
                    f"{c.split('_', 1)[1].lower()} {km:g}km" if km is not None
                    else c.split('_', 1)[1].lower() for c, km in near
                )
        hotel_id = o.get("hotel_id") or o.get("id") or "?"
        print(f"      • {o['title'][:42]:42s} | id={hotel_id} | {o['location'].get('city')} "
              f"| {star} | review {score}{feel_str} | {price}{cap}{purpose_str}{lmk_str}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(" ".join(sys.argv[1:]))
    else:
        # vài câu demo
        for q in [
            "khách sạn có hồ bơi ở Đà Nẵng",
            "resort gần biển cho gia đình ở Nha Trang",
            "resort hạng sang có spa ở Phú Quốc",
            "khách sạn cho cặp đôi có hồ bơi vô cực",
        ]:
            show(q)
