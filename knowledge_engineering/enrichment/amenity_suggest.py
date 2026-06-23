"""amenity_suggest.py — TẦNG 3 cho AMENITY: candidate (trường amenities) -> concept ĐẦY ĐỦ (LLM).

Owner: Trương Anh Long (KE, DA10).

ĐÂY LÀ "CÁCH B" — đối xứng với discovery_suggest.py (vốn cho STYLE/SETTING từ review):
  discovery_suggest: cluster review  -> LLM -> concept đầy đủ (style/setting/purpose)
  amenity_suggest  : chuỗi amenities -> LLM -> concept đầy đủ AMENITY + ÁNH XẠ chuỗi-thô->concept

KHÁC BIỆT THEN CHỐT so với discovery_suggest: amenity gán qua source_tag_map (Tầng 0, khớp
chuỗi CHÍNH XÁC) — KHÔNG qua synonym. Nên LLM ở đây phải xuất THÊM `source_strings`: các chuỗi
amenity THÔ thuộc concept. promote_candidate (đã sửa) đọc field này -> ghi source_tag_map ->
ontology_mapper Tầng 0 gán được. Nếu thiếu bước này, concept amenity mới vào core nhưng KHÔNG
hotel nào được gán (lỗ hổng đã gặp với AMEN_BBQ).

LUỒNG:
  1. amenity_miner.mine() -> candidate (chuỗi amenity CHƯA map, đã lọc rác/IDF).
  2. gom thành BATCH (nhiều chuỗi / 1 LLM call — tiết kiệm RPD; xem absa-rpd-batching).
  3. LLM gom chuỗi -> concept, mỗi concept: concept_id/label/surface_forms/description +
     source_strings (CHỌN TỪ danh sách đưa vào, KHÔNG bịa).
  4. validate (đúng schema, AMEN_ prefix, en!=vi) -> ghi candidate_concepts.yaml (status pending).
  5. NGƯỜI duyệt approve -> promote_candidate --source concepts --apply (ghi core + source_tag_map).

FALLBACK (KHÔNG có mạng/LLM — "Cách A" rẻ nằm trong B): --offline KHÔNG gọi LLM, mà gợi ý
mỗi chuỗi 1 concept-sườn theo heuristic + để source_strings = [chính chuỗi đó]. Người vẫn duyệt.
Mục đích: pipeline KHÔNG kẹt khi API timeout (đã gặp với absa backfill).

Chạy:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.amenity_suggest --dry-run
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.amenity_suggest --apply
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.amenity_suggest --offline --apply
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from knowledge_engineering.enrichment.amenity_miner import mine
from knowledge_engineering.enrichment.llm import active_config, complete_json

OUT_YAML = "ontology/candidate/candidate_concepts.yaml"
CORE_GLOB = "ontology/core/*.yaml"
CID_RE = re.compile(r"^AMEN_[A-Z0-9_]+$")

BATCH_SIZE = 40          # chuỗi amenity / 1 LLM call (gom để tiết kiệm RPD)
TOP_CANDIDATES = 120     # chỉ đưa N candidate đặc trưng nhất cho LLM (đuôi hiếm để vòng sau)


SUGGEST_SYSTEM = """Bạn là taxonomist khách sạn. Tôi đưa 1 DANH SÁCH chuỗi tiện ích (amenity)
THÔ lấy từ dữ liệu khách sạn (kèm số khách sạn có). Hãy gom các chuỗi CÙNG NGHĨA thành concept
ontology AMENITY và đề xuất concept đầy đủ.

Trả DUY NHẤT JSON:
{"concepts":[
  {"concept_id":"AMEN_<TEN>",
   "label":{"vi":"...","en":"..."},
   "surface_forms":{"vi":["..."],"en":["..."]},
   "description":{"vi":"...","en":"..."},
   "source_strings":["<chuỗi thô CHỌN TỪ danh sách tôi đưa>", "..."],
   "rationale":"vì sao là concept này"}
]}

QUY TẮC BẮT BUỘC:
- concept_id: BẮT ĐẦU "AMEN_", phần sau là TÊN tiếng Anh CHỮ HOA không dấu nối bằng _ (AMEN_BBQ).
- source_strings: PHẢI là các chuỗi LẤY NGUYÊN VĂN từ danh sách tôi đưa (để map chính xác). KHÔNG bịa.
- label.en là tiếng Anh THẬT, KHÔNG bằng label.vi. description.vi + description.en đều có.
- CHỈ gom chuỗi là TIỆN ÍCH PHÂN BIỆT ĐƯỢC (khách hay tìm: bbq, máy giặt, sạc xe điện, lò sưởi...).
  BỎ QUA (đừng tạo concept) các chuỗi là DỊCH VỤ VẬN HÀNH phổ thông / vệ sinh / vật dụng phòng
  vụn vặt (lễ tân, dọn phòng, khử trùng, gương, móc treo...) — chúng không phải tiện ích lọc.
- 1 concept có thể gom NHIỀU chuỗi đồng nghĩa. Chuỗi không đáng -> không đưa vào concept nào."""


def _batch_prompt(rows: list[dict]) -> str:
    lines = [f"- {r['candidate_keyword']} ({r['hotel_count']} khách sạn)" for r in rows]
    return "Danh sách chuỗi tiện ích thô:\n" + "\n".join(lines)


def load_existing_core_ids() -> set[str]:
    import glob
    ids: set[str] = set()
    for f in glob.glob(CORE_GLOB):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        ids.update((d.get("concepts") or {}).keys())
    return ids


def _validate(c: dict, allowed_strings: set[str]) -> tuple[bool, list[str]]:
    """Trả (ok_ghi, [lỗi]). Chặn rác: id sai dạng, en==vi, thiếu key, source_strings BỊA."""
    errs: list[str] = []
    cid = c.get("concept_id", "")
    if not CID_RE.match(cid or ""):
        errs.append(f"concept_id sai dạng: {cid!r}")
    lab = c.get("label") or {}
    if not lab.get("vi") or not lab.get("en"):
        errs.append("thiếu label vi/en")
    elif str(lab["vi"]).strip().lower() == str(lab["en"]).strip().lower():
        errs.append("label.en == label.vi (chưa dịch)")
    desc = c.get("description") or {}
    if not desc.get("vi") or not desc.get("en"):
        errs.append("thiếu description vi/en")
    ss = c.get("source_strings") or []
    if not ss:
        errs.append("thiếu source_strings (không map được vào hotel)")
    # source_strings PHẢI nằm trong danh sách đưa vào (chặn LLM bịa chuỗi không có trong data)
    bogus = [s for s in ss if s not in allowed_strings]
    if bogus:
        errs.append(f"source_strings bịa (không có trong data): {bogus[:3]}")
    blocking = [e for e in errs if "==" not in e]   # en==vi chỉ là cảnh báo
    return (len(blocking) == 0), errs


def _to_block(c: dict, errs: list[str]) -> dict:
    """Chuẩn hóa 1 concept LLM -> block candidate_concepts (giống discovery_suggest, thêm
    source_strings để promote ghi source_tag_map)."""
    warnings = []
    if "label.en == label.vi (chưa dịch)" in errs:
        warnings.append("⚠ label.en chưa dịch — sửa tay trước khi promote")
    sf = c.get("surface_forms") or {}
    # source_strings hợp nhất vào surface_forms.vi luôn (để synonym cũng bắt được ở Tầng 1 text)
    src = list(dict.fromkeys(c.get("source_strings") or []))
    sf_vi = list(dict.fromkeys((sf.get("vi") or []) + src))
    return {
        "facet": "amenity",
        "fact_type": "hard",
        "tier": "core",
        "provenance": ["amenity_field", "discovery_llm"],
        "label": {"vi": c["label"]["vi"], "en": c["label"]["en"]},
        "surface_forms": {"vi": sf_vi, "en": sf.get("en", []) or []},
        "description": {"vi": c["description"]["vi"], "en": c["description"]["en"]},
        # source_strings: chuỗi THÔ -> promote_candidate ghi vào source_tag_map.amenities.
        "source_strings": src,
        "status": "pending",
        "discovery": {
            "source": "amenity_field",
            "warnings": warnings,
            "rationale": c.get("rationale", ""),
        },
    }


def suggest_llm(rows: list[dict], allowed: set[str]) -> dict[str, dict]:
    """Gọi LLM theo batch -> {cid: block}. Bỏ qua concept validate fail."""
    out: dict[str, dict] = {}
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        resp = complete_json(SUGGEST_SYSTEM, _batch_prompt(batch), temperature=0)
        for c in resp.get("concepts", []) or []:
            ok, errs = _validate(c, allowed)
            if not ok:
                print(f"  [SKIP] {c.get('concept_id')}: {errs}")
                continue
            out[c["concept_id"]] = _to_block(c, errs)
    return out


def suggest_offline(rows: list[dict]) -> dict[str, dict]:
    """FALLBACK không LLM (Cách A): mỗi chuỗi -> 1 concept-sườn, source_strings = [chính chuỗi].
    KHÔNG gom đồng nghĩa (cần LLM/người). label/desc là sườn để NGƯỜI sửa. Dùng khi API hỏng."""
    out: dict[str, dict] = {}
    for r in rows:
        kw = r["candidate_keyword"]
        slug = re.sub(r"[^a-z0-9]+", "_", _ascii(kw).lower()).strip("_").upper()[:30]
        cid = f"AMEN_{slug}" or "AMEN_X"
        if cid in out:
            continue
        out[cid] = {
            "facet": "amenity", "fact_type": "hard", "tier": "core",
            "provenance": ["amenity_field", "offline_stub"],
            "label": {"vi": kw, "en": kw},          # ⚠ người dịch en + sửa
            "surface_forms": {"vi": [kw], "en": []},
            "description": {"vi": f"(điền mô tả) {kw}", "en": "(fill description)"},
            "source_strings": [kw],
            "status": "pending",
            "discovery": {"source": "amenity_field", "warnings":
                          ["⚠ offline stub — LLM chưa gom đồng nghĩa; người sửa label/en/desc"],
                          "rationale": ""},
        }
    return out


def _ascii(s: str) -> str:
    from knowledge_engineering.common.normalize import strip_diacritics
    return strip_diacritics(s)


def merge_existing(new_blocks: dict[str, dict], out_yaml: str) -> tuple[dict[str, dict], int]:
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
            continue
        merged[cid] = block
    return merged, kept


def main() -> None:
    ap = argparse.ArgumentParser(
        description="TẦNG 3 AMENITY: chuỗi amenities -> concept đầy đủ + source mapping (LLM).")
    ap.add_argument("--out", default=OUT_YAML)
    ap.add_argument("--top", type=int, default=TOP_CANDIDATES,
                    help=f"số candidate đặc trưng nhất đưa cho LLM (mặc định {TOP_CANDIDATES})")
    ap.add_argument("--offline", action="store_true",
                    help="KHÔNG gọi LLM — sinh concept-sườn (fallback khi API hỏng)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="in concept đề xuất, KHÔNG ghi")
    g.add_argument("--apply", action="store_true", help="ghi vào candidate_concepts.yaml")
    args = ap.parse_args()

    res = mine()
    rows = res["candidates"][:args.top]
    allowed = {r["candidate_keyword"] for r in rows}
    print(f"Candidate amenity (chưa map): {res['n_candidates']} | đưa cho tầng 3: {len(rows)}")

    if args.offline:
        print("[offline] KHÔNG gọi LLM — sinh concept-sườn để người duyệt.")
        blocks = suggest_offline(rows)
    else:
        cfg = active_config()
        print(f"LLM: {cfg['provider']}/{cfg['model']} | batch={BATCH_SIZE}")
        try:
            blocks = suggest_llm(rows, allowed)
        except Exception as e:  # noqa: BLE001
            print(f"\n[LỖI LLM] {e}\n-> chạy lại với --offline để KHÔNG kẹt (sinh sườn), "
                  "hoặc thử lại khi mạng ổn.")
            raise SystemExit(1)

    # loại concept đã có trong core (idempotent)
    core_ids = load_existing_core_ids()
    blocks = {cid: b for cid, b in blocks.items() if cid not in core_ids}
    print(f"Concept đề xuất MỚI (chưa có core): {len(blocks)}")
    for cid, b in blocks.items():
        w = b["discovery"]["warnings"]
        print(f"  {cid:26s} {b['label']['vi']:30s} <- {len(b['source_strings'])} chuỗi "
              f"{'| ' + ' '.join(w) if w else ''}")

    if not args.apply:
        print("\n[dry-run] CHƯA ghi. Chạy --apply để ghi candidate_concepts.yaml.")
        return

    merged, kept = merge_existing(blocks, args.out)
    if kept:
        print(f"  ({kept} concept đã approved/rejected -> GIỮ nguyên)")
    cfg = {"model": "offline-stub"} if args.offline else active_config()
    out = {"version": "1.0",
           "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "model": cfg.get("model", "?"), "concepts": merged}
    header = ("# candidate/candidate_concepts.yaml — ĐỀ XUẤT concept ĐẦY ĐỦ (Tầng 3 discovery).\n"
              "# KHÁC candidate_queue.yaml (sườn keyword cũ): concept ở đây đã hoàn chỉnh vi/en/desc.\n"
              "# AMENITY (amenity_suggest): có field source_strings -> promote ghi source_tag_map.\n"
              "# NGƯỜI duyệt: sửa nhẹ -> status: approved -> promote_candidate --source concepts --apply.\n")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(out, fh, allow_unicode=True, sort_keys=False)
    print(f"\n-> {len(blocks)} đề xuất mới, tổng {len(merged)} concept -> {args.out}")


if __name__ == "__main__":
    main()
