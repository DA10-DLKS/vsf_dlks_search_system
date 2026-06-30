# Test Report — DA10 Platform

## 1. Test Summary

| Test Category | Total | Passed | Failed | Coverage |
|---|---|---|---|---|
| Unit Tests | 45 | 45 | 0 | 78% |
| Integration Tests | 12 | 12 | 0 | 85% |
| E2E Tests | 8 | 8 | 0 | 90% |
| **Total** | **65** | **65** | **0** | **82%** |

---

## 2. Unit Tests

### 2.1 Fusion & Ranking (`test_fusion_ranking.py`)

| Test | Description | Status |
|---|---|---|
| test_business_rerank_normalizes_text_signal | V1: min-max normalization | ✅ |
| test_rrf_by_hotel_merges_sources | V9: Hotel-level RRF | ✅ |
| test_rrf_by_hotel_prefers_best_rank | V9: Best rank selection | ✅ |
| test_aggregate_by_hotel_deduplicates | Hotel aggregation | ✅ |
| test_aggregate_by_hotel_price_sort | Price sort | ✅ |

### 2.2 Intent Parser (`test_intent_parser.py`)

| Test | Description | Status |
|---|---|---|
| test_parse_city | City extraction | ✅ |
| test_parse_concepts | Concept extraction | ✅ |
| test_parse_price_range | Price range parsing | ✅ |
| test_parse_no_diacritics | No-diacritics support | ✅ |

### 2.3 Vector Search (`test_qdrant_service.py`)

| Test | Description | Status |
|---|---|---|
| test_search_returns_results | Basic search | ✅ |
| test_search_with_filters | Filtered search | ✅ |
| test_search_payload_limited | V11: Payload optimization | ✅ |

### 2.4 Import Smoke (`test_imports_smoke.py`)

| Test | Description | Status |
|---|---|---|
| test_import_all_modules | All modules importable | ✅ |

---

## 3. Integration Tests

### 3.1 API Endpoints

| Endpoint | Method | Status |
|---|---|---|
| `/health` | GET | ✅ |
| `/health/deep` | GET | ✅ |
| `/search` | GET | ✅ |
| `/search` | POST | ✅ |
| `/context` | POST | ✅ |
| `/hybrid_search` | GET | ✅ |
| `/metrics` | GET | ✅ |

### 3.2 Pipeline Integration

| Component | Status |
|---|---|
| Intent → Filter → Candidate | ✅ |
| BM25 + Vector → RRF | ✅ |
| RRF → Rerank → Business | ✅ |
| Business → Aggregate | ✅ |
| Aggregate → Context | ✅ |

---

## 4. End-to-End Tests

### 4.1 Golden Dataset Evaluation

| Metric | Target | Achieved | Status |
|---|---|---|---|
| Recall@10 | >0.53 | 0.5495 | ✅ |
| Recall@50 | >0.90 | 0.9505 | ✅ |
| Hit@10 | >0.98 | 1.00 | ✅ |
| nDCG@10 | >0.80 | 0.8235 | ✅ |
| MRR | >0.90 | 0.9065 | ✅ |

### 4.2 Performance Tests

| Metric | Target | Achieved | Status |
|---|---|---|---|
| BM25 P50 | <250ms | 60ms | ✅ |
| BM25 P95 | <500ms | 108ms | ✅ |
| BM25 P99 | <1000ms | 142ms | ✅ |
| Error Rate | <0.1% | 0.00% | ✅ |

---

## 5. Test Environment

| Component | Version | Configuration |
|---|---|---|
| Python | 3.12 | - |
| Qdrant | Latest | 13,838 vectors |
| OpenSearch | 2.x | 520 documents |
| PostgreSQL | 16 | 520 hotels |

---

## 6. Test Execution

### 6.1 Run All Tests

```bash
# Unit + Integration
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Specific test file
pytest tests/test_fusion_ranking.py -v
```

### 6.2 Golden Evaluation

```bash
# Full evaluation
curl "http://localhost:8000/eval/golden?k=10"

# Quick test (10 queries)
curl "http://localhost:8000/eval/golden?k=10&limit=10"
```

---

## 7. Known Test Issues

| Issue | Severity | Status |
|---|---|---|
| pgvector tests test wrong backend | Low | Known (Qdrant tests cover) |
| Golden dataset only 59 queries | Medium | Planned expansion |

---

## 8. CI/CD Integration

Tests run automatically on:
- Pull requests to `develop`
- Push to `develop`
- Manual trigger

**CI Gate:**
```bash
# Fail if recall drops below threshold
GATE_MODE=1
GATE_MIN_RECALL=0.53
GATE_MIN_HIT=0.98
```

---

*Report generated: 30/06/2026*
