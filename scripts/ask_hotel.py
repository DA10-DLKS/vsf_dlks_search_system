"""Test nhanh endpoint GET /hotel/{hotel_id}/ask — hỏi thông tin trong phạm vi 1 khách sạn.

Tự ép stdout sang UTF-8 nên gõ/hiển thị tiếng Việt đúng trên console Windows (cp1252).

Cách dùng:
  # Chế độ tương tác (gõ nhiều câu liên tiếp, Enter rỗng để thoát):
  python scripts/ask_hotel.py 48363

  # Hỏi 1 câu rồi thoát:
  python scripts/ask_hotel.py 48363 "Khách sạn có cho mang thú cưng không"

  # Tùy chọn: số chunk trả về (mặc định 5) và URL API:
  python scripts/ask_hotel.py 48363 "..." --top-k 8 --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys

import requests

# Console Windows mặc định cp1252 -> in tiếng Việt lỗi. Ép UTF-8 cho stdin/stdout.
for _stream in (sys.stdout, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def ask(base_url: str, hotel_id: int, query: str, top_k: int) -> None:
    try:
        resp = requests.get(
            f"{base_url}/hotel/{hotel_id}/ask",
            params={"q": query, "top_k": top_k},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"[LỖI] Không gọi được API: {exc}")
        return

    if resp.status_code != 200:
        print(f"[LỖI] HTTP {resp.status_code}: {resp.text[:300]}")
        return

    data = resp.json()
    print(f"\nHotel {data['hotel_id']} | query: {data['query']} | {data['count']} chunk\n" + "-" * 70)
    for i, c in enumerate(data["chunks"], 1):
        text = (c.get("text") or "").replace("\n", " ")
        print(f"#{i}  score={c['score']:.3f}  [{c.get('section')}]")
        print(f"    {text[:300]}{'…' if len(text) > 300 else ''}\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Hỏi thông tin 1 khách sạn qua API /hotel/{id}/ask")
    p.add_argument("hotel_id", type=int, help="ID khách sạn")
    p.add_argument("query", nargs="?", help="Câu hỏi (bỏ trống = chế độ tương tác)")
    p.add_argument("--top-k", type=int, default=5, help="Số chunk trả về (mặc định 5)")
    p.add_argument("--url", default="http://localhost:8000", help="Base URL API")
    args = p.parse_args()

    if args.query:
        ask(args.url, args.hotel_id, args.query, args.top_k)
        return

    print(f"Chế độ tương tác — hotel {args.hotel_id}. Gõ câu hỏi rồi Enter. Enter rỗng để thoát.")
    while True:
        try:
            q = input("\nCâu hỏi> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        ask(args.url, args.hotel_id, q, args.top_k)


if __name__ == "__main__":
    main()
