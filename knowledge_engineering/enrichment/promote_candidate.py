"""promote_candidate.py — Duyệt candidate -> Core ontology BẰNG SCRIPT (không sửa tay core/*.yaml).

Owner: Trương Anh Long (KE, DA10). Đóng lỗ hổng quy trình: trước đây promote concept (tennis/karaoke)
= MỞ FILE core/*.yaml GÕ TAY. Lên production không thể bắt người vận hành sửa YAML liên tục. Script
này biến promote thành: NGƯỜI chỉ đánh `status: approved` + đặt `suggested_concept_id` trong hàng đợi
-> SCRIPT sinh block concept đúng schema vào core, build lại synonym, gợi ý backfill. Có audit log.

NGUYÊN TẮC (mô hình Core/Candidate, _meta.yaml > tiers):
  - KHÔNG tự promote: chỉ xử lý candidate người đã đánh `approved` (con người vẫn là cái van duyệt).
  - Sinh SƯỜN surface_forms từ candidate keyword + examples -> NGƯỜI review (sửa --dry-run trước khi ghi).
  - Idempotent: concept đã có trong core -> SKIP (không ghi đè), báo để người biết.
  - Sau ghi: build_synonym_index (tự gọi) + in lệnh backfill để gán concept mới cho HOTEL CŨ (hồi tố).

HÀNG ĐỢI (1 nguồn duyệt — quyết định 2026-06-10): ontology/candidate/candidate_queue.yaml.
  Candidate từ review (candidate_mining.py, mode --to-queue) được merge VÀO ĐÂY -> người duyệt 1 chỗ.

Chạy:
  # 1. xem sườn sẽ sinh (KHÔNG ghi) — người review surface_forms:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --dry-run
  # 2. ghi thật vào core + build synonym:
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --apply
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

META = "ontology/_meta.yaml"
QUEUE = "ontology/candidate/candidate_queue.yaml"
SOURCE_TAG_MAP = "ontology/source_tag_map.yaml"
CONCEPTS = "ontology/candidate/candidate_concepts.yaml"  # nguồn Tầng 3 (concept ĐẦY ĐỦ song ngữ)
PROMOTE_LOG = "ontology/candidate/promote_log.yaml"   # audit: ai/khi nào/từ candidate nào

# Required theo concept_schema (_meta.yaml). Dùng để VALIDATE block từ candidate_concepts.yaml
# trước khi ghi core (chặn lỗi `en: <tiếng việt>` / thiếu key tận gốc — KHÔNG ghi rác core).
REQUIRED_FIELDS = ["facet", "fact_type", "tier", "label", "description"]


def _load(path: str) -> dict:
    return yaml.safe_load(open(path, encoding="utf-8")) or {}


def load_facet_files() -> dict[str, str]:
    """facet -> đường dẫn file core. _meta.yaml ghi path tương đối từ ontology/ (vd 'core/amenity.yaml');
    script chạy từ gốc repo -> thêm prefix 'ontology/'. Bỏ qua facet không có file (vd style trỏ
    core/style.yaml cũng cần prefix)."""
    meta = _load(META)
    out = {}
    for f, spec in (meta.get("facets") or {}).items():
        fp = spec.get("file", "")
        if fp and not fp.startswith("ontology/"):
            fp = "ontology/" + fp
        out[f] = fp
    return out


def load_existing_concept_ids(core_glob: str = "ontology/core/*.yaml") -> set[str]:
    import glob
    ids: set[str] = set()
    for f in glob.glob(core_glob):
        d = _load(f)
        ids.update((d.get("concepts") or {}).keys())
    return ids


def default_fact_type(facet: str) -> str:
    return (_load(META).get("facets") or {}).get(facet, {}).get("default_fact_type", "soft")


def build_concept_block(cand: dict) -> tuple[str, dict]:
    """Từ 1 candidate (approved) -> (concept_id, block concept đúng concept_schema).

    SƯỜN: label lấy từ candidate_keyword (người sửa); surface_forms gợi ý = keyword + examples
    (gộp, khử trùng) — NGƯỜI review xóa sai/thêm thiếu. description để placeholder cho người sửa.
    """
    cid = cand["suggested_concept_id"]
    facet = cand["suggested_facet"]
    kw = str(cand.get("candidate_keyword", "")).strip()
    # label vi = phần trước dấu "/" hoặc "(" của keyword (gọn lại); người chỉnh sau.
    label_vi = kw.split("/")[0].split("(")[0].strip() or cid
    # surface_forms sườn: examples + keyword, lowercase, khử trùng, giữ thứ tự xuất hiện.
    raw_forms = list(cand.get("examples") or [])
    if kw and "/" not in kw and "(" not in kw:
        raw_forms.insert(0, kw)
    seen, forms_vi = set(), []
    for x in raw_forms:
        x = str(x).strip().lower()
        if x and x not in seen:
            seen.add(x)
            forms_vi.append(x)
    block = {
        "facet": facet,
        "fact_type": default_fact_type(facet),
        "tier": "core",
        "provenance": [cand.get("source", "review"), "candidate_promoted"],
        "label": {"vi": label_vi, "en": label_vi},      # ⚠ người sửa en + chỉnh vi cho đúng
        "surface_forms": {"vi": forms_vi, "en": []},     # ⚠ người review: bỏ sai, thêm en
        "description": {"vi": f"(điền mô tả) {label_vi}", "en": "(fill description)"},
    }
    return cid, block


def append_concepts_to_core(facet_file: str, new_blocks: dict[str, dict]) -> None:
    """Thêm concept mới vào file core. Đọc-sửa-ghi giữ concept cũ; chỉ THÊM, không đụng cái có sẵn."""
    p = Path(facet_file)
    d = _load(facet_file) if p.exists() else {}
    d.setdefault("concepts", {})
    d["concepts"].update(new_blocks)
    header = (f"# {facet_file} — cập nhật bởi promote_candidate.py "
              f"({date.today().isoformat()}). Concept promote từ candidate_queue.\n")
    # giữ header gốc nếu có (dòng comment đầu file) — đọc thô để không mất chú thích.
    orig_head = ""
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        orig_head = "".join(l for l in txt.splitlines(keepends=True) if l.lstrip().startswith("#"))[:2000]
    with open(facet_file, "w", encoding="utf-8") as fh:
        fh.write(orig_head or header)
        yaml.safe_dump(d, fh, allow_unicode=True, sort_keys=False)


def append_promote_log(entries: list[dict]) -> None:
    log = _load(PROMOTE_LOG) if Path(PROMOTE_LOG).exists() else {"promotions": []}
    log.setdefault("promotions", []).extend(entries)
    with open(PROMOTE_LOG, "w", encoding="utf-8") as fh:
        yaml.safe_dump(log, fh, allow_unicode=True, sort_keys=False)


def append_source_tag_map(entries: dict[str, str], path: str = SOURCE_TAG_MAP) -> int:
    """Thêm {chuỗi thô -> concept_id} vào source_tag_map.amenities. Đóng lỗ hổng: amenity gán qua
    Tầng 0 (khớp chuỗi), nên concept amenity mới PHẢI có mapping ở đây mới gán được hotel.

    Bỏ chuỗi đã có (idempotent, KHÔNG ghi đè map cũ). Dùng ruamel-free: đọc-sửa-ghi bằng PyYAML,
    GIỮ header comment đầu file. Trả số entry thật sự thêm."""
    if not entries:
        return 0
    d = yaml.safe_load(open(path, encoding="utf-8")) or {}
    amen = d.setdefault("amenities", {})
    added = 0
    for s, cid in entries.items():
        if s not in amen:           # không đụng chuỗi đã map (tôn trọng quyết định cũ)
            amen[s] = cid
            added += 1
    if added:
        txt = Path(path).read_text(encoding="utf-8")
        head = "".join(l for l in txt.splitlines(keepends=True) if l.lstrip().startswith("#"))
        with open(path, "w", encoding="utf-8") as fh:
            if head:
                fh.write(head)
                if not head.endswith("\n"):
                    fh.write("\n")
            yaml.safe_dump(d, fh, allow_unicode=True, sort_keys=False)
    return added


def run(apply: bool) -> dict:
    queue = _load(QUEUE)
    cands = queue.get("candidates", []) or []
    approved = [c for c in cands if c.get("status") == "approved" and c.get("suggested_concept_id")]
    existing = load_existing_concept_ids()
    facet_files = load_facet_files()

    # gom theo file core, bỏ concept đã tồn tại (idempotent)
    to_write: dict[str, dict[str, dict]] = {}   # facet_file -> {cid: block}
    log_entries, skipped, planned = [], [], []
    for c in approved:
        cid, block = build_concept_block(c)
        if cid in existing:
            skipped.append(cid)
            continue
        ff = facet_files.get(block["facet"])
        if not ff:
            skipped.append(f"{cid}(facet lạ:{block['facet']})")
            continue
        to_write.setdefault(ff, {})[cid] = block
        planned.append((cid, block))
        log_entries.append({"concept_id": cid, "facet": block["facet"],
                            "from_candidate": c.get("candidate_keyword"),
                            "date": date.today().isoformat()})

    return {"approved": approved, "planned": planned, "skipped": skipped,
            "to_write": to_write, "log_entries": log_entries, "apply": apply}


def _validate_full_block(cid: str, block: dict) -> list[str]:
    """VALIDATE block từ candidate_concepts.yaml (Tầng 3) trước khi ghi core. Trả list lỗi CỨNG;
    rỗng = ghi được. Chặn `en==vi` / thiếu key tận gốc — KHÔNG ghi rác vào core."""
    errs = []
    for k in REQUIRED_FIELDS:
        if k not in block:
            errs.append(f"thiếu '{k}'")
    lab = block.get("label") or {}
    if not lab.get("vi") or not lab.get("en"):
        errs.append("label thiếu vi/en")
    elif str(lab["vi"]).strip().lower() == str(lab["en"]).strip().lower():
        errs.append("label.en == label.vi (chưa dịch — sửa tay trước khi promote)")
    desc = block.get("description") or {}
    if not desc.get("vi") or not desc.get("en"):
        errs.append("description thiếu vi/en")
    return errs


def run_concepts(apply: bool) -> dict:
    """Nguồn MỚI: candidate_concepts.yaml (Tầng 3, concept ĐẦY ĐỦ). Ghi THẲNG core, KHÔNG sinh sườn.
    Chỉ xử lý status: approved. STRIP metadata discovery (status/discovery) trước khi ghi core."""
    data = _load(CONCEPTS)
    concepts = data.get("concepts", {}) or {}
    approved = [(cid, b) for cid, b in concepts.items() if b.get("status") == "approved"]
    existing = load_existing_concept_ids()
    facet_files = load_facet_files()

    to_write: dict[str, dict[str, dict]] = {}
    # source_tag_entries: {chuỗi thô -> concept_id} cho AMENITY — ghi vào source_tag_map để Tầng 0
    # ontology_mapper gán được (amenity KHÔNG đi qua synonym). Đóng lỗ hổng "concept vào core nhưng
    # không hotel nào được gán". Nguồn = field source_strings do amenity_suggest (Cách B) sinh.
    source_tag_entries: dict[str, str] = {}
    log_entries, skipped, planned = [], [], []
    for cid, block in approved:
        if cid in existing:
            skipped.append(f"{cid}(đã có)")
            continue
        errs = _validate_full_block(cid, block)
        if errs:
            skipped.append(f"{cid}(lỗi: {'; '.join(errs)})")
            continue
        ff = facet_files.get(block.get("facet"))
        if not ff:
            skipped.append(f"{cid}(facet lạ:{block.get('facet')})")
            continue
        # source_strings (nếu có): chuỗi thô -> concept, gom để ghi source_tag_map. KHÔNG vào core.
        for s in (block.get("source_strings") or []):
            if s:
                source_tag_entries[s] = cid
        # STRIP metadata discovery + source_strings — core chỉ giữ field schema concept
        core_block = {k: v for k, v in block.items()
                      if k not in ("status", "discovery", "source_strings")}
        to_write.setdefault(ff, {})[cid] = core_block
        planned.append((cid, core_block))
        log_entries.append({"concept_id": cid, "facet": block.get("facet"),
                            "from_candidate": f"discovery:{(block.get('discovery') or {}).get('cluster_id','')}",
                            "date": date.today().isoformat()})

    return {"approved": [c for c, _ in approved], "planned": planned, "skipped": skipped,
            "to_write": to_write, "log_entries": log_entries,
            "source_tag_entries": source_tag_entries, "apply": apply}


def _print_plan(res: dict) -> None:
    print(f"Candidate approved: {len(res['approved'])} | "
          f"sẽ promote MỚI: {len(res['planned'])} | bỏ qua (đã có/lỗi): {len(res['skipped'])}")
    if res["skipped"]:
        print(f"  bỏ qua: {res['skipped']}")
    for cid, block in res["planned"]:
        print(f"\n--- {cid}  (facet={block['facet']}, fact_type={block['fact_type']}) ---")
        print(yaml.safe_dump({cid: block}, allow_unicode=True, sort_keys=False), end="")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Promote candidate approved -> Core (script, không sửa tay).")
    ap.add_argument("--source", choices=["queue", "concepts"], default="queue",
                    help="queue=candidate_queue.yaml (sườn keyword, sinh sườn); "
                         "concepts=candidate_concepts.yaml (Tầng 3, concept ĐẦY ĐỦ, ghi thẳng). Mặc định queue.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="CHỈ in concept sẽ ghi (mặc định)")
    g.add_argument("--apply", action="store_true", help="GHI thật vào core/*.yaml + build synonym")
    args = ap.parse_args()

    print(f"Nguồn: {args.source} "
          f"({'candidate_concepts.yaml — concept đầy đủ' if args.source == 'concepts' else 'candidate_queue.yaml — sinh sườn'})\n")
    res = run_concepts(apply=args.apply) if args.source == "concepts" else run(apply=args.apply)
    _print_plan(res)

    if not args.apply:
        print("\n[dry-run] CHƯA ghi. Review sườn trên (đặc biệt surface_forms + description),"
              " chỉnh trong candidate_queue.yaml nếu cần, rồi chạy lại với --apply.")
        sys.exit(0)

    if not res["planned"]:
        print("\nKhông có concept mới để ghi."); sys.exit(0)

    for facet_file, blocks in res["to_write"].items():
        append_concepts_to_core(facet_file, blocks)
        print(f"\n[ghi] {len(blocks)} concept -> {facet_file}")
    append_promote_log(res["log_entries"])
    print(f"[log] ghi {len(res['log_entries'])} mục -> {PROMOTE_LOG}")

    # AMENITY: ghi source_strings -> source_tag_map (Tầng 0). Concept amenity KHÔNG đi qua synonym;
    # thiếu bước này thì concept vào core nhưng KHÔNG hotel nào được gán (lỗ hổng đã gặp với BBQ).
    st_added = append_source_tag_map(res.get("source_tag_entries") or {})
    if st_added:
        print(f"[source_tag_map] thêm {st_added} ánh xạ chuỗi-thô -> concept (amenity gán được Tầng 0)")

    # build lại synonym để concept mới có surface form (rule + query nhận ra)
    print("\n[build] sinh lại synonym_dictionary...")
    from knowledge_engineering.common.build_synonym_index import write as build_synonym
    n, conf = build_synonym()
    print(f"  -> {n} surface form ({conf} đa-concept)")

    new_ids = [cid for cid, _ in res["planned"]]
    has_amenity = bool(res.get("source_tag_entries"))
    print("\n=== BƯỚC TIẾP (gán concept mới cho HOTEL CŨ — hồi tố, không chạy lại all) ===")
    if has_amenity:
        # amenity = HARD, gán qua ontology_mapper (KHÔNG cần LLM backfill). Chạy mapper lại là đủ.
        print("  # amenity (HARD) — chạy lại mapper để gán theo source_tag_map vừa cập nhật:")
        print("  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.ontology_mapper")
    print("  # concept SOFT (style/aspect từ review) — cần backfill LLM:")
    print(f"  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.absa "
          f"--backfill {' '.join(new_ids)} --yes")
    print("  rồi: profile_builder + build_objects  (đưa concept mới vào object)")
