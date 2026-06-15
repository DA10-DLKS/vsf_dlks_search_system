"""verify_relation_golden.py — Bước 12 roadmap: verify relation boost trên golden query set.

A/B: chạy mỗi golden query với boost BẬT vs TẮT (qua query_demo.search), so:
  - số kết quả (recall) — boost chỉ ranking nên KHÔNG được đổi số kết quả;
  - vị trí groundtruth hotel_ids trong top — boost nên giúp (hoặc ít nhất không hại).

Boost ở query_demo áp qua PURPOSE_EVIDENCE (relation graph). Tắt boost = rỗng hóa map đó.

Sinh: docs/reports/ontology/relation_golden_verify.md
Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.verify_relation_golden
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from knowledge_engineering.enrichment import query_demo
from knowledge_engineering.governance.evaluate_query_expansion import parse_golden

ROOT = Path(__file__).resolve().parents[2]
OUT_MD = ROOT / "docs/reports/ontology/relation_golden_verify.md"


def hotel_rank(hits: list[dict], hotel_ids: set[str]) -> int | None:
    """Vị trí (1-based) của groundtruth hotel đầu tiên trong hits; None nếu không có."""
    for i, o in enumerate(hits, 1):
        hid = str(o.get("hotel_id") or o.get("id") or "")
        # golden hotel_ids là số (acc_<n>); object id dạng 'acc_123'
        num = hid.replace("acc_", "")
        if num.isdigit() and int(num) in hotel_ids:
            return i
    return None


def run() -> dict:
    golden = parse_golden()
    rows = []
    orig_evidence = dict(query_demo.PURPOSE_EVIDENCE)
    for gq in golden:
        if not gq.hotel_ids:
            continue
        ids = set(int(x) for x in gq.hotel_ids)
        # boost OFF
        query_demo.PURPOSE_EVIDENCE = {}
        off = query_demo.search(gq.query, limit=50)
        rank_off = hotel_rank(off["hits"], ids)
        # boost ON
        query_demo.PURPOSE_EVIDENCE = orig_evidence
        on = query_demo.search(gq.query, limit=50)
        rank_on = hotel_rank(on["hits"], ids)
        rows.append({
            "qid": gq.qid, "query": gq.query,
            "n_off": off["n"], "n_on": on["n"],
            "rank_off": rank_off, "rank_on": rank_on,
            "trace": on.get("expansion_trace", []),
        })
    query_demo.PURPOSE_EVIDENCE = orig_evidence
    return {"rows": rows}


def verdict(r: dict) -> str:
    if r["n_off"] != r["n_on"]:
        return "⚠ recall đổi (boost không nên lọc!)"
    if r["rank_off"] is None and r["rank_on"] is None:
        return "groundtruth ngoài top"
    if r["rank_on"] is None:
        return "—"
    if r["rank_off"] is None:
        return "boost kéo groundtruth vào top ✅"
    if r["rank_on"] < r["rank_off"]:
        return "boost đẩy groundtruth lên ✅"
    if r["rank_on"] > r["rank_off"]:
        return "⚠ boost đẩy groundtruth xuống"
    return "không đổi"


def write_report(data: dict) -> None:
    rows = data["rows"]
    L = []
    L.append("# Relation Boost — Golden Query Verify (Bước 12 roadmap)")
    L.append("")
    L.append("> Sinh bởi `knowledge_engineering/governance/verify_relation_golden.py`. Read-only.")
    L.append(f"> Ngày: {date.today().isoformat()}. A/B boost ON vs OFF trên golden có groundtruth.")
    L.append("")
    n_recall_change = sum(1 for r in rows if r["n_off"] != r["n_on"])
    n_up = sum(1 for r in rows if r["rank_on"] is not None and r["rank_off"] is not None and r["rank_on"] < r["rank_off"])
    n_in = sum(1 for r in rows if r["rank_off"] is None and r["rank_on"] is not None)
    n_down = sum(1 for r in rows if r["rank_on"] is not None and r["rank_off"] is not None and r["rank_on"] > r["rank_off"])
    L.append("## Tổng kết")
    L.append("")
    L.append(f"- Câu có groundtruth kiểm: **{len(rows)}**")
    L.append(f"- Recall (số kết quả) thay đổi do boost: **{n_recall_change}** (kỳ vọng 0 — boost chỉ ranking)")
    L.append(f"- Boost đẩy groundtruth LÊN top: **{n_up}**")
    L.append(f"- Boost kéo groundtruth VÀO top (trước đó ngoài): **{n_in}**")
    L.append(f"- Boost đẩy groundtruth XUỐNG: **{n_down}**")
    L.append("")
    L.append("## Chi tiết")
    L.append("")
    L.append("| qid | n(off) | n(on) | rank(off) | rank(on) | nhận xét |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['qid']} | {r['n_off']} | {r['n_on']} | "
                 f"{r['rank_off'] if r['rank_off'] else '—'} | {r['rank_on'] if r['rank_on'] else '—'} | {verdict(r)} |")
    L.append("")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data = run()
    write_report(data)
    rows = data["rows"]
    n_recall_change = sum(1 for r in rows if r["n_off"] != r["n_on"])
    print(f"Verify {len(rows)} câu có groundtruth. Recall đổi do boost: {n_recall_change} (kỳ vọng 0).")
    print(f"-> {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
