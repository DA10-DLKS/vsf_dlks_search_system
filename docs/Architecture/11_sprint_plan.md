# 11 – Trạng thái Dự án

## Trạng thái hiện tại: **HOÀN THÀNH** ✅

Dự án DA10 Knowledge & Retrieval Platform đã hoàn thành và đang chạy production.

## Các Sprint đã hoàn thành

| Sprint | Nội dung | Trạng thái |
|---|---|---|
| Sprint 1 | Crawler + Ingestion (clean/dedup/validate) | ✅ |
| Sprint 2 | Chunking + Embedding + Indexing (vector + BM25) | ✅ |
| Sprint 3 | Hybrid Retrieval + Re-ranking (Node 1→9) | ✅ |
| Sprint 4 | Context Construction + API | ✅ |
| Sprint 5 | Evaluation (Recall, MRR, nDCG) + Observability | ✅ |
| Sprint 6 | Hardening, Docker, Documentation | ✅ |

## Metrics hiện tại

| Metric | Giá trị | Ghi chú |
|---|---|---|
| Recall@10 | 0.5495 | Candidate-only mode |
| Hit@10 | 1.00 | |
| MRR | 0.9065 | |
| BM25 P50 latency | 60ms | |
| Hotels indexed | 520 | Agoda crawled data |

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Vector DB**: Qdrant (bge-m3 embeddings)
- **Search Engine**: OpenSearch (BM25)
- **Database**: PostgreSQL (metadata)
- **Monitoring**: Prometheus + Grafana (local)
- **Deployment**: Docker Compose (local), Cloud Run (production)

## Known Issues

1. Auth layer chưa có (cần DA09 handle)
2. Grafana chỉ chạy local (chưa deploy)
3. Cross-encoder reranker tắt mặc định (USE_RERANKER=0)
