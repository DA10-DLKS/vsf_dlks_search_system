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
from pydantic import BaseModel
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


@app.on_event("startup")
def _warmup() -> None:
    """V12: nạp sẵn synonym (tránh cold-start ~978ms request đầu mỗi worker). An toàn nếu lỗi.

    Quan trọng (fix segfault): các route hybrid chạy ở threadpool của Starlette (def route).
    Nếu để model XLM-RoBERTa (bge-m3 embedding và bge-reranker cross-encoder) lazy-load LẦN ĐẦU
    trong thread con đó, torch native crash (exit 139) trên CPU/Windows. Khởi tạo cả hai NGAY Ở
    STARTUP (main thread) tránh được. Reranker chỉ warmup khi USE_RERANKER bật (mặc định off).
    Thứ tự: cross-encoder trước, bge-m3 sau (an toàn theo kiểm chứng init order)."""
    try:
        from retrieval.query_processing import warmup
        warmup()
    except Exception:
        pass

    # Cross-encoder reranker (chỉ khi bật) — nạp ở main thread.
    if os.environ.get("USE_RERANKER", "0") == "1":
        try:
            from retrieval.reranking.neural_rerank import _load_model
            _load_model()
        except Exception:
            pass

    # bge-m3 embedding (lazy service) — ép khởi tạo ở main thread để tránh lazy-load trong threadpool.
    try:
        _get_vector_service()
    except Exception:
        pass


# CORS: frontend chạy ở origin khác (file:// hoặc localhost:5173...) gọi API localhost:8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend tĩnh tại /ui (đồng đội thêm: search_ui.html + index.html).
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

# Service text retrieval khởi tạo LAZY + cache (load model bge-m3 1 lần). None nếu service vắng.
_VEC_SVC = None
_VEC_INIT = False


def _get_vector_service():
    global _VEC_SVC, _VEC_INIT
    if not _VEC_INIT:
        _VEC_INIT = True
        try:
            from retrieval.vector_search.qdrant_service import create_qdrant_search_service
            _VEC_SVC = create_qdrant_search_service(offline=False)
        except Exception:
            _VEC_SVC = None
    return _VEC_SVC


def _get_bm25_service():
    try:
        return keyword_search_service if client.indices.exists(index=INDEX_NAME) else None
    except Exception:
        return None


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
            vector_service=_get_vector_service(),
            bm25_service=_get_bm25_service(),
            top_n=top_n,
            generate_answer=answer,
        )
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        return result
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Hybrid search error: {exc}")


# ---- Endpoint cho FRONTEND (schema frontend/src/types/searchTypes.js) ----------
# Frontend gọi POST /search + POST /context. Adapter dịch shape pipeline -> shape frontend.
class SearchRequest(BaseModel):
    query: str
    filters: dict | None = None


class ContextRequest(BaseModel):
    result_id: str
    query: str | None = None   # V6: câu hỏi gốc của user để answer bám nhu cầu (tùy chọn)


@app.post("/search")
def fe_search(req: SearchRequest) -> dict:
    """Frontend search: {query, filters} -> {query, results[], total}. Chạy hybrid retrieval
    (KHÔNG sinh LLM answer ở đây cho nhanh; answer lấy qua /context khi user mở chi tiết)."""
    from api.frontend_adapter import to_search_response
    from retrieval.hybrid_search import run_hybrid_search

    endpoint = "/search[POST]"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()
    start = time.time()
    try:
        result = run_hybrid_search(
            req.query,
            vector_service=_get_vector_service(),
            bm25_service=_get_bm25_service(),
            top_n=10,
            generate_answer=False,
        )
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start)
        return to_search_response(req.query, result)
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")


@app.post("/context")
def fe_context(req: ContextRequest) -> dict:
    """Frontend context: {result_id='hotel_<id>'} -> {result_id, llm_context, citations, ...}.
    Node 9 sinh llm_context từ chính hotel được chọn (không search lại)."""
    from api.frontend_adapter import build_hotel_context

    endpoint = "/context[POST]"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()
    start = time.time()
    try:
        out = build_hotel_context(req.result_id, query=req.query)
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start)
        return out
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Context error: {exc}")
