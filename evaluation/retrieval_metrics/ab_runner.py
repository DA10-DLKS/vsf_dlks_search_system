"""ab_runner.py — A/B harness đo đòn bẩy từng fix (FULL vs NO-SERVICE vs BM25-only vs vector-only).

Mục đích: trước/sau mỗi fix (V1, V9, ...) chạy 1 lệnh, in bảng so sánh cấu hình để biết fix
có cải thiện thật không — KHÔNG suy đoán. Dùng chung evaluate() của eval_golden.

Chạy: .venv/Scripts/python.exe -X utf8 -m evaluation.retrieval_metrics.ab_runner
"""

from __future__ import annotations

import os
import time

from evaluation.retrieval_metrics.eval_golden import evaluate


def _build_services():
    """Dựng vector (Qdrant) + bm25 (OpenSearch) service như api/main.py, an toàn nếu vắng."""
    from opensearchpy import OpenSearch
    from retrieval.lexical_search import BM25SearchService

    os_url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    index = os.environ.get("BM25_INDEX", "vsf_hotels_bm25_current")
    bm25 = None
    try:
        client = OpenSearch(os_url, maxsize=25)
        if client.indices.exists(index=index):
            bm25 = BM25SearchService(client=client, index_name=index)
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] BM25 service vắng: {exc}")

    vec = None
    try:
        from retrieval.vector_search.qdrant_service import create_qdrant_search_service

        vec = create_qdrant_search_service(offline=False)
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] Vector service vắng: {exc}")

    return vec, bm25


def _row(name: str, vec, bm25, k: int, limit):
    t0 = time.perf_counter()
    res = evaluate(k=k, vector_service=vec, bm25_service=bm25, limit=limit)
    dt = time.perf_counter() - t0
    s = res["summary"]
    return name, s, dt, res


def main() -> int:
    k = int(os.environ.get("EVAL_K", "10"))
    limit = os.environ.get("EVAL_LIMIT")
    limit = int(limit) if limit else None

    print(f"Dựng service (Qdrant + OpenSearch)... K={k} limit={limit}")
    vec, bm25 = _build_services()
    print(f"  vector_service={'OK' if vec else 'None'}  bm25_service={'OK' if bm25 else 'None'}")

    configs = [
        ("FULL (vector+bm25)", vec, bm25),
        ("NO-SERVICE (KE only)", None, None),
        ("BM25-only", None, bm25),
        ("vector-only", vec, None),
    ]

    print(f"\n{'Config':<24} {'Recall':>8} {'Prec':>8} {'Hit':>8} {'MRR':>8} {'sec':>7}")
    print("-" * 70)
    full = none = None
    for name, v, b in configs:
        _, s, dt, _ = _row(name, v, b, k, limit)
        if name.startswith("FULL"):
            full = s
        if name.startswith("NO-SERVICE"):
            none = s
        print(f"{name:<24} {s['recall']:>8.4f} {s['precision']:>8.4f} "
              f"{s['hit']:>8.4f} {s['rr']:>8.4f} {dt:>7.1f}")

    if full and none:
        print("-" * 70)
        print(f"{'FULL − NO-SERVICE':<24} {full['recall']-none['recall']:>+8.4f} "
              f"{full['precision']-none['precision']:>+8.4f} "
              f"{full['hit']-none['hit']:>+8.4f} {full['rr']-none['rr']:>+8.4f}")
        print(f"\nn_queries={full['n_queries']}")

    # V8: CI gate — fail nếu FULL tụt dưới ngưỡng (bắt regression chất lượng). Ngưỡng đặt dưới
    # baseline hiện tại (recall@10=0.5495, hit=1.0) một biên an toàn. Bật bằng env GATE_MODE=1.
    if os.environ.get("GATE_MODE") == "1" and full:
        min_recall = float(os.environ.get("GATE_MIN_RECALL", "0.53"))
        min_hit = float(os.environ.get("GATE_MIN_HIT", "0.98"))
        failed = []
        if full["recall"] < min_recall:
            failed.append(f"Recall@{k}={full['recall']:.4f} < {min_recall}")
        if full["hit"] < min_hit:
            failed.append(f"Hit@{k}={full['hit']:.4f} < {min_hit}")
        if failed:
            print("\n❌ GATE FAILED: " + "; ".join(failed))
            return 1
        print(f"\n✅ GATE PASSED (recall≥{min_recall}, hit≥{min_hit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
