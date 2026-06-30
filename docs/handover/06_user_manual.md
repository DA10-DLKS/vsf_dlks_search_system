# User Manual — DA10 Search Platform

## 1. Introduction

DA10 là nền tảng tìm kiếm khách sạn thông minh, sử dụng AI để hiểu câu hỏi tiếng Việt và trả về kết quả phù hợp nhất.

---

## 2. Getting Started

### 2.1 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 10, macOS, Linux | Ubuntu 22.04 |
| Python | 3.12+ | 3.12 |
| RAM | 8GB | 16GB |
| Disk | 20GB free | 50GB SSD |
| Docker | 24.0+ | Latest |

### 2.2 Installation

#### Step 1: Clone Repository

```bash
git clone https://github.com/DA10-DLKS/vsf_dlks_search_system.git
cd vsf_dlks_search_system
```

#### Step 2: Create Virtual Environment

```bash
# Linux/Mac
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Setup Environment Variables

```bash
# Copy example
cp .env.example .env

# Edit .env with your settings
# Default values work for local development
```

### 2.3 Start Services

#### Option A: Docker Compose (Recommended)

```bash
# Start all infrastructure
docker compose up -d

# Check status
docker compose ps
```

This starts:
- PostgreSQL (port 5432)
- Qdrant (port 6333)
- OpenSearch (port 9200)
- Prometheus (port 9090)
- Grafana (port 3000)

#### Step 5: Start API Server

```bash
# Development mode (with auto-reload)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Step 6: Index Data (First Time Only)

```bash
# Index vectors to Qdrant
python indexing/vector_index/qdrant_index.py

# Index documents to OpenSearch
python indexing/bm25_index/index_bm25.py
```

### 2.4 Verify Installation

```bash
# Health check
curl http://localhost:8000/health/deep

# Expected output
{
  "status": "ok",
  "checks": {
    "opensearch": {"status": "ok"},
    "qdrant": {"status": "ok"},
    "postgres": {"status": "ok"}
  }
}
```

---

## 3. Using the Platform

### 3.1 Web Interface

1. Open browser, go to: **http://localhost:8000/ui/**
2. Type your search query in the search box
3. Press Enter or click Search button
4. View results

### 3.2 API (Swagger UI)

1. Open browser, go to: **http://localhost:8000/docs**
2. Click on the endpoint you want to test
3. Click "Try it out"
4. Enter parameters and click "Execute"

### 3.3 Command Line (cURL)

#### Search

```bash
# Basic search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "resort gần biển"}'

# Search with filters
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "khách sạn ở Đà Nẵng",
    "top_k": 5,
    "filters": {
      "city": "Đà Nẵng",
      "price_max": 3000000
    }
  }'
```

#### Get Context

```bash
curl -X POST http://localhost:8000/context \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 542,
    "query": "resort gần biển"
  }'
```

---

## 4. Search Features

### 4.1 Natural Language Query

Hệ thống hiểu câu hỏi tiếng Việt tự nhiên:

| Query Type | Example |
|---|---|
| Địa điểm | "Khách sạn ở Đà Nẵng" |
| Tiện nghi | "Resort có bể bơi và spa" |
| Phong cách | "Chỗ yên tĩnh để nghỉ dưỡng" |
| Đối tượng | "Phù hợp cho gia đình có trẻ nhỏ" |
| Giá cả | "Khách sạn giá rẻ gần sân bay" |
| Kết hợp | "Resort sang trọng ở Phú Quốc cho tuần trăng mật" |

### 4.2 Filters

Sử dụng bộ lọc để thu hẹp kết quả:

- **City:** Lọc theo thành phố
- **Star Rating:** Lọc theo số sao (1-5)
- **Price:** Lọc theo khoảng giá
- **Amenities:** Lọc theo tiện nghi

### 4.3 No Diacritics Support

Có thể gõ câu hỏi không dấu:

```
"khach san gan bien" → "khách sạn gần biển"
"resort yen tinh" → "resort yên tĩnh"
```

---

## 5. Understanding Results

### 5.1 Result Card

Mỗi kết quả hiển thị:

- **Tên khách sạn**
- **Đánh giá:** Số sao + điểm review
- **Giá:** Giá phòng từ (VND/đêm)
- **Tiện nghi:** Các tiện nghi nổi bật
- **Mô tả:** Tóm tắt ngắn
- **Xếp hạng:** Điểm relevance (0-1)

### 5.2 Explainable Results

Hệ thống giải thích tại sao khách sạn được chọn:

- **Concept khớp:** Tiện nghi/phong cách nào match với query
- **Điểm review:** Khách sạn được đánh giá cao
- **Giá phù hợp:** Trong tầm giá của bạn
- **Vị trí:** Gần địa điểm bạn muốn

---

## 6. Example Queries

### 6.1 Family Vacation

```
Query: "Resort có khu vui chơi trẻ em ở Nha Trang"
Kết quả: Các resort có Kids Club, bể bơi trẻ em, activities
```

### 6.2 Business Trip

```
Query: "Khách sạn trung tâm thành phố có phòng họp"
Kết quả: Các khách sạn có meeting room, WiFi, near city center
```

### 6.3 Romantic Getaway

```
Query: "Biệt thự riêng tư có hồ bơi cho tuần trăng mật"
Kết quả: Các villa private pool, romantic style, quiet
```

---

## 7. Monitoring & Dashboards

### 7.1 Access Dashboards

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | Anonymous Admin |
| Prometheus | http://localhost:9090 | None |
| OpenSearch Dashboard | http://localhost:5601 | None |

### 7.2 View Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics to watch
- da10_http_request_duration_seconds (latency)
- da10_search_degraded_total (degraded mode)
- da10_rerank_method_total (rerank distribution)
- da10_dependency_up (service health)
```

---

## 8. Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_fusion_ranking.py -v

# Run golden evaluation
curl "http://localhost:8000/eval/golden?limit=10"
```

---

## 9. Tips for Better Results

### 9.1 Be Specific

| Less Effective | More Effective |
|---|---|
| "Khách sạn" | "Resort 5 sao ở Phú Quốc" |
| "Tốt" | "Đánh giá trên 8 điểm" |
| "Rẻ" | "Dưới 2 triệu một đêm" |

### 9.2 Use Natural Language

```
✅ "Tìm chỗ chill chill yên tĩnh gần biển cho 2 người"
✅ "Cần khách sạn có spa và hồ bơi, giá dưới 3 triệu"
❌ "hotel beach pool cheap"
```

### 9.3 Combine Criteria

```
"Resort có bãi biển riêng ở Đà Nẵng, phù hợp gia đình, giá dưới 5 triệu"
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Solution |
|---|---|
| Port already in use | Change port: `--port 8001` |
| Docker not starting | Restart Docker Desktop |
| Module not found | Activate virtual environment |
| Connection refused | Check if services are running: `docker compose ps` |

### 10.2 Check Logs

```bash
# API logs
docker compose logs api

# OpenSearch logs
docker compose logs opensearch

# Qdrant logs
docker compose logs qdrant
```

### 10.3 Reset Everything

```bash
# Stop all services
docker compose down

# Remove volumes (fresh start)
docker compose down -v

# Rebuild
docker compose up -d --build
```

---

## 11. FAQ

**Q: Hệ thống hỗ trợ ngôn ngữ nào?**
A: Tiếng Việt (có dấu và không dấu).

**Q: Kết quả có luôn giá không?**
A: Có, hiển thị giá phòng từ (VND/đêm).

**Q: Tại sao một số khách sạn không có giá?**
A: Một số khách sạn chưa có dữ liệu giá từ nguồn crawl.

**Q: Có thể tìm theo khu vực không?**
A: Có, sử dụng tên thành phố hoặc quận/huyện.

**Q: Làm sao để thêm dữ liệu mới?**
A: Chạy crawler: `python scripts/crawl_hotels.py`

---

## 12. API Quick Reference

### Health Check
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/deep
```

### Search
```bash
# POST (hybrid search)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your query here"}'

# GET (BM25 baseline)
curl "http://localhost:8000/search?q=your+query"
```

### Context
```bash
curl -X POST http://localhost:8000/context \
  -H "Content-Type: application/json" \
  -d '{"hotel_id": 542, "query": "your query"}'
```

### Metrics
```bash
curl http://localhost:8000/metrics
```

---

*Document version: 1.1 | Last updated: 30/06/2026*
