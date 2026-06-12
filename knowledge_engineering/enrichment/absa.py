"""absa.py — Aspect-Based Sentiment Analysis cho review (Sprint 2, Bước 5.3).

Owner: Trương Anh Long (KE, DA10). Mỗi review tiếng Việt -> trích cặp (khía cạnh, cảm xúc, span)
bằng LLM (qua llm.py đa-provider). Bổ sung cho SEED (5.2): thêm SPAN dẫn chứng + concept STYLE_*
ngoài 7 aspect mà aggregate Agoda không có.

NGUYÊN TẮC (mục 0.5 + 2.4):
  - concept TRUNG TÍNH: "hơi ồn" -> {STYLE_QUIET, negative}, KHÔNG tạo STYLE_NOT_QUIET.
  - aspect CHỈ trong 7 ASPECT_* (ràng buộc vocabulary). style chỉ trong tập cho phép.
  - mỗi review tối đa 1 phiếu/concept (dedupe ở aggregate 5.4).
  - LLM chỉ chạy review (ca khó/giàu thông tin); KHÔNG sửa ontology.

Chạy mẫu:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.absa --hotel 805030 --limit 20
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from knowledge_engineering.enrichment.llm import complete_json, active_config

# Số request LLM gọi SONG SONG. ABSA là I/O-bound (chờ HTTP) nên thread giúp nhiều.
# 12 an toàn với rate-limit gpt-4o-mini; tăng nếu tier cao, giảm nếu gặp 429.
DEFAULT_WORKERS = 12

REVIEWS_DIR = "data/raw/reviews"
CORE_GLOB = "ontology/core/*.yaml"

# prompt_version: PHẦN CỐ ĐỊNH của bản prompt (đổi khi sửa câu chữ/luật). Nhưng vocab giờ đọc từ
# ontology -> version THẬT = base + hash(vocab). Để: thêm/bớt concept -> version đổi -> evidence
# cũ biết là sinh từ vocab khác (xem effective_prompt_version). v1=vi-only, v2=đa ngôn ngữ,
# v3=vocab-ontology, v4=thêm field `novel` (discovery Tầng 1) vào CÙNG prompt ABSA,
# v5=siết novel CHỈ thu PHONG CÁCH/VIBE (loại view/giá/ăn uống/tiện ích — thử nghiệm thật 53 hotel
#    cho thấy novel v4 quá rộng, bắt cả aspect, không ra style mới).
PROMPT_VERSION_BASE = "v5-novel-style-only"


# ---------------------------------------------------------------------------
# VOCAB ĐỌC TỪ ONTOLOGY (KHÔNG hard-code) — promote concept mới chỉ cần sửa ontology/core/*.yaml.
# Đọc concept facet=aspect/style; kèm label để LLM hiểu rõ concept (đa ngôn ngữ).
# ---------------------------------------------------------------------------
def load_vocab(core_glob: str = CORE_GLOB) -> dict[str, dict]:
    """{concept_id: {facet, label_vi, label_en}} cho mọi concept facet in {aspect, style}.
    Sắp xếp DETERMINISTIC (theo id) để hash vocab ổn định -> cache không vỡ vô cớ."""
    vocab: dict[str, dict] = {}
    for f in sorted(glob.glob(core_glob)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            if v.get("facet") in ("aspect", "style"):
                lab = v.get("label", {}) or {}
                vocab[cid] = {"facet": v["facet"],
                              "label_vi": lab.get("vi", ""), "label_en": lab.get("en", "")}
    return dict(sorted(vocab.items()))


def _vocab_lists(vocab: dict[str, dict]) -> tuple[list[str], list[str]]:
    """(ASPECTS, STYLES) — id sắp xếp, để dựng prompt + lọc."""
    aspects = [c for c, v in vocab.items() if v["facet"] == "aspect"]
    styles = [c for c, v in vocab.items() if v["facet"] == "style"]
    return aspects, styles


def build_system_prompt(vocab: dict[str, dict]) -> str:
    """Dựng prompt SYSTEM từ vocab ontology. Mỗi concept ghi id + nhãn vi/en để LLM định nghĩa rõ."""
    aspects, styles = _vocab_lists(vocab)

    def _fmt(ids: list[str]) -> str:
        return "; ".join(f"{c} ({vocab[c]['label_vi']}/{vocab[c]['label_en']})" for c in ids)

    return f"""Bạn trích cảm xúc theo khía cạnh (ABSA) từ review khách sạn.
Review CÓ THỂ bằng nhiều ngôn ngữ (Việt, Anh, Hàn, Nga, Trung...). Dù review ngôn ngữ nào,
vẫn trả về concept ID CHUNG (tiếng Anh) dưới đây và span trích NGUYÊN VĂN theo ngôn ngữ gốc.

aspect CHỈ chọn trong: {_fmt(aspects)}
style (cảm nhận phong cách, tùy chọn) CHỈ chọn trong: {_fmt(styles)}

Quy tắc:
- Mỗi khía cạnh/phong cách được NHẮC tới -> 1 mục {{concept, sentiment, span}}.
- sentiment: positive | negative | neutral | mixed.
- span: trích NGUYÊN VĂN đoạn ngắn trong review làm bằng chứng.
- TRUNG TÍNH: "hơi ồn" -> {{"concept":"STYLE_QUIET","sentiment":"negative"}} (KHÔNG tạo NOT_QUIET).
- Không bịa khía cạnh review không nhắc tới. Không nhắc gì -> mảng rỗng.

NGOÀI ra (DISCOVERY): chỉ thu vào field "novel" khi review nhắc tới một PHONG CÁCH / VIBE / KIẾN
TRÚC / THẨM MỸ của khách sạn mà danh sách style ở trên CHƯA có. Ví dụ HỢP LỆ: cổ điển, tối giản,
phong cách công nghiệp, kiểu Nhật/Bắc Âu, bohemian, tân cổ điển, retro, nhiệt đới, vintage...
  {{"phrase": tên phong cách (tiếng Việt CHUẨN, dịch nếu review ngoại ngữ),
    "gloss": diễn giải ngắn, "sentiment": positive|negative|neutral|mixed,
    "span": trích nguyên văn}}.
- TUYỆT ĐỐI KHÔNG đưa vào novel: view/cảnh, vị trí, giá cả, đồ ăn/bữa sáng, tiện ích (hồ bơi, bãi
  biển, spa...), độ ồn, sạch sẽ, thái độ nhân viên, chất lượng dịch vụ — đó là ASPECT/AMENITY/LOCATION,
  KHÔNG phải phong cách. Nếu không chắc là PHONG CÁCH -> BỎ.
- KHÔNG bịa. KHÔNG lặp lại style đã có ở trên. Không có phong cách lạ -> "novel": [].

CHỈ trả JSON đúng dạng:
{{"overall_sentiment":"positive|negative|neutral|mixed",
  "items":[{{"concept":"ASPECT_... hoặc STYLE_...","sentiment":"...","span":"..."}}],
  "novel":[{{"phrase":"...","gloss":"...","sentiment":"...","span":"..."}}]}}"""


def effective_prompt_version(vocab: dict[str, dict]) -> str:
    """Version THẬT = base + hash 8 ký tự của tập concept_id. Thêm/bớt concept -> version đổi ->
    evidence cũ phân biệt được là sinh từ vocab khác (không nhầm 14-concept với 15-concept)."""
    h = hashlib.sha1("|".join(sorted(vocab)).encode()).hexdigest()[:8]
    return f"{PROMPT_VERSION_BASE}+{h}"


# Nạp 1 lần lúc import (deterministic). Các hàm dưới dùng biến module này.
VOCAB = load_vocab()
ASPECTS, STYLES = _vocab_lists(VOCAB)
SYSTEM = build_system_prompt(VOCAB)
PROMPT_VERSION = effective_prompt_version(VOCAB)


def _clean_result(out: dict, allowed: set[str], want_novel: bool) -> dict:
    """Lọc 1 KẾT QUẢ thô của LLM -> dict chuẩn {overall_sentiment, items, novel}.
    DÙNG CHUNG cho cả analyze_review (đơn) lẫn analyze_reviews_batch (gộp) -> đảm bảo output
    TỪNG REVIEW GIỐNG HỆT nhau dù gọi đơn hay batch. KHÔNG đổi schema ở đây = output ổn định."""
    items = []
    seen = set()                       # DEDUPE: mỗi concept tối đa 1 phiếu/review (prompt yêu cầu
                                       # vậy nhưng LLM vẫn trả trùng) -> lọc tại nguồn, evidence sạch.
    for it in out.get("items", []) or []:
        if not isinstance(it, dict):
            continue
        c = it.get("concept")
        if c in allowed and c not in seen:
            seen.add(c)
            items.append({
                "concept": c,
                "sentiment": it.get("sentiment", "neutral"),
                "span": (it.get("span") or "")[:200],
            })
    # DISCOVERY: cụm lạ ngoài vocab. KHÔNG lọc chống-trùng-mapped ở đây (giữ raw thật) — Tầng 2/3 lo.
    novel = []
    if want_novel:
        for it in out.get("novel", []) or []:
            if not isinstance(it, dict):
                continue
            ph = (it.get("phrase") or "").strip()
            if not ph:
                continue
            novel.append({
                "phrase": ph[:80],
                "gloss": (it.get("gloss") or "")[:160],
                "sentiment": it.get("sentiment", "neutral"),
                "span": (it.get("span") or "")[:200],
            })
    return {"overall_sentiment": out.get("overall_sentiment", "neutral"),
            "items": items, "novel": novel}


def analyze_review(text: str, system: str = SYSTEM, allowed: set[str] | None = None,
                   want_novel: bool = True) -> dict:
    """Trả {overall_sentiment, items:[{concept, sentiment, span}], novel:[{phrase,gloss,...}]}.
    Lọc concept ngoài vocab. `novel` = phát hiện DISCOVERY (Tầng 1) — cụm/style LẠ ngoài vocab,
    LLM CHỈ gợi ý, KHÔNG tự thêm ontology. want_novel=False (vd backfill) -> bỏ qua novel.
    GIỮ hàm này (gọi đơn) cho backfill + test; đường ABSA chính dùng analyze_reviews_batch."""
    if not text or not text.strip():
        return {"overall_sentiment": "neutral", "items": [], "novel": []}
    out = complete_json(system, text.strip()[:2000], temperature=0)
    if allowed is None:
        allowed = set(ASPECTS) | set(STYLES)
    return _clean_result(out, allowed, want_novel)


# ---------------------------------------------------------------------------
# BATCH: gộp N review vào 1 request LLM (giảm số request ~N lần — tránh trần RPD provider).
# RÀNG BUỘC: batch chỉ đổi CÁCH GỌI; output TỪNG review ghi vào store GIỐNG HỆT gọi đơn
# (cùng _clean_result). LLM trả THIẾU/LỆCH phần tử -> map theo idx, thiếu thì BỎ (không ghi)
# -> review đó vào todo lần sau (resume theo review_id), KHÔNG gán nhầm kết quả review khác.
# ---------------------------------------------------------------------------
BATCH_SIZE = 20

# Prompt batch = SYSTEM gốc (vocab + luật + novel) + phần BAO yêu cầu trả MẢNG theo idx.
# Tách phần bao ra để khi SYSTEM đổi (thêm concept) thì batch tự cập nhật theo, không lệch.
_BATCH_WRAP = """

--- CHẾ ĐỘ BATCH ---
Bạn sẽ nhận NHIỀU review, mỗi review đánh số [idx] (bắt đầu 0). Áp DÙNG ĐÚNG các quy tắc trên cho
TỪNG review một cách ĐỘC LẬP. Trả về DUY NHẤT JSON dạng:
{{"results":[{{"idx":0,"overall_sentiment":"...","items":[...],"novel":[...]}}, ...]}}
- PHẢI có đúng 1 phần tử cho MỖI idx được hỏi; "idx" khớp số review. KHÔNG gộp, KHÔNG bỏ sót.
- items/novel theo đúng định dạng đã mô tả ở trên (concept/sentiment/span; phrase/gloss/sentiment/span)."""


def _batch_system(system: str = SYSTEM) -> str:
    return system + _BATCH_WRAP


def analyze_reviews_batch(texts: list[str], system: str = SYSTEM,
                          allowed: set[str] | None = None, want_novel: bool = True) -> dict[int, dict]:
    """Gộp `texts` (đã đủ dài, đã strip) vào 1 request. Trả {idx: result_dict} CHỈ cho idx LLM trả
    hợp lệ. idx THIẾU -> không có trong dict -> caller coi như chưa xong -> resume lần sau.
    Mỗi result_dict đi qua _clean_result -> GIỐNG HỆT output analyze_review đơn lẻ."""
    if allowed is None:
        allowed = set(ASPECTS) | set(STYLES)
    if not texts:
        return {}
    # đánh số review trong user prompt
    user = "\n\n".join(f"[{i}] {t.strip()[:2000]}" for i, t in enumerate(texts))
    out = complete_json(_batch_system(system), user, temperature=0)
    results: dict[int, dict] = {}
    for r in out.get("results", []) or []:
        if not isinstance(r, dict):
            continue
        idx = r.get("idx")
        if not isinstance(idx, int) or idx < 0 or idx >= len(texts) or idx in results:
            continue                       # idx lạ/trùng -> bỏ (an toàn, không gán nhầm)
        results[idx] = _clean_result(r, allowed, want_novel)
    return results


# evidence CHIA THEO HOTEL: review_evidence/hotel_<id>.json (mỗi hotel 1 file).
# Lý do (vs 1 file gộp): 112k review -> 1 file ~100MB ghi lại mỗi lần = chậm dần + hỏng
# cả mẻ. Theo hotel: resume/ghi nhanh (file nhỏ ~150KB), hỏng cục bộ, khớp pattern
# data/raw/reviews (1 file/hotel). profile gộp thì vẫn 1 file (hotel_profiles.json).
EVIDENCE_DIR = Path("knowledge_engineering/enrichment/review_evidence")

# DISCOVERY (Tầng 1): cụm/style LẠ do LLM trích, GHI TÍCH LŨY 1 dòng/phát hiện. derived -> gitignore.
# Nguyên liệu cho Tầng 2 (discovery_cluster.py). KHÔNG ghi từ trong vùng nóng đa luồng: buffer trong
# RAM rồi flush 1 lần/hotel ở finally (xem analyze_hotel). _DISCOVERY_LOCK phòng trường hợp sau này
# nhiều hotel chạy song song cùng append.
DISCOVERY_JSONL = Path("knowledge_engineering/enrichment/raw_discovery.jsonl")
_DISCOVERY_LOCK = threading.Lock()


def _append_discovery(rows: list[dict]) -> None:
    """Append list dòng discovery vào jsonl (1 phát hiện/dòng). Gọi 1 lần/hotel ở finally."""
    if not rows:
        return
    DISCOVERY_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _DISCOVERY_LOCK, open(DISCOVERY_JSONL, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _evidence_path(hotel_id: int) -> Path:
    return EVIDENCE_DIR / f"hotel_{hotel_id}.json"


def _load_evidence(hotel_id: int) -> dict:
    """Evidence đã có của 1 hotel (resume). Key = str(review_id) -> KHÔNG chạy lại."""
    p = _evidence_path(hotel_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_evidence(hotel_id: int, store: dict) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    _evidence_path(hotel_id).write_text(
        json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")


def _review_text(r: dict) -> str:
    text = r.get("text") or ""
    extra = " ".join(filter(None, [r.get("positives"), r.get("negatives")]))
    return (text + " " + extra).strip()


def _sample_balanced(reviews: list, limit: int | None) -> list:
    """Lấy mẫu CÂN BẰNG theo rating, KHÔNG phải `[:limit]`.

    Lý do: crawler dùng sort_strategy=low_first -> review ĐẦU file toàn điểm thấp
    (50 đầu rating ~5.7 vs 50 cuối ~9.5). Lấy `[:limit]` = chỉ đọc phần tệ nhất ->
    ABSA lệch tiêu cực. Giải: sắp theo rating rồi lấy CÁCH ĐỀU -> mẫu trải đủ tệ/TB/tốt.
    (Aspect score vẫn lấy từ SEED/Agoda — toàn bộ review, cân bằng sẵn. ABSA chỉ cần
    sự HIỆN DIỆN của style + span, nên mẫu cân bằng là đủ, không cần crawl lại.)
    """
    if not limit or limit >= len(reviews):
        return reviews
    ranked = sorted(reviews, key=lambda r: (r.get("rating") is None, r.get("rating") or 0))
    step = len(ranked) / limit
    return [ranked[int(i * step)] for i in range(limit)]


# Review ngắn hơn ngưỡng này (sau khi gộp text+pos+neg) -> KHÔNG đáng gọi LLM:
# "ok", "tốt", "good", "👍" chỉ ra mảng rỗng mà vẫn tốn 1 call. Skip -> tiết kiệm vài %.
MIN_REVIEW_CHARS = 15


def analyze_hotel(hotel_id: int, limit: int | None = None, save_every: int = 10,
                  max_workers: int = DEFAULT_WORKERS) -> dict:
    """Chạy ABSA cho review 1 hotel. LƯU INCREMENTAL + RESUME:
    - review_id đã có trong evidence store -> BỎ QUA (không gọi API lại).
    - review quá ngắn (< MIN_REVIEW_CHARS) -> BỎ QUA gọi LLM (không đáng tiền).
    - cứ `save_every` review xong -> ghi file (lỗi giữa chừng không mất phần đã trả tiền).
    Trả dict {review_id: evidence}.

    Candidate mining TÁCH RIÊNG (candidate_mining.py) — nó cần quét TOÀN corpus 1 lượt nhất
    quán (trần IDF dựa mẫu số toàn hotel), không hợp với nhịp chia-đợt/resume của ABSA.
    """
    f = Path(REVIEWS_DIR) / f"hotel_{hotel_id}_reviews.json"
    if not f.exists():
        raise FileNotFoundError(f"Không có file review: {f}")
    reviews = json.loads(f.read_text(encoding="utf-8")).get("reviews", [])
    reviews = _sample_balanced(reviews, limit)   # cân bằng theo rating, KHÔNG [:limit]

    from datetime import datetime, timezone
    cfg = active_config()
    meta_run = {"provider": cfg["provider"], "model": cfg["model"],
                "prompt_version": PROMPT_VERSION}

    store = _load_evidence(hotel_id)
    done_before = len(store)

    # Lọc ra các review CẦN gọi LLM (chưa có trong store + đủ dài). Resume + skip ngắn.
    # RESUME THEO VERSION: chỉ skip review đã chạy CÙNG prompt_version hiện tại. Evidence sinh
    # từ vocab/prompt CŨ (version khác) -> chạy lại để đồng nhất (vd đổi vocab -> version đổi).
    # KHÔNG xóa evidence cũ trước: chỉ ghi đè bằng kết quả mới khi chạy lại (an toàn nếu lỗi giữa chừng).
    todo = []
    stale = 0
    for r in reviews:
        rid = str(r.get("review_id"))
        if rid in store and store[rid].get("prompt_version") == PROMPT_VERSION:
            continue                            # đã chạy CÙNG version -> resume, không tốn tiền lại
        if rid in store:
            stale += 1                          # có nhưng version cũ -> sẽ chạy lại
        text = _review_text(r)
        if len(text) < MIN_REVIEW_CHARS:        # quá ngắn -> không gọi LLM
            continue
        todo.append((rid, r, text))
    if stale:
        print(f"  ({stale} review version cũ -> chạy lại theo {PROMPT_VERSION})")

    if not todo:
        print(f"  (đã có sẵn {done_before}, không có review mới — bỏ qua)")
        return store

    # Gọi LLM SONG SONG qua ThreadPool, đơn vị = 1 BATCH (BATCH_SIZE review/request) thay vì 1 review.
    # Giảm số request ~BATCH_SIZE lần -> tránh trần RPD provider. Thread vẫn giúp nhiều batch bay
    # cùng lúc (I/O-bound). LLM trả thiếu idx -> review đó KHÔNG ghi store -> vào todo lần sau (resume).
    chunks = [todo[i:i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]

    def _work(chunk):
        texts = [text for (_rid, _r, text) in chunk]
        res_map = analyze_reviews_batch(texts)        # {idx: result} chỉ idx LLM trả hợp lệ
        # ghép lại theo vị trí trong chunk -> (rid, r, res) cho idx có kết quả; idx thiếu -> bỏ
        out = []
        for i, (rid, r, _text) in enumerate(chunk):
            if i in res_map:
                out.append((rid, r, res_map[i]))
        return out

    processed = 0
    discovery_rows: list[dict] = []          # buffer phát hiện novel -> flush 1 lần ở finally
    lock = threading.Lock()
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_work, ch): ch for ch in chunks}
            for fut in as_completed(futures):
                batch_out = fut.result()
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                with lock:
                    for rid, r, res in batch_out:
                        store[rid] = {
                            "review_id": r.get("review_id"),
                            "hotel_id": hotel_id,
                            "rating": r.get("rating"),
                            "overall_sentiment": res["overall_sentiment"],
                            "items": res["items"],
                            "novel": res.get("novel", []),
                            **meta_run,
                            "created_at": now,
                        }
                        # gom phát hiện novel vào buffer (KHÔNG ghi file trong vùng nóng đa luồng)
                        for nv in res.get("novel", []):
                            discovery_rows.append({
                                "hotel_id": hotel_id,
                                "review_id": r.get("review_id"),
                                "phrase": nv["phrase"], "gloss": nv["gloss"],
                                "sentiment": nv["sentiment"], "span": nv["span"],
                                "prompt_version": PROMPT_VERSION, "created_at": now,
                            })
                        processed += 1
                    _save_evidence(hotel_id, store)            # lưu sau mỗi batch (an toàn resume)
                    print(f"    ... {processed}/{len(todo)} review xong "
                          f"({processed * 100 // max(1, len(todo))}%)", flush=True)
    finally:
        _save_evidence(hotel_id, store)          # LUÔN lưu, kể cả khi lỗi giữa chừng
        _append_discovery(discovery_rows)        # flush phát hiện novel 1 lần/hotel
    if discovery_rows:
        print(f"  (+{len(discovery_rows)} phát hiện novel -> {DISCOVERY_JSONL.name})")
    print(f"  (đã có sẵn {done_before}, chạy mới {processed}, tổng {len(store)} evidence)")
    return store


# ---------------------------------------------------------------------------
# BACKFILL INCREMENTAL — promote concept MỚI mà KHÔNG chạy lại toàn bộ ABSA.
#
# Bài toán: thêm 1 STYLE mới (vd STYLE_JAPANDI duyệt từ candidate_queue) -> prompt đổi -> nếu
# chạy lại cả corpus thì tốn lại từ đầu. Giải: chỉ hỏi LLM về CONCEPT MỚI, chỉ trên HOTEL ỨNG VIÊN
# (candidate_mining đã khoanh vùng hotel nào nhắc tới nó), rồi GHÉP vào evidence cũ (không xóa).
#
# Luồng: duyệt candidate -> thêm vào ontology/core/style.yaml -> chạy backfill ----.
# ---------------------------------------------------------------------------
def _backfill_system(new_concepts: dict[str, dict]) -> str:
    """Prompt RÚT GỌN chỉ hỏi về concept MỚI (không nhắc 14 concept cũ -> rẻ + focus)."""
    def _fmt(ids):
        return "; ".join(f"{c} ({new_concepts[c]['label_vi']}/{new_concepts[c]['label_en']})" for c in ids)
    ids = sorted(new_concepts)
    return f"""Bạn kiểm review khách sạn xem có nhắc tới các PHONG CÁCH/KHÍA CẠNH MỚI sau không.
Review CÓ THỂ bằng nhiều ngôn ngữ. Trả concept ID chung (tiếng Anh) + span nguyên văn.

CHỈ xét các concept: {_fmt(ids)}

Quy tắc:
- Chỉ trả concept review THỰC SỰ nhắc tới (kể cả phủ định -> sentiment=negative). Không nhắc -> rỗng.
- TRUNG TÍNH: "không hề yên tĩnh" -> sentiment negative (KHÔNG bịa concept phủ định).
CHỈ trả JSON: {{"items":[{{"concept":"...","sentiment":"positive|negative|neutral|mixed","span":"..."}}]}}"""


def backfill_concepts(hotel_id: int, new_ids: list[str], max_workers: int = DEFAULT_WORKERS,
                      forms: list[str] | None = None) -> int:
    """Hỏi LLM về `new_ids` trên review của 1 hotel, GHÉP items mới vào evidence ĐÃ CÓ.

    KHÔNG xóa/ghi đè item cũ: chỉ THÊM cặp (concept_mới, sentiment, span) vào e['items'] của
    từng review (nếu review đó nhắc tới). Đánh dấu `backfilled_versions` theo từng concept để audit.
    Trả số review sửa.
    """
    new_vocab = {c: VOCAB[c] for c in new_ids if c in VOCAB}
    if not new_vocab:
        raise ValueError(f"concept backfill không có trong ontology vocab: {new_ids}")
    system = _backfill_system(new_vocab)
    allowed = set(new_vocab)

    store = _load_evidence(hotel_id)
    if not store:
        return 0  # hotel chưa có evidence base -> ABSA thường sẽ phủ, không backfill
    f = Path(REVIEWS_DIR) / f"hotel_{hotel_id}_reviews.json"
    reviews = {str(r.get("review_id")): r for r in
               json.loads(f.read_text(encoding="utf-8")).get("reviews", [])}

    def _mentions_surface_form(rid: str) -> bool:
        if not forms:
            return True
        from knowledge_engineering.common.normalize import normalize as _norm
        text = _review_text(reviews[rid])
        blob = _norm(text, fold=True)
        return any(form in blob for form in forms)

    # Chỉ backfill review ĐÃ có evidence (đồng bộ mẫu với base), có nhắc surface form,
    # và CHƯA xét đủ concept này.
    # NOTE: field legacy `backfilled_version` là global theo review; không dùng để skip nữa vì
    # chạy STYLE_A trước sẽ làm STYLE_B bị bỏ qua. Từ đây audit theo concept.
    bf_ver = effective_prompt_version(VOCAB)
    todo = []
    for rid, e in store.items():
        if rid not in reviews:
            continue
        if not _mentions_surface_form(rid):
            continue
        done = e.get("backfilled_versions", {}) or {}
        if any(done.get(cid) != bf_ver for cid in allowed):
            todo.append(rid)
    if not todo:
        return 0

    def _work(rid):
        text = _review_text(reviews[rid])
        if len(text) < MIN_REVIEW_CHARS:
            return rid, []
        res = analyze_review(text, system=system, allowed=allowed, want_novel=False)
        return rid, res["items"]

    changed = 0
    lock = threading.Lock()
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for fut in as_completed({ex.submit(_work, rid): rid for rid in todo}):
                rid, new_items = fut.result()
                with lock:
                    e = store[rid]
                    have = {it["concept"] for it in e.get("items", [])}
                    added = [it for it in new_items if it["concept"] not in have]
                    if added:
                        e.setdefault("items", []).extend(added)
                        changed += 1
                    done = e.setdefault("backfilled_versions", {})
                    for cid in allowed:
                        done[cid] = bf_ver   # đánh dấu đã xét version này (kể cả rỗng)
    finally:
        _save_evidence(hotel_id, store)
    return changed


# ---------------------------------------------------------------------------
# Ước lượng chi phí (gpt-4o-mini) — để xác nhận TRƯỚC khi đốt tiền
# ---------------------------------------------------------------------------
# giá 2025 (USD / 1M token)
PRICE = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.0)}


def list_review_hotels() -> list[int]:
    """Danh sách hotel_id có file review, sắp tăng dần (deterministic)."""
    import re
    ids = []
    for f in glob.glob(f"{REVIEWS_DIR}/hotel_*_reviews.json"):
        m = re.search(r"hotel_(\d+)_reviews", f)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def estimate_cost(hotel_id: int, limit: int | None, model: str) -> dict:
    f = Path(REVIEWS_DIR) / f"hotel_{hotel_id}_reviews.json"
    reviews = json.loads(f.read_text(encoding="utf-8")).get("reviews", [])
    reviews = _sample_balanced(reviews, limit)   # cùng mẫu cân bằng như khi chạy thật
    store = _load_evidence(hotel_id)
    # todo = chưa có HOẶC có nhưng version cũ (sẽ chạy lại) — khớp logic resume-theo-version.
    def _needs_run(r) -> bool:
        rid = str(r.get("review_id"))
        return rid not in store or store[rid].get("prompt_version") != PROMPT_VERSION
    todo = [r for r in reviews if _needs_run(r)]
    # BATCH: gộp BATCH_SIZE review/request. 1 request = system (1 lần) + BATCH_SIZE review text;
    # output = mảng -> ~out_tok/review. Số request = ceil(todo/BATCH_SIZE) -> đây mới là con số
    # ăn vào trần RPD (không phải số review). Token-in: system batch ~340 + tổng text review/4.
    import math
    n_req = math.ceil(len(todo) / BATCH_SIZE) if todo else 0
    avg_chars = sum(len(_review_text(r)) for r in todo) / max(1, len(todo))
    sys_tok = 340                          # SYSTEM (vocab + novel + bao batch) ~340 token
    out_tok = 120                          # output/ review (items + novel)
    pin, pout = PRICE.get(model, PRICE["gpt-4o-mini"])
    in_tok_total = n_req * sys_tok + len(todo) * (avg_chars / 4)   # system × số request + text
    out_tok_total = len(todo) * out_tok
    cost = (in_tok_total * pin + out_tok_total * pout) / 1_000_000
    return {"todo": len(todo), "n_requests": n_req, "skip_cached": len(reviews) - len(todo),
            "avg_chars": int(avg_chars), "est_usd": round(cost, 4)}


def _summarize(ev: dict) -> None:
    from collections import Counter
    cs = Counter(); n_items = 0
    for e in ev.values():
        for it in e["items"]:
            cs[(it["concept"], it["sentiment"])] += 1; n_items += 1
    print(f"  -> {len(ev)} review, {n_items} cặp (concept, sentiment).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ABSA per-review. Chạy 1 hotel (--hotel) hoặc cả corpus (--all).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--hotel", type=int, help="chạy 1 hotel")
    g.add_argument("--all", action="store_true", help="chạy nhiều hotel (batch)")
    g.add_argument("--backfill", nargs="+", metavar="CONCEPT_ID",
                   help="BACKFILL concept MỚI (vd STYLE_JAPANDI) vào evidence đã có — KHÔNG chạy lại "
                        "toàn bộ. Chỉ hỏi LLM về concept này, trên hotel candidate_queue khoanh vùng.")
    ap.add_argument("--limit", type=int, default=None,
                    help="số review/hotel (mẫu cân bằng theo rating). MẶC ĐỊNH = LẤY HẾT review "
                         "đã crawl (≤400/hotel). Đặt số (vd --limit 20) để cắt mẫu nhỏ tiết kiệm tiền.")
    ap.add_argument("--max-hotels", type=int, default=None, help="[batch] tối đa N hotel")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                    help=f"số request LLM SONG SONG (mặc định {DEFAULT_WORKERS}; giảm nếu gặp 429)")
    ap.add_argument("--budget-usd", type=float, default=None,
                    help="[batch] DỪNG khi tổng dự toán vượt ngân sách này (chặn cứng chi phí)")
    ap.add_argument("--dry-run", action="store_true", help="CHỈ dự toán, KHÔNG gọi API")
    ap.add_argument("--yes", action="store_true", help="bỏ xác nhận (chạy thẳng)")
    args = ap.parse_args()

    cfg = active_config()
    is_openai = cfg["provider"] == "openai"
    print(f"LLM: {cfg['provider']}/{cfg['model']}\n")

    # ----- NHÁNH BACKFILL: promote concept mới vào evidence đã có (không chạy lại all) -----
    if args.backfill:
        unknown = [c for c in args.backfill if c not in VOCAB]
        if unknown:
            print(f"[LỖI] concept chưa có trong ontology/core/*.yaml: {unknown}\n"
                  f"  -> thêm vào ontology trước (style.yaml/aspect.yaml) rồi chạy lại."); sys.exit(1)
        # KHOANH HOTEL bằng SYNONYM (không phụ thuộc candidate_queue). Sau promote, concept mới
        # đã có surface_forms trong synonym_dictionary -> quét review hotel có evidence, hotel nào
        # NHẮC tới surface_form của concept thì backfill. Chính xác (dựa text thật) + ít phụ thuộc.
        from knowledge_engineering.common.normalize import normalize as _norm
        SYN = "ontology/synonym_dictionary.yaml"
        want = set(args.backfill)
        # surface_forms (đã fold) trỏ tới concept cần backfill
        syn = (yaml.safe_load(open(SYN, encoding="utf-8")) or {}).get("synonyms", {}) or {}
        forms = [f for f, cids in syn.items() if set(cids) & want and len(f) >= 3]
        if not forms:
            print(f"[LỖI] concept {args.backfill} chưa có surface_form trong synonym_dictionary.\n"
                  f"  -> promote (promote_candidate.py) tạo surface_forms trước."); sys.exit(1)
        # quét hotel có evidence: hotel nào có review chứa 1 trong forms -> vào targets
        targets = []
        for hid in list_review_hotels():
            if not _evidence_path(hid).exists():
                continue
            try:
                revs = json.loads((Path(REVIEWS_DIR) / f"hotel_{hid}_reviews.json")
                                  .read_text(encoding="utf-8")).get("reviews", [])
            except FileNotFoundError:
                continue
            blob = _norm(" . ".join(_review_text(r) for r in revs[:400]), fold=True)
            if any(f in blob for f in forms):
                targets.append(hid)
        scope = f"hotel có evidence + nhắc {forms[:3]}"
        print(f"=== BACKFILL {args.backfill} ===\n  surface_forms: {forms}")
        print(f"  phạm vi: {scope} ({len(targets)} hotel)")
        if args.dry_run:
            print("  --dry-run: không gọi API."); sys.exit(0)
        if is_openai and not args.yes:
            ans = input(f">>> Backfill trên ~{len(targets)} hotel? gõ 'yes': ")
            if ans.strip().lower() != "yes":
                print("Đã hủy."); sys.exit(0)
        total_changed = 0
        for i, hid in enumerate(targets, 1):
            try:
                n = backfill_concepts(hid, args.backfill, max_workers=args.workers, forms=forms)
            except FileNotFoundError:
                continue
            total_changed += n
            if n:
                print(f"  [{i}/{len(targets)}] hotel {hid}: +{n} review có concept mới", flush=True)
        print(f"\nXong backfill. {total_changed} review được bổ sung concept {args.backfill}.")
        print("-> chạy lại profile_builder + build_objects để concept mới vào object.")
        sys.exit(0)

    # ----- danh sách hotel cần chạy -----
    if args.all:
        hotels = list_review_hotels()
        if args.max_hotels:
            hotels = hotels[:args.max_hotels]
    else:
        hotels = [args.hotel]

    # ----- DỰ TOÁN toàn bộ TRƯỚC (gom + chặn ngân sách) -----
    plan = []           # (hotel_id, est) — chỉ hotel còn review todo, trong ngân sách
    total_cost = 0.0; total_todo = 0; total_req = 0; skipped_budget = 0
    for hid in hotels:
        try:
            est = estimate_cost(hid, args.limit, cfg["model"])
        except FileNotFoundError:
            continue
        if est["todo"] == 0:
            continue
        # chặn ngân sách: nếu cộng hotel này vượt budget -> dừng nhận thêm
        if args.budget_usd is not None and is_openai and total_cost + est["est_usd"] > args.budget_usd:
            skipped_budget = len([h for h in hotels if h >= hid])  # ước lượng còn lại
            break
        plan.append((hid, est)); total_cost += est["est_usd"]
        total_todo += est["todo"]; total_req += est["n_requests"]

    print(f"=== DỰ TOÁN {'(BATCH)' if args.all else ''} ===")
    print(f"  hotel sẽ chạy   : {len(plan)}" + (f" (cắt vì ngân sách, bỏ ~{skipped_budget})" if skipped_budget else ""))
    print(f"  review chạy mới : {total_todo}")
    print(f"  REQUEST LLM     : {total_req}  (batch {BATCH_SIZE} review/request — ăn vào trần RPD)")
    if is_openai:
        print(f"  CHI PHÍ ƯỚC TÍNH: ${round(total_cost,4)}  (model {cfg['model']}"
              + (f", trần ${args.budget_usd}" if args.budget_usd else "") + ")")
    else:
        print(f"  provider {cfg['provider']} — miễn phí/local")

    if not plan:
        print("\nKhông có review mới để chạy. Dừng."); sys.exit(0)
    if args.dry_run:
        print("\n--dry-run: CHỈ dự toán, không gọi API."); sys.exit(0)

    if is_openai and not args.yes:
        ans = input(f"\n>>> Chạy {total_todo} review / {len(plan)} hotel (~${round(total_cost,4)})? gõ 'yes': ")
        if ans.strip().lower() != "yes":
            print("Đã hủy — không gọi API, không tốn tiền."); sys.exit(0)

    # ----- CHẠY -----
    import time
    print(f"\n>>> Bắt đầu: {len(plan)} hotel, {args.workers} request song song.\n")
    t_start = time.time()
    done_reviews = 0
    for i, (hid, est) in enumerate(plan, 1):
        t_h = time.time()
        print(f"[{i}/{len(plan)}] hotel {hid} (~{est['todo']} review todo)...", flush=True)
        ev = analyze_hotel(hid, args.limit, max_workers=args.workers)
        _summarize(ev)
        # log tiến độ tổng + ETA (ước theo tốc độ trung bình tới giờ)
        done_reviews += est["todo"]
        elapsed = time.time() - t_start
        rate = done_reviews / elapsed if elapsed > 0 else 0      # review/giây
        remain = total_todo - done_reviews
        eta_min = (remain / rate / 60) if rate > 0 else 0
        print(f"    hotel xong trong {time.time()-t_h:.0f}s | "
              f"tổng {i}/{len(plan)} hotel, ~{done_reviews}/{total_todo} review | "
              f"{rate:.1f} rev/s | ETA ~{eta_min:.0f} phút\n", flush=True)
    print(f"\nXong {len(plan)} hotel trong {(time.time()-t_start)/60:.0f} phút. "
          f"Evidence -> {EVIDENCE_DIR}/hotel_*.json")
