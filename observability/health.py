"""DA10 — Deep health probes (§8 monitoring_plan), bản thích nghi cho project hiện tại.

Khác bản cũ (observability/main.py): KHÔNG phụ thuộc `config.settings` / `core.retrieval`.
Probe trực tiếp qua biến môi trường của repo này:
    OPENSEARCH_URL, BM25_INDEX, QDRANT_URL, QDRANT_COLLECTION, DATABASE_URL

Dùng từ api/main.py:
    from observability.health import deep_health
    body, ok = deep_health()        # body=dict, ok=bool (all deps up)
"""
from __future__ import annotations

import os
import time

from observability.metrics import DEP_UP, DEP_PROBE_DURATION


def _probe(dependency: str, fn) -> dict:
    """Chạy fn() đo latency, cập nhật gauge da10_dependency_up + histogram probe.
    Trả {"status": "ok"|"error", "latency_ms"|"message": ...}."""
    t = time.perf_counter()
    try:
        fn()
        dur = time.perf_counter() - t
        DEP_UP.labels(dependency=dependency).set(1)
        DEP_PROBE_DURATION.labels(dependency=dependency).observe(dur)
        return {"status": "ok", "latency_ms": round(dur * 1000, 1)}
    except Exception as exc:  # noqa: BLE001 — probe phải nuốt mọi lỗi để báo cáo status
        DEP_UP.labels(dependency=dependency).set(0)
        return {"status": "error", "message": str(exc)[:300]}


def _check_opensearch() -> None:
    from opensearchpy import OpenSearch

    url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    if not OpenSearch(url).ping():
        raise RuntimeError("opensearch ping returned False")


def _check_qdrant() -> None:
    from qdrant_client import QdrantClient

    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    QdrantClient(url=url).get_collections()


def _check_postgres() -> None:
    import psycopg2

    dsn = os.environ.get("DATABASE_URL", "postgresql://da10:da10@localhost:5432/da10")
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
    finally:
        conn.close()


def deep_health() -> tuple[dict, bool]:
    """Probe OpenSearch + Qdrant + Postgres. Trả (body, all_ok).

    body = {status, checks{dep:{status,latency_ms|message}}, index_opensearch, index_qdrant}
    all_ok = True chỉ khi TẤT CẢ deps status == ok (HTTP 503 nếu False).
    """
    checks = {
        "opensearch": _probe("opensearch", _check_opensearch),
        "qdrant": _probe("qdrant", _check_qdrant),
        "postgres": _probe("postgres", _check_postgres),
    }
    all_ok = all(c["status"] == "ok" for c in checks.values())
    body = {
        "status": "ok" if all_ok else "error",
        "checks": checks,
        "index_opensearch": os.environ.get("BM25_INDEX", "vsf_hotels_bm25_current"),
        "index_qdrant": os.environ.get("QDRANT_COLLECTION", "vsf_travel"),
    }
    return body, all_ok
