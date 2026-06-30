# Lessons Learned — DA10 Project

## 1. Technical Lessons

### 1.1 Vector Search

| Lesson | Details |
|---|---|
| **Chunking strategy matters less than expected** | whole_section vs fixed_token: difference <0.1 nDCG |
| **context_prefix is critical** | Adding hotel name to chunks: 0→1.0 recall improvement |
| **bge-m3 over vietnamese-embedding** | Better MRR, handles no-diacritics |
| **Hotel-level fusion for mixed granularity** | BM25 doc-level + Qdrant chunk-level → fuse at hotel |

### 1.2 Scoring & Ranking

| Lesson | Details |
|---|---|
| **Score scale mismatch is silent killer** | RRF [0,0.016] vs review [0,1] → text signal invisible |
| **Min-max normalization works** | Simple fix for scale mismatch |
| **Calibrate weights with data** | neural=0.05 via sweep, not intuition |
| **Business signals > text for this domain** | KE labels stronger than vector on travel corpus |

### 1.3 Infrastructure

| Lesson | Details |
|---|---|
| **Docker Compose ≠ Production** | Local stack doesn't map to Cloud Run |
| **Cold start is real** | 978ms for synonym load on first request |
| **Payload optimization matters** | Qdrant 840ms → 244ms by limiting fields |
| **Cache simple things** | Hard filter normalize: 227ms → 2ms |

---

## 2. Process Lessons

### 2.1 Evaluation

| Lesson | Details |
|---|---|
| **A/B testing catches what unit tests miss** | FULL vs NO-SERVICE revealed vector was useless |
| **Golden dataset is gold** | 59 queries found bugs no code review caught |
| **Measure before and after** | Baseline is essential for proving improvement |
| **Report multiple metrics** | Recall@10 looks bad, Recall@50 tells truth |

### 2.2 Documentation

| Lesson | Details |
|---|---|
| **Write assessment, not just code** | 607-line system assessment found 17 issues |
| **Two audits can contradict** | Static audit vs running audit: different conclusions |
| **Numbers beat opinions** | "Vector is useless" → measured: "only +0.9% recall" |

### 2.3 Team

| Lesson | Details |
|---|---|
| **Specialists > generalists for core** | Ontology needs depth, not breadth |
| **Documentation doesn't equal implementation** | Reports are not code |
| **Git history reveals truth** | Can't fake commits |

---

## 3. Architecture Lessons

### 3.1 What Worked

| Decision | Outcome |
|---|---|
| PostgreSQL over DuckDB | Better for production, real-time sharing |
| Qdrant over pgvector | Better performance, dedicated |
| Hybrid search architecture | Flexibility to degrade gracefully |
| Ontology-first approach | Strong foundation for search quality |

### 3.2 What Didn't Work

| Decision | Issue | Fix |
|---|---|---|
| DuckDB initially | Not production-ready | Migrated to PostgreSQL |
| BM25 doc-level indexing | Granularity mismatch | Hotel-level fusion |
| Cross-encoder default on | Too slow on CPU | Default off, env switch |
| pgvector tests | Testing wrong backend | Added Qdrant tests |

---

## 4. Project Management Lessons

### 4.1 Sprint Planning

| Lesson | Details |
|---|---|
| **Start with walking skeleton** | End-to-end first, optimize later |
| **Parallel work needs clear contracts** | API contract should be defined early |
| **Technical debt accumulates fast** | Fix issues before they compound |

### 4.2 Team Coordination

| Lesson | Details |
|---|---|
| **Dependency mapping is essential** | Know who blocks whom |
| **Daily sync prevents divergence** | Catch issues early |
| **Code review catches architecture issues** | Not just style |

---

## 5. Recommendations for Next Team

### 5.1 Must Do

1. **Deploy monitoring** — Prometheus/Grafana on GCE
2. **Add authentication** — JWT or API key
3. **Expand golden dataset** — 200+ queries
4. **GPU for embedding** — Required for SLO

### 5.2 Should Do

1. **Chunk-level BM25 indexing** — Proper fusion
2. **Query expansion** — Better recall for abstract queries
3. **Caching layer** — Reduce latency
4. **Load testing** — Validate SLO under load

### 5.3 Nice to Have

1. **Multi-language support** — English queries
2. **Real-time price updates** — Live pricing
3. **User feedback loop** — Improve ranking
4. **A/B testing framework** — Continuous improvement

---

## 6. Key Metrics to Track

| Metric | Current | Target |
|---|---|---|
| Recall@10 | 0.5495 | >0.60 |
| Recall@50 | 0.9505 | >0.98 |
| E2E Latency | ~1.6s | <500ms |
| Error Rate | 0% | <0.1% |

---

## 7. Final Thoughts

The DA10 project demonstrated that:
1. **Hybrid search works** but requires careful calibration
2. **Knowledge engineering is the foundation** — ontology quality drives search quality
3. **Measurement is everything** — what gets measured gets improved
4. **Simple fixes can have big impact** — min-max normalization was 10 lines but fixed the core issue

---

*Compiled by DA10 Team — 30/06/2026*
