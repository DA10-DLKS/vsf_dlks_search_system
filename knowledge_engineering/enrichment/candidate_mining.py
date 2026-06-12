"""candidate_mining.py — Đào keyword ỨNG VIÊN từ review (string match, KHÔNG LLM).

Owner: Trương Anh Long (KE, DA10). Mục tiêu: đếm các cụm tiếng Việt LẶP NHIỀU mà CHƯA map được
vào concept nào (lọt qua synonym_dictionary). Nguyên liệu cho vòng phản hồi ontology (thêm
STYLE/concept mới) — KHÔNG tự thêm concept, chỉ GỢI Ý để người duyệt (promote_candidate.py).

NGUỒN: data/cleaned/*.json > reviews_detail.sample_comments (99% tiếng Việt — Agoda đã dịch).
  KHÔNG dùng data/raw/reviews (chỉ 11% VN -> top nhiễu ngoại ngữ piscine/agreable). Xem __main__.

NGUYÊN TẮC:
  - KHÔNG gọi LLM: thuần string match -> gần như miễn phí.
  - KHÔNG sửa ontology: chỉ ghi candidate_queue, người duyệt mới quyết.
  - Đếm (số lần nhắc) + (số hotel) + (ví dụ) + (hotels[]) để lọc nhiễu + khoanh vùng backfill.

Chạy độc lập: python -m knowledge_engineering.enrichment.candidate_mining
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

from knowledge_engineering.common.normalize import normalize, strip_diacritics

SYNONYM_YAML = "ontology/synonym_dictionary.yaml"
LOCATION_YAML = "ontology/core/location.generated.yaml"
OUT_JSON = "knowledge_engineering/enrichment/candidate_queue.json"

# n-gram cần xét (1-3 từ): style/concept hay là cụm 1-3 từ ("yên tĩnh", "kiến trúc pháp").
NGRAM_MIN, NGRAM_MAX = 1, 3

# Stopword — cụm chỉ gồm stopword là nhiễu, bỏ. LƯU Ý (lược đồ Sprint 4): stoplist phải
# đứng TRƯỚC bộ lọc support, vì rác phổ thông ("and", "room") có support CAO NHẤT -> nếu để
# support lọc thì rác lọt còn concept hiếm (japandi) bị loại. Stoplist bắt nhiễu-phổ-thông;
# support chỉ bắt nhiễu-lẻ-tẻ (gõ sai, từ ngẫu nhiên). Hai tầng bắt 2 loại nhiễu khác nhau.
#
# Sau fold, dấu bị bỏ nên tiếng Việt và tiếng Anh trộn vào nhau -> cần CẢ stopword VN lẫn EN.
# EN gồm: (a) grammar words (and/the/was) + (b) DANH TỪ KHÁCH SẠN thông dụng (room/staff/hotel)
# — nhóm (b) support rất cao, không liệt kê thì lọt hết.
_STOP_VI = {
    "và", "là", "của", "có", "không", "rất", "thì", "mà", "ở", "cho", "với", "này", "đó",
    "các", "những", "một", "được", "đã", "khi", "nên", "cũng", "vì", "nhưng", "lại", "ra",
    "vào", "đi", "lắm", "quá", "nhiều", "ít", "hơn", "nhất", "tôi", "mình", "chúng", "họ",
    "anh", "chị", "em", "ạ", "à", "ơi", "nha", "nhé", "ok", "oke", "cả", "khá", "thật",
    "phòng", "khách", "sạn", "nhân", "viên", "rồi", "sẽ", "đến", "tại", "trong", "ngoài",
}
_STOP_EN = {
    # (a) grammar / function words
    "and", "the", "a", "an", "to", "of", "in", "on", "at", "for", "with", "was", "were",
    "is", "are", "be", "been", "but", "or", "so", "we", "i", "you", "they", "it", "its",
    "this", "that", "there", "here", "had", "have", "has", "from", "as", "by", "not", "no",
    "very", "too", "more", "most", "all", "some", "any", "our", "my", "their", "his", "her",
    "if", "when", "then", "than", "also", "just", "can", "will", "would", "did", "do", "does",
    "us", "them", "out", "up", "about", "again", "only", "really", "much", "well", "get",
    "which", "one", "like", "don", "bit", "quite", "even", "many", "next", "back", "still",
    "make", "made", "go", "going", "went", "come", "came", "want", "need", "see", "saw",
    "s", "t", "m", "re", "ll", "ve", "didn", "wasn", "isn", "couldn", "wouldn",  # tách dấu '
    # (b) danh từ/tính từ khách sạn thông dụng — support CAO, không loại thì lấn át candidate
    "room", "rooms", "staff", "hotel", "place", "stay", "stayed", "night", "nights", "day",
    "days", "time", "good", "great", "nice", "clean", "friendly", "helpful", "comfortable",
    "location", "breakfast", "food", "service", "pool", "beach", "view", "bed", "bathroom",
    "price", "value", "area", "city", "trip", "everything", "recommend", "definitely",
    "convenient", "water", "small", "big", "large", "lovely", "perfect", "amazing", "little",
}
# Stoplist DÙNG để so với gram ĐÃ FOLD (bỏ dấu). Vì gram tạo từ fold_toks nên "không"->"khong".
# Fold cả stoplist VN -> "khong/rat/khach" tự vào, KHÔNG cần liệt kê tay 2 dạng. EN vốn không dấu.
_STOP = {strip_diacritics(w) for w in _STOP_VI} | _STOP_EN

# Có dấu tiếng Việt? (sau fold thì hết dấu -> phải xét TRƯỚC fold). Dùng để: cụm CÓ DẤU luôn
# giữ (nhánh "có dấu -> giữ"); cụm ASCII thuần mới qua bộ lọc support (nhánh bắt japandi/boutique).
_VN_DIACRITIC = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE)


def _load_mapped_forms() -> set[str]:
    """Tập surface_form ĐÃ map (đã normalize) — để biết cụm nào CHƯA map (= candidate).

    Gồm: (1) synonym_dictionary (concept đã có) + (2) ĐỊA DANH (location.generated). Địa danh
    KHÔNG phải concept phong cách/tiện ích -> loại để không lọt vào candidate (lat/sai gon/tau).
    Dùng DANH SÁCH địa danh THẬT (không đoán): label + surface_forms của mọi LOC concept.
    """
    forms: set[str] = set()
    data = yaml.safe_load(open(SYNONYM_YAML, encoding="utf-8")) or {}
    syn = data.get("synonyms", data)  # hỗ trợ cả dạng nested lẫn phẳng
    for form in syn:
        forms.add(normalize(str(form), fold=True))
    # địa danh: label.vi + surface_forms.vi/en của location.generated
    loc = yaml.safe_load(open(LOCATION_YAML, encoding="utf-8")) or {}
    for v in (loc.get("concepts") or {}).values():
        lab = (v.get("label") or {}).get("vi", "")
        if lab:
            forms.add(normalize(lab, fold=True))
        sf = v.get("surface_forms") or {}
        for lang in ("vi", "en"):
            for s in sf.get(lang, []) or []:
                forms.add(normalize(str(s), fold=True))
    return forms


# Cache normalize (underthesea tokenize CHẬM — phần tốn 99% thời gian). Cùng text -> cùng kết
# quả -> lưu đĩa, lần chạy lại (chỉ chỉnh logic dump) gần như tức thì. Key = hash text; value =
# (raw, fold) đã normalize. add_review tách token + n-gram thì RẺ, không cache.
NORM_CACHE = "knowledge_engineering/enrichment/.norm_cache.pkl"


class Miner:
    """Gom candidate qua nhiều review. add_review() rẻ (string match), dump() ghi file."""

    def __init__(self, use_cache: bool = True) -> None:
        self.mapped = _load_mapped_forms()
        self.freq: dict[str, int] = defaultdict(int)          # cụm -> số lần nhắc
        self.hotels: dict[str, set] = defaultdict(set)        # cụm -> tập hotel_id
        self.examples: dict[str, str] = {}                    # cụm -> 1 ví dụ review
        self.has_vn: dict[str, bool] = {}                     # cụm (fold) -> gốc CÓ DẤU VN?
        self.all_hotels: set = set()                          # tổng hotel đã quét (cho trần IDF)
        # cache normalize: {hash(text): (raw, fold)} — bỏ qua underthesea cho text đã gặp.
        self.use_cache = use_cache
        self._norm_cache: dict[str, tuple[str, str]] = {}
        self._cache_dirty = False
        if use_cache and Path(NORM_CACHE).exists():
            try:
                import pickle
                self._norm_cache = pickle.loads(Path(NORM_CACHE).read_bytes())
            except Exception:
                self._norm_cache = {}

    def _normalize_cached(self, text: str) -> tuple[str, str]:
        """(raw fold=False, fold=True) — đọc cache nếu có, không thì gọi underthesea + lưu."""
        if not self.use_cache:
            return normalize(text, fold=False).replace("_", " "), normalize(text, fold=True)
        import hashlib
        key = hashlib.sha1(text.encode("utf-8")).hexdigest()
        hit = self._norm_cache.get(key)
        if hit is not None:
            return hit
        val = (normalize(text, fold=False).replace("_", " "), normalize(text, fold=True))
        self._norm_cache[key] = val
        self._cache_dirty = True
        return val

    def save_cache(self) -> None:
        if self.use_cache and self._cache_dirty:
            import pickle
            Path(NORM_CACHE).parent.mkdir(parents=True, exist_ok=True)
            Path(NORM_CACHE).write_bytes(pickle.dumps(self._norm_cache))

    def add_review(self, text: str, hotel_id: int | None = None) -> None:
        if not text or not text.strip():
            return
        if hotel_id is not None:
            self.all_hotels.add(hotel_id)
        # 2 bản SONG SONG cùng token-hóa: bản có dấu (để biết cụm là tiếng Việt) + bản fold
        # (để gom đồng-âm-khác-cách-gõ). Cùng đi qua normalize nên ranh giới từ khớp nhau.
        raw, fold = self._normalize_cached(text)             # CACHE: bỏ qua underthesea nếu đã gặp
        raw_toks = [t for t in re.split(r"[^0-9a-zà-ỹ]+", raw, flags=re.IGNORECASE) if t]
        fold_toks = [t for t in re.split(r"[^0-9a-zđ]+", fold) if t]
        if len(raw_toks) != len(fold_toks):   # lệch token (hiếm) -> bỏ has_vn, vẫn đếm theo fold
            raw_toks = fold_toks
        seen_this_review: set[str] = set()
        for n in range(NGRAM_MIN, NGRAM_MAX + 1):
            for i in range(len(fold_toks) - n + 1):
                parts = fold_toks[i:i + n]
                gram = " ".join(parts)
                if gram in self.mapped:           # đã map -> không phải candidate
                    continue
                # cụm n>=2 BẮT ĐẦU/KẾT THÚC bằng stopword = mảnh câu vụn ("floor and", "i highly",
                # "enjoyed our"), KHÔNG phải khái niệm. Concept là cụm danh từ/tính từ liền mạch.
                if n >= 2 and (parts[0] in _STOP or parts[-1] in _STOP):
                    continue
                if all(t in _STOP for t in parts):  # toàn stopword (VN+EN) -> nhiễu
                    continue
                if len(gram) < 3:                 # quá ngắn -> nhiễu
                    continue
                if gram in seen_this_review:      # mỗi review đếm 1 lần/cụm (chống spam)
                    continue
                seen_this_review.add(gram)
                self.freq[gram] += 1
                if hotel_id is not None:
                    self.hotels[gram].add(hotel_id)
                self.examples.setdefault(gram, text.strip()[:160])
                # đánh dấu cụm có dấu tiếng Việt không (xét trên bản raw cùng vị trí)
                if gram not in self.has_vn:
                    raw_gram = " ".join(raw_toks[i:i + n])
                    self.has_vn[gram] = bool(_VN_DIACRITIC.search(raw_gram))

    def dump(self, min_freq: int = 5, min_hotels: int = 2,
             ascii_min_freq: int = 20, ascii_min_hotels: int = 5,
             max_hotel_ratio: float = 0.40, top: int = 2000) -> dict:
        """Ghi candidate_queue.json. LỌC giữ rộng, XẾP HẠNG theo độ ĐẶC TRƯNG để người duyệt.

        LỌC (giữ rộng — KHÔNG cắt mất concept thật):
            đã map ontology/synonym?            -> loại  (ở add_review)
            toàn/đầu/cuối stopword?             -> loại  (ở add_review)
            xuất hiện > max_hotel_ratio hotel?  -> loại  (TRẦN IDF: chỉ chặn rác ĐỈNH phổ thông)
            đủ support tối thiểu (VN/ASCII)?    -> GIỮ
        Đo thật (2026-06-10): concept thật trải RỘNG 5–134 hotel ("cổ điển" 134, "view núi" 22,
        "retro" 8) -> KHÔNG có ngưỡng hotel_count cứng tách được nhiễu khỏi concept. Nên KHÔNG
        hạ trần IDF thấp (giết "cổ điển"/"châu âu"); giữ 40% chỉ chặn rác đỉnh (vui choi 200 hotel).

        XẾP HẠNG (rank_score = TF-IDF) — thay vì sort theo hotel_count (đẩy cụm PHỔ THÔNG vô dụng
        lên đầu). Cụm đáng chú ý = lặp nhiều LẦN nhưng KHÔNG trải khắp hotel:
            rank_score = freq * log(N / hotel_count)
        Cụm ở 200/502 hotel -> log nhỏ -> chìm; "view núi" 22 hotel -> log lớn -> nổi. Người duyệt
        lướt từ trên xuống gặp concept đặc trưng trước. top=2000 (rộng) để không cắt mất đuôi hiếm.

        2 ngưỡng support: cụm VN tin hơn -> ngưỡng thấp; ASCII dễ rác -> ngưỡng cao.
        """
        import math
        n_all = max(1, len(self.all_hotels))
        max_hotels = int(n_all * max_hotel_ratio)
        rows = []
        for gram, f in self.freq.items():
            nh = len(self.hotels.get(gram, ()))
            if nh > max_hotels:                    # TRẦN IDF: quá phổ biến -> từ thông dụng, loại
                continue
            # BỎ 1-TỪ-ĐƠN: concept phong cách/tiện ích hầu như luôn là CỤM >=2 từ ("biển riêng",
            # "cáp treo", "bể bơi vô cực"). Gram 1 từ phần lớn là MẢNH underthesea cắt sai từ địa
            # danh/tên riêng ("lat"<-đà lạt, "tau"<-vũng tàu, "son", "ham"). Loại -> top sạch hơn
            # nhiều. (Mất concept 1-từ hiếm như "homestay" nhưng nó thường đã ở synonym rồi.)
            if " " not in gram:
                continue
            is_vn = self.has_vn.get(gram, False)
            if is_vn:
                keep = f >= min_freq and nh >= min_hotels
            else:                                  # ASCII thuần -> ngưỡng cao hơn
                keep = f >= ascii_min_freq and nh >= ascii_min_hotels
            if keep:
                # rank_score: TF-IDF — cao khi lặp nhiều LẦN nhưng ÍT hotel (đặc trưng nhóm).
                rank_score = round(f * math.log(n_all / nh), 1)
                rows.append({
                    "candidate": gram,
                    "rank_score": rank_score,
                    "freq": f,
                    "hotel_count": nh,
                    # hotels: DANH SÁCH hotel_id nhắc tới cụm này. Cần để BACKFILL concept mới
                    # (absa.py --backfill) khoanh đúng hotel, gán per-hotel KHÔNG chạy lại cả corpus.
                    "hotels": sorted(self.hotels.get(gram, ())),
                    "lang": "vi" if is_vn else "ascii",
                    "example": self.examples.get(gram, ""),
                    "status": "new",            # new | accepted | merged | rejected (người duyệt set)
                    "suggested_concept_id": "", # người duyệt điền (Sprint 4)
                })
        # GỘP N-GRAM CON: "cau lac"/"lac bo" là mảnh của "cau lac bo". Nếu cụm CON nằm gọn trong
        # 1 cụm DÀI hơn VÀ xuất hiện ở tập hotel gần trùng (cụm con không phổ biến hơn đáng kể) ->
        # bỏ cụm con, giữ cụm dài (đủ nghĩa hơn). Ngưỡng 1.25: cụm con chỉ "sống" nếu nó xuất hiện
        # rộng hơn cụm dài >25% (tức nó có nghĩa riêng, không chỉ là mảnh).
        longer = sorted(rows, key=lambda r: -len(r["candidate"].split()))
        drop: set[str] = set()
        for sub in rows:
            sw = sub["candidate"].split()
            if len(sw) >= 3:
                continue                          # cụm 3 từ đã dài nhất (NGRAM_MAX) -> không bị bao
            for lng in longer:
                lw = lng["candidate"].split()
                if len(lw) <= len(sw):
                    continue
                # sub là dãy con liên tiếp của lng?
                if any(lw[i:i+len(sw)] == sw for i in range(len(lw)-len(sw)+1)):
                    if sub["hotel_count"] <= lng["hotel_count"] * 1.25:
                        drop.add(sub["candidate"])
                    break
        rows = [r for r in rows if r["candidate"] not in drop]

        rows.sort(key=lambda r: -r["rank_score"])  # đặc trưng nhất lên đầu (KHÔNG theo hotel_count)
        rows = rows[:top]
        out = {"version": "1.0", "note": "candidate cho Sprint 4 — người duyệt, KHÔNG tự thêm.",
               "n_hotels_scanned": n_all, "idf_max_hotels": max_hotels,
               "n_candidates": len(rows), "candidates": rows}
        Path(OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
        Path(OUT_JSON).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out


# ---------------------------------------------------------------------------
# Chạy độc lập: mine từ data/cleaned/*.json > reviews_detail.sample_comments.
#
# NGUỒN = sample_comments (KHÔNG phải data/raw/reviews). Lý do (đo thật 2026-06-10):
#   - sample_comments: 99% TIẾNG VIỆT (Agoda đã dịch) -> candidate ra cụm VN có nghĩa.
#   - data/raw/reviews: chỉ 11% VN, 89% ngoại ngữ (Anh/Pháp/Đức) -> top toàn "piscine/agreable/
#     schon" = nhiễu ngoại ngữ. Đổi nguồn = diệt nhiễu ở GỐC, không phải vá bằng filter ngôn ngữ.
#   sample_comments là review Agoda chọn lọc (~hàng trăm/hotel) — đủ để PHÁT HIỆN concept mới.
# ---------------------------------------------------------------------------
CLEANED_GLOB = "data/cleaned/hotel_*.json"

if __name__ == "__main__":
    import glob

    m = Miner()
    n_cmt = 0
    for f in glob.glob(CLEANED_GLOB):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        hid = data.get("hotel_id")
        for c in (data.get("reviews_detail") or {}).get("sample_comments", []) or []:
            text = c.get("text") or ""
            if text.strip():
                m.add_review(text, hid)
                n_cmt += 1
    m.save_cache()          # lưu cache normalize -> lần chạy lại (chỉnh logic dump) gần như tức thì
    out = m.dump()
    print(f"Quét {n_cmt} sample_comment (tiếng Việt) -> {out['n_candidates']} candidate "
          f"(>=5 lần, >=2 hotel).")
    print(f"-> {OUT_JSON}")
    for r in out["candidates"][:30]:
        print(f"  score {r['rank_score']:7.1f} | {r['hotel_count']:3d} hotel | {r['freq']:4d}x "
              f"| [{r['lang']}] {r['candidate']}")