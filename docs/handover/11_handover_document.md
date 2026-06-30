# Handover Document — DA10 Platform

## 1. Project Overview

**Project Name:** DA10 — Knowledge & Retrieval Layer
**Purpose:** Search intelligence for DA09 (Travel AI Chatbot)
**Repository:** https://github.com/DA10-DLKS/vsf_dlks_search_system
**Status:** Completed

---

## 2. Handover Checklist

### 2.1 Code & Repository

| Item | Status | Location |
|---|---|---|
| Source code | ✅ | `github.com/DA10-DLKS/vsf_dlks_search_system` |
| Main branch | ✅ | `main` (release) |
| Develop branch | ✅ | `develop` (active) |
| CI/CD pipeline | ✅ | `.github/workflows/deploy.yml` |
| Dockerfile | ✅ | `Dockerfile` |
| docker-compose.yml | ✅ | Root directory |

### 2.2 Infrastructure

| Item | Status | Access |
|---|---|---|
| Cloud Run service | ✅ | `search-api` (asia-southeast1) |
| PostgreSQL | ⚠️ | Manual setup required |
| Qdrant | ⚠️ | Manual setup required |
| OpenSearch | ⚠️ | Manual setup required |

### 2.3 Data

| Item | Status | Location |
|---|---|---|
| Hotel data (520) | ✅ | `data/cleaned/` |
| Vector index | ⚠️ | Re-index required (Qdrant) |
| BM25 index | ⚠️ | Re-index required (OpenSearch) |
| Ontology | ✅ | `ontology/` |
| Knowledge objects | ✅ | `knowledge_engineering/` |

### 2.4 Documentation

| Document | Status | Location |
|---|---|---|
| Project Closure Report | ✅ | `docs/handover/01_project_closure_report.md` |
| Technical Documentation | ✅ | `docs/handover/02_technical_documentation.md` |
| API Documentation | ✅ | `docs/handover/03_api_documentation.md` |
| Deployment Guide | ✅ | `docs/handover/04_deployment_guide.md` |
| Operation Runbook | ✅ | `docs/handover/05_operation_runbook.md` |
| User Manual | ✅ | `docs/handover/06_user_manual.md` |
| Test Report | ✅ | `docs/handover/07_test_report.md` |
| Known Issues | ✅ | `docs/handover/08_known_issues.md` |
| Release Notes | ✅ | `docs/handover/09_release_notes.md` |
| Lessons Learned | ✅ | `docs/handover/10_lessons_learned.md` |

---

## 3. Access Requirements

### 3.1 GitHub

```
Organization: DA10-DLKS
Repository: vsf_dlks_search_system
Branches: main, develop
```

### 3.2 Google Cloud

```
Project ID: [GCP_PROJECT_ID]
Region: asia-southeast1
Service: search-api
```

### 3.3 Credentials

| Service | Credentials | Location |
|---|---|---|
| GitHub | Personal access tokens | Team members |
| GCP | Service account key | [REDACTED] |
| PostgreSQL | da10/da10 | cloudrun.env |
| Qdrant | No auth (local) | cloudrun.env |
| OpenSearch | No auth (local) | cloudrun.env |

---

## 4. Setup Instructions

### 4.1 First Time Setup

```bash
# 1. Clone repository
git clone https://github.com/DA10-DLKS/vsf_dlks_search_system.git
cd vsf_dlks_search_system

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start infrastructure
docker compose up -d qdrant opensearch postgres

# 5. Index data
python indexing/vector_index/qdrant_index.py
python indexing/bm25_index/index_bm25.py

# 6. Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4.2 Verify Setup

```bash
# Health check
curl http://localhost:8000/health/deep

# Test search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "resort gần biển"}'

# Golden evaluation
curl "http://localhost:8000/eval/golden?limit=10"
```

---

## 5. Key Contacts

| Role | Name | Email |
|---|---|---|
| Project Lead | Đỗ Minh Hiếu | [email] |
| Technical Lead | Trương Anh Long | [email] |
| DA09 Integration | [DA09 Lead] | [email] |

---

## 6. Known Issues to Address

| Priority | Issue | Recommended Action |
|---|---|---|
| High | No auth on API | Add JWT/API key |
| High | Monitoring not deployed | Deploy Prometheus/Grafana |
| High | E2E latency >1s | Use GPU for embedding |
| Medium | Golden dataset small | Expand to 200+ queries |
| Medium | No rate limiting | Configure in API gateway |

---

## 7. Next Steps for Receiving Team

1. **Review documentation** — Start with `02_technical_documentation.md`
2. **Set up development environment** — Follow `04_deployment_guide.md`
3. **Run tests** — Verify everything works
4. **Deploy monitoring** — Follow `05_operation_runbook.md`
5. **Address known issues** — Prioritize from `08_known_issues.md`

---

## 8. Acceptance

| Role | Name | Signature | Date |
|---|---|---|---|
| Handover By | Đỗ Minh Hiếu | _____________ | ___/___/2026 |
| Received By | _____________ | _____________ | ___/___/2026 |

---

*Document prepared for project handover — 30/06/2026*
