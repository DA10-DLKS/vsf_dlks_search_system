# Báo Cáo Tổng Hợp Đóng Góp Của Nguyễn Duy Hiếu Trong Dự Án DA10 OTA AI Search Platform

## 1. Vai Trò Và Phạm Vi Phụ Trách

Trong dự án DA10 OTA AI Search Platform, Nguyễn Duy Hiếu phụ trách mảng **Frontend Demo Tool / Display Layer**. Đây là lớp giao diện có nhiệm vụ trực quan hóa các kết quả từ hệ thống Search, Retrieval, RAG, Context và Evaluation để phục vụ quá trình demo, kiểm thử tích hợp, review kỹ thuật và trình bày với mentor hoặc cấp quản lý.

Phạm vi công việc chính bao gồm:

- Xây dựng giao diện demo tìm kiếm khách sạn.
- Hiển thị kết quả Search/Retrieval từ backend.
- Trực quan hóa metadata, ontology tags, ranking explanation, context chunks, citations và source documents.
- Kết nối frontend với các API thật như `GET /search`, `GET /hybrid_search`, `POST /context`, `GET /eval/golden`.
- Xây dựng giao diện explainability giúp người xem hiểu vì sao hệ thống trả ra một kết quả.
- Chuẩn bị tài liệu kiến trúc, tài liệu handover, tài liệu mentor review và task tracking cho phần frontend.

Vai trò này có ý nghĩa quan trọng vì frontend là lớp biến các kết quả kỹ thuật từ backend thành một sản phẩm có thể quan sát, trình bày và đánh giá được.

## 2. Các Hạng Mục Đã Hoàn Thành

### 2.1. Xây Dựng Frontend Demo Tool Ban Đầu

Nguyễn Duy Hiếu đã xây dựng bộ giao diện demo ban đầu cho luồng Search/RAG của hệ thống OTA AI Search Platform.

Các file liên quan:

```text
frontend/search_ui.html
frontend/search_ui_v2.html
frontend/mock_api_responses.json
frontend/mock_api_responses_v2.json
frontend/README.md
frontend/frontend_design.md
frontend/demo_scenarios.md
frontend/ux_report.md
```

Giao diện này thể hiện được luồng cơ bản:

```text
User Query
-> Top-K Results
-> Metadata
-> Citations
-> Source Documents
-> Context Chunks
-> LLM Consumption Preview
```

Ý nghĩa của phần việc này là giúp dự án có một bản demo frontend độc lập từ sớm, ngay cả khi backend hoặc API contract chưa hoàn thiện đầy đủ.

### 2.2. Chuyển Từ Mock Demo Sang Kết Nối Backend Thật

Sau giai đoạn mock, Nguyễn Duy Hiếu đã nâng cấp giao diện để kết nối với backend thật. Trọng tâm là giao diện:

```text
frontend/explainable_retrieval_console.html
```

Giao diện này sử dụng các endpoint thực tế của hệ thống:

```text
GET /search
GET /hybrid_search
POST /context
GET /eval/golden
```

Nhờ đó, frontend không còn chỉ là giao diện mô phỏng, mà trở thành công cụ kiểm tra và trình bày kết quả thật từ backend.

Giá trị mang lại:

- Kiểm tra được Search API thật.
- Kiểm tra được Hybrid Retrieval API.
- Kiểm tra được Context API khi người dùng chọn khách sạn.
- Hiển thị được kết quả evaluation từ golden dataset.
- Giúp phát hiện các lỗi tích hợp giữa frontend, backend, OpenSearch, Qdrant và dữ liệu.

### 2.3. Xây Dựng Explainable Retrieval Console

Một trong các phần việc quan trọng nhất là xây dựng giao diện **Explainable Retrieval Console**.

File chính:

```text
frontend/explainable_retrieval_console.html
```

Giao diện này không chỉ hiển thị danh sách khách sạn, mà còn giải thích toàn bộ quá trình hệ thống xử lý query.

Các khu vực chính trong giao diện gồm:

- Query Input
- Query Understanding
- Ontology Tags
- BM25 Baseline
- Retrieval Pipeline
- Ranking Explanation
- Context Package
- Review/Citation Evidence
- Latency Trace
- Golden Dataset Evaluation
- Sơ đồ luồng dữ liệu có timing

Giao diện này giúp trả lời các câu hỏi quan trọng:

```text
Hệ thống hiểu query như thế nào?
Query được gắn ontology tag nào?
Vì sao khách sạn này được chọn?
Vì sao khách sạn này được xếp hạng cao?
Pipeline retrieval đi qua những bước nào?
Bước nào đang chậm?
Context nào được đưa cho LLM?
Citation/evidence nào hỗ trợ kết quả?
```

Đây là phần giúp frontend trở thành công cụ explainability, không chỉ là giao diện hiển thị kết quả.

### 2.4. Hiển Thị BM25 Baseline Và Hybrid Retrieval

Frontend đã hỗ trợ hiển thị kết quả từ cả hai hướng:

```text
GET /search        -> BM25 baseline
GET /hybrid_search -> explainable/hybrid retrieval flow
```

Các thông tin được hiển thị bao gồm:

- Tên khách sạn
- Thành phố/khu vực
- Loại hình lưu trú
- Điểm BM25
- Review score
- Star rating
- Mô tả khách sạn
- Ranking signals nếu backend trả về
- Top-K hotel results

Điểm quan trọng là giao diện đã phân biệt được:

- Kết quả BM25 thuần.
- Kết quả hybrid retrieval.
- Các phần backend chưa expose đủ field.

Điều này giúp mentor hoặc người review nhìn thấy sự khác biệt giữa keyword search cơ bản và retrieval pipeline có explainability.

### 2.5. Hiển Thị Query Understanding Và Ontology Tags

Nguyễn Duy Hiếu đã thiết kế phần hiển thị query understanding và ontology tags để làm rõ cách hệ thống hiểu ý định người dùng.

Ví dụ với query:

```text
khách sạn phù hợp cho trẻ nhỏ gần VinWonders Phú Quốc
```

Giao diện có thể hiển thị các tag như:

```text
OBJ_HOTEL
PURPOSE_FAMILY
AMEN_KIDS_FRIENDLY
LMK_VINWONDERS_PHU_QUOC
LOC_PHU_QUOC
```

Khi backend chưa expose đủ field, frontend có cơ chế fallback rõ ràng và đánh dấu đây là fallback/frontend rule, không giả lập là output chính thức từ backend.

Giá trị của phần này là giúp người xem hiểu rằng hệ thống không chỉ match keyword, mà còn cố gắng hiểu mục đích, địa điểm, landmark và nhu cầu của người dùng.

### 2.6. Xây Dựng Ranking Explanation

Frontend đã có phần giải thích vì sao một khách sạn có thể được xếp hạng cao.

Các yếu tố được trình bày gồm:

- BM25 score
- Review score
- Star rating
- Ontology match
- Location match
- Family/kids-friendly signals
- Rerank/business score nếu backend trả về
- Matched chunks nếu có

Phần này có ý nghĩa quan trọng trong demo vì giúp người xem không chỉ thấy “khách sạn nào đứng đầu”, mà còn thấy “vì sao khách sạn đó đứng đầu”.

### 2.7. Hiển Thị Context Package, Citation Và Evidence

Frontend đã hỗ trợ phần Context Package và Evidence thông qua:

```text
POST /context
```

Các thông tin được hiển thị gồm:

- Context chunks
- Source documents
- Citations
- Positive evidence
- Negative evidence
- LLM-ready context nếu backend trả về

Giao diện cũng xử lý rõ trường hợp backend chưa trả đủ field, ví dụ:

- Không có `llm_context`
- Không có `context_text`
- Không có citations
- Không có source documents
- Context API lỗi hoặc chưa sẵn sàng

Điểm tốt của phần này là frontend thể hiện đúng boundary: nếu backend chưa có dữ liệu thì frontend báo rõ, không tự nhận là dữ liệu thật.

### 2.8. Bổ Sung Latency Trace Và Sơ Đồ Luồng Dữ Liệu

Nguyễn Duy Hiếu đã bổ sung phần đo latency và giải thích thời gian xử lý.

Các chỉ số được hiển thị gồm:

- Wall-clock latency từ phía browser.
- Thời gian request `GET /hybrid_search`.
- Thời gian request `GET /search`.
- Backend `/search took_ms`.
- Backend stage timing trong `/hybrid_search`, ví dụ:
  - intent
  - filter
  - text_retrieval
  - fusion
  - rerank
  - context
- Thời gian `POST /context` sau khi người dùng chọn khách sạn.

Ngoài ra, giao diện có nút:

```text
Xem sơ đồ luồng dữ liệu + timing
```

Nút này giúp người xem thấy trực quan query đi qua các bước nào và mỗi bước mất bao lâu.

Giá trị của phần này:

- Giúp phát hiện bottleneck trong pipeline.
- Giúp backend team biết bước nào cần tối ưu.
- Giúp mentor hiểu hệ thống hoạt động theo flow thật.
- Làm demo kỹ thuật có chiều sâu hơn thay vì chỉ hiển thị kết quả cuối.

### 2.9. Xây Dựng Evaluation Dashboard / Evaluation Display Layer

Nguyễn Duy Hiếu đã xây dựng phần giao diện hiển thị kết quả evaluation.

Các file liên quan:

```text
frontend/evaluation_dashboard.html
frontend/evaluation_dashboard_design.md
frontend/mock_evaluation_results.json
```

Phần này thể hiện các metric như:

- Recall
- Precision
- Hit
- MRR
- nDCG
- Query-level evaluation
- Golden dataset evaluation

Quan trọng: frontend chỉ hiển thị kết quả evaluation, không tự tính toán metric thay backend. Điều này giữ đúng phạm vi trách nhiệm:

```text
Backend/Evaluation team tính toán metric.
Frontend hiển thị metric.
```

### 2.10. Xây Dựng Streamlit Explainable Console

Ngoài HTML demo, Nguyễn Duy Hiếu cũng có phần giao diện Streamlit để hỗ trợ debug và quan sát dễ hơn:

```text
frontend/streamlit_explainable_console.py
```

Mục tiêu của phần này là hỗ trợ kiểm tra API, debug dữ liệu trả về và bắt lỗi frontend-backend dễ hơn so với HTML tĩnh.

### 2.11. Tài Liệu Kiến Trúc, Handover Và Review

Nguyễn Duy Hiếu đã tạo hệ thống tài liệu khá đầy đủ cho phần frontend và trạng thái dự án.

Các tài liệu tiêu biểu:

```text
docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md
docs/docs_NDHieu/HIEU_TASK_BOARD.md
docs/docs_NDHieu/HIEU_CURRENT_STATUS.md
docs/docs_NDHieu/API_SCHEMA_IMPACT_HIEU.md
docs/docs_NDHieu/FRONTEND_MENTOR_PRESENTATION.md
docs/docs_NDHieu/QUERY_FLOW_DIAGRAM_PREVIEW.md
docs/docs_NDHieu/DESIGN_RECOMMENDATION.md
docs/docs_NDHieu/EXPLAINABILITY_UI_SPEC.md
docs/docs_NDHieu/UI_WIREFRAME_EXPLAINABILITY.md
docs/docs_NDHieu/BACKEND_API_ISSUES_FOR_FRONTEND.md
```

Các tài liệu này giúp:

- Mentor hiểu phần frontend đang làm gì.
- Thành viên mới có thể tiếp quản dự án.
- AI reviewer có đủ ngữ cảnh để review.
- Nhóm phân biệt rõ phần đã làm, phần đang thiếu và phần phụ thuộc backend.
- Ghi lại các vấn đề API/backend ảnh hưởng đến frontend.

## 3. Giá Trị Đóng Góp Đối Với Dự Án

### 3.1. Biến Backend Thành Sản Phẩm Có Thể Quan Sát

Backend có thể trả API, retrieval score, context chunks hoặc evaluation metric, nhưng nếu không có frontend thì các kết quả đó khó trình bày với người không trực tiếp đọc code.

Frontend do Nguyễn Duy Hiếu xây dựng giúp:

- Hiển thị kết quả backend một cách trực quan.
- Trình bày được pipeline xử lý query.
- Làm rõ giá trị của ontology, retrieval, reranking và context.
- Giúp người xem hiểu hệ thống hoạt động như thế nào.

### 3.2. Hỗ Trợ Demo Mentor Và Báo Cáo Quản Lý

Explainable Retrieval Console có vai trò quan trọng trong demo vì nó cho phép trình bày:

```text
Query -> Ontology -> Retrieval -> Ranking -> Context -> Evidence
```

Đây là cách trình bày có chiều sâu, phù hợp với một hệ thống AI Search/RAG, thay vì chỉ hiển thị danh sách kết quả cuối cùng.

### 3.3. Phát Hiện Lỗi Tích Hợp

Trong quá trình làm frontend, Nguyễn Duy Hiếu đã phát hiện nhiều vấn đề thực tế như:

- API có route nhưng dependency chưa sẵn sàng.
- Search index/config chưa khớp.
- Context response thiếu field.
- Backend chưa expose đủ explainability signals.
- Hybrid route có latency cao ở một số stage.
- Một số field cần frontend fallback hoặc hiển thị TODO.

Những phát hiện này giúp backend team có thông tin để điều chỉnh và hoàn thiện hệ thống.

### 3.4. Giữ Rõ Ranh Giới Trách Nhiệm

Trong phần frontend, Nguyễn Duy Hiếu đã giữ rõ boundary:

- Frontend hiển thị dữ liệu.
- Backend tính toán retrieval/ranking/evaluation.
- Evaluation team tạo metric.
- Frontend không tự nhận mock/fallback là kết quả chính thức.

Điều này giúp tránh nhầm lẫn khi demo hoặc review kỹ thuật.

## 4. Các File Tiêu Biểu Có Thể Dùng Để Minh Chứng

Khi cần trình bày với giám đốc hoặc mentor, có thể mở các file sau:

```text
frontend/explainable_retrieval_console.html
```

Minh chứng chính cho Explainable Retrieval Console, kết nối API thật, latency trace, context/evidence và evaluation.

```text
frontend/search_ui.html
frontend/search_ui_v2.html
```

Minh chứng cho quá trình phát triển từ mock Search UI sang Search UI v2 theo schema/API mới.

```text
frontend/evaluation_dashboard.html
```

Minh chứng cho phần Evaluation Display Layer.

```text
frontend/streamlit_explainable_console.py
```

Minh chứng cho giao diện hỗ trợ debug API/frontend-backend.

```text
docs/docs_NDHieu/HIEU_FRONTEND_ARCHITECTURE.md
```

Minh chứng cho kiến trúc frontend và phạm vi trách nhiệm.

```text
docs/docs_NDHieu/FRONTEND_MENTOR_PRESENTATION.md
```

Minh chứng cho tài liệu trình bày mentor.

```text
docs/docs_NDHieu/BACKEND_API_ISSUES_FOR_FRONTEND.md
```

Minh chứng cho quá trình phát hiện và ghi nhận vấn đề tích hợp backend ảnh hưởng đến frontend.

```text
docs/docs_NDHieu/QUERY_FLOW_DIAGRAM_PREVIEW.md
```

Minh chứng cho sơ đồ luồng dữ liệu và explainability flow.

## 5. Kết Luận

Nguyễn Duy Hiếu đã đảm nhiệm và triển khai phần **Frontend Demo Tool / Display Layer** cho dự án DA10 OTA AI Search Platform. Phần việc này không chỉ dừng ở xây dựng giao diện hiển thị kết quả, mà đã phát triển thành một bộ công cụ trực quan hóa toàn bộ luồng Search/Retrieval/RAG/Evaluation.

Các đóng góp chính bao gồm:

- Xây dựng Search UI demo.
- Chuyển từ mock sang kết nối backend thật.
- Phát triển Explainable Retrieval Console.
- Hiển thị ontology tags, BM25 baseline, hybrid retrieval, ranking explanation, context package, citation/evidence.
- Bổ sung latency trace và sơ đồ luồng dữ liệu có timing.
- Xây dựng Evaluation Display Layer.
- Tạo tài liệu kiến trúc, handover, mentor review và task tracking.
- Hỗ trợ phát hiện vấn đề tích hợp frontend-backend.

Có thể đánh giá rằng phần frontend do Nguyễn Duy Hiếu thực hiện đóng vai trò quan trọng trong việc biến các thành phần kỹ thuật của DA10 thành một hệ thống có thể demo, quan sát, kiểm chứng và trình bày rõ ràng với mentor hoặc cấp quản lý.
