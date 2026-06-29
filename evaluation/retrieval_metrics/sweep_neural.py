"""sweep_neural.py — Quét trọng số neural (text-signal) để calibrate V1.

Sau khi chuẩn hóa text-signal [0,1], trọng số neural=0.5 làm text ÁP ĐẢO nhãn KE (vốn mạnh
hơn trên golden này) -> recall tụt. Quét neural_weight để tìm điểm text-signal BỔ SUNG chứ
không lấn át KE. Load service 1 lần, đo FULL cho nhiều trọng số.

Chạy: .venv/Scripts/python.exe -X utf8 -m evaluation.retrieval_metrics.sweep_neural
"""

from __future__ import annotations

import os

from evaluation.retrieval_metrics.ab_runner import _build_services
from evaluation.retrieval_metrics.eval_golden import evaluate


def main() -> int:
    k = int(os.environ.get("EVAL_K", "10"))
    grid = os.environ.get("NEURAL_GRID", "0.0,0.05,0.1,0.15,0.2,0.3,0.5").split(",")

    print("Dựng service (load model 1 lần)...")
    vec, bm25 = _build_services()
    print(f"  vector={'OK' if vec else 'None'} bm25={'OK' if bm25 else 'None'}\n")

    print(f"{'neural_w':>9} {'Recall':>8} {'Prec':>8} {'Hit':>8} {'MRR':>8}")
    print("-" * 46)
    best = (None, -1.0)
    for nw in grid:
        os.environ["NEURAL_WEIGHT"] = nw
        s = evaluate(k=k, vector_service=vec, bm25_service=bm25)["summary"]
        print(f"{nw:>9} {s['recall']:>8.4f} {s['precision']:>8.4f} "
              f"{s['hit']:>8.4f} {s['rr']:>8.4f}")
        if s["recall"] > best[1]:
            best = (nw, s["recall"])
    os.environ.pop("NEURAL_WEIGHT", None)
    print("-" * 46)
    print(f"best neural_weight={best[0]} recall={best[1]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
