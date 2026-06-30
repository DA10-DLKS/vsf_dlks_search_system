# Known Issues — DA10 Platform

## 1. Critical Issues

| ID | Issue | Impact | Workaround |
|---|---|---|---|
| KI-001 | Cross-encoder reranker requires GPU | Reranker runs in fallback mode | Use density-fallback (default) |

---

## 2. High Priority Issues

| ID | Issue | Impact | Workaround |
|---|---|---|---|
| KI-002 | No authentication on API | Anyone can access | Deploy API gateway (Apigee) |
| KI-003 | No rate limiting | Potential abuse | Configure in API gateway |
| KI-004 | E2E latency ~1.6s | Exceeds 500ms SLO | Use GPU for embedding |
| KI-005 | Monitoring not deployed | No production observability | Deploy Prometheus/Grafana on GCE |

---

## 3. Medium Priority Issues

| ID | Issue | Impact | Workaround |
|---|---|---|---|
| KI-006 | Golden dataset only 59 queries | Limited evaluation | Expand to 200+ queries |
| KI-007 | Some hotels missing price | Incomplete results | Mock price (existing) |
| KI-008 | CORS `*` in development | Security risk | Restrict origins for production |
| KI-009 | BM25 analyzer Vietnamese basic | Some queries not optimized | Already using asciifolding |

---

## 4. Low Priority Issues

| ID | Issue | Impact | Workaround |
|---|---|---|---|
| KI-010 | pgvector tests test wrong backend | False confidence | Qdrant tests cover functionality |
| KI-011 | Frontend HTML standalone only | Not production-ready | Build React app |
| KI-012 | Some docs outdated | Confusion | Update during handover |

---

## 5. Resolved Issues

| ID | Issue | Resolution |
|---|---|---|
| KI-013 | Score scale mismatch (V1) | Min-max normalization |
| KI-014 | RRF granularity mismatch (V9) | Hotel-level fusion |
| KI-015 | BM25 analyzer standard (V10) | Vietnamese analyzer |
| KI-016 | Candidate empty (V3) | Fallback to vector |
| KI-017 | Cold start 978ms (V12) | Preload at startup |
| KI-018 | Qdrant 9% unindexed (V14) | Trigger optimize |
| KI-019 | No test for fusion (V13) | Added 13 tests |

---

## 6. Limitations

### 6.1 Technical Limitations

| Limitation | Reason | Impact |
|---|---|---|
| Embedding on CPU | No GPU in deployment | High latency |
| Cross-encoder off by default | Requires GPU | Lower rerank quality |
| Single-region deployment | GCP asia-southeast1 | No failover |

### 6.2 Data Limitations

| Limitation | Reason | Impact |
|---|---|---|
| 520 hotels only | Crawl scope | Limited coverage |
| Vietnamese hotels only | Project scope | No international |
| Agoda data only | Single source | Potential bias |

---

## 7. Security Considerations

| Issue | Status | Recommendation |
|---|---|---|
| No auth | Open | Add JWT/API key |
| No rate limiting | Open | Configure in gateway |
| CORS `*` | Development only | Restrict for production |
| Secrets in env | OK | Use Secret Manager |

---

## 8. Performance Considerations

| Metric | Current | Target | Status |
|---|---|---|---|
| E2E Latency | ~1.6s | <500ms | ⚠️ Needs GPU |
| BM25 Latency | 60ms P50 | <250ms | ✅ |
| Vector Latency | 300ms P50 | <300ms | ✅ |
| Error Rate | 0% | <0.1% | ✅ |

---

*Last updated: 30/06/2026*
