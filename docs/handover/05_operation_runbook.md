# Operation Runbook — DA10 Platform

## 1. Service Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Cloud Run  │────▶│   Qdrant     │     │  PostgreSQL  │
│  (API)       │     │  (Vector)    │     │   (Metadata) │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       ├────────────▶┌──────────────┐
       │             │  OpenSearch  │
       │             │   (BM25)     │
       │             └──────────────┘
       │
       └────────────▶┌──────────────┐
                     │   GCS/Qdrant │
                     │  (Storage)   │
                     └──────────────┘
```

---

## 2. Common Operations

### 2.1 Check Service Status

```bash
# Health check
curl https://search-api-xxxxxx.as.a.run.app/health/deep

# Expected response
{
  "status": "ok",
  "checks": {
    "opensearch": {"status": "ok"},
    "qdrant": {"status": "ok"},
    "postgres": {"status": "ok"}
  }
}
```

### 2.2 View Logs

```bash
# Cloud Run logs
gcloud run services logs read search-api \
  --region=asia-southeast1 \
  --limit=100

# Filter errors
gcloud run services logs read search-api \
  --region=asia-southeast1 \
  --filter="severity=ERROR"
```

### 2.3 Check Metrics

```bash
# Prometheus metrics
curl https://search-api-xxxxxx.as.a.run.app/metrics

# Key metrics to monitor
- da10_http_request_duration_seconds (latency)
- da10_search_degraded_total (degraded mode)
- da10_rerank_method_total (rerank distribution)
- da10_dependency_up (service health)
```

---

## 3. Troubleshooting

### 3.1 High Latency (>500ms)

**Symptoms:** P95 latency exceeds SLO

**Diagnosis:**
```bash
# Check stage breakdown
curl "https://search-api-xxxxxx.as.a.run.app/observability/slow_requests?min_ms=500&limit=5"
```

**Common Causes:**
| Stage | Normal | Problem |
|---|---|---|
| parse_intent | <5ms | Cold start (synonym load) |
| hard_filter | <5ms | Cache miss |
| bm25 | <150ms | OpenSearch overload |
| vector | <300ms | Qdrant overload |
| embed | <100ms | CPU-only (need GPU) |

**Solutions:**
1. Cold start: Pre-warm with startup event
2. OpenSearch: Scale up or optimize index
3. Qdrant: Check HNSW index status
4. Embed: Use GPU instance

### 3.2 Zero Results

**Symptoms:** Search returns empty results

**Diagnosis:**
```bash
# Check if candidates exist
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}' \
  | jq '.total_found'
```

**Common Causes:**
- Candidate pool empty (no hotels match filters)
- Vector service down (degraded mode)
- Index not built

**Solutions:**
1. Verify index exists: `curl http://localhost:9200/_cat/indices`
2. Check Qdrant collection: `curl http://localhost:6333/collections`
3. Re-index if needed

### 3.3 Service Down

**Symptoms:** 503 or health check fails

**Diagnosis:**
```bash
# Check dependency status
curl https://search-api-xxxxxx.as.a.run.app/health/deep

# Check Cloud Run status
gcloud run services describe search-api --region=asia-southeast1
```

**Solutions:**
1. Dependency down: Restart specific service
2. Cloud Run down: Check GCP status page
3. Memory/CPU: Increase resources

---

## 4. Scaling

### 4.1 Cloud Run Auto-scaling

```bash
# Update scaling settings
gcloud run services update search-api \
  --region=asia-southeast1 \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=20
```

### 4.2 Qdrant Scaling

```bash
# Check collection stats
curl http://localhost:6333/collections/vsf_travel

# Optimize if needed
curl -X PATCH http://localhost:6333/collections/vsf_travel \
  -H "Content-Type: application/json" \
  -d '{"optimizer_config": {"indexing_threshold": 100}}'
```

---

## 5. Backup & Recovery

### 5.1 Qdrant Backup

```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/vsf_travel/snapshots

# Download snapshot
curl -o backup.tar http://localhost:6333/collections/vsf_travel/snapshots/BACKUP_ID
```

### 5.2 PostgreSQL Backup

```bash
# Dump database
pg_dump -h localhost -U da10 da10 > backup.sql

# Restore
psql -h localhost -U da10 da10 < backup.sql
```

---

## 6. Monitoring Alerts

### 6.1 Prometheus Alerts

| Alert | Condition | Action |
|---|---|---|
| HighErrorRate | 5xx > 5% for 5m | Check logs, restart |
| HighLatency | P95 > 1.5s for 10m | Scale up, check deps |
| DependencyDown | dep == 0 for 1m | Restart dependency |
| SearchDegraded | degraded > 0 for 5m | Check vector/BM25 |

### 6.2 Grafana Dashboards

- **DA10 API:** Request rate, latency, errors
- **Pipeline Stages:** Intent, filter, retrieval, rerank
- **Dependencies:** OpenSearch, Qdrant, PostgreSQL health

---

## 7. Emergency Procedures

### 7.1 Complete Service Outage

```bash
# 1. Check GCP status
gcloud run services describe search-api --region=asia-southeast1

# 2. Rollback to last known good
gcloud run services update-traffic search-api \
  --region=asia-southeast1 \
  --to-revisions=LAST_GOOD_REVISION=100

# 3. If still down, redeploy
gcloud builds submit --config=cloudbuild.yaml .
```

### 7.2 Data Corruption

```bash
# 1. Stop writes to affected service
# 2. Restore from backup
# 3. Re-index if vector/BM25 affected
python indexing/vector_index/qdrant_index.py
python indexing/bm25_index/index_bm25.py
# 4. Verify with golden eval
curl "http://localhost:8000/eval/golden?limit=10"
```

---

## 8. Contacts

| Role | Name | Contact |
|---|---|---|
| Project Lead | Đỗ Minh Hiếu | [email] |
| Technical Lead | Trương Anh Long | [email] |
| DevOps | Đỗ Minh Hiếu | [email] |

---

*Document version: 1.0 | Last updated: 30/06/2026*
