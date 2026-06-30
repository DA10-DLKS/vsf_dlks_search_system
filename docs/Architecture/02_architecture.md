# 02 – Kiến trúc

Repo này ánh xạ với sơ đồ các layer của DA10.

## Cấu trúc thư mục

```
data/                   Dữ liệu thô (crawled JSON) + cleaned
crawler/                Web crawler (Agoda, etc.)
ingestion/              Pipeline làm sạch, dedup, validate
knowledge_engineering/  Chunking, embedding, enrichment, entity extraction
ontology/               Ontology, synonym, query expansion
indexing/               Vector (Qdrant), BM25 (OpenSearch), metadata index
retrieval/              Hybrid search pipeline (Node 1→9)
context/                Context package, citation, prompt builder
api/                    FastAPI endpoints
frontend/               Frontend adapter (serves static files)
observability/          Prometheus metrics, logging, health probe
evaluation/             Retrieval metrics, RAG eval, golden dataset
guardrails/             Input validation, query sanitization
config/                 Configuration files
scripts/                Utility scripts
```

## Luồng dữ liệu (Pipeline Node 1→9)

```
Node 1  parse_intent (retrieval/query_processing)
    ↓
Node 2  hard filter (retrieval/filtering)
    ↓
Node 3  concept lookup (retrieval/filtering)
    ↓
Node 4  candidate builder (retrieval/filtering)
    ↓
Node 6  BM25 + Vector search (retrieval/lexical_search + vector_search)
    ↓
Node 7  RRF fusion + profile boost (retrieval/reranking)
    ↓
Node 7B neural rerank (retrieval/reranking)
    ↓
Node 7C business rerank + aggregate_by_hotel (retrieval/reranking)
    ↓
Node 8  ContextPackage + prompt (context/)
    ↓
Node 9  LLM answer (context/answer_generator.py)
```

## Hợp đồng đầu ra

`api/` trả về **Gói ngữ cảnh sẵn sàng cho LLM** (LLM-Ready Context Package):
```json
{
  "intent": {...},
  "top_hotels": [...],
  "context_package": {
    "query": "...",
    "chunks": [...],
    "metadata": {...}
  },
  "prompt": "...",
  "answer": "..."  // optional (Node 9)
}
```

## API Endpoints

| Endpoint | Method | Mô tả |
|---|---|---|
| `/search` | POST | Frontend search → hybrid retrieval |
| `/context` | POST | Frontend context → LLM answer |
| `/hybrid_search` | GET | Hybrid search (Node 1→9) |
| `/hotel/{hotel_id}/ask` | GET | Semantic search trong 1 hotel |
| `/eval/golden` | GET | Golden dataset evaluation |
| `/health` | GET | Simple health check |
| `/health/deep` | GET | Deep health (OpenSearch + Qdrant + Postgres) |
| `/metrics` | GET | Prometheus metrics |
| `/observability/slow_requests` | GET | Slow request logs |
