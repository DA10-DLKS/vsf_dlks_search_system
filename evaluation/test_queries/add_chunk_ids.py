"""add_chunk_ids.py — Điền relevant_chunk_ids cho golden v2 (đo RAG chunk-level).

CHẠY SAU KHI index Qdrant xong (collection vsf_travel có đủ chunk). Lý do tách: embed bge-m3
nặng, có thể chạy ở máy khác; script này chỉ cần Qdrant đã có dữ liệu.

Định nghĩa chunk relevant (khách quan, nối hotel-level đã có ở v2):
  chunk relevant cho câu Q <=> chunk THUỘC hotel relevant của Q (đã xác định multi-signal)
  VÀ payload chunk mang concept của Q (ontology_concepts ∩ Q.soft_signals) — tức đoạn văn
  thực sự nói về tiêu chí câu hỏi, không phải mọi chunk của hotel.

Với câu LMK/PURPOSE (không nằm ở ontology_concepts chunk): lấy chunk overview/description của
hotel relevant (đại diện hotel). Câu STYLE/ASPECT/AMEN: ưu tiên chunk có concept khớp.

Chạy: .venv/Scripts/python.exe -X utf8 -m evaluation.test_queries.add_chunk_ids
"""

from __future__ import annotations

import json
import os

GOLDEN_V2 = "data/golden_dataset/golden_set_v2.json"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "vsf_travel")
MAX_CHUNK_PER_HOTEL = 3   # giới hạn chunk/hotel để relevant set không phình


def _load_chunks_by_hotel():
    """Quét toàn bộ point Qdrant -> {hotel_id: [(chunk_id, concepts, section)]}."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL)
    by_hotel: dict[int, list] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION, limit=512, offset=offset, with_payload=True
        )
        for p in points:
            pl = p.payload or {}
            hid = pl.get("hotel_id")
            if hid is None:
                continue
            by_hotel.setdefault(hid, []).append(
                (pl.get("chunk_id"), set(pl.get("ontology_concepts") or []), pl.get("section"))
            )
        if offset is None:
            break
    return by_hotel


def add_chunk_ids() -> dict:
    v2 = json.load(open(GOLDEN_V2, encoding="utf-8"))
    by_hotel = _load_chunks_by_hotel()
    if not by_hotel:
        raise RuntimeError(
            f"Qdrant collection '{COLLECTION}' rỗng — chạy index trước "
            f"(indexing.vector_index.qdrant_index)."
        )

    n_filled = 0
    for q in v2:
        if q["eval_status"] != "active":
            continue
        concept_set = {s for s in q.get("soft_signals", []) if s.isupper() and "_" in s}
        rel_chunks: list[str] = []
        for hid in q["relevant_hotel_ids"]:
            chunks = by_hotel.get(hid, [])
            # ưu tiên chunk có concept khớp; nếu không có -> chunk overview/description đại diện
            matched = [c for c in chunks if c[1] & concept_set]
            if not matched:
                matched = [c for c in chunks if c[2] in ("overview", "description")][:1] or chunks[:1]
            for cid, _, _ in matched[:MAX_CHUNK_PER_HOTEL]:
                if cid:
                    rel_chunks.append(cid)
        q["relevant_chunk_ids"] = rel_chunks
        if rel_chunks:
            n_filled += 1

    json.dump(v2, open(GOLDEN_V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"filled": n_filled, "total_active": sum(1 for q in v2 if q["eval_status"] == "active")}


if __name__ == "__main__":
    r = add_chunk_ids()
    print(f"Đã điền relevant_chunk_ids cho {r['filled']}/{r['total_active']} câu active.")
