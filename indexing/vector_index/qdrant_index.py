"""qdrant_index.py — Index chunk embeddings vào Qdrant (vector store của dự án per .env).

Repo có sẵn pgvector_index.py (Postgres) làm tham chiếu, nhưng .env cấu hình Qdrant và
service Qdrant đang chạy -> tầng vector dùng Qdrant. Tái dùng chunk_document (chunk text từ
data/cleaned + nhãn KE đã đính ở Nhóm 0) và embedding bge-m3; chỉ thay phần ghi store.

Mỗi chunk -> 1 point: vector = embed(chunk.text), payload = chunk.to_payload() (gồm
ontology_concepts/semantic_profile/nearby_landmarks... để retrieval filter/rerank).

Chạy: .venv/Scripts/python.exe -X utf8 -m indexing.vector_index.qdrant_index
"""

from __future__ import annotations

import os
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


def build_points(documents: Iterable[dict[str, Any]], embedding_model, batch: int = BATCH_DEFAULT):
    """Sinh point Qdrant theo lô. Yield list[PointStruct]."""
    from qdrant_client.models import PointStruct

    buf_chunks = []
    for document in documents:
        for chunk in chunk_document(document):
            buf_chunks.append(chunk)
            if len(buf_chunks) >= batch:
                yield _embed_batch(buf_chunks, embedding_model, PointStruct)
                buf_chunks = []
    if buf_chunks:
        yield _embed_batch(buf_chunks, embedding_model, PointStruct)


def _embed_batch(chunks, embedding_model, PointStruct):
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
) -> int:
    from qdrant_client import QdrantClient

    client = QdrantClient(url=qdrant_url)
    model = get_embedding_model("bge-m3", offline=offline)
    if offline:
        dim = 32   # HashEmbeddingModel
    ensure_collection(client, collection, dim)

    docs = iter_clean_documents(data_dir)
    if limit_docs:
        docs = (d for i, d in enumerate(docs) if i < limit_docs)

    total = 0
    for points in build_points(docs, model):
        client.upsert(collection_name=collection, points=points)
        total += len(points)
    return total


def main() -> int:
    qdrant_url = os.environ.get("QDRANT_URL", QDRANT_URL_DEFAULT)
    collection = os.environ.get("QDRANT_COLLECTION", COLLECTION_DEFAULT)
    data_dir = os.environ.get("CLEANED_DATA_DIR", DATA_DIR_DEFAULT)
    offline = os.environ.get("EMBED_OFFLINE", "").lower() in ("1", "true", "yes")
    n = index_to_qdrant(qdrant_url=qdrant_url, collection=collection,
                        data_dir=data_dir, offline=offline)
    print(f"Indexed {n} chunks into Qdrant collection '{collection}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
