"""qdrant_index.py — Index chunk embeddings vào Qdrant (vector store của dự án per .env).

Repo có sẵn pgvector_index.py (Postgres) làm tham chiếu, nhưng .env cấu hình Qdrant và
service Qdrant đang chạy -> tầng vector dùng Qdrant. Tái dùng chunk_document (chunk text từ
data/cleaned + nhãn KE đã đính ở Nhóm 0) và embedding bge-m3; chỉ thay phần ghi store.

Mỗi chunk -> 1 point: vector = embed(chunk.text), payload = chunk.to_payload() (gồm
ontology_concepts/semantic_profile/nearby_landmarks... để retrieval filter/rerank).

Chạy: .venv/Scripts/python.exe -X utf8 -m indexing.vector_index.qdrant_index
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from indexing.embedding import get_embedding_model
from indexing.vector_index.pgvector_index import iter_clean_documents
from knowledge_engineering.chunking import chunk_document

QDRANT_URL_DEFAULT = "http://localhost:6333"
COLLECTION_DEFAULT = "vsf_travel"
DATA_DIR_DEFAULT = "data/cleaned"
VECTOR_DIM_DEFAULT = 1024   # bge-m3
BATCH_DEFAULT = 64
CHECKPOINT_FILE = "data/qdrant_index_checkpoint.json"


def _point_id(chunk_id: str) -> str:
    """Qdrant point id phải là uuid/int. Map chunk_id (sha1 16-hex) -> uuid ổn định."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def ensure_collection(client, collection: str, dim: int) -> None:
    from qdrant_client.models import Distance, VectorParams

    existing = {c.name for c in client.get_collections().collections}
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def _load_checkpoint() -> set[int]:
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    with open(CHECKPOINT_FILE) as f:
        return set(json.load(f))


def _save_checkpoint(hotel_ids: set[int]) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(sorted(hotel_ids), f)


def build_points_for_hotel(document: dict[str, Any], embedding_model):
    """Sinh point Qdrant cho 1 hotel. Trả list[PointStruct]."""
    from qdrant_client.models import PointStruct

    chunks = chunk_document(document)
    if not chunks:
        return []
    embeddings = embedding_model.embed([c.text for c in chunks])
    points = []
    for chunk, emb in zip(chunks, embeddings, strict=True):
        payload = chunk.to_payload()
        payload["raw_text"] = chunk.raw_text
        points.append(
            PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=emb.vector,
                payload=payload,
            )
        )
    return points


def index_to_qdrant(
    *,
    qdrant_url: str = QDRANT_URL_DEFAULT,
    collection: str = COLLECTION_DEFAULT,
    data_dir: str = DATA_DIR_DEFAULT,
    dim: int = VECTOR_DIM_DEFAULT,
    offline: bool = False,
    limit_docs: int | None = None,
    resume: bool = True,
) -> int:
    from qdrant_client import QdrantClient

    client = QdrantClient(url=qdrant_url)
    model = get_embedding_model("bge-m3", offline=offline)
    if offline:
        dim = 32   # HashEmbeddingModel
    ensure_collection(client, collection, dim)

    done_ids = _load_checkpoint() if resume else set()
    total = 0
    total_docs = 0
    skipped = 0
    t0 = time.time()

    for doc in iter_clean_documents(data_dir):
        hid = doc.get("hotel_id")
        if hid is None:
            continue
        total_docs += 1
        if resume and hid in done_ids:
            skipped += 1
            continue

        points = build_points_for_hotel(doc, model)
        if points:
            client.upsert(collection_name=collection, points=points)
            total += len(points)
        done_ids.add(hid)
        _save_checkpoint(done_ids)

        elapsed = time.time() - t0
        print(f"  [{total_docs}] hotel_id={hid} -> {len(points)} chunks | total={total} | {elapsed:.0f}s", flush=True)

    print(f"Indexed {total} chunks from {total_docs - skipped} hotels ({skipped} skipped).")
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    return total


def main() -> int:
    qdrant_url = os.environ.get("QDRANT_URL", QDRANT_URL_DEFAULT)
    collection = os.environ.get("QDRANT_COLLECTION", COLLECTION_DEFAULT)
    data_dir = os.environ.get("CLEANED_DATA_DIR", DATA_DIR_DEFAULT)
    offline = os.environ.get("EMBED_OFFLINE", "").lower() in ("1", "true", "yes")
    resume = os.environ.get("QDRANT_RESUME", "true").lower() in ("1", "true", "yes")
    n = index_to_qdrant(qdrant_url=qdrant_url, collection=collection,
                        data_dir=data_dir, offline=offline, resume=resume)
    print(f"Indexed {n} chunks into Qdrant collection '{collection}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
