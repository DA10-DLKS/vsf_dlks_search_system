"""create_index.py — Tạo index BM25 từ index_mapping.json (analyzer VN + mapping strict).

Bù khoảng trống quy trình: index_bm25.py KHÔNG tự tạo index (giả định đã có sẵn). Khi mapping
ĐỔI (vd thêm field name_alt) thì index cũ — dynamic:strict — từ chối doc có field mới. Phải
tạo lại index với mapping mới rồi mới index_bm25.

Chạy:
  # tạo nếu chưa có (idempotent — đã có thì báo, KHÔNG đụng):
  .venv/Scripts/python.exe -X utf8 -m indexing.bm25_index.create_index
  # XÓA rồi tạo lại với mapping hiện tại (dùng khi mapping đổi):
  .venv/Scripts/python.exe -X utf8 -m indexing.bm25_index.create_index --recreate

Sau đó: python -m indexing.bm25_index.index_bm25  (đẩy doc).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from opensearchpy import OpenSearch

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME = os.environ.get("BM25_TARGET_INDEX") or os.environ.get("BM25_INDEX", "vsf_hotels_bm25_current")
MAPPING_PATH = Path(__file__).parent / "index_mapping.json"


def main() -> int:
    client = OpenSearch(OPENSEARCH_URL, maxsize=25)
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    ap = argparse.ArgumentParser(description="Tạo index BM25 từ index_mapping.json.")
    ap.add_argument("--recreate", action="store_true",
                    help="XÓA index hiện tại rồi tạo lại (dùng khi mapping đổi). Mất data trong index, "
                         "phải chạy index_bm25 lại sau đó.")
    args = ap.parse_args()

    exists = client.indices.exists(index=INDEX_NAME)
    if exists and not args.recreate:
        print(f"Index {INDEX_NAME} ĐÃ tồn tại. Dùng --recreate để xóa + tạo lại với mapping mới.")
        return 0
    if exists and args.recreate:
        print(f"[xóa] index cũ {INDEX_NAME} (mapping cũ)...")
        client.indices.delete(index=INDEX_NAME)

    print(f"[tạo] {INDEX_NAME} từ {MAPPING_PATH.name} (analyzer VN + name_alt)...")
    client.indices.create(index=INDEX_NAME, body=mapping)
    print(f"OK. Tiếp: python -m indexing.bm25_index.index_bm25  (đẩy doc từ data/cleaned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
