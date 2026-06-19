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
from prometheus_client import Histogram, Counter, generate_latest
from retrieval.lexical_search import BM25SearchService

# Observability (DA10 monitoring): registry DÙNG CHUNG cho cả da10_* lẫn search_bm25_*,
# JSON logger, deep health probe. Xem observability/README.md.
from observability.metrics import (
    REGISTRY,
    HTTP_REQUESTS,
    HTTP_DURATION,
    SEARCH_ZERO_RESULTS,
    CONTEXT_DURATION,
)
from observability.logging import get_logger
from observability.health import deep_health

# Load environment variables
load_dotenv()

_log = get_logger()

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
INDEX_NAME = os.environ.get('BM25_INDEX', 'vsf_hotels_bm25_current')

# Initialize OpenSearch Client
client = OpenSearch(OPENSEARCH_URL, maxsize=25)
keyword_search_service = BM25SearchService(
    client=client, index_name=INDEX_NAME)

# Prometheus metrics — đăng ký vào REGISTRY chung (import từ observability.metrics) để
# /metrics gộp cả search_bm25_* (cũ) lẫn da10_* (observability) trong một generate_latest.
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


@app.middleware("http")
async def _metrics_middleware(request, call_next):
    """Observability: đếm da10_http_requests_total + đo da10_http_request_duration_seconds
    cho MỌI request. Dùng route path (template) làm label endpoint để tránh nổ cardinality."""
    start = time.perf_counter()
    response = await call_next(request)
    endpoint = request.scope.get("route").path if request.scope.get("route") else request.url.path
    HTTP_DURATION.labels(endpoint=endpoint).observe(time.perf_counter() - start)
    HTTP_REQUESTS.labels(
        endpoint=endpoint, method=request.method, status=str(response.status_code)
    ).inc()
    return response

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


@app.get("/health/deep")
def health_deep():
    """Deep health: probe OpenSearch + Qdrant + Postgres (observability.health.deep_health).
    Cập nhật gauge da10_dependency_up. Trả 503 nếu bất kỳ dependency nào down."""
    from fastapi.responses import JSONResponse

    body, ok = deep_health()
    return JSONResponse(content=body, status_code=200 if ok else 503)


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint — gộp da10_* (observability) + search_bm25_* (cũ)."""
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST

    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/search")
def search_bm25(
    q: str = Query(..., description="Search query"),
    size: int = Query(10, ge=1, le=20, description="Số kết quả BM25 trả về"),
) -> dict:
    """
    BM25 search endpoint (Sprint 1 baseline).
    Tracks latency and error counts via Prometheus.
    """
    start_time = time.time()
    endpoint = "/search"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()

    try:
        response = keyword_search_service.search(q, size=size)
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


@app.get("/eval/golden")
def eval_golden(
    k: int = Query(10, ge=1, le=50, description="Cắt top-K khi tính metric"),
    limit: int = Query(10, ge=1, le=100, description="Số câu golden chạy (giữ nhỏ để nhanh)"),
    use_services: bool = Query(
        False, description="True = dùng vector(Qdrant)+BM25; False = candidate-only (nhanh, nhẹ RAM)"
    ),
) -> dict:
    """Chạy golden dataset → trả metric Recall/Precision/Hit/MRR/nDCG (summary + per-query).

    Đồng bộ: request CHỜ tới khi chạy xong. ~2s/câu (candidate-only), nên giữ `limit` nhỏ;
    limit=59 (toàn bộ câu active) có thể mất vài phút. Cập nhật gauge da10_eval_metric để
    /metrics phản ánh lần chạy gần nhất."""
    from evaluation.retrieval_metrics.eval_golden import evaluate
    from observability.metrics import EVAL_METRIC, EVAL_QUERIES, EVAL_DURATION

    endpoint = "/eval/golden"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()
    start = time.time()
    try:
        vec = _get_vector_service() if use_services else None
        bm25 = _get_bm25_service() if use_services else None
        result = evaluate(k=k, vector_service=vec, bm25_service=bm25, limit=limit)
        summary = result["summary"]

        # Cập nhật Prometheus gauge (để xem được cả qua /metrics nếu cần).
        klabel = str(summary.get("k", k))
        for name in ("recall", "precision", "hit", "rr", "ndcg"):
            EVAL_METRIC.labels(name=("mrr" if name == "rr" else name), k=klabel).set(
                summary.get(name, 0.0)
            )
        EVAL_QUERIES.set(summary.get("n_queries", 0))
        duration = time.time() - start
        EVAL_DURATION.observe(duration)

        return {
            "summary": summary,
            "per_query": result["per_query"],
            "duration_s": round(duration, 2),
            "mode": "full (vector+bm25)" if use_services else "candidate-only",
        }
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Golden eval error: {exc}")


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
