"""reindex_vietnamese.py — V10: reindex BM25 sang index dùng vietnamese_analyzer (an toàn, A/B).

Tạo index THỬ `vsf_hotels_bm25_vi` với mapping mới (analyzer tiếng Việt), copy doc từ index
hiện tại bằng _reindex API (không cần đọc lại data file), rồi để A/B so với index cũ. KHÔNG
đụng index đang chạy — chỉ promote alias sau khi đo thấy tốt hơn.

Chạy: .venv/Scripts/python.exe -X utf8 -m indexing.bm25_index.reindex_vietnamese
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from opensearchpy import OpenSearch

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
SOURCE_INDEX = os.environ.get("BM25_INDEX", "vsf_hotels_bm25_current")
TARGET_INDEX = os.environ.get("BM25_VI_INDEX", "vsf_hotels_bm25_vi")
MAPPING_PATH = Path(__file__).parent / "index_mapping.json"


def main() -> int:
    client = OpenSearch(OPENSEARCH_URL, maxsize=25)
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    if client.indices.exists(index=TARGET_INDEX):
        print(f"Xóa index thử cũ {TARGET_INDEX}...")
        client.indices.delete(index=TARGET_INDEX)

    print(f"Tạo {TARGET_INDEX} với vietnamese_analyzer...")
    client.indices.create(index=TARGET_INDEX, body=mapping)

    src_count = client.count(index=SOURCE_INDEX)["count"]
    print(f"Reindex {SOURCE_INDEX} ({src_count} doc) -> {TARGET_INDEX}...")
    # Doc BM25 rất to (12-14k ký tự/field) → batch lớn vượt giới hạn coordinating (107MB) gây 429.
    # Reindex batch nhỏ (10 doc/lần) + throttle.
    resp = client.reindex(
        body={
            "source": {"index": SOURCE_INDEX, "size": 10},
            "dest": {"index": TARGET_INDEX},
        },
        wait_for_completion=True,
        request_timeout=600,
        requests_per_second=200,
    )
    client.indices.refresh(index=TARGET_INDEX)
    dst_count = client.count(index=TARGET_INDEX)["count"]
    print(f"Xong: created={resp.get('created')} failures={len(resp.get('failures') or [])} "
          f"| {SOURCE_INDEX}={src_count} {TARGET_INDEX}={dst_count}")
    if dst_count != src_count:
        print("⚠ Số doc KHÔNG khớp — kiểm tra failures trước khi A/B.")
        return 1
    print(f"\nA/B: set BM25_INDEX={TARGET_INDEX} rồi chạy ab_runner để so recall BM25.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
