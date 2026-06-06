# Bảng Quản Lý Công Việc - Nguyễn Duy Hiếu

Người phụ trách: Nguyễn Duy Hiếu
Vai trò: Frontend Demo Tool
Phạm vi: Frontend demo cho DA10 - OTA AI Search Platform

Mục tiêu frontend:

```text
User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption
```

File này là **nguồn theo dõi chính** cho công việc frontend của Nguyễn Duy Hiếu.

## Quy Tắc Quản Lý

- Mỗi task mới phải có một ID duy nhất.
- Không xóa task cũ.
- Task không còn phù hợp thì đánh dấu `CANCELLED`.
- Task mới có thể thêm vào `Task Registry` mà không cần đổi cấu trúc board.
- Không chỉ track file; phải track mục đích, deliverable và giá trị nghiệp vụ.

Status values:

- TODO
- IN_PROGRESS
- DONE
- BLOCKED
- CANCELLED

## Sprint Progress Estimation

| Sprint | Planned Tasks | Completed Tasks | Partial Tasks | Estimated Completion % |
| ------ | ------------- | --------------- | ------------- | ---------------------- |
| Sprint 1 | 8 | 7 | 1 | 94% |
| Sprint 2 | 8 | 0 | 6 | 38% |
| Sprint 3 | 6 | 0 | 4 | 33% |
| Total Frontend Roadmap | 22 | 7 | 11 | 57% |

Cách tính:

- DONE = 1.0 điểm.
- IN_PROGRESS/partial artifact = 0.5 điểm.
- TODO/BLOCKED/CANCELLED = 0 điểm.
- Total frontend roadmap = `(7 DONE + 11 partial * 0.5) / 22 = 56.8%`, làm tròn thành 57%.

## Task Registry

| ID | Task | Sprint | Status | Owner | Added Date | Completed Date | Purpose | Deliverables |
| -- | ---- | ------ | ------ | ----- | ---------- | -------------- | ------- | ------------ |
| HIEU-S1-001 | Thiết kế kiến trúc frontend | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Xác định cách frontend demo được tổ chức, tích hợp API và hiển thị RAG flow. | `frontend/frontend_design.md` |
| HIEU-S1-002 | Thiết kế search UI | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Tạo trải nghiệm tìm kiếm để mentor thấy query, kết quả và traceability. | `frontend/search_ui.html` |
| HIEU-S1-003 | Thiết kế dashboard | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Mô tả layout dashboard và cách dashboard chứng minh Search/RAG flow. | `frontend/dashboard_design.md`, `frontend/src/dashboard/Dashboard.jsx` |
| HIEU-S1-004 | Tạo mock API responses | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Mô phỏng Search API và Context API trước khi backend sẵn sàng. | `frontend/mock_api_responses.json` |
| HIEU-S1-005 | Tạo demo scenarios | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Xác định các tình huống demo OTA để kiểm thử UI và trình bày với mentor. | `frontend/demo_scenarios.md` |
| HIEU-S1-006 | Chuẩn bị mentor Q&A | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Chuẩn bị câu trả lời cho mentor về scope, mock data, RAG traceability và hạn chế. | `MENTOR_QA.md` |
| HIEU-S1-007 | Giải thích mock data | Sprint 1 | DONE | Nguyễn Duy Hiếu | 2026-06-03 | 2026-06-03 | Giúp mentor hiểu vì sao result được chọn, score đến từ đâu và document/chunk nào hỗ trợ. | `MOCK_DATA_EXPLAINED.md` |
| HIEU-S1-008 | Review Sprint 1 và nhận feedback mentor | Sprint 1 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Xác nhận demo có đủ thuyết phục trước khi chuyển sang Sprint 2. | Feedback notes trong `frontend/ux_report.md` |
| HIEU-S2-001 | Xây Search Interface | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Cho phép người dùng nhập query, submit, xem loading/error/empty/results. | `frontend/src/components/SearchInterface.jsx` |
| HIEU-S2-002 | Xây API Client | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Tách logic gọi Search API/Context API khỏi UI để dễ đổi mock sang backend thật. | `frontend/src/api/api_client.js` |
| HIEU-S2-003 | Xây Result Components | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Hiển thị Top-K results theo cấu trúc có thể tái sử dụng. | `ResultList.jsx`, `ResultCard.jsx` |
| HIEU-S2-004 | Xây Metadata/Citation/Context Components | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Làm rõ traceability của kết quả RAG: metadata, citation, source, context. | `MetadataCard.jsx`, `CitationList.jsx`, `ContextPreview.jsx` |
| HIEU-S2-005 | Xây config layer mock/real API | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Cho phép chuyển giữa mock API và backend thật mà không sửa component. | `frontend/src/config/config.js` |
| HIEU-S2-006 | Xây UI state components | Sprint 2 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Đảm bảo demo không bị trống hoặc vỡ UI khi loading, lỗi API hoặc không có kết quả. | `LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx` |
| HIEU-S2-007 | Quyết định setup React/Vite runtime | Sprint 2 | TODO | Nguyễn Duy Hiếu + Team | 2026-06-03 |  | Quyết định có biến React-ready components thành app chạy được trong Sprint 2 không. | Team decision, possible `package.json`/Vite setup |
| HIEU-S2-008 | Smoke test tích hợp React components | Sprint 2 | TODO | Nguyễn Duy Hiếu | 2026-06-03 |  | Xác nhận components hoạt động cùng nhau trong runtime thật. | Smoke test notes hoặc test result |
| HIEU-S3-001 | Hoàn thiện Final Dashboard | Sprint 3 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Tạo màn hình demo cuối để trình bày flow, metric target và kết quả Search/RAG. | `Dashboard.jsx`, final dashboard integration |
| HIEU-S3-002 | E2E Testing | Sprint 3 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Kiểm tra flow query -> result -> metadata -> citation -> context. | `frontend/tests/e2e_test.js` |
| HIEU-S3-003 | UX Optimization | Sprint 3 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Cải thiện khả năng đọc, demo usability và responsive behavior. | `frontend/ux_report.md` |
| HIEU-S3-004 | Tích hợp backend thật | Sprint 3 | TODO | Nguyễn Duy Hiếu + Backend/API owner | 2026-06-03 |  | Chuyển demo từ mock data sang Search API và Context API thật. | Verified real API mode |
| HIEU-S3-005 | Review responsive cho mentor demo | Sprint 3 | IN_PROGRESS | Nguyễn Duy Hiếu | 2026-06-03 |  | Đảm bảo demo hiển thị tốt trên laptop/màn chiếu. | Visual review notes trong `ux_report.md` |
| HIEU-S3-006 | Chuẩn bị final demo | Sprint 3 | TODO | Nguyễn Duy Hiếu | 2026-06-03 |  | Chuẩn bị kịch bản trình bày cuối và checklist demo. | Final demo script/checklist |

## Deliverables Mapping

| Deliverable | Purpose | Related Files | Sprint | Status |
| ----------- | ------- | ------------- | ------ | ------ |
| Frontend architecture design | Định nghĩa kiến trúc, folder structure, API flow và RAG display flow. | `frontend/frontend_design.md` | Sprint 1 | DONE |
| Standalone Search/RAG demo | Demonstrate Search/RAG flow without backend or build setup. | `frontend/search_ui.html` | Sprint 1 | DONE |
| Dashboard design | Mô tả layout dashboard, widget, traceability và metric/demo indicators. | `frontend/dashboard_design.md` | Sprint 1 | DONE |
| Mock Search/Context API data | Simulate Search API and Context API before backend exists. | `frontend/mock_api_responses.json` | Sprint 1 | DONE |
| Demo scenarios | Định nghĩa 3 query demo và expected UI behavior. | `frontend/demo_scenarios.md` | Sprint 1 | DONE |
| Mentor Q&A | Prepare for mentor review and common technical/product questions. | `MENTOR_QA.md` | Sprint 1 | DONE |
| Mock data explanation | Explain ranking, scores, metadata, citations, documents and chunks. | `MOCK_DATA_EXPLAINED.md` | Sprint 1 | DONE |
| API client abstraction | Support mock mode and future real backend mode. | `frontend/src/api/api_client.js`, `frontend/src/config/config.js` | Sprint 2 | IN_PROGRESS |
| React component set | Prepare reusable UI components for future React/Vite app. | `frontend/src/components/*.jsx`, `frontend/src/dashboard/Dashboard.jsx` | Sprint 2 | IN_PROGRESS |
| UI state handling | Handle loading, error, empty and missing citation/context states. | `LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx`, `search_ui.html` | Sprint 2 | IN_PROGRESS |
| E2E checklist | Document expected end-to-end behavior before automated tests exist. | `frontend/tests/e2e_test.js` | Sprint 3 | IN_PROGRESS |
| UX report | Track demo usability, limitations and mentor feedback. | `frontend/ux_report.md` | Sprint 3 | IN_PROGRESS |

## Daily Accomplishments

### 2026-06-03

| Completed Item | Why It Matters | Related Sprint |
| -------------- | -------------- | -------------- |
| `frontend/search_ui.html` completed | Allows standalone demo without backend or React/Vite setup. | Sprint 1 |
| `frontend/mock_api_responses.json` completed | Provides stable mock Search API and Context API data. | Sprint 1 |
| `frontend/frontend_design.md` completed | Gives architecture context for mentor and future development. | Sprint 1 |
| `frontend/dashboard_design.md` completed | Defines how dashboard should communicate Search/RAG traceability. | Sprint 1 |
| `frontend/demo_scenarios.md` completed | Gives clear demo cases and expected UI behavior. | Sprint 1 |
| `MENTOR_QA.md` completed | Prepares answers for mentor review questions. | Sprint 1 |
| `MOCK_DATA_EXPLAINED.md` completed | Explains ranking, hardcoded scores, documents and chunks. | Sprint 1 |
| React-ready components created | Reduces Sprint 2 implementation effort even though runtime is not set up yet. | Sprint 2 |
| `frontend/tests/e2e_test.js` checklist created | Defines what must be verified later with automated tests. | Sprint 3 |
| `frontend/ux_report.md` created | Provides a place to record UX feedback and next iteration notes. | Sprint 3 |

## New Requests / Scope Changes

| Date | Request | Source | Impact | Status |
| ---- | ------- | ------ | ------ | ------ |
| 2026-06-03 | Add definition of done, citation/context UI, demo scenarios and clearer folder structure. | Peer review/user request | Expanded Sprint 1 scope from file list to implementation-quality plan. | DONE |
| 2026-06-03 | Add `ContextPreview.jsx`, type/schema, UI states and README run guide. | Peer review/user request | Added clearer Sprint 2 frontend architecture expectations. | DONE |
| 2026-06-03 | Add config layer, state components, API client requirements and type shapes. | User request | Added mock/real API switch and stable frontend data shape. | DONE |
| 2026-06-03 | Add `ux_report.md` and `dashboard_design.md`. | User request | Added Sprint 3 UX tracking and dashboard design deliverable. | DONE |
| 2026-06-03 | Implement approved frontend plan. | User request | Created standalone demo, mock data, docs and React-ready modules. | DONE |
| 2026-06-03 | Generate project memory files and ignore them. | User request | Added state/architecture/decision/review memory, then added to `.gitignore`. | DONE |
| 2026-06-03 | Review `search_ui.html` for mentor readiness. | User request | Added Top-K heading, context expand/collapse and verified states. | DONE |
| 2026-06-03 | Create mentor Q&A and mock data explanation. | User request | Improved mentor review readiness. | DONE |
| 2026-06-03 | Create and refactor personal task board. | User request | Converted tracking into project-management board with registry and roadmap. | DONE |

## Personal Roadmap

Tối đa 10 item, chỉ gồm việc đã xong, việc tiếp theo và việc đang bị chặn.

| Type | Item | Status |
| ---- | ---- | ------ |
| Completed | Standalone Search/RAG HTML demo is ready for functional mentor review. | DONE |
| Completed | Mock API data and demo scenarios are ready. | DONE |
| Completed | Mentor Q&A and mock data explanation are ready. | DONE |
| Completed | React-ready component foundation exists. | IN_PROGRESS |
| Next | Open `frontend/search_ui.html` on actual laptop/projector and do a visual review. | TODO |
| Next | Run 3 demo queries with mentor/team and collect feedback. | IN_PROGRESS |
| Next | Update `frontend/ux_report.md` with feedback and UX limitations. | TODO |
| Next | Confirm whether Sprint 2 should add React/Vite runtime. | TODO |
| Blocked | Align `api_client.js` with real `/search` and `/context` schemas. | BLOCKED by API contract |
| Blocked | Verify real backend integration. | BLOCKED by backend availability |

## Immediate Backlog

| Priority | Task | Sprint | Depends On | Estimate | Status |
| -------- | ---- | ------ | ---------- | -------- | ------ |
| High | Review Sprint 1 và nhận feedback mentor | Sprint 1 | Buổi review với mentor | 0.5 ngày | IN_PROGRESS |
| High | Quyết định setup React/Vite runtime | Sprint 2 | Quyết định của team | 0.5 ngày | TODO |
| High | Align API Client với backend contract | Sprint 2 | API contract chính thức | 1 ngày | IN_PROGRESS |
| High | Smoke test tích hợp React components | Sprint 2 | React app runtime setup | 1 ngày | TODO |
| High | Tích hợp backend thật | Sprint 3 | Backend availability, Search API, Context API | 1-2 ngày | TODO |
| High | Hoàn thiện Final Dashboard | Sprint 3 | Component Sprint 2, API integration | 1 ngày | IN_PROGRESS |
| High | Chuẩn bị final demo | Sprint 3 | Dashboard, E2E, UX review | 0.5-1 ngày | TODO |
| Medium | Review responsive cho mentor demo | Sprint 3 | Laptop/màn chiếu thật | 0.5 ngày | IN_PROGRESS |
| Medium | Cập nhật UX report sau feedback | Sprint 3 | Mentor feedback | 0.5 ngày | TODO |
| Medium | Kiểm tra drift giữa mock JSON và HTML | Sprint 1/2 | Không có | 0.5 ngày | TODO |

## This Week Focus

Những việc Nguyễn Duy Hiếu nên thực tế làm tiếp trong tuần này:

1. Mở `frontend/search_ui.html` trên laptop/màn chiếu thật để kiểm tra trực quan.
2. Chạy 3 demo query với mentor hoặc teammate.
3. Ghi feedback vào `frontend/ux_report.md`.
4. Hỏi team có cần thêm React/Vite trong Sprint 2 không.
5. Hỏi API/backend owner schema chính thức của `/search` và `/context`.
6. Soát lại `MENTOR_QA.md` và `MOCK_DATA_EXPLAINED.md` trước buổi review.

## Ready To Start

Các task không bị chặn bởi thành viên khác:

| Task | Sprint | Business Value |
| ---- | ------ | -------------- |
| Review trực quan `search_ui.html` trên laptop/màn chiếu | Sprint 1/3 | Giảm rủi ro demo bị vỡ layout khi trình bày. |
| Chạy 3 demo query với mentor/team | Sprint 1 | Xác nhận demo flow đủ rõ và đúng nhu cầu mentor. |
| Cập nhật `frontend/ux_report.md` sau feedback | Sprint 3 | Biến feedback thành action cụ thể cho iteration tiếp theo. |
| Kiểm tra drift giữa `search_ui.html` và `mock_api_responses.json` | Sprint 1/2 | Tránh demo HTML lệch với mock API source. |
| Chuẩn bị speaking notes cho final demo | Sprint 3 | Tăng chất lượng trình bày và giảm phụ thuộc vào ứng biến. |

## Waiting On Others

Các task đang bị chặn bởi API contract, backend availability hoặc quyết định của team:

| Blocker | Affects Tasks | Owner/Source Needed | Notes |
| ------- | ------------- | ------------------- | ----- |
| API contract | API Client, real API integration, response normalizer | API & Evaluation owner/backend team | Cần schema request/response cuối cùng cho `/search` và `/context`. |
| Backend availability | Real backend integration, config verification, E2E with real API | Backend/API owner | Cần backend chạy ổn định để test real mode. |
| Team decision on React/Vite | React runtime setup, component smoke test, final dashboard integration | Team/mentor | Repo hiện chưa có frontend build setup. |
| Final golden queries | Demo scenarios, mock data refinement, mentor demo script | Team/mentor | Hiện đã có 3 query demo, nhưng cần xác nhận có dùng làm golden queries chính thức không. |
| Mentor feedback | UX Optimization, final demo preparation | Mentor | Cần feedback sau khi xem standalone demo. |

## Current Management Summary

- Sprint 1 progress: 94%
- Sprint 2 progress: 38%
- Sprint 3 progress: 33%
- Total frontend roadmap progress: 57%
- Recommended next task: review trực quan `frontend/search_ui.html` trên laptop/màn chiếu thật và lấy feedback mentor.
- Highest risk item: API contract/backend chưa ổn định, ảnh hưởng trực tiếp tới `api_client.js` và real backend integration.
## Task Registry Addendum - 2026-06-05

Note: This addendum is temporary until the main Task Registry table is normalized.

| ID | Task | Sprint | Status | Owner | Added Date | Completed Date | Purpose | Deliverables |
| -- | ---- | ------ | ------ | ----- | ---------- | -------------- | ------- | ------------ |
| HIEU-S3-007 | Design Evaluation Dashboard Display Layer | Sprint 3 | IN_PROGRESS | Nguyen Duy Hieu | 2026-06-05 |  | Display Search API and Context API evaluation metrics produced by API/Evaluation team. Hieu displays; Kien calculates. | `frontend/evaluation_dashboard_design.md`, `frontend/mock_evaluation_results.json`, `frontend/evaluation_dashboard.html`, `frontend/src/dashboard/EvaluationDashboard.jsx` |

## Deliverables Mapping Addendum - 2026-06-05

| Deliverable | Purpose | Related Files | Sprint | Status |
| ----------- | ------- | ------------- | ------ | ------ |
| Evaluation Dashboard Display Layer | Display mock/demo evaluation metrics now and Kien-provided evaluation outputs later. | `frontend/evaluation_dashboard_design.md`, `frontend/mock_evaluation_results.json`, `frontend/evaluation_dashboard.html`, `frontend/src/dashboard/EvaluationDashboard.jsx` | Sprint 3 | IN_PROGRESS |

## New Requests / Scope Changes Addendum - 2026-06-05

| Date | Request | Source | Impact | Status |
| ---- | ------- | ------ | ------ | ------ |
| 2026-06-05 | Add Evaluation Dashboard Display Layer. | User request | Adds display-only evaluation metrics dashboard; Kien owns calculation, Hieu owns frontend display. | IN_PROGRESS |
