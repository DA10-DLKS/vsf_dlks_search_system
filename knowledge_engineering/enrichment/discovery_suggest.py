"""discovery_suggest.py — TẦNG 3 pipeline Discovery: cluster -> ĐỀ XUẤT concept ĐẦY ĐỦ (LLM).

Owner: Trương Anh Long (KE, DA10). Đọc clusters.json (Tầng 2) -> mỗi cluster đủ lớn -> 1 LLM call
sinh ĐỀ XUẤT concept HOÀN CHỈNH song ngữ (concept_id, label vi/en, surface_forms vi/en,
description vi/en, facet) + CẢNH BÁO tự động (script gắn, không nhờ LLM):
  - neg_ratio cao -> "chủ yếu tiêu cực, có thể là than phiền (ASPECT) không phải STYLE".
  - gần concept core đã có (embedding) -> "cân nhắc trùng/gộp".

NGUYÊN TẮC:
  - KHÔNG để LLM tự ghi ontology. Output = candidate_concepts.yaml (status: pending) cho NGƯỜI duyệt.
  - VALIDATE chặn lỗi `en: <tiếng việt>` tận gốc: concept_id đúng dạng, label.en != label.vi,
    đủ key vi+en. Thiếu -> SKIP cluster đó (KHÔNG ghi rác), log để người biết.
  - Chạy lại -> MERGE theo concept_id: GIỮ concept người đã approved/rejected, chỉ cập nhật pending.

Chạy:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_suggest
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_suggest --offline  # smoke (embed dup-check)
"""

from __future__ import annotations

import argparse
import glob
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from knowledge_engineering.enrichment.llm import complete_json, active_config

CLUSTERS_JSON = "knowledge_engineering/enrichment/clusters.json"
OUT_YAML = "ontology/candidate/candidate_concepts.yaml"
META = "ontology/_meta.yaml"
CORE_GLOB = "ontology/core/*.yaml"

DEFAULT_MIN_HOTELS = 3       # cluster < N hotel -> quá hiếm, bỏ (đỡ tốn LLM call)
NEG_WARN = 0.6               # neg_ratio >= -> cảnh báo "chủ yếu tiêu cực"
SIM_DUP = 0.75               # cosine label_hint vs concept core >= -> cảnh báo trùng
CID_RE = re.compile(r"^[A-Z]+_[A-Z0-9_]+$")
VALID_FACETS = {"style", "amenity", "setting", "purpose", "aspect"}


def default_fact_type(facet: str) -> str:
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    return (meta.get("facets") or {}).get(facet, {}).get("default_fact_type", "soft")


def load_core_concepts() -> list[dict]:
    """[{concept_id, facet, label_vi, label_en}] cho concept core — để cảnh báo trùng."""
    out = []
    for f in sorted(glob.glob(CORE_GLOB)):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        for cid, v in (d.get("concepts") or {}).items():
            lab = v.get("label", {}) or {}
            out.append({"concept_id": cid, "facet": v.get("facet", ""),
                        "label_vi": lab.get("vi", ""), "label_en": lab.get("en", "")})
    return out


SUGGEST_SYSTEM = """Bạn là taxonomist khách sạn. Cho 1 NHÓM cụm từ đồng nghĩa rút từ review thật
(kèm sentiment + ví dụ), hãy đề xuất 1 concept cho ontology khách sạn.

Trả DUY NHẤT JSON:
{"concept_id":"<PREFIX>_<TEN>",
 "facet":"style|amenity|setting|purpose",
 "label":{"vi":"...","en":"..."},
 "surface_forms":{"vi":["..."],"en":["..."]},
 "description":{"vi":"...","en":"..."},
 "rationale":"vì sao nên là concept này"}

QUY TẮC BẮT BUỘC:
- concept_id: PREFIX theo facet (style->STYLE_, amenity->AMEN_, setting->SETTING_, purpose->PURPOSE_),
  phần sau là TÊN tiếng Anh CHỮ HOA không dấu, nối bằng _ (vd STYLE_VINTAGE, AMEN_INFINITY_POOL).
- label.en PHẢI là tiếng Anh THẬT, TUYỆT ĐỐI KHÔNG để bằng label.vi.
- surface_forms.vi gồm các member + biến thể hợp lý; surface_forms.en có ÍT NHẤT 1 từ tiếng Anh.
- description.vi + description.en đều là câu mô tả ngắn (en bằng tiếng Anh thật).
- KHÔNG bịa concept không khớp cụm. Chọn facet đúng nhất (phong cách=style, tiện ích=amenity,
  bối cảnh/vị trí=setting, mục đích chuyến đi=purpose)."""


def _cluster_user_prompt(c: dict) -> str:
    sd = c["sentiment_dist"]
    return (f"Nhóm cụm (đồng nghĩa): {c['members']}\n"
            f"Xuất hiện ở {c['hotel_count']} khách sạn, {c['freq']} lần.\n"
            f"Sentiment: positive={sd.get('positive',0)}, negative={sd.get('negative',0)}, "
            f"neutral={sd.get('neutral',0)}, mixed={sd.get('mixed',0)} (neg_ratio={c['neg_ratio']}).\n"
            f"Ví dụ trích từ review: {c.get('examples', [])[:5]}")


def _validate(sug: dict) -> tuple[bool, list[str]]:
    """Trả (ok_để_ghi, [lỗi/cảnh báo]). ok=False -> SKIP (không ghi rác core về sau)."""
    errs = []
    cid = sug.get("concept_id", "")
    if not CID_RE.match(cid or ""):
        errs.append(f"concept_id sai dạng: {cid!r}")
    facet = sug.get("facet", "")
    if facet not in VALID_FACETS:
        errs.append(f"facet lạ: {facet!r}")
    lab = sug.get("label") or {}
    if not lab.get("vi") or not lab.get("en"):
        errs.append("thiếu label vi/en")
    elif lab["vi"].strip().lower() == lab["en"].strip().lower():
        errs.append("label.en == label.vi (chưa dịch)")
    desc = sug.get("description") or {}
    if not desc.get("vi") or not desc.get("en"):
        errs.append("thiếu description vi/en")
    sf = sug.get("surface_forms") or {}
    if not (sf.get("vi") or sf.get("en")):
        errs.append("thiếu surface_forms")
    # chỉ những lỗi CỨNG (dạng id/facet/thiếu key) mới chặn ghi; "en==vi" là cảnh báo (vẫn ghi, đánh dấu)
    blocking = [e for e in errs if "==" not in e]
    return (len(blocking) == 0), errs


def suggest(clusters: list[dict], core: list[dict], offline: bool,
            min_hotels: int) -> dict[str, dict]:
    """Mỗi cluster đủ lớn -> 1 LLM call -> block concept đầy đủ + metadata discovery. Trả {cid: block}."""
    from indexing.embedding.registry import get_embedding_model
    model = get_embedding_model("bge-m3", offline=offline)

    # embed concept core 1 lần (để cảnh báo trùng)
    core_vecs = []
    if core:
        reps = [f"{c['label_vi']} / {c['label_en']}" for c in core]
        core_vecs = [r.vector for r in model.embed(reps)]

    import numpy as np
    out: dict[str, dict] = {}
    for c in clusters:
        if c["hotel_count"] < min_hotels:
            continue
        sug = complete_json(SUGGEST_SYSTEM, _cluster_user_prompt(c), temperature=0)
        ok, errs = _validate(sug)
        if not ok:
            print(f"  [SKIP] {c['cluster_id']} ({c['members'][:3]}): {errs}")
            continue
        cid = sug["concept_id"]

        warnings = []
        if c["neg_ratio"] >= NEG_WARN:
            warnings.append(f"⚠ chủ yếu tiêu cực ({int(c['neg_ratio']*100)}%) — có thể là than "
                            f"phiền (ASPECT) không phải {sug['facet'].upper()}; cân nhắc đổi facet/bỏ")
        if "label.en == label.vi (chưa dịch)" in errs:
            warnings.append("⚠ label.en chưa dịch — sửa tay trước khi promote")
        # cảnh báo trùng concept core (embedding label_hint vs core reps)
        if core_vecs:
            hv = model.embed([c["label_hint"]])[0].vector
            sims = np.asarray(core_vecs, dtype="float32") @ np.asarray(hv, dtype="float32")
            j = int(sims.argmax())
            if float(sims[j]) >= SIM_DUP:
                warnings.append(f"⚠ gần {core[j]['concept_id']} "
                                f"(sim {float(sims[j]):.2f}) — cân nhắc trùng/gộp")

        block = {
            "facet": sug["facet"],
            "fact_type": default_fact_type(sug["facet"]),
            "tier": "core",
            "provenance": ["review", "discovery_llm"],
            "label": {"vi": sug["label"]["vi"], "en": sug["label"]["en"]},
            "surface_forms": {"vi": (sug.get("surface_forms") or {}).get("vi", []) or [],
                              "en": (sug.get("surface_forms") or {}).get("en", []) or []},
            "description": {"vi": sug["description"]["vi"], "en": sug["description"]["en"]},
            "status": "pending",
            "discovery": {
                "cluster_id": c["cluster_id"], "hotel_count": c["hotel_count"], "freq": c["freq"],
                "sentiment_dist": c["sentiment_dist"], "neg_ratio": c["neg_ratio"],
                "warnings": warnings, "members": c["members"],
                "examples": c.get("examples", [])[:5],
                "rationale": sug.get("rationale", ""),
            },
        }
        out[cid] = block
    return out


def merge_existing(new_blocks: dict[str, dict], out_yaml: str) -> dict[str, dict]:
    """MERGE theo concept_id: GIỮ concept người đã approved/rejected; chỉ thêm/cập nhật pending."""
    p = Path(out_yaml)
    existing = {}
    if p.exists():
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        existing = d.get("concepts", {}) or {}
    merged = dict(existing)
    kept = 0
    for cid, block in new_blocks.items():
        old = existing.get(cid)
        if old and old.get("status") in ("approved", "rejected"):
            kept += 1
            continue                      # tôn trọng quyết định của người, không ghi đè
        merged[cid] = block
    if kept:
        print(f"  ({kept} concept đã approved/rejected -> GIỮ nguyên, không ghi đè)")
    return merged


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TẦNG 3 Discovery: cluster -> đề xuất concept đầy đủ (LLM).")
    ap.add_argument("--in", dest="inp", default=CLUSTERS_JSON, help="clusters.json")
    ap.add_argument("--out", default=OUT_YAML, help="candidate_concepts.yaml")
    ap.add_argument("--min-hotels", type=int, default=DEFAULT_MIN_HOTELS,
                    help=f"cluster < N hotel thì bỏ (mặc định {DEFAULT_MIN_HOTELS})")
    ap.add_argument("--offline", action="store_true",
                    help="HashEmbeddingModel cho dup-check (smoke); LLM vẫn theo .env")
    args = ap.parse_args()

    import json
    data = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    clusters = data.get("clusters", [])
    cfg = active_config()
    print(f"LLM: {cfg['provider']}/{cfg['model']} | clusters: {len(clusters)} "
          f"(xử lý >= {args.min_hotels} hotel)")

    core = load_core_concepts()
    blocks = suggest(clusters, core, args.offline, args.min_hotels)
    if not blocks:
        print("Không sinh được đề xuất nào (cluster nhỏ hoặc validate fail)."); raise SystemExit(0)

    merged = merge_existing(blocks, args.out)
    out = {"version": "1.0",
           "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "model": cfg["model"], "concepts": merged}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    # header giải thích (giữ ngắn) + dump
    header = ("# candidate/candidate_concepts.yaml — ĐỀ XUẤT concept ĐẦY ĐỦ (Tầng 3 discovery).\n"
              "# KHÁC candidate_queue.yaml (sườn keyword cũ): concept ở đây đã hoàn chỉnh vi/en/desc.\n"
              "# NGƯỜI duyệt: sửa nhẹ -> đặt status: approved (hoặc rejected). Sau đó:\n"
              "#   promote_candidate.py --source concepts --apply  (ghi core + build synonym).\n")
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(out, fh, allow_unicode=True, sort_keys=False)
    print(f"-> {len(blocks)} đề xuất mới, tổng {len(merged)} concept -> {args.out}")
    for cid, b in blocks.items():
        w = b["discovery"]["warnings"]
        print(f"  {cid} ({b['facet']}) {b['label']} {'| ' + ' '.join(w) if w else ''}")
