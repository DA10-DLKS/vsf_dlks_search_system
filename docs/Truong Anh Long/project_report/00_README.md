# Báo cáo chi tiết dự án — Hệ thống tìm kiếm khách sạn DA10

Bộ báo cáo mô tả chi tiết quá trình thực hiện & triển khai từng khâu của hệ thống tìm kiếm/RAG khách sạn (corpus **520 khách sạn Việt Nam**, dữ liệu thật từ Agoda).

## Mục lục

| # | Đầu việc | File |
|---|---|---|
| 01 | **Data** — crawl & clean | [01_data_crawl_clean.md](01_data_crawl_clean.md) |
| 02 | **Ontology** & Knowledge Engineering | [02_ontology.md](02_ontology.md) |
| 03 | **Chunking & Embedding** | [03_chunking_embedding.md](03_chunking_embedding.md) |
| 04 | **Retrieval & Ranking** | [04_retrieval_ranking.md](04_retrieval_ranking.md) |
| 05 | **Search Indexing** (BM25 + Vector) | [05_search_indexing.md](05_search_indexing.md) |
| 06 | **Frontend** | [06_frontend.md](06_frontend.md) |
| 07 | **Monitoring & Observability** | [07_monitoring.md](07_monitoring.md) |

## Luồng dữ liệu xuyên hệ thống

```
Agoda ─crawl─▶ data/raw ─clean/validate─▶ data/cleaned (520)
                                              │
              Knowledge Engineering ──────────┤
              (ontology + ABSA + relations)   │
                                              ▼
                                   knowledge_objects.json (520 nhãn)
                                              │
                   chunk_document + attach_ke_labels + bge-m3 (1024-d)
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                         OpenSearch BM25            Qdrant vector
                                  └───────────┬───────────┘
                            Retrieval pipeline (Node 1→9)
                  intent ▸ filter ▸ candidate ▸ BM25+vector
                  ▸ RRF fusion ▸ rerank ▸ context ▸ LLM
                                              │
                              FastAPI (/search, /context, /hybrid_search)
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                              Frontend (RAG demo)   Observability
                                                    (Prometheus/Grafana)
```

## Số liệu chốt

- **520** khách sạn VN (`data/cleaned`), **518** file review.
- Ontology: **3.927** concept có surface_form; địa danh tự sinh 1 country / 14 province / 69 city / 126 area / 153 landmark.
- Embedding: **bge-m3**, 1024 chiều, cosine.
- Rerank: **bge-reranker-v2-m3** (cross-encoder, mặc định off → density-fallback).
- Golden: 70 câu/bản (59 active). Mốc: **Recall 0.5114, MRR 0.9065, Hit 0.9831** (golden_set_v2, neural_w=0.05).

## Ghi chú

Các báo cáo bám sát code thực tế trong repo (file path là link clickable), nêu cả các quyết định kỹ thuật & bài học (fix scale mismatch RRF, segfault torch trong threadpool, blue-green alias, chống màn hình trắng...). Không có số liệu bịa: giá/grades thiếu được để null hoặc đánh dấu placeholder.
