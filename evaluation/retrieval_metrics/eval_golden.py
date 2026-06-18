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


def _ndcg(pred_k: list[int], rel: set[int]) -> float:
    """nDCG@k relevance nhị phân. IDCG = xếp tối đa min(|rel|,k) hit lên đầu. V4: nDCG quan tâm
    THỨ HẠNG, không phạt vì không gói hết 38-40 ground-truth vào k ô (khác recall@k)."""
    import math

    dcg = sum(1.0 / math.log2(i + 1) for i, h in enumerate(pred_k, start=1) if h in rel)
    ideal = min(len(rel), len(pred_k))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _metrics_for(predicted: list[int], relevant: list[int], k: int) -> dict[str, float]:
    pred_k = predicted[:k]
    rel = set(relevant)
    if not rel:
        return {"recall": 0.0, "precision": 0.0, "hit": 0.0, "rr": 0.0, "ndcg": 0.0}
    hit_set = rel & set(pred_k)
    recall = len(hit_set) / len(rel)
    precision = len(hit_set) / max(len(pred_k), 1)
    hit = 1.0 if hit_set else 0.0
    rr = 0.0
    for i, h in enumerate(pred_k, start=1):
        if h in rel:
            rr = 1.0 / i
            break
    return {"recall": recall, "precision": precision, "hit": hit, "rr": rr,
            "ndcg": _ndcg(pred_k, rel)}


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

    agg = {"recall": 0.0, "precision": 0.0, "hit": 0.0, "rr": 0.0, "ndcg": 0.0}
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


def evaluate_multi_k(
    ks: tuple[int, ...] = (10, 20, 50),
    golden_path: str = GOLDEN_DEFAULT,
    vector_service=None,
    bm25_service=None,
    limit: int | None = None,
) -> dict[int, dict[str, Any]]:
    """V4: chạy pipeline 1 LẦN (top_n=max(ks)) rồi tính metric cho từng K — báo cáo Recall@K,
    nDCG@10... song song. Tránh ảo giác recall@10 thấp khi ground-truth có 15-40 hotel/câu."""
    from retrieval.hybrid_search import run_hybrid_search

    kmax = max(ks)
    golden = json.load(open(golden_path, encoding="utf-8"))
    golden = [g for g in golden if g.get("eval_status", "active") == "active"]
    if limit:
        golden = golden[:limit]

    aggs = {k: {"recall": 0.0, "precision": 0.0, "hit": 0.0, "rr": 0.0, "ndcg": 0.0} for k in ks}
    n = 0
    for g in golden:
        relevant = g.get("relevant_hotel_ids", [])
        if not relevant:
            continue
        res = run_hybrid_search(
            g["query"], vector_service=vector_service, bm25_service=bm25_service, top_n=kmax
        )
        predicted = [c["hotel_id"] for c in res["context_package"]["chunks"]]
        n += 1
        for k in ks:
            m = _metrics_for(predicted, relevant, k)
            for key in aggs[k]:
                aggs[k][key] += m[key]
    n = n or 1
    return {k: {**{key: round(v / n, 4) for key, v in agg.items()}, "n_queries": n, "k": k}
            for k, agg in aggs.items()}


def main() -> int:
    from evaluation.retrieval_metrics.ab_runner import _build_services

    vec, bm25 = _build_services()
    multi = evaluate_multi_k(ks=(10, 20, 50), vector_service=vec, bm25_service=bm25)
    n = next(iter(multi.values()))["n_queries"]
    print(f"=== Golden eval đa-K (n={n} câu active, FULL vector+bm25) ===")
    print(f"{'K':>4}{'Recall':>9}{'Prec':>8}{'Hit':>8}{'MRR':>8}{'nDCG':>8}")
    for k, s in multi.items():
        print(f"{k:>4}{s['recall']:>9.4f}{s['precision']:>8.4f}"
              f"{s['hit']:>8.4f}{s['rr']:>8.4f}{s['ndcg']:>8.4f}")
    print("\nGhi chú V4: ground-truth nhiều câu có 15-40 hotel → Recall@10 thấp là kỳ vọng toán học.")
    print("nDCG@10 + Recall@20/@50 phản ánh năng lực thật (xem recall bung mạnh theo K).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
