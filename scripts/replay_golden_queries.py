"""replay_golden_queries.py — Bắn TẤT CẢ query trong golden_set vào API để sinh dữ liệu
latency cho UI truy vết request chậm (/ui/slow_requests.html).

Mỗi request đi qua pipeline -> API log `search_completed` kèm query + stage_ms -> hiện lên UI.

Chạy (Git Bash, API phải đang chạy ở :8000):
    python scripts/replay_golden_queries.py
Tùy chọn:
    --base http://localhost:8000        # địa chỉ API
    --golden data/golden_dataset/golden_set_v2.json
    --endpoint search | hybrid_search   # mặc định search (POST, đúng luồng frontend)
    --only-active                       # chỉ chạy câu eval_status=active (bỏ các câu excluded)
    --delay 0.2                         # nghỉ giữa các request (giây), tránh dồn tải
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--golden", default="data/golden_dataset/golden_set_v2.json")
    ap.add_argument("--endpoint", default="search", choices=["search", "hybrid_search"])
    ap.add_argument("--only-active", action="store_true",
                    help="Chỉ chạy eval_status=active (bỏ câu excluded)")
    ap.add_argument("--delay", type=float, default=0.0, help="Nghỉ giữa các request (giây)")
    args = ap.parse_args()

    items = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    queries: list[tuple[str, str]] = []
    for it in items:
        q = (it.get("query") or "").strip()
        if not q:
            continue
        if args.only_active and it.get("eval_status") != "active":
            continue
        queries.append((it.get("query_id") or "?", q))

    print(f"Tổng {len(queries)} query -> {args.base} (POST /{args.endpoint})\n")
    results: list[tuple[float, str, str]] = []
    for i, (qid, q) in enumerate(queries, 1):
        t = time.time()
        try:
            if args.endpoint == "search":
                body = json.dumps({"query": q}).encode("utf-8")
                req = urllib.request.Request(
                    f"{args.base}/search", data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
            else:
                url = f"{args.base}/hybrid_search?q={urllib.parse.quote(q)}&top_n=10"
                req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=120) as r:
                r.read()
            ms = (time.time() - t) * 1000
            results.append((ms, qid, q))
            print(f"[{i:>3}/{len(queries)}] {qid:<8} {ms:8.1f} ms  {q[:55]}")
        except urllib.error.URLError as e:
            print(f"[{i:>3}/{len(queries)}] {qid:<8} LỖI: {e}")
        if args.delay:
            time.sleep(args.delay)

    if results:
        results.sort(reverse=True)
        print("\n== Top 10 chậm nhất ==")
        for ms, qid, q in results[:10]:
            print(f"  {ms:8.1f} ms  {qid:<8} {q[:55]}")
        avg = sum(r[0] for r in results) / len(results)
        print(f"\nTrung bình: {avg:.1f} ms | tổng {len(results)} request thành công")
    print(f"\nMở UI xem chi tiết: {args.base}/ui/slow_requests.html")


if __name__ == "__main__":
    main()
