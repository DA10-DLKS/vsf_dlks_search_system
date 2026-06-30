# Deployment Guide — DA10 Platform

## Prerequisites

- Google Cloud SDK (`gcloud`)
- Docker
- Git
- GCP Project with billing enabled

---

## 1. Local Development

### 1.1 Clone & Setup

```bash
git clone https://github.com/DA10-DLKS/vsf_dlks_search_system.git
cd vsf_dlks_search_system

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Start Services

```bash
# Start infrastructure
docker compose up -d qdrant opensearch postgres

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.3 Verify

```bash
# Health check
curl http://localhost:8000/health/deep

# Test search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "resort gần biển"}'
```

---

## 2. Production Deployment (Cloud Run)

### 2.1 Prerequisites

```bash
# Set GCP project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable vpcaccess.googleapis.com
```

### 2.2 Create VPC Connector

```bash
gcloud compute networks vpc-access connectors create da10-connector \
  --region=asia-southeast1 \
  --range=10.8.0.0/28
```

### 2.3 Deploy

```bash
# Using Cloud Build
gcloud builds submit --config=cloudbuild.yaml .

# Or manual deploy
docker build -t gcr.io/YOUR_PROJECT/search-api .
docker push gcr.io/YOUR_PROJECT/search-api

gcloud run deploy search-api \
  --image=gcr.io/YOUR_PROJECT/search-api \
  --region=asia-southeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --cpu=2 \
  --memory=8Gi \
  --vpc-connector=da10-connector \
  --env-vars-file=cloudrun.env
```

### 2.4 Environment Variables

Create `cloudrun.env`:

```bash
APP_ENV=production
LOG_LEVEL=INFO
QDRANT_URL=http://YOUR_QDRANT_IP:6333
QDRANT_COLLECTION=vsf_travel
OPENSEARCH_URL=http://YOUR_OPENSEARCH_IP:9200
BM25_INDEX=vsf_hotels_bm25_vi
EMBEDDING_MODEL=BAAI/bge-m3
```

---

## 3. Infrastructure Setup

### 3.1 Qdrant (Vector DB)

```bash
# Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest

# Or GCP Compute Engine
# - Machine type: e2-standard-4
# - Disk: 50GB SSD
# - Install Docker, then run above
```

### 3.2 OpenSearch (BM25)

```bash
# Docker
docker run -d \
  --name opensearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g" \
  opensearchproject/opensearch:2
```

### 3.3 PostgreSQL

```bash
# Docker
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=da10 \
  -e POSTGRES_USER=da10 \
  -e POSTGRES_PASSWORD=da10 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16
```

---

## 4. Data Indexing

### 4.1 Vector Index (Qdrant)

```bash
# Run indexing script
python indexing/vector_index/qdrant_index.py

# Verify
curl http://localhost:6333/collections/vsf_travel
```

### 4.2 BM25 Index (OpenSearch)

```bash
# Create index
curl -X PUT "http://localhost:9200/vsf_hotels_bm25_vi" \
  -H "Content-Type: application/json" \
  -d "@indexing/bm25_index/index_mapping.json"

# Index data
python indexing/bm25_index/index_bm25.py
```

---

## 5. Monitoring Setup

### 5.1 Start Monitoring Stack

```bash
docker compose up -d prometheus grafana
```

### 5.2 Access

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (Anonymous Admin)

### 5.3 Dashboards

Grafana auto-provisions:
- Dashboard: `da10_api`
- Datasource: Prometheus

---

## 6. CI/CD Pipeline

### GitHub Actions Workflow

Located at `.github/workflows/deploy.yml`:

1. **Trigger:** Push to `develop` or `main`
2. **Build:** Docker image
3. **Push:** Artifact Registry
4. **Deploy:** Cloud Run

### Manual Deploy

```bash
# Trigger Cloud Build
gcloud builds submit --config=cloudbuild.yaml .
```

---

## 7. Rollback

```bash
# List revisions
gcloud run revisions list --service=search-api --region=asia-southeast1

# Rollback to previous
gcloud run services update-traffic search-api \
  --region=asia-southeast1 \
  --to-revisions=PREVIOUS_REVISION=100
```

---

## 8. Troubleshooting

| Issue | Solution |
|---|---|
| Service won't start | Check logs: `gcloud run services logs read search-api` |
| VPC connector error | Verify connector exists and is in same region |
| Memory exceeded | Increase `--memory` in deploy command |
| Cold start slow | Set `--min-instances=1` |

---

*Document version: 1.0 | Last updated: 30/06/2026*
