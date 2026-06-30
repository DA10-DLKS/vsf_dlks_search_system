# Project Closure Report — DA10 Knowledge & Retrieval Platform

**Project:** DA10 — Knowledge & Retrieval Layer for Travel AI Search
**Duration:** Sprint 1–3 (06/2026)
**Status:** Completed

---

## 1. Executive Summary

DA10 là nền tảng tri thức du lịch phục vụ DA09 (AI Chatbot), cung cấp khả năng tìm kiếm khách sạn thông minh bằng tiếng Việt. Hệ thống crawl dữ liệu từ Agoda, xây dựng pipeline ETL, lập chỉ mục hybrid (BM25 + Vector Search), rồi expose ra Search API / Context API cho downstream.

## 2. Objectives Achieved

| Objective | Status |
|---|---|
| Crawl 520+ khách sạn Việt Nam từ Agoda | ✅ |
| Pipeline data quality: 0% missing, 0% duplicate | ✅ |
| Hybrid search (BM25 + Vector) hoạt động end-to-end | ✅ |
| Context API cho DA09 RAG | ✅ |
| Observability stack (Prometheus/Grafana) | ✅ |
| CI/CD pipeline (GitHub Actions → Cloud Run) | ✅ |
| Golden evaluation framework | ✅ |

## 3. Deliverables

### Code & Infrastructure
- **Repository:** `github.com/DA10-DLKS/vsf_dlks_search_system`
- **Branches:** `develop` (active), `main` (release)
- **Deployment:** Google Cloud Run (asia-southeast1)
- **Stack:** Python 3.12, FastAPI, PostgreSQL 16, Qdrant, OpenSearch 2

### Data Assets
- 520 hotels (518 with reviews)
- 13,838 vector chunks (bge-m3, 1024-d)
- 520 BM25 documents (hotel-level)
- 3,927 ontology concepts
- Knowledge objects with ABSA aspects

### Documentation
- Architecture docs (docs/01–11)
- Project reports per team member
- API contracts (Search API, Context API)
- Deployment guide
- Operation runbook

## 4. Key Metrics

| Metric | Value |
|---|---|
| Recall@10 | 0.5495 |
| Recall@50 | 0.9505 |
| Hit@10 | 1.00 |
| nDCG@10 | 0.8235 |
| MRR | 0.9065 |
| BM25 Latency P50 | 60ms |
| BM25 Latency P95 | 108ms |

## 5. Team

| Member | Role | Contribution |
|---|---|---|
| Đỗ Minh Hiếu | Lead + DevOps + Data | Pipeline, DB, CI/CD, Frontend |
| Trương Anh Long | Ontology + System | Ontology, Retrieval pipeline, Observability |
| Lê Hoàng Đạt | Search + Docker | BM25, OpenSearch, Vector search |
| Vũ Đức Kiên | API + Monitoring | API design, Golden dataset |
| Nguyễn Ngọc Khánh Duy | Embed + Chunking | Research, Benchmark reports |
| Nguyễn Anh Tài | Rerank + Retrieval | Fusion, Reranking logic |

## 6. Known Limitations

- Cross-encoder reranker chưa chạy trên CPU (cần GPU)
- Latency E2E ~1.6s (trần = embed bge-m3 trên CPU)
- Chưa có auth/rate-limit cho production
- Golden dataset chỉ 59 câu active

## 7. Recommendations for Next Phase

1. Deploy monitoring stack (Prometheus/Grafana) lên Compute Engine
2. Thêm auth (JWT/API key) cho production
3. Benchmark cross-encoder trên GPU环境
4. Mở rộng golden dataset lên 200+ câu
5. Thêm caching layer cho query phổ biến

## 8. Sign-off

| Role | Name | Date |
|---|---|---|
| Project Lead | Đỗ Minh Hiếu | 30/06/2026 |
| Technical Lead | Trương Anh Long | 30/06/2026 |

---

*Document prepared for project closure and handover.*
