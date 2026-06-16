"""eval_golden.py — Đo pipeline hybrid trên golden_set_v1.json (Node 7 roadmap evaluation).

Chạy run_hybrid_search cho từng câu golden, so top_n hotel_id với relevant_hotel_ids -> tính
Recall@K, Precision@K, MRR, Hit@K. Mặc định chạy KHÔNG cần service (candidate + nhãn KE) để
đo được ngay; cắm vector/bm25 service khi có index để đo bản đầy đủ.

Chạy: .venv/Scripts/python.exe -X utf8 -m evaluation.retrieval_metrics.eval_golden
"""

from __future__ import annotations

import json
from typing import Any

GOLDEN_DEFAULT = "data/golden_dataset/golden_set_v2.json"


def _metrics_for(predicted: list[int], relevant: list[int], k: int) -> dict[str, float]:
    pred_k = predicted[:k]
    rel = set(relevant)
    if not rel:
        return {"recall": 0.0, "precision": 0.0, "hit": 0.0, "rr": 0.0}
    hit_set = rel & set(pred_k)
    recall = len(hit_set) / len(rel)
    precision = len(hit_set) / max(len(pred_k), 1)
    hit = 1.0 if hit_set else 0.0
    rr = 0.0
    for i, h in enumerate(pred_k, start=1):
        if h in rel:
            rr = 1.0 / i
            break
    return {"recall": recall, "precision": precision, "hit": hit, "rr": rr}


def evaluate(
    golden_path: str = GOLDEN_DEFAULT,
    k: int = 10,
    vector_service=None,
    bm25_service=None,
    limit: int | None = None,
) -> dict[str, Any]:
    from retrieval.hybrid_search import run_hybrid_search

    golden = json.load(open(golden_path, encoding="utf-8"))
    # v2: chỉ đo câu active (excluded = nhãn không đủ tin cậy, không tính vào metric)
    golden = [g for g in golden if g.get("eval_status", "active") == "active"]
    if limit:
        golden = golden[:limit]

    agg = {"recall": 0.0, "precision": 0.0, "hit": 0.0, "rr": 0.0}
    rows = []
    for g in golden:
        relevant = g.get("relevant_hotel_ids", [])
        if not relevant:
            continue
        res = run_hybrid_search(
            g["query"], vector_service=vector_service, bm25_service=bm25_service, top_n=k
        )
        predicted = [c["hotel_id"] for c in res["context_package"]["chunks"]]
        m = _metrics_for(predicted, relevant, k)
        for key in agg:
            agg[key] += m[key]
        rows.append({"query_id": g["query_id"], "query": g["query"][:50],
                     "n_relevant": len(relevant), **m})

    n = len(rows) or 1
    summary = {key: round(val / n, 4) for key, val in agg.items()}
    summary["n_queries"] = len(rows)
    summary["k"] = k
    return {"summary": summary, "per_query": rows}


def main() -> int:
    result = evaluate(k=10)
    s = result["summary"]
    print(f"=== Golden eval (n={s['n_queries']} câu, K={s['k']}, KHÔNG service text) ===")
    print(f"  Recall@{s['k']}:    {s['recall']}")
    print(f"  Precision@{s['k']}: {s['precision']}")
    print(f"  Hit@{s['k']}:       {s['hit']}")
    print(f"  MRR:          {s['rr']}")
    # vài câu kém nhất để soi
    worst = sorted(result["per_query"], key=lambda r: r["recall"])[:5]
    print("  5 câu recall thấp nhất:")
    for r in worst:
        print(f"    [{r['query_id']}] recall={r['recall']:.2f} | {r['query']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
