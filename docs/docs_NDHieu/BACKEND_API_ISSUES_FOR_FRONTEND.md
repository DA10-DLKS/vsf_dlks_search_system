# Backend/API Issues Blocking Frontend Real Data

Generated date: 2026-06-18

Owner of this document: Nguyen Duy Hieu frontend/display layer.

Scope: This file records backend/runtime issues discovered while testing the frontend Explainable Retrieval Console. Hieu should not fix these backend issues dza
POST http://localhost:9200/travel_bm25/_search [status:N/A]
urllib3.exceptions.NewConnectionError:
HTTPConnection(host='localhost', port=9200): Failed to establish a new connection: [Errno 111] Connection refused
```

Observed frontend/API result:

```powershell
curl.exe --max-time 20 "http://127.0.0.1:8000/search?q=khach%20san"
```

Response:

```json
{"detail":"Keyword search backend unavailable"}
```

Why this blocks frontend:

- The frontend can call `GET /search`.
- The API route exists.
- But the API route fails before returning hotel results because the API container cannot connect to OpenSearch.

Likely backend/Docker cause:

- Inside Docker, `localhost` points to the API container itself, not the OpenSearch container.
- The API likely needs an internal Docker service URL such as `http://opensearch:9200`.

Hieu frontend action:

- Do not modify backend config.
- Keep UI showing the exact dependency failure.
- Wait for backend/API owner to fix container service URL or provide a working API base URL.

## Issue 3: Hybrid Search Route Exists But Fails Runtime Dependency

Test command:

```powershell
curl.exe --max-time 70 "http://127.0.0.1:8000/hybrid_search?q=khach%20san%20phu%20hop%20cho%20tre%20nho%20gan%20VinWonders%20Phu%20Quoc&top_n=10&answer=false"
```

Response:

```json
{"detail":"Hybrid search error: [Errno 111] Connection refused"}
```

API log:

```text
GET /hybrid_search?... HTTP/1.1" 500 Internal Server Error
UserWarning: Failed to obtain server version. Unable to check client-server compatibility.
```

Why this blocks frontend:

- Explainable Retrieval Console depends on `GET /hybrid_search` for:
  - query understanding
  - candidate count
  - BM25/vector/fusion/rerank trace
  - ranked hotels
  - matched chunks/context package
- The route exists but cannot complete because backend dependencies are unavailable or misconfigured.

## Issue 4: Qdrant Host Port Visibility Needs Backend Verification

Observed:

- Qdrant container log shows collection `vsf_travel` loads successfully.
- `docker compose ps` showed Qdrant running, but one check showed only `6333/tcp` instead of a host-published `0.0.0.0:6333->6333/tcp`.

Impact:

- If API expects Qdrant via host URL or internal Docker URL incorrectly, hybrid/vector retrieval may fail.

Needed backend verification:

- Confirm API container can reach Qdrant from inside Docker.
- Confirm API uses the correct Qdrant URL for Docker network.

## Issue 5: Context API Route Exists But Did Not Return Within Test Timeout

Frontend schema fix:

- OpenAPI says `POST /context` requires:

```json
{
  "result_id": "hotel_<id>",
  "query": "..."
}
```

- Frontend was updated to send `result_id` instead of `hotel_id`.

Test command:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/context' -Method Post -ContentType 'application/json' -Body '{"result_id":"hotel_test","query":"khach san"}'
```

Observed result:

```text
Request timed out after 25 seconds.
```

Impact:

- Frontend can now send the correct schema.
- Backend context generation/retrieval is still not usable for demo until it returns a response in a predictable time.

## Frontend Fixes Already Applied

File updated:

```text
frontend/explainable_retrieval_console.html
```

Changes:

- Added configurable API base URL.
- Added API health/OpenAPI check.
- Increased frontend request timeout from 12 seconds to 60 seconds.
- Improved error messages for:
  - wrong port/app
  - backend unreachable
  - dependency/index unavailable
  - route exists but runtime fails
- Fixed `POST /context` payload to use backend schema field:

```json
{
  "result_id": "hotel_<id>",
  "query": "..."
}
```

instead of sending only `hotel_id`.

## Commands Used For Verification

```powershell
docker compose ps
curl.exe --max-time 10 http://127.0.0.1:8000/health
curl.exe --max-time 10 http://127.0.0.1:8000/openapi.json
curl.exe --max-time 20 "http://127.0.0.1:8000/search?q=khach%20san"
curl.exe --max-time 70 "http://127.0.0.1:8000/hybrid_search?q=khach%20san%20phu%20hop%20cho%20tre%20nho%20gan%20VinWonders%20Phu%20Quoc&top_n=10&answer=false"
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/context' -Method Post -ContentType 'application/json' -Body '{"result_id":"hotel_test","query":"khach san"}'
docker compose logs --tail 120 api
```

## Current Frontend Status

Ready:

- The Explainable Retrieval Console can call the correct DA10 API base URL.
- It correctly detects whether the API is DA10 or another app.
- It displays backend dependency failures instead of silently failing.
- It is prepared to render `GET /hybrid_search`, `GET /search`, and `POST /context` once backend dependencies work.

Blocked by backend:

- Real hotel result list.
- Real ranking explanation.
- Real context package.
- Real citations/evidence.

## What Backend/API Owner Needs To Check

1. API container environment variables for OpenSearch URL.
2. API container environment variables for Qdrant URL.
3. Whether `travel_bm25` index exists inside OpenSearch.
4. Whether API can connect to OpenSearch from inside the Docker network.
5. Whether API can connect to Qdrant from inside the Docker network.
6. Whether `/hybrid_search` should fail fast with structured dependency error instead of generic `[Errno 111] Connection refused`.
