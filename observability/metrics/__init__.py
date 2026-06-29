"""DA10 — Prometheus metrics collectors (§6.2 monitoring_plan).

Import toàn bộ từ đây; không tạo metric object ở nơi khác tránh duplicate registration.

Tất cả collector đăng ký trên ``REGISTRY`` chung (không phải default global registry)
để `api/main.py` gom cả metrics `da10_*` lẫn `search_bm25_*` cũ vào MỘT lần
``generate_latest(REGISTRY)`` ở endpoint ``GET /metrics``.
"""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# Registry dùng chung cho toàn project (xem api/main.py: search_bm25_* cũng đăng ký vào đây).
REGISTRY = CollectorRegistry()

# ── HTTP layer ────────────────────────────────────────────────────────────────

HTTP_REQUESTS = Counter(
    "da10_http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
    registry=REGISTRY,
)

HTTP_DURATION = Histogram(
    "da10_http_request_duration_seconds",
    "HTTP request duration in seconds",
    # method tách GET /search (BM25 baseline) khỏi POST /search (hybrid) — cùng route path
    # nhưng latency rất khác nhau; thiếu method thì p95 trộn 2 endpoint -> sai.
    ["endpoint", "method"],
    buckets=[0.05, 0.1, 0.15, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0],
    registry=REGISTRY,
)

SEARCH_ZERO_RESULTS = Counter(
    "da10_search_zero_results_total",
    "Search requests returning zero results",
    ["search_mode"],
    registry=REGISTRY,
)

# ── Degraded retrieval & rerank method (chất lượng vận hành) ──────────────────

SEARCH_DEGRADED = Counter(
    "da10_search_degraded_total",
    "Hybrid search chạy THIẾU nguồn text retrieval (tụt về candidate-only). "
    "label source=bm25|vector|both = nguồn đang vắng.",
    ["source"],
    registry=REGISTRY,
)

RERANK_METHOD = Counter(
    "da10_rerank_method_total",
    "Phương pháp rerank thực tế đã chạy mỗi lần search. "
    "label method=cross-encoder|density-fallback.",
    ["method"],
    registry=REGISTRY,
)

# ── LLM (Node 9) — thành phần ngoài đắt/chậm/dễ lỗi nhất của hệ RAG ───────────

LLM_DURATION = Histogram(
    "da10_llm_duration_seconds",
    "Thời gian gọi LLM sinh câu trả lời (Node 9), giây.",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 60.0],
    registry=REGISTRY,
)

LLM_REQUESTS = Counter(
    "da10_llm_requests_total",
    "Tổng lần gọi LLM. label status=ok|error (error = thiếu key/mạng/parse, answer rỗng).",
    ["status"],
    registry=REGISTRY,
)

CONTEXT_DURATION = Histogram(
    "da10_context_build_duration_seconds",
    "Context build duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 15.0, 30.0, 60.0, 120.0],
    registry=REGISTRY,
)

# ── Per-stage pipeline (§6.2 da10_stage_duration_seconds) ────────────────────

STAGE_DURATION = Histogram(
    "da10_stage_duration_seconds",
    "Pipeline stage duration in seconds",
    ["stage"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0, 15.0, 30.0],
    registry=REGISTRY,
)

# ── Golden dataset evaluation (chạy on-demand từ UI) ─────────────────────────

EVAL_METRIC = Gauge(
    "da10_eval_metric",
    "Golden dataset evaluation metric (lần chạy gần nhất). label name=recall|precision|hit|mrr|ndcg",
    ["name", "k"],
    registry=REGISTRY,
)

EVAL_QUERIES = Gauge(
    "da10_eval_queries_total",
    "Số câu golden đã đánh giá trong lần chạy gần nhất",
    registry=REGISTRY,
)

EVAL_DURATION = Histogram(
    "da10_eval_duration_seconds",
    "Thời gian chạy golden evaluation (giây)",
    buckets=[1, 5, 15, 30, 60, 120, 300, 600],
    registry=REGISTRY,
)

# ── Dependency health ─────────────────────────────────────────────────────────

DEP_UP = Gauge(
    "da10_dependency_up",
    "Dependency health: 1=up, 0=down",
    ["dependency"],
    registry=REGISTRY,
)

DEP_PROBE_DURATION = Histogram(
    "da10_dependency_probe_duration_seconds",
    "Dependency probe latency in seconds",
    ["dependency"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5],
    registry=REGISTRY,
)
