# API Documentation — DA10 Knowledge & Retrieval Platform

## Base URL

```
Production: https://search-api-xxxxxx.as.a.run.app
Local: http://localhost:8000
```

## Authentication

Currently **no authentication** required (allow_unauthenticated).

> ⚠️ For production, add JWT/API key authentication.

---

## 1. Health Check

### GET `/health`

Liveness probe.

**Response:**
```json
{
  "status": "ok"
}
```

### GET `/health/deep`

Readiness probe — checks OpenSearch, Qdrant, PostgreSQL.

**Response:**
```json
{
  "status": "ok",
  "checks": {
    "opensearch": {"status": "ok", "latency_ms": 5.2},
    "qdrant": {"status": "ok", "latency_ms": 3.1},
    "postgres": {"status": "ok", "latency_ms": 2.8}
  }
}
```

---

## 2. Search API

### POST `/search`

Hybrid search with intent parsing, reranking, and business scoring.

**Request:**
```json
{
  "query": "resort yên tĩnh gần biển cho gia đình",
  "top_k": 10,
  "filters": {
    "city": "Đà Nẵng",
    "price_max": 3000000
  }
}
```

**Response:**
```json
{
  "query": "resort yên tĩnh gần biển cho gia đình",
  "total_found": 47,
  "returned": 10,
  "latency_ms": 312,
  "rerank_method": "density-fallback",
  "results": [
    {
      "hotel_id": 542,
      "name": "DoubleTree by Hilton Hotel & Suites",
      "city": "Houston (TX)",
      "star_rating": 3.0,
      "review_score": 7.6,
      "price_from": 1500000,
      "description": "Thêm an tâm với Hilton CleanStay...",
      "amenities_top": ["Bể bơi ngoài trời", "Nhà hàng"],
      "ranking": {
        "final_score": 0.834,
        "rank": 1,
        "relevance_score": 0.912
      }
    }
  ],
  "parsed_intent": {
    "original_query": "resort yên tĩnh gần biển cho gia đình",
    "intent_type": "hotel_search",
    "confidence": 0.87
  }
}
```

### GET `/search`

BM25 baseline search (legacy).

**Parameters:**
- `q` (string): Query text
- `size` (int): Number of results (default: 10)

**Example:**
```
GET /search?q=khách+sạn+gần+biển&size=5
```

---

## 3. Context API

### POST `/context`

Returns context package for LLM consumption.

**Request:**
```json
{
  "hotel_id": 542,
  "query": "resort yên tĩnh gần biển cho gia đình",
  "query_id": "q-7f3a2b91-4c1e-4d8f-b2a3-9e0f1c2d3e4f",
  "options": {
    "max_context_tokens": 1500,
    "include_chunks": true
  }
}
```

**Response:**
```json
{
  "hotel_id": 542,
  "hotel_name": "DoubleTree by Hilton Hotel & Suites",
  "context_text": "Nằm ở vị trí trung tâm tại Westchase...",
  "chunks": [
    {
      "chunk_id": "chunk-542-desc-001",
      "text": "Nằm ở vị trí trung tâm tại Westchase...",
      "source_type": "hotel_description",
      "scores": {
        "rrf_score": 0.82,
        "reranker_score": 0.91
      }
    }
  ],
  "citations": [
    {
      "citation_id": "cit-001",
      "chunk_id": "chunk-542-desc-001",
      "source_type": "hotel_description",
      "relevance_score": 0.91
    }
  ],
  "latency_ms": 45
}
```

---

## 4. Evaluation API

### GET `/eval/golden`

Run golden dataset evaluation on-demand.

**Parameters:**
- `k` (int): Top-K (default: 10)
- `limit` (int): Number of queries (default: all)
- `use_services` (bool): Use vector+BM25 (default: true)

**Example:**
```
GET /eval/golden?k=10&limit=10
```

**Response:**
```json
{
  "summary": {
    "recall": 0.5495,
    "precision": 0.6983,
    "hit": 1.0,
    "mrr": 0.9065,
    "ndcg": 0.8235
  },
  "n_queries": 59,
  "duration_seconds": 125.3
}
```

---

## 5. Metrics

### GET `/metrics`

Prometheus metrics endpoint.

**Key Metrics:**
- `da10_http_request_duration_seconds` — HTTP latency
- `da10_stage_duration_seconds` — Pipeline stage latency
- `da10_rerank_method_total` — Rerank method distribution
- `da10_dependency_up` — Service health

---

## Error Responses

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Query is required",
    "user_message": "Vui lòng nhập câu tìm kiếm"
  }
}
```

**Error Codes:**
- `INVALID_REQUEST` — Request body invalid
- `HOTEL_NOT_FOUND` — Hotel ID doesn't exist
- `NO_RESULTS` — No hotels match filters
- `RETRIEVAL_TIMEOUT` — Pipeline exceeded SLO
- `INTERNAL_ERROR` — Unexpected error

---

## Rate Limits

Currently **no rate limits** configured.

> ⚠️ For production, implement rate limiting (recommended: 100 req/min per client).

---

*API Version: v1 | Last updated: 30/06/2026*
