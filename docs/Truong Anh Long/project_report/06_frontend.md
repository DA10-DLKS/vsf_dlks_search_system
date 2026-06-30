# Báo cáo 06 — Frontend

Frontend trình diễn toàn bộ luồng AI Search / RAG, làm rõ tính **giải thích được (explainable)**: từ câu hỏi → top-K kết quả → metadata → citation → source documents → context chunks → LLM. Có hai dạng giao diện: **HTML standalone** (mở trực tiếp, không build) và **module React** (sẵn sàng ghép vào Vite).

---

## 1. Luồng trình diễn (RAG traceability)

```
User Query → Top-K Results → Metadata → Citation → Source Documents → Context Chunks → LLM Consumption
```

Mục tiêu UX: người xem **thấy được vì sao** một khách sạn được chọn (concept khớp, điểm review, citation về chunk thật), không phải hộp đen.

---

## 2. Hai dạng giao diện

### 2.1 HTML standalone (review nhanh, không build)

| File | Vai trò |
|---|---|
| `frontend/search_ui.html`, `search_ui_v2.html` | giao diện tìm kiếm chính (mock data nhúng sẵn) |
| `frontend/index.html` | trang chủ / điều hướng |
| `frontend/explainable_retrieval_console.html` | **console giải thích retrieval** — soi intent, candidate, fusion, rerank theo từng node |
| `frontend/evaluation_dashboard.html` | dashboard kết quả đánh giá golden |
| `frontend/streamlit_explainable_console.py` | bản Streamlit của console giải thích |

Mở trực tiếp trong trình duyệt, không cần build. Dữ liệu mock: `mock_api_responses.json` / `_v2.json`, `mock_evaluation_results.json`.

### 2.2 React module (`frontend/src/`)

Các component tái sử dụng, sẵn sàng đưa vào Vite app (`Dashboard.jsx` là entry kỳ vọng):

| Component | Hiển thị |
|---|---|
| `SearchInterface.jsx` | ô nhập, submit, các trạng thái loading/error/empty |
| `ResultList.jsx` | danh sách kết quả đã xếp hạng |
| `ResultCard.jsx` | tiêu đề, snippet, score, metadata, citation, source, context |
| `MetadataCard.jsx` | vị trí, loại, tiện ích, điểm, thông tin ranking |
| `CitationList.jsx` | citation (xử lý thiếu citation) |
| `ContextPreview.jsx` | context chunks (xử lý thiếu context) |
| `LoadingState / ErrorState / EmptyState` | trạng thái tái dùng |
| `Dashboard.jsx` | tổng quan demo, mục tiêu metric, luồng RAG |
| `EvaluationDashboard.jsx` | dashboard đánh giá |

---

## 3. Kết nối API

### 3.1 Mock vs Real (`src/config/config.js`)

`api_client.js` đọc `USE_MOCK_API`:
- `true` → trả từ `mock_api_responses.json` (review không cần backend).
- `false` → gọi backend thật:
  - `POST {API_BASE_URL}/search`
  - `POST {API_BASE_URL}/context`

```js
export const config = {
  API_BASE_URL: "http://localhost:8000",
  USE_MOCK_API: false,
  SEARCH_ENDPOINT: "/search",
  CONTEXT_ENDPOINT: "/context"
};
```

### 3.2 Hợp đồng với backend (`api/main.py` + `api/frontend_adapter.py`)

| Endpoint | Request | Response |
|---|---|---|
| `POST /search` | `{query, filters?}` | `{query, results[], total}` |
| `POST /context` | `{result_id="hotel_<id>", query?}` | `{result_id, llm_context, citations, ...}` |

- `/search` chạy hybrid retrieval (Node 1→8) nhưng **KHÔNG sinh LLM answer** (cho nhanh).
- `/context` gọi Node 9 sinh `llm_context` từ chính hotel được chọn (không search lại) — `query` tùy chọn để answer bám đúng nhu cầu user (V6).
- `frontend_adapter.py` dịch shape pipeline → shape frontend (`searchTypes.js`).

Backend cũng mount frontend tĩnh tại `/ui` (`StaticFiles`), và bật **CORS `*`** để file://localhost gọi được API. Frontend đề xuất ở [api/main.py](api/main.py) qua `app.mount("/ui", ...)`.

---

## 4. Xử lý trạng thái & độ bền UX

Giao diện không bao giờ "vỡ trắng":
- **Empty state**: query không có kết quả → thông báo rõ (gõ query không có trong mock để xem).
- **Error state**: API lỗi → ErrorState (gõ query chứa `error` để demo).
- **Loading state**: UI tải tái dùng.
- **Fallback citation/context**: thiếu citation hoặc context → hiện thông báo thay vì hỏng.

Backend cũng đỡ về phía dữ liệu: pipeline chống màn hình trắng (candidate rỗng → fallback), nên frontend hiếm khi rơi vào empty thật.

---

## 5. Demo & test

- **3 câu demo chuẩn**:
  1. `Tôi muốn resort yên tĩnh gần biển cho gia đình`
  2. `Khách sạn phù hợp cho chuyến công tác ở trung tâm`
  3. `Địa điểm nghỉ dưỡng có tiện ích cho trẻ em`
- **E2E test**: `frontend/tests/e2e_test.js`.
- **Tài liệu thiết kế**: `frontend_design.md`, `dashboard_design.md`, `DESIGN-airbnb.md`, `demo_scenarios.md`, `ux_report.md`.

---

## 6. Điểm nhấn: Explainable Retrieval Console

`explainable_retrieval_console.html` (+ bản Streamlit) là công cụ debug/demo quan trọng nhất: nó hiển thị **từng bước của pipeline** — intent đã parse, concept khớp, candidate, RRF/fusion, phương thức rerank thực tế (`rerank_method`: cross-encoder vs density-fallback), business score breakdown. Đây là cầu nối trực quan để giải thích "vì sao xếp hạng như vậy", khớp với triết lý explainable của hệ thống.

> Trạng thái git hiện tại đang chỉnh `frontend/explainable_retrieval_console.html` và `api/main.py` (nhánh `feat/observability-monitoring`).
