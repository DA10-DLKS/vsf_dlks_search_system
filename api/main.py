"""DA10 Platform Services API (Layer 8).

Exposes Search / Context / Knowledge APIs consumed by DA09.
TODO: register routers from api/routes/.
"""

import os
import time
from fastapi import FastAPI, Query
from opensearchpy import OpenSearch
from dotenv import load_dotenv
from prometheus_client import Histogram, Counter, generate_latest, CollectorRegistry

# Load environment variables
load_dotenv()

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
INDEX_NAME = os.environ.get('BM25_INDEX', 'travel_bm25')

# Initialize OpenSearch Client
client = OpenSearch(OPENSEARCH_URL)

# Prometheus metrics
REGISTRY = CollectorRegistry()
REQUEST_LATENCY = Histogram(
    'search_bm25_request_duration_seconds',
    'BM25 search request latency in seconds',
    ['endpoint'],
    registry=REGISTRY
)
REQUESTS_TOTAL = Counter(
    'search_bm25_requests_total',
    'Total BM25 search requests',
    ['endpoint'],
    registry=REGISTRY
)
ERRORS_TOTAL = Counter(
    'search_bm25_errors_total',
    'Total BM25 search errors',
    ['endpoint'],
    registry=REGISTRY
)

app = FastAPI(title="DA10 Knowledge & Retrieval Platform")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(REGISTRY)


@app.get("/search")
def search_bm25(q: str = Query(..., description="Search query")) -> dict:
    """
    BM25 search endpoint (Sprint 1 baseline).
    Tracks latency and error counts via Prometheus.
    """
    start_time = time.time()
    endpoint = "/search"
    REQUESTS_TOTAL.labels(endpoint=endpoint).inc()

    try:
        query_body = {
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": ["name^2", "description", "city", "address", "amenities"]
                }
            }
        }
        
        response = client.search(
            index=INDEX_NAME,
            body=query_body
        )
        
        hits = response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append({
                "id": source.get("id"),
                "name": source.get("name"),
                "accommodation_type": source.get("accommodation_type"),
                "star_rating": source.get("star_rating"),
                "review_score": source.get("review_score"),
                "address": source.get("address"),
                "city": source.get("city"),
                "description": source.get("description"),
                "score": hit.get("_score")
            })
            
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

        return {
            "query": q,
            "results": results,
            "took_ms": int(latency * 1000),
            "total_hits": response.get("hits", {}).get("total", {}).get("value", 0)
        }
    except Exception as e:
        ERRORS_TOTAL.labels(endpoint=endpoint).inc()
        raise


# TODO:
# from api.routes import search_api, context_api, knowledge_api
# app.include_router(search_api.router)
# app.include_router(context_api.router)
# app.include_router(knowledge_api.router)
