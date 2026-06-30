# 08 – Dịch vụ Nền tảng / Hợp đồng API (Layer 8)

`api/` cung cấp các dịch vụ truy xuất tái sử dụng được mà DA09 sẽ gọi.

## Base URL
```
http://localhost:8000
```

## Endpoints

### Search API (Frontend)

#### `POST /search`
Frontend search endpoint. Hybrid retrieval → results.

**Request:**
```json
{
  "query": "khách sạn có hồ bơi ở Nha Trang",
  "filters": null,
  "top_n": 10
}
```

**Response:**
```json
{
  "query": "...",
  "results": [
    {
      "hotel_id": 65153,
      "title": "Vinpearl Resort Nha Trang",
      "score": 0.85,
      "location": "Nha Trang, Khánh Hòa",
      "category": "Hotel",
      "amenities": ["Hồ bơi", "Spa", "Wi-Fi"],
      "ranking_info": "5★ · điểm 8.5/10",
      "price_level": "Cao cấp",
      "best_for": ["Gia đình", "Cặp đôi"],
      "rooms": [...],
      "rooms_matching": [...]
    }
  ],
  "total": 5
}
```

#### `POST /context`
Frontend context endpoint. Build LLM context for selected hotel.

**Request:**
```json
{
  "result_id": "hotel_65153",
  "query": "khách sạn có hồ bơi không?"
}
```

**Response:**
```json
{
  "result_id": "hotel_65153",
  "llm_context": "Khách sạn Vinpearl Resort Nha Trang có hồ bơi...",
  "citations": [...],
  "source_documents": [...],
  "context_chunks": [...],
  "evidence": {
    "positives": [...],
    "negatives": [...]
  }
}
```

### Hybrid Search API

#### `GET /hybrid_search`
Hybrid retrieval Node 1→9. Full pipeline.

**Query Parameters:**
| Param | Type | Default | Mô tả |
|---|---|---|---|
| `q` | string | required | Câu hỏi tiếng Việt |
| `top_n` | int | 5 | Số hotel tối đa |
| `answer` | bool | false | Sinh LLM answer (Node 9) |

**Response:**
```json
{
  "intent": {
    "concepts": ["AMEN_POOL", "LOC_NHA_TRANG"],
    "city": "Nha Trang",
    "range": {...}
  },
  "n_candidates": 45,
  "n_fused": 45,
  "rerank_method": "density-fallback",
  "stage_ms": {
    "intent": 12.5,
    "filter": 8.3,
    "text_retrieval": 45.2,
    "fusion": 3.1,
    "rerank": 15.7,
    "context": 2.1
  },
  "top_hotels": [...],
  "context_package": {...},
  "prompt": "...",
  "answer": "..."  // optional
}
```

### Hotel Ask API

#### `GET /hotel/{hotel_id}/ask`
Semantic search trong phạm vi 1 khách sạn.

**Query Parameters:**
| Param | Type | Default | Mô tả |
|---|---|---|---|
| `q` | string | required | Câu hỏi |
| `top_k` | int | 5 | Số chunk trả về |
| `sections` | list | null | Lọc theo section (description, room_type, faq, overview) |

**Response:**
```json
{
  "hotel_id": 65153,
  "query": "có cho mang thú cưng không?",
  "sections_filter": [],
  "count": 3,
  "chunks": [
    {
      "chunk_id": "chunk_65153_overview",
      "text": "...",
      "section": "description",
      "source_type": "hotel_content",
      "score": 0.89
    }
  ]
}
```

### Evaluation API

#### `GET /eval/golden`
Chạy golden dataset evaluation.

**Query Parameters:**
| Param | Type | Default | Mô tả |
|---|---|---|---|
| `k` | int | 10 | Top-K for metrics |
| `limit` | int | 10 | Số câu golden chạy |
| `use_services` | bool | false | Dùng vector+BM25 services |

**Response:**
```json
{
  "summary": {
    "k": 10,
    "n_queries": 10,
    "recall": 0.55,
    "precision": 0.055,
    "hit": 1.0,
    "mrr": 0.91,
    "ndcg": 0.62
  },
  "per_query": [...],
  "duration_s": 12.5,
  "mode": "candidate-only"
}
```

### Observability API

#### `GET /health`
Simple health check.

**Response:** `{"status": "ok"}`

#### `GET /health/deep`
Deep health: probe OpenSearch + Qdrant + Postgres.

**Response:**
```json
{
  "opensearch": true,
  "qdrant": true,
  "postgres": true
}
```

#### `GET /metrics`
Prometheus metrics endpoint.

**Response:** Prometheus text format

#### `GET /observability/slow_requests`
Đọc slow request logs.

**Query Parameters:**
| Param | Type | Default | Mô tả |
|---|---|---|---|
| `min_ms` | float | 0 | Ngưỡng latency tối thiểu |
| `limit` | int | 50 | Số request trả về |

**Response:**
```json
{
  "threshold_ms": 100,
  "count": 5,
  "requests": [
    {
      "timestamp": "2026-06-28T10:30:00",
      "request_id": "abc123",
      "event": "hybrid_search_completed",
      "query": "khách sạn ở Phú Quốc",
      "latency_ms": 250.5,
      "stage_ms": {...},
      "n_results": 5,
      "rerank_method": "density-fallback"
    }
  ]
}
```

## Error Responses

```json
{
  "detail": "Hybrid search error: ..."
}
```

Status codes:
- `200`: Success
- `500`: Internal server error
- `503`: Service unavailable (backend down)
