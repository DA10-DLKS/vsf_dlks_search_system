# 06 – Hạ tầng Truy xuất (Layer 6)

`retrieval/`: Pipeline hybrid retrieval Node 1→9

## Cấu trúc thư mục

```
retrieval/
├── query_processing/      Node 1: parse_intent (intent_parser.py)
├── filtering/             Node 2-4: hard_filter, concept_index, candidate builder
├── lexical_search/        Node 6a: BM25 search (OpenSearch)
├── vector_search/         Node 6b: Semantic search (Qdrant + bge-m3)
├── hybrid_search/         Orchestrator: pipeline.py (nối Node 1→9)
└── reranking/             Node 7: RRF fusion, neural rerank, business rerank
```

## Pipeline Nodes

| Node | Module | Mô tả |
|---|---|---|
| **Node 1** | `query_processing/intent_parser.py` | Parse query → intent (concepts, city, brand, price, star, exclude) |
| **Node 2** | `filtering/hard_filter.py` | Hard filter: city, star, score, brand, price range |
| **Node 3** | `filtering/concept_index.py` | Concept lookup: inverted index for amenities, purposes, landmarks |
| **Node 4** | `filtering/` | Candidate builder: gộp hard filter + concept filter + review score |
| **Node 6** | `lexical_search/` + `vector_search/` | BM25 + Vector search trên candidates |
| **Node 7** | `reranking/fusion.py` | RRF fusion + profile boost |
| **Node 7B** | `reranking/neural_rerank.py` | Cross-encoder rerank (optional, USE_RERANKER=1) |
| **Node 7C** | `reranking/fusion.py` | Business rerank + aggregate_by_hotel |
| **Node 8** | `context/context_package.py` | ContextPackage + prompt builder |
| **Node 9** | `context/answer_generator.py` | LLM answer generation (optional) |

## Thiết kế tolerant

Pipeline chạy được ngay cả khi thiếu service:
- Thiếu BM25 → dùng vector-only
- Thiếu Vector → dùng BM25-only
- Thiếu cả hai → dùng candidate + KE labels (business score)
- Cross-encoder tắt mặc định (USE_RERANKER=0) → dùng density-fallback

## Đầu ra
Danh sách hotel đã xếp hạng kèm context package:
```json
{
  "intent": {...},
  "top_hotels": [...],
  "context_package": {
    "query": "...",
    "chunks": [...],
    "metadata": {...}
  },
  "prompt": "..."
}
```
