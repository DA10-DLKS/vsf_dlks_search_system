"""DA10 Platform Services API (Layer 8).

Exposes Search / Context / Knowledge APIs consumed by DA09.
TODO: register routers from api/routes/.
"""

import os
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from opensearchpy import OpenSearch
from dotenv import load_dotenv
from prometheus_client import Histogram, Counter, generate_latest, CollectorRegistry
from retrieval.lexical_search import BM25SearchService

# Load environment variables
load_dotenv()

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
INDEX_NAME = os.environ.get('BM25_INDEX', 'vsf_hotels_bm25_current')

# Initialize OpenSearch Client
client = OpenSearch(OPENSEARCH_URL, maxsize=25)
keyword_search_service = BM25SearchService(
    client=client, index_name=INDEX_NAME)

# Prometheus metrics
REGISTRY = CollectorRegistry()
REQUEST_LATENCY = Histogram(
    'search_bm25_request_duration_seconds',
    'BM25 search request latency in seconds',
    ['endpoint'],
    registry=REGISTRY
)
REQUESTS_TOTAL = Counter(
    'search_bm25_requests_total',
    'Total BM25 search requests',
    ['endpoint'],
    registry=REGISTRY
)
ERRORS_TOTAL = Counter(
    'search_bm25_errors_total',
    'Total BM25 search errors',
    ['endpoint'],
    registry=REGISTRY
)

app = FastAPI(title="DA10 Knowledge & Retrieval Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(REGISTRY)


@app.get("/search")
def search_bm25(q: str = Query(..., description="Search query")) -> dict:
    """
    BM25 search endpoint (Sprint 1 baseline).
    Tracks latency and error counts via Prometheus.
    """
    start_time = time.time()
    endpoint = "/search"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()

    try:
        response = keyword_search_service.search(q)
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
        return response
    except Exception:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(
            status_code=503, detail="Keyword search backend unavailable")


# ---- Hybrid search (Node 1->8) -------------------------------------------------
# Khởi tạo service text retrieval LAZY + an toàn: nếu OpenSearch/Qdrant chưa sẵn thì pipeline
# vẫn chạy bằng candidate + nhãn KE (không vỡ API). Cắm service thật khi hạ tầng + index sẵn.
def _bm25_for_fusion():
    return keyword_search_service if _has_index(client, INDEX_NAME) else None


def _has_index(os_client, name) -> bool:
    try:
        return bool(os_client.indices.exists(index=name))
    except Exception:
        return False


def _vector_service():
    try:
        from retrieval.vector_search.qdrant_service import create_qdrant_search_service
        return create_qdrant_search_service(offline=False)
    except Exception:
        return None


@app.get("/hybrid_search")
def hybrid_search(
    q: str = Query(..., description="Câu hỏi tiếng Việt"),
    top_n: int = Query(5, ge=1, le=20),
    answer: bool = Query(False, description="Sinh câu trả lời LLM (Node 9)"),
) -> dict:
    """Hybrid retrieval Node 1->9: intent -> filter -> candidate -> BM25+vector -> fusion ->
    rerank -> ContextPackage + prompt [-> LLM answer]. Service text retrieval tự dùng nếu sẵn."""
    from retrieval.hybrid_search import run_hybrid_search

    endpoint = "/hybrid_search"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()
    start_time = time.time()
    try:
        result = run_hybrid_search(
            q,
            vector_service=_vector_service(),
            bm25_service=_bm25_for_fusion(),
            top_n=top_n,
            generate_answer=answer,
        )
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        return result
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Hybrid search error: {exc}")


# TODO:
# from api.routes import search_api, context_api, knowledge_api
# app.include_router(search_api.router)
# app.include_router(context_api.router)
# app.include_router(knowledge_api.router)
