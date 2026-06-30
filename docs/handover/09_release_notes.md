# Release Notes — DA10 v1.0

**Release Date:** 30/06/2026

---

## 1. Overview

DA10 v1.0 là bản release đầu tiên, cung cấp Knowledge & Retrieval Layer cho hệ thống tìm kiếm khách sạn AI.

---

## 2. New Features

### 2.1 Core Search

- ✅ Hybrid search (BM25 + Vector) end-to-end
- ✅ Intent parsing cho tiếng Việt
- ✅ Concept-based filtering (ontology)
- ✅ Business reranking (review, price, concept)
- ✅ Hotel-level aggregation

### 2.2 APIs

- ✅ `POST /search` — Hybrid search
- ✅ `POST /context` — Context for LLM
- ✅ `GET /search` — BM25 baseline
- ✅ `GET /health/deep` — Readiness probe
- ✅ `GET /metrics` — Prometheus metrics

### 2.3 Data Pipeline

- ✅ Agoda crawler (520 hotels)
- ✅ Cleaning & deduplication
- ✅ PostgreSQL migration
- ✅ Vector indexing (Qdrant)
- ✅ BM25 indexing (OpenSearch)

### 2.4 Knowledge Engineering

- ✅ Ontology (3,927 concepts)
- ✅ ABSA aspect extraction
- ✅ Semantic profiles
- ✅ Relation graph

### 2.5 Infrastructure

- ✅ Docker Compose setup
- ✅ Cloud Run deployment
- ✅ CI/CD pipeline
- ✅ Monitoring stack

---

## 3. Performance Metrics

| Metric | Value |
|---|---|
| Recall@10 | 0.5495 |
| Recall@50 | 0.9505 |
| Hit@10 | 1.00 |
| nDCG@10 | 0.8235 |
| MRR | 0.9065 |
| BM25 P50 | 60ms |
| BM25 P95 | 108ms |

---

## 4. Bug Fixes

| Issue | Resolution |
|---|---|
| Score scale mismatch (V1) | Min-max normalization |
| RRF granularity mismatch (V9) | Hotel-level fusion |
| BM25 analyzer standard (V10) | Vietnamese analyzer |
| Candidate empty (V3) | Fallback to vector |
| Cold start 978ms (V12) | Preload at startup |

---

## 5. Breaking Changes

| Change | Migration |
|---|---|
| `BM25_INDEX` default changed | Update `.env` to `vsf_hotels_bm25_vi` |
| `travel_bm25` deprecated | Use `vsf_hotels_bm25_current` or `_vi` |

---

## 6. Dependencies

| Package | Version |
|---|---|
| Python | 3.12 |
| FastAPI | 0.111+ |
| PostgreSQL | 16 |
| Qdrant | Latest |
| OpenSearch | 2.x |
| bge-m3 | 1024-d |

---

## 7. Known Issues

- Cross-encoder reranker requires GPU
- E2E latency ~1.6s (CPU-bound)
- No authentication on API
- Golden dataset only 59 queries

See `08_known_issues.md` for full list.

---

## 8. Contributors

| Member | Role |
|---|---|
| Đỗ Minh Hiếu | Lead, DevOps, Data |
| Trương Anh Long | Ontology, System |
| Lê Hoàng Đạt | Search, Docker |
| Vũ Đức Kiên | API, Monitoring |
| Nguyễn Ngọc Khánh Duy | Embed, Chunking |
| Nguyễn Anh Tài | Rerank, Retrieval |

---

## 9. Links

- **Repository:** https://github.com/DA10-DLKS/vsf_dlks_search_system
- **API Docs:** https://search-api-xxxxxx.as.a.run.app/docs
- **Grafana:** Local only (localhost:3000)

---

*Release prepared by DA10 Team*
