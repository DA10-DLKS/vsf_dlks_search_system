"""DA10 Platform Services API (Layer 8).

Exposes Search / Context / Knowledge APIs consumed by DA09.
TODO: register routers from api/routes/.
"""

import asyncio
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
from observability.logging import get_logger, set_request_id
from observability.health import deep_health

# Load environment variables
load_dotenv()

_log = get_logger()

# Debug dump cấu trúc response ([SCHEMA]) mặc định TẮT (đã hạ xuống DEBUG). Bật lại khi cần soi
# schema bằng SCHEMA_DEBUG=1 (vd lúc đối chiếu contract với frontend).
if os.environ.get("SCHEMA_DEBUG", "0") == "1":
    import logging as _logging
    _log.setLevel(_logging.DEBUG)

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


def _log_response_structure(endpoint: str, data, prefix: str = "") -> None:
    """Log cấu trúc response để verify schema. Chỉ in key + type, không dump toàn bộ data."""
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                _log.debug("[SCHEMA] %s  %s -> dict (%d keys: %s)", endpoint, path, len(v), ", ".join(v.keys()))
            elif isinstance(v, list):
                _log.debug("[SCHEMA] %s  %s -> list[%d]", endpoint, path, len(v))
                if v and isinstance(v[0], dict):
                    _log.debug("[SCHEMA] %s  %s[0] keys: %s", endpoint, path, ", ".join(v[0].keys()))
            else:
                _log.debug("[SCHEMA] %s  %s -> %s = %s", endpoint, path, type(v).__name__,
                          repr(v)[:120])
    else:
        _log.debug("[SCHEMA] %s  %s -> %s", endpoint, prefix or "root", type(data).__name__)


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


# Background probe: refresh gauge da10_dependency_up ĐỊNH KỲ. Prometheus scrape /metrics chứ KHÔNG
# gọi /health/deep, nên nếu chỉ cập nhật gauge khi gọi tay /health/deep thì gauge sẽ "chết"/cũ.
# Task này định kỳ chạy deep_health() (trong threadpool vì probe là blocking I/O) để gauge luôn tươi.
_DEP_PROBE_TASK: "asyncio.Task | None" = None


async def _dep_probe_loop() -> None:
    interval = float(os.environ.get("DEP_PROBE_INTERVAL", "30"))
    while True:
        try:
            await asyncio.to_thread(deep_health)  # cập nhật DEP_UP + DEP_PROBE_DURATION
        except Exception:
            pass  # probe đã tự nuốt lỗi; phòng hờ ở đây để loop không chết
        await asyncio.sleep(interval)


@app.on_event("startup")
async def _start_dep_probe() -> None:
    """Probe deps 1 lần ngay lúc startup (gauge có giá trị tức thì) rồi chạy nền định kỳ."""
    global _DEP_PROBE_TASK
    try:
        await asyncio.to_thread(deep_health)
    except Exception:
        pass
    _DEP_PROBE_TASK = asyncio.create_task(_dep_probe_loop())


@app.on_event("shutdown")
async def _stop_dep_probe() -> None:
    if _DEP_PROBE_TASK is not None:
        _DEP_PROBE_TASK.cancel()


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
    # request_id: ưu tiên header X-Request-ID từ client/proxy, nếu không có thì tự sinh.
    # Set vào contextvar -> mọi dòng log trong request này tự mang request_id (truy vết xuyên stage).
    import uuid
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    set_request_id(rid)

    start = time.perf_counter()
    status_code = 500  # mặc định nếu downstream ném exception trước khi có response
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        # try/finally: request ném exception vẫn được đo + đếm (trước đây bỏ sót).
        endpoint = request.scope.get("route").path if request.scope.get("route") else request.url.path
        HTTP_DURATION.labels(endpoint=endpoint, method=request.method).observe(
            time.perf_counter() - start
        )
        HTTP_REQUESTS.labels(
            endpoint=endpoint, method=request.method, status=str(status_code)
        ).inc()

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


_COMPLETED_EVENTS = {"search_completed", "hybrid_search_completed", "context_completed"}


@app.get("/observability/slow_requests")
def slow_requests(
    min_ms: float = Query(0, ge=0, description="Chỉ lấy request có latency_ms >= ngưỡng này"),
    limit: int = Query(50, ge=1, le=500, description="Số request gần nhất trả về"),
) -> dict:
    """Đọc logs/da10.jsonl, trả các request đã hoàn tất (kèm query + breakdown stage_ms) để
    truy vết request CHẬM. Đây là 'poor man's tracing' theo request_id — không cần Loki/OTel.

    Trả {threshold_ms, count, requests[]} sắp xếp theo THỜI GIAN giảm dần (mới nhất lên đầu).
    requests[] gồm: timestamp, request_id, event, query, latency_ms, stage_ms{...}, n_results,
    rerank_method."""
    import json

    path = Path("logs/da10.jsonl")
    if not path.is_file():
        return {"threshold_ms": min_ms, "count": 0, "requests": [], "note": "logs/da10.jsonl chưa có"}

    rows: list[dict] = []
    try:
        # File trần 10MB (RotatingFileHandler) -> đọc toàn bộ an toàn cho endpoint admin.
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or "completed" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("event") not in _COMPLETED_EVENTS:
                    continue
                if float(rec.get("latency_ms", 0)) < min_ms:
                    continue
                rows.append({
                    "timestamp": rec.get("timestamp"),
                    "request_id": rec.get("request_id"),
                    "event": rec.get("event"),
                    "query": rec.get("query"),
                    "latency_ms": rec.get("latency_ms"),
                    "stage_ms": rec.get("stage_ms") or {},
                    "n_results": rec.get("n_results"),
                    "rerank_method": rec.get("rerank_method"),
                })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Đọc log lỗi: {exc}")

    # Log ghi theo thứ tự thời gian (cũ -> mới); đảo ngược để MỚI NHẤT lên đầu, rồi cắt limit.
    rows.reverse()
    return {"threshold_ms": min_ms, "count": len(rows[:limit]), "requests": rows[:limit]}


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
        latency_ms = round((time.time() - start_time) * 1000, 1)
        REQUEST_LATENCY.labels(endpoint=endpoint).observe((latency_ms) / 1000)
        if not result.get("top_hotels"):
            SEARCH_ZERO_RESULTS.labels(search_mode="hybrid").inc()
        _log.info("", extra={"event": "hybrid_search_completed", "latency_ms": latency_ms,
                             "query": q[:200], "stage_ms": result.get("stage_ms"),
                             "n_results": len(result.get("top_hotels", [])),
                             "rerank_method": result.get("rerank_method"), "answer": answer})
        _log.debug("=== [SCHEMA CHECK] GET /hybrid_search ===")
        _log_response_structure("GET /hybrid_search", result)
        if "top_hotels" in result and result["top_hotels"]:
            _log.debug("=== [SCHEMA CHECK] GET /hybrid_search top_hotels[0] detail ===")
            _log_response_structure("GET /hybrid_search  top_hotels[0]", result["top_hotels"][0])
        if "context_package" in result:
            _log_response_structure("GET /hybrid_search  context_package", result["context_package"])
        if "answer" in result:
            _log_response_structure("GET /hybrid_search  answer", result["answer"])
        return result
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Hybrid search error: {exc}")


@app.get("/hotel/{hotel_id}/ask")
def hotel_ask(
    hotel_id: int,
    q: str = Query(..., description="Câu hỏi về khách sạn (VD: có cho mang thú cưng không)"),
    top_k: int = Query(5, ge=1, le=20, description="Số chunk liên quan trả về"),
    sections: list[str] | None = Query(
        None,
        description="Lọc phụ: chỉ search trong các section này (loại bớt chunk). Giá trị hợp lệ: "
        "description, room_type, faq, overview, semantic_profile. Lặp tham số: "
        "?sections=faq&sections=description.",
    ),
) -> dict:
    """Trả các CHUNK liên quan nhất tới câu hỏi TRONG PHẠM VI 1 khách sạn.

    Khác /hybrid_search (tìm xuyên nhiều khách sạn rồi gom theo hotel): endpoint này khoá cứng
    theo hotel_id và chỉ semantic-search trong các chunk của đúng khách sạn đó (Qdrant filter
    payload.hotel_id == hotel_id). Nguồn là vector (chunk-level); BM25 là doc-level nên không
    dùng ở đây. Không sinh câu trả lời LLM — chỉ trả chunk + score.

    sections (tùy chọn): filter phụ cùng cấp với hotel_id — chạy trên payload, không đụng vector,
    chỉ loại bớt chunk không thuộc section yêu cầu (OR giữa các section)."""
    endpoint = "/hotel/{hotel_id}/ask"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()
    start = time.time()

    vec = _get_vector_service()
    if vec is None:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=503, detail="Vector search backend unavailable")

    try:
        res = vec.search(q, candidate_hotel_ids=[hotel_id], top_k=top_k, sections=sections)
        chunks = [
            {
                "chunk_id": h.get("chunk_id"),
                "text": h.get("text"),
                "section": h.get("section"),
                "source_type": h.get("source_type"),
                "score": h.get("score"),
            }
            for h in res.get("results", [])
        ]
        latency_ms = round((time.time() - start) * 1000, 1)
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency_ms / 1000)
        if not chunks:
            SEARCH_ZERO_RESULTS.labels(search_mode="hotel_ask").inc()
        _log.info("", extra={"event": "hotel_ask_completed", "latency_ms": latency_ms,
                             "hotel_id": hotel_id, "query": q[:200], "n_results": len(chunks),
                             "sections_filter": sections or []})
        return {
            "hotel_id": hotel_id,
            "query": q,
            "sections_filter": sections or [],
            "count": len(chunks),
            "chunks": chunks,
        }
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Hotel ask error: {exc}")


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
        latency_ms = round((time.time() - start) * 1000, 1)
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency_ms / 1000)
        resp = to_search_response(req.query, result)
        if not resp.get("results"):
            SEARCH_ZERO_RESULTS.labels(search_mode="frontend").inc()
        _log.info("", extra={"event": "search_completed", "latency_ms": latency_ms,
                             "query": req.query[:200], "stage_ms": result.get("stage_ms"),
                             "n_results": len(resp.get("results", [])),
                             "rerank_method": result.get("rerank_method")})
        _log.debug("=== [SCHEMA CHECK] POST /search ===")
        _log_response_structure("POST /search", resp)
        if resp.get("results"):
            _log.debug("=== [SCHEMA CHECK] POST /search results[0] detail ===")
            _log_response_structure("POST /search  results[0]", resp["results"][0])
            r0 = resp["results"][0]
            if r0.get("metadata"):
                _log_response_structure("POST /search  results[0].metadata", r0["metadata"])
            if r0.get("citations"):
                _log_response_structure("POST /search  results[0].citations[0]", r0["citations"][0])
            if r0.get("context_chunks"):
                _log_response_structure("POST /search  results[0].context_chunks[0]", r0["context_chunks"][0])
        return resp
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
        elapsed = time.time() - start
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        # CONTEXT_DURATION có buckets tới 120s (LLM chậm) -> p95 đúng, không bão hòa như histogram HTTP.
        CONTEXT_DURATION.observe(elapsed)
        _log.info("", extra={"event": "context_completed", "latency_ms": round(elapsed * 1000, 1),
                             "result_id": req.result_id, "has_answer": bool(out.get("llm_context"))})
        _log.debug("=== [SCHEMA CHECK] POST /context ===")
        _log_response_structure("POST /context", out)
        if out.get("citations"):
            _log_response_structure("POST /context  citations[0]", out["citations"][0])
        if out.get("source_documents"):
            _log_response_structure("POST /context  source_documents[0]", out["source_documents"][0])
        if out.get("context_chunks"):
            for i, chunk in enumerate(out["context_chunks"][:3]):
                _log_response_structure(f"POST /context  context_chunks[{i}]", chunk)
        if out.get("evidence"):
            _log_response_structure("POST /context  evidence", out["evidence"])
            if out["evidence"].get("positives"):
                _log_response_structure("POST /context  evidence.positives[0]", out["evidence"]["positives"][0])
            if out["evidence"].get("negatives"):
                _log_response_structure("POST /context  evidence.negatives[0]", out["evidence"]["negatives"][0])
        return out
    except Exception as exc:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise HTTPException(status_code=500, detail=f"Context error: {exc}")
