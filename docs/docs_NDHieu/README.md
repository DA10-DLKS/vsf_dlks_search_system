# Tài Liệu Bàn Giao - Nguyễn Duy Hiếu

Thư mục này tổng hợp tài liệu bàn giao phần việc của **Nguyễn Duy Hiếu** trong dự án **DA10 OTA AI Search Platform**.

Phạm vi chính của Hiếu:

- Frontend Demo Tool / DA10 Display Layer.
- Giao diện Search/RAG demo.
- Explainable Retrieval Console.
- Hiển thị Search API, Hybrid Retrieval, Context API và Evaluation output.
- Tài liệu kiến trúc, task tracking, mentor review và handover cho phần frontend.

Hiếu **không sở hữu** các phần:

- Data cleaning.
- Ontology backend.
- Embedding.
- BM25/OpenSearch backend.
- Vector/Qdrant backend.
- Hybrid retrieval algorithm.
- Ranking/reranking algorithm.
- Evaluation metric calculation.
- DA09 chatbot/copilot response generation.

## 1. Nên Đọc Theo Thứ Tự Nào

Người mới tiếp quản hoặc reviewer nên đọc theo thứ tự sau:

1. `PROJECT_MASTER_CONTEXT.md`  
   Bối cảnh tổng thể dự án, mục tiêu, MVP, kiến trúc và trạng thái hiện tại.

2. `HIEU_CURRENT_STATUS.md`  
   Trạng thái hiện tại phần frontend của Nguyễn Duy Hiếu.

3. `HIEU_FRONTEND_ARCHITECTURE.md`  
   Kiến trúc frontend, phạm vi trách nhiệm và vị trí của frontend trong DA09/DA10.

4. `HIEU_TASK_BOARD.md`  
   Bảng tracking công việc cá nhân theo sprint/task/deliverable.

5. `FRONTEND_MENTOR_PRESENTATION.md`  
   Tài liệu dùng để trình bày phần frontend với mentor.

6. `NGUYEN_DUY_HIEU_CONTRIBUTION_REPORT.md`  
   Báo cáo tổng hợp đóng góp của Nguyễn Duy Hiếu trong dự án.

7. `BACKEND_API_ISSUES_FOR_FRONTEND.md`  
   Các vấn đề backend/API ảnh hưởng đến frontend.

8. `QUERY_FLOW_DIAGRAM_PREVIEW.md`  
   Sơ đồ giải thích luồng query, retrieval, context và latency.

## 2. Nhóm Tài Liệu Theo Mục Đích

### 2.1. Tài Liệu Tổng Quan Dự Án

| File | Mục đích |
| ---- | -------- |
| `PROJECT_MASTER_CONTEXT.md` | Bối cảnh tổng thể dự án, mục tiêu, MVP và kiến trúc cấp cao. |
| `PROJECT_STATE.md` | Snapshot trạng thái dự án tại thời điểm tạo tài liệu. |
| `PROJECT_STATE_SNAPSHOT.md` | Phân loại completed/partial/blocked theo module. |
| `REPOSITORY_MAP.md` | Bản đồ thư mục, entry points và file quan trọng. |
| `TECHNICAL_ONBOARDING.md` | Tài liệu onboarding kỹ thuật cho người mới. |
| `QUICKSTART.md` | Hướng dẫn chạy dự án và các command cơ bản. |
| `REPOSITORY_REVIEW.md` | Báo cáo review repository chi tiết. |

### 2.2. Tài Liệu Kiến Trúc Frontend

| File | Mục đích |
| ---- | -------- |
| `HIEU_FRONTEND_ARCHITECTURE.md` | Kiến trúc hệ thống frontend của Hiếu. |
| `architecture.md` | Ghi chú kiến trúc ban đầu. |
| `DECISIONS.md` | Các quyết định kỹ thuật đã ghi nhận. |
| `API_SCHEMA_IMPACT_HIEU.md` | Phân tích tác động API schema của Kiên lên frontend. |
| `QUERY_FLOW_DIAGRAM_PREVIEW.md` | Sơ đồ query flow và timing để đưa vào UI/demo. |

### 2.3. Tài Liệu Frontend Demo / Explainability

| File | Mục đích |
| ---- | -------- |
| `DESIGN_RECOMMENDATION.md` | Đề xuất thiết kế Explainable Retrieval Console. |
| `EXPLAINABILITY_SIGNAL_INVENTORY.md` | Danh sách tín hiệu explainability tìm thấy từ repo/code. |
| `EXPLAINABILITY_UI_SPEC.md` | Đặc tả UI explainability chi tiết. |
| `UI_WIREFRAME_EXPLAINABILITY.md` | Wireframe và layout đề xuất cho giao diện explainability. |
| `FRONTEND_MENTOR_PRESENTATION.md` | Báo cáo trình bày frontend cho mentor. |
| `BACKEND_API_ISSUES_FOR_FRONTEND.md` | Danh sách lỗi/thiếu hụt backend ảnh hưởng trực tiếp tới UI. |

### 2.4. Tài Liệu Quản Lý Công Việc Cá Nhân

| File | Mục đích |
| ---- | -------- |
| `HIEU_TASK_BOARD.md` | Bảng quản lý task cá nhân theo sprint, deliverable và scope changes. |
| `HIEU_CURRENT_STATUS.md` | Trạng thái hiện tại phần frontend của Hiếu. |
| `NGUYEN_DUY_HIEU_CONTRIBUTION_REPORT.md` | Báo cáo tổng hợp đóng góp cá nhân. |
| `AI_REVIEW_BRIEF.md` | Tóm tắt ngắn cho mentor hoặc AI reviewer. |

### 2.5. Tài Liệu Team / Dependency

| File | Mục đích |
| ---- | -------- |
| `TEAM_DEPENDENCY_MAP.md` | Bản đồ dependency giữa các thành viên và module. |
| `TEAM_OWNERSHIP.md` | Ownership được suy ra từ tài liệu/repo. |

### 2.6. Tài Liệu Hình Ảnh Kiến Trúc

| File | Mục đích |
| ---- | -------- |
| `enterprise_AI_travel_platfom.png` | Hình kiến trúc Enterprise AI Travel Platform. |
| `DA10_Enterprise.png` | Hình kiến trúc DA10 Enterprise/Knowledge Platform. |
| `DA09_Travel_AI.png` | Hình kiến trúc DA09 Travel AI/Copilot layer. |

## 3. File Nên Đưa Vào Repo Khi Bàn Giao

Nên đưa các file sau vào repo vì có giá trị bàn giao rõ ràng:

```text
docs/docs_NDHieu/README.md
docs/docs_NDHieu/PROJECT_MASTER_CONTEXT.md
docs/docs_NDHieu/HIEU_CURRENT_STATUS.md
docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md
docs/docs_NDHieu/HIEU_TASK_BOARD.md
docs/docs_NDHieu/FRONTEND_MENTOR_PRESENTATION.md
docs/docs_NDHieu/NGUYEN_DUY_HIEU_CONTRIBUTION_REPORT.md
docs/docs_NDHieu/BACKEND_API_ISSUES_FOR_FRONTEND.md
docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md
docs/docs_NDHieu/QUERY_FLOW_DIAGRAM_PREVIEW.md
docs/docs_NDHieu/TEAM_DEPENDENCY_MAP.md
docs/docs_NDHieu/TECHNICAL_ONBOARDING.md
docs/docs_NDHieu/REPOSITORY_MAP.md
```

Các file explainability chi tiết cũng nên đưa lên nếu mục tiêu là bàn giao đầy đủ thiết kế UI:

```text
docs/docs_NDHieu/DESIGN_RECOMMENDATION.md
docs/docs_NDHieu/EXPLAINABILITY_SIGNAL_INVENTORY.md
docs/docs_NDHieu/EXPLAINABILITY_UI_SPEC.md
docs/docs_NDHieu/UI_WIREFRAME_EXPLAINABILITY.md
```

## 4. File Cần Kiểm Tra Trước Khi Đăng Lên Repo

Trước khi đăng lên repo, nên kiểm tra lại:

- Có thông tin nhạy cảm không.
- Có nội dung tạm thời hoặc nhận xét nội bộ không nên public không.
- Có file nào trùng nội dung hoặc đã lỗi thời không.
- Có file ảnh quá lớn không cần thiết không.

Các file ảnh trong thư mục này có dung lượng lớn hơn file Markdown, nên chỉ giữ nếu cần minh họa kiến trúc:

```text
enterprise_AI_travel_platfom.png
DA10_Enterprise.png
DA09_Travel_AI.png
```

## 5. Current Frontend Deliverables Liên Quan

Các file frontend chính tương ứng với tài liệu này:

```text
frontend/explainable_retrieval_console.html
frontend/search_ui.html
frontend/search_ui_v2.html
frontend/evaluation_dashboard.html
frontend/streamlit_explainable_console.py
frontend/mock_api_responses.json
frontend/mock_api_responses_v2.json
frontend/mock_evaluation_results.json
```

Trong đó file quan trọng nhất để demo hiện tại là:

```text
frontend/explainable_retrieval_console.html
```

File này thể hiện:

- Query Understanding.
- Ontology tags.
- BM25 baseline.
- Hybrid retrieval.
- Ranking explanation.
- Context package.
- Citation/evidence.
- Latency trace.
- Golden dataset evaluation.
- Sơ đồ luồng dữ liệu có timing.

## 6. Ghi Chú Bàn Giao

Khi bàn giao cho người mới, cần nhấn mạnh:

- Frontend của Hiếu là Display Layer, không phải backend retrieval engine.
- Các metric evaluation do backend/evaluation team tính toán, frontend chỉ hiển thị.
- Nếu backend chưa expose field, frontend phải ghi rõ `TODO`, `fallback` hoặc `backend chưa trả field`.
- Không được tự coi mock/fallback là dữ liệu chính thức từ backend.
- Khi API contract thay đổi, cần cập nhật đồng thời:
  - `frontend/explainable_retrieval_console.html`
  - `frontend/src/api/api_client.js`
  - `frontend/src/types/searchTypes.js`
  - mock data nếu còn dùng
  - tài liệu kiến trúc liên quan

## 7. Trạng Thái Git Cần Lưu Ý

Một số file trong thư mục `docs/docs_NDHieu` có thể đang ở trạng thái untracked tại local. Trước khi push, nên kiểm tra bằng:

```bash
git status --short docs/docs_NDHieu
```

Nếu muốn add toàn bộ tài liệu bàn giao của Hiếu:

```bash
git add docs/docs_NDHieu
```

Nếu chỉ muốn add nhóm tài liệu cần thiết, nên add từng file theo danh sách ở mục 3.

## 8. Tóm Tắt Một Câu

Thư mục `docs/docs_NDHieu` là bộ tài liệu bàn giao phần việc của Nguyễn Duy Hiếu, bao gồm kiến trúc frontend, trạng thái triển khai, task board, tài liệu mentor review, dependency với backend/API và các đề xuất explainability UI cho DA10 OTA AI Search Platform.
