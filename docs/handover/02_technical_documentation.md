# Technical Documentation — DA10 Architecture

## 1. System Overview

DA10 là Knowledge & Retrieval Layer, cung cấp search intelligence cho DA09 (Travel AI Chatbot).

```
┌─────────────────────────────────────────────────────────────────┐
│                        DA09 (AI Chatbot)                        │
│                    ↓ POST /search  ↓ POST /context              │
├─────────────────────────────────────────────────────────────────┤
│                     DA10 API Layer (FastAPI)                    │
│              /search  /context  /hybrid_search  /metrics       │
├─────────────────────────────────────────────────────────────────┤
│                   Retrieval Pipeline (9 Nodes)                  │
│  Intent → Filter → Candidate → BM25+Vector → RRF → Rerank    │
├─────────────────────────────────────────────────────────────────┤
│                     Storage Layer                               │
│   PostgreSQL 16  │  Qdrant (vector)  │  OpenSearch 2 (BM25)   │
├─────────────────────────────────────────────────────────────────┤
│                   Knowledge Engineering                         │
│        Ontology (3,927 concepts)  │  ABSA  │  Relations       │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| API Framework | FastAPI | 0.111+ |
| Language | Python | 3.12 |
| Database | PostgreSQL | 16 |
| Vector DB | Qdrant | Latest |
| Search Engine | OpenSearch | 2.x |
| Embedding | bge-m3 | 1024-d |
| Reranker | bge-reranker-v2-m3 | Cross-encoder |
| Container | Docker + Docker Compose | Latest |
| CI/CD | GitHub Actions | - |
| Deployment | Google Cloud Run | asia-southeast1 |
| Monitoring | Prometheus + Grafana | Latest |

## 3. Data Pipeline

```
Agoda Crawler → Raw Data → Cleaning → Dedup → Validation → PostgreSQL
                                     ↓
                              Chunking (whole_section)
                                     ↓
                              Embedding (bge-m3)
                                     ↓
                         Qdrant (vector) + OpenSearch (BM25)
```

### 3.1 Data Quality Metrics

| Metric | Target | Achieved |
|---|---|---|
| Missing Rate | < 5% | 0% |
| Duplicate Rate | < 2% | 0% |
| Validation Errors | 0 | 0 |
| Hotels Processed | 500+ | 520 |

## 4. Retrieval Pipeline (9 Nodes)

| Node | Name | Description |
|---|---|---|
| 1 | parse_intent | Query tiếng Việt → StructuredIntent |
| 2 | hard_filter | Lọc city/star/score |
| 3 | concept_lookup | Inverted index concept → hotel_ids |
| 4 | candidate_builder | Giao/hợp + cap, ưu tiên IDF |
| 6 | text_retrieval | BM25 + Vector trên candidate |
| 7 | rrf_fusion | Hợp nhất 2 nguồn ở cấp hotel |
| 7B | neural_rerank | Cross-encoder (fallback density) |
| 7C | business_rerank | Review/price/concept + aggregate |
| 8 | context_package | Đóng gói cho LLM |

## 5. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/health/deep` | Readiness (OpenSearch, Qdrant, Postgres) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/search` | BM25 baseline search |
| POST | `/search` | Hybrid search (intent + rerank) |
| POST | `/context` | Context package for LLM |
| GET | `/hybrid_search` | GET wrapper for hybrid search |
| GET | `/eval/golden` | Golden dataset evaluation |

## 6. Ontology Structure

| Facet | Count | Example |
|---|---|---|
| Location (LOC_*) | 210 | LOC_DA_NANG, LOC_PHU_QUOC |
| Landmark (LMK_*) | 577 | LMK_BA_NA_HILLS |
| Amenity (AMEN_*) | 30 | AMEN_SPA, AMEN_POOL |
| Style (STYLE_*) | 15 | STYLE_QUIET, STYLE_LIVELY |
| Purpose (PURPOSE_*) | 5 | PURPOSE_FAMILY, PURPOSE_ROMANTIC |
| Price Tier (PRICE_*) | 3 | PRICE_BUDGET, PRICE_LUXURY |

## 7. Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://da10:da10@localhost:5432/da10

# Vector Search
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=vsf_travel

# BM25 Search
OPENSEARCH_URL=http://localhost:9200
BM25_INDEX=vsf_hotels_bm25_vi

# Embedding
EMBEDDING_MODEL=BAAI/bge-m3

# Reranker (optional)
USE_RERANKER=0  # Set 1 to enable cross-encoder
```

## 8. Architecture Decisions

| Decision | Rationale |
|---|---|
| bge-m3 over vietnamese-embedding | Better MRR (0.770 vs 0.520), handles no-diacritics |
| Qdrant over pgvector | Better performance, dedicated vector DB |
| whole_section chunking | Best nDCG (0.645), fewer chunks |
| RRF over linear fusion | More robust to score scale differences |
| Hotel-level fusion | BM25 doc-level vs Qdrant chunk-level mismatch |

---

*Document version: 1.0 | Last updated: 30/06/2026*
