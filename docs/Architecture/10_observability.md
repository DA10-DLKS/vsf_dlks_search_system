# 10 – Quan sát & Quản trị (Xuyên suốt)

`observability/`: Monitoring, logging, health checks

## Cấu trúc thư mục

```
observability/
├── __init__.py
├── health.py            Deep health probe (OpenSearch + Qdrant + Postgres)
├── metrics/             Prometheus metrics (da10_*, search_bm25_*)
├── logging/             JSON logger (da10.jsonl)
├── tracing/             Request tracing (via request_id)
├── grafana/             Grafana dashboards
├── prometheus.yml       Prometheus config
└── alerts.yml           Alert rules
```

## Metrics (Prometheus)

### HTTP Metrics
- `da10_http_requests_total` - Total HTTP requests
- `da10_http_request_duration_seconds` - HTTP request latency

### Search Metrics
- `search_bm25_request_duration_seconds` - BM25 search latency
- `search_bm25_requests_total` - Total BM25 requests
- `search_bm25_errors_total` - Total BM25 errors
- `da10_search_zero_results_total` - Zero results counter
- `da10_search_degraded_total` - Degraded mode counter

### Pipeline Metrics
- `da10_stage_duration_seconds` - Pipeline stage latency (intent, filter, text_retrieval, fusion, rerank, context)
- `da10_rerank_method_total` - Rerank method counter (cross-encoder vs density-fallback)

### Evaluation Metrics
- `da10_eval_metric` - Evaluation metrics (recall, precision, hit, mrr, ndcg)
- `da10_eval_queries_total` - Number of eval queries
- `da10_eval_duration_seconds` - Evaluation duration

### Dependency Metrics
- `da10_dependency_up` - Dependency health (opensearch, qdrant, postgres)

## Logging

JSON logger ghi ra `logs/da10.jsonl`:
```json
{
  "timestamp": "2026-06-28T10:30:00",
  "level": "info",
  "event": "hybrid_search_completed",
  "request_id": "abc123",
  "query": "khách sạn ở Phú Quốc",
  "latency_ms": 250.5,
  "stage_ms": {
    "intent": 12.5,
    "filter": 8.3,
    "text_retrieval": 45.2,
    "fusion": 3.1,
    "rerank": 15.7,
    "context": 2.1
  },
  "n_results": 5,
  "rerank_method": "density-fallback"
}
```

## Health Checks

### Simple Health
```
GET /health → {"status": "ok"}
```

### Deep Health
```
GET /health/deep → {
  "opensearch": true,
  "qdrant": true,
  "postgres": true
}
```

## Grafana Dashboard

Dashboard URL: `http://localhost:3000` (local only)

Metrics visible:
- Request rate & latency
- Search quality (zero results, degraded mode)
- Pipeline stage breakdown
- Dependency health

## API Endpoints for Observability

| Endpoint | Mô tả |
|---|---|
| `GET /metrics` | Prometheus metrics |
| `GET /health` | Simple health check |
| `GET /health/deep` | Deep health probe |
| `GET /observability/slow_requests` | Slow request logs |
