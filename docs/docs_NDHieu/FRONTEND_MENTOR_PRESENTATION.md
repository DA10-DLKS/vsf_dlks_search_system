# BÁO CÁO TRÌNH BÀY FRONTEND DEMO TOOL

**Dự án:** DA10 OTA AI Search Platform  
**Người phụ trách:** Nguyễn Duy Hiếu  
**Phạm vi:** Frontend Demo Tool / DA10 Display Layer  
**Mục đích:** Trình bày cho mentor cách frontend trực quan hóa kết quả Search, Retrieval, Context và Evaluation do DA10 cung cấp.

---

## 1. Mục tiêu phần frontend

Frontend không chỉ hiển thị danh sách khách sạn. Mục tiêu chính là giúp người xem hiểu được toàn bộ hành trình của một truy vấn:

```text
User Query
-> Query Understanding
-> Ontology Tags
-> Candidate Retrieval
-> BM25 / Vector / Fusion
-> Ranking
-> Top-K Hotels
-> Context Chunks
-> Citations / Evidence
-> LLM Consumption
```

Giao diện cần trả lời được ba câu hỏi:

1. Hệ thống hiểu câu query như thế nào?
2. Vì sao một khách sạn được trả về và xếp hạng cao?
3. Những đoạn dữ liệu nào có thể được đưa vào LLM làm context?

Frontend do Nguyễn Duy Hiếu phụ trách chỉ **tiêu thụ và trình bày output**. Frontend không tính toán embedding, retrieval score, ranking score hay evaluation metrics.

---

## 2. Ranh giới trách nhiệm

### Phần Hiếu phụ trách

- Giao diện nhập query.
- Hiển thị Top-K khách sạn.
- Hiển thị metadata khách sạn.
- Hiển thị ontology tags và query understanding nếu backend trả về.
- Hiển thị BM25 score, hybrid score và ranking signals nếu backend trả về.
- Hiển thị context chunks, citations, source documents và review evidence.
- Hiển thị context dành cho LLM.
- Xử lý loading, empty, partial response và error state.
- Xây dựng console debug để xác định endpoint nào đang lỗi.
- Hiển thị evaluation output do nhóm API/Evaluation cung cấp.

### Phần Hiếu không phụ trách

- Thu thập và làm sạch dữ liệu.
- Xây dựng ontology hoặc tính ontology confidence.
- Chunking và embedding.
- BM25, vector search, hybrid fusion và reranking.
- Cài đặt backend API.
- Tính Recall, MRR, NDCG hoặc các evaluation metrics khác.
- Sinh câu trả lời của DA09 chatbot.

---

## 3. Các giao diện đã xây dựng

### 3.1 Explainable Retrieval Console bằng HTML

**File:** `frontend/explainable_retrieval_console.html`

Vai trò:

- Chạy trực tiếp trong trình duyệt.
- Gọi backend thật qua `GET /health`, `GET /search`, `GET /hybrid_search` và `POST /context`.
- Hiển thị query journey, ontology tags, BM25 results, retrieval pipeline, ranking explanation và context/evidence.
- Khi hybrid backend lỗi, giao diện vẫn hiển thị phần BM25 thật và đánh dấu rõ phần fallback.

Ưu điểm:

- Không cần npm, React hoặc Vite.
- Phù hợp trình chiếu nhanh.
- Giao diện trực quan cho mentor.

Giới hạn:

- Debug exception và raw response khó hơn Streamlit.
- Một số phần chỉ hiển thị được khi backend expose đủ field.

### 3.2 Explainable Retrieval Console bằng Streamlit

**File:** `frontend/streamlit_explainable_console.py`

Vai trò:

- Là công cụ debug và demo backend API.
- Hiển thị status code, latency, error detail và raw JSON cho từng endpoint.
- Tách riêng các tab BM25 Search, Hybrid Trace, Context/Evidence và Raw Debug.
- Giúp phân biệt lỗi frontend, lỗi API contract và lỗi dependency backend.

Lệnh chạy:

```powershell
streamlit run frontend/streamlit_explainable_console.py --server.port 8501
```

Mở trình duyệt:

```text
http://127.0.0.1:8501
```

### 3.3 Search UI standalone

Các file:

- `frontend/search_ui.html`: bản demo cũ ổn định.
- `frontend/search_ui_v2.html`: bản demo theo Search -> Context schema mới.

Hai file này vẫn được giữ để đối chiếu và demo offline, nhưng Explainable Retrieval Console là giao diện chính cho phần trình bày hiện tại.

### 3.4 Evaluation Dashboard

Các file:

- `frontend/evaluation_dashboard.html`
- `frontend/src/dashboard/EvaluationDashboard.jsx`
- `frontend/mock_evaluation_results.json`

Dashboard hiện dùng dữ liệu MOCK / DEMO và phải được ghi nhãn rõ ràng. Vu Đức Kiên hoặc nhóm Evaluation tính metric; Hiếu chỉ hiển thị kết quả.

---

## 4. Luồng dữ liệu frontend hiện tại

### 4.1 Health check

```text
Frontend -> GET /health -> API status
```

Mục đích:

- Xác nhận frontend đang gọi đúng DA10 API.
- Phát hiện trường hợp port 8000 bị một service Python khác chiếm.

### 4.2 BM25 Search

```text
Query -> GET /search?q=<query> -> OpenSearch BM25 -> Hotel results
```

Frontend có thể hiển thị ngay:

- Hotel ID.
- Tên khách sạn.
- Thành phố và địa chỉ.
- Loại hình lưu trú.
- Số sao.
- Review score.
- Mô tả.
- Amenities.
- BM25 score.
- Thời gian xử lý.

Đây là phần đã sử dụng dữ liệu khách sạn thật từ backend.

### 4.3 Hybrid Search

```text
Query
-> Intent Parsing
-> Ontology Concept Matching
-> Candidate Building
-> BM25 + Vector Search
-> RRF Fusion
-> Reranking
-> Top Hotels
-> Context Package
```

Endpoint dự kiến:

```http
GET /hybrid_search?q=<query>&top_n=10&answer=false
```

Frontend đã chuẩn bị để hiển thị:

- `intent`
- `concepts`
- `n_candidates`
- `n_fused`
- `bm25_rank`
- `vector_rank`
- `rrf_score`
- `rerank_score`
- `business_score`
- `final_score`
- `top_hotels`
- `context_package`

Trạng thái thực tế: route tồn tại nhưng độ ổn định còn phụ thuộc embedding model, Qdrant, OpenSearch và startup warmup. Frontend phải hiển thị lỗi thật hoặc partial response, không được giả vờ hybrid đã chạy thành công.

### 4.4 Context API

```text
Selected Hotel
-> POST /context
-> Context Package
-> Evidence / Citations
-> LLM-ready Context
```

Request:

```json
{
  "result_id": "hotel_17242876",
  "query": "khách sạn phù hợp cho trẻ nhỏ gần VinWonders Phú Quốc"
}
```

Frontend kỳ vọng backend trả:

- `result_id`
- `llm_context` hoặc `context_text`
- `context_chunks`
- `citations`
- `source_documents`
- `evidence.positives`
- `evidence.negatives`

Hiện backend có thể trả citation/chunk ID và evidence nhưng `llm_context` có thể rỗng. Frontend hiển thị cảnh báo thay vì tự tạo context giả.

---

## 5. Query demo chính

Query đề xuất:

```text
khách sạn phù hợp cho trẻ nhỏ gần VinWonders Phú Quốc
```

### Điều cần trình bày

1. Nhập query và chạy trace.
2. Health check xác nhận đang gọi đúng backend.
3. Hiển thị ontology tags, ví dụ:
   - `OBJ_HOTEL`
   - `PURPOSE_FAMILY`
   - `AMEN_KIDS_FRIENDLY`
   - `LMK_VINWONDERS_PHU_QUOC`
   - `LOC_PHU_QUOC`
4. Hiển thị mở rộng ontology, ví dụ:
   - `PURPOSE_FAMILY -> AMEN_KIDS_CLUB`
   - `PURPOSE_FAMILY -> AMEN_KIDS_POOL`
   - `LMK_VINWONDERS_PHU_QUOC -> LOC_PHU_QUOC`
5. Hiển thị Top-K kết quả BM25 thật.
6. Chọn một khách sạn và giải thích các tín hiệu đang có:
   - Khớp địa điểm Phú Quốc.
   - Có VinWonders/Vinpearl trong nội dung.
   - Có tiện ích trẻ em hoặc phòng gia đình.
   - Review score.
   - BM25 score.
7. Gọi Context API và hiển thị evidence/citation nếu backend trả được.

### Quy tắc trung thực khi trình bày

- Tag có nguồn `frontend fallback` không được gọi là output chính thức của ontology backend.
- BM25 result là dữ liệu thật nếu lấy từ `GET /search`.
- Hybrid score chỉ là dữ liệu thật khi `GET /hybrid_search` trả thành công.
- Evaluation metric trong dashboard hiện là MOCK / DEMO.
- Không gọi citation ID là citation đầy đủ nếu chưa có snippet và source URL.

---

## 6. Xử lý trạng thái và lỗi

Frontend có các trạng thái riêng:

| Trạng thái | Cách hiển thị |
|---|---|
| Loading | Hiển thị endpoint đang được gọi và thời gian chờ |
| API không reachable | Báo rõ API base URL, port hoặc Docker chưa chạy |
| HTTP 404 | Cảnh báo có thể đang gọi nhầm service/port |
| HTTP 500 hybrid | Hiển thị error body và fallback sang BM25 nếu có |
| Empty result | Hiển thị không có kết quả thay vì bảng rỗng |
| Context thiếu | Hiển thị chunk/citation hiện có và cảnh báo field thiếu |
| Partial response | Giữ phần dữ liệu hợp lệ, đánh dấu phần backend chưa trả |

Streamlit được bổ sung vì HTML thuần khó xem stack trace và raw response. Đây là công cụ giúp frontend phối hợp với backend hiệu quả hơn, không thay đổi ownership backend.

---

## 7. Kết quả đạt được

### Đã hoàn thành

- Có giao diện HTML standalone để demo Search/RAG.
- Có Explainable Retrieval Console kết nối backend thật.
- Có Streamlit console để debug từng API.
- Hiển thị được BM25 hotel results từ dữ liệu thật.
- Hiển thị được metadata và ranking evidence cơ bản.
- Có ontology tag fallback được ghi nhãn rõ.
- Có UI cho context, citations, source documents và review evidence.
- Có loading/error/empty/partial-response state.
- Có Evaluation Dashboard mock được ghi nhãn đúng ownership.
- Có React-ready components cho hướng tích hợp sau này.

### Chưa hoàn thành hoặc còn phụ thuộc

- Hybrid Search chưa ổn định trong mọi lần chạy.
- Backend chưa luôn trả đầy đủ score breakdown từng bước.
- Context API chưa luôn trả `llm_context/context_text` có nội dung.
- Citation hiện có thể chỉ là ID, chưa đủ snippet/source URL.
- React/Vite runtime chưa được thiết lập thành ứng dụng chạy hoàn chỉnh.
- Evaluation Dashboard chưa kết nối evaluation output thật của Kiên.

---

## 8. Giá trị của phần frontend

Frontend tạo ra ba giá trị chính:

1. **Khả năng trình diễn:** mentor có thể nhìn thấy kết quả tìm kiếm trên dữ liệu thật.
2. **Khả năng giải thích:** giao diện cho thấy query, ontology tags, retrieval stage, score và evidence thay vì chỉ hiện danh sách hotel.
3. **Khả năng kiểm thử tích hợp:** Streamlit console chỉ ra endpoint, status code, latency và raw response, giúp frontend/backend xác định đúng ownership của lỗi.

---

## 9. Kế hoạch tiếp theo

### P0 - Cần làm ngay

- Thống nhất API base URL và loại bỏ port conflict khi demo.
- Nhận response contract cuối cho `/hybrid_search` và `/context`.
- Yêu cầu backend trả context chunk dạng object có text, score và metadata.
- Yêu cầu citation có snippet, source type và source URL.

### P1 - Sau khi backend ổn định

- Bỏ dần ontology fallback frontend, ưu tiên output backend thật.
- Hiển thị ranking breakdown chính thức.
- Kết nối Evaluation Dashboard với output thật của Kiên.
- Chuẩn hóa error response cho tất cả endpoint.

### P2 - Hoàn thiện sản phẩm

- Quyết định React/Vite runtime.
- Chuyển các prototype thành component production-ready.
- Bổ sung E2E test với backend thật.
- Tối ưu responsive cho laptop và máy chiếu.

---

## 10. Kịch bản trình bày 3-5 phút

> Em là Nguyễn Duy Hiếu, phụ trách Frontend Demo Tool, tức lớp hiển thị output của DA10. Phạm vi của em không phải xây retrieval hoặc tính evaluation metric, mà là làm cho Search/RAG có thể quan sát và giải thích được.
>
> Giao diện chính là Explainable Retrieval Console. Khi người dùng nhập query, frontend gọi health check, Search API, Hybrid Search API và Context API. Với dữ liệu backend trả về, UI trình bày query understanding, ontology tags, candidate retrieval, ranking signals, Top-K hotel và context/evidence.
>
> Phần BM25 hiện đã kết nối dữ liệu khách sạn thật. Người xem có thể thấy tên khách sạn, địa chỉ, loại hình, review score, mô tả, amenities và BM25 score. Với hybrid trace, UI đã chuẩn bị các vị trí cho candidate count, vector rank, RRF score, rerank score và final score. Nếu backend chưa trả được, UI hiển thị đúng lỗi và chỉ dùng BM25 fallback, không giả lập kết quả hybrid.
>
> Khi chọn một khách sạn, frontend gọi Context API để lấy context chunks, citations, source documents và review evidence. Hiện phần này còn phụ thuộc backend trả context text và citation detail đầy đủ. Frontend không tự tạo dữ liệu để tránh làm sai provenance.
>
> Ngoài bản HTML để trình chiếu, em xây thêm Streamlit console để xem status code, latency và raw JSON của từng endpoint. Công cụ này giúp phát hiện nhanh lỗi port, Docker, API contract hoặc dependency backend.
>
> Kết quả hiện tại là frontend đã demo được Search trên dữ liệu thật, có explainability UI và có cơ chế xử lý partial/error state. Bước tiếp theo là chốt contract hybrid/context và kết nối evaluation output thật để hoàn thiện end-to-end RAG trace.

---

## 11. Câu hỏi mentor có thể đặt ra

### Ontology tags trên UI có phải backend trả thật không?

Nếu `/hybrid_search` thành công thì dùng output backend. Nếu route lỗi, UI hiển thị fallback và ghi rõ nguồn `frontend fallback`; không được coi đó là kết quả ontology chính thức.

### Vì sao một khách sạn đứng đầu?

Hiện có thể giải thích bằng BM25 score, location, amenities, review score và đoạn mô tả khớp query. Giải thích đầy đủ về vector/RRF/rerank chỉ thực hiện khi backend trả các field tương ứng.

### Citation hiện có đủ tin cậy không?

Chưa hoàn toàn nếu backend chỉ trả citation ID. Citation hoàn chỉnh cần `text_snippet`, `chunk_id`, `source_document`, `source_url` và relevance score.

### Frontend có tính Recall/MRR/NDCG không?

Không. Nhóm Evaluation tính metric; frontend chỉ hiển thị report hoặc API output và phải ghi rõ mock hay real.

### Vì sao dùng cả HTML và Streamlit?

HTML phù hợp trình chiếu trực quan, không cần runtime phức tạp. Streamlit phù hợp debug tích hợp API vì hiển thị raw response, exception và latency rõ hơn.

---

## 12. Kết luận

Phần frontend đã chuyển từ demo mock đơn thuần sang **DA10 Explainable Retrieval Display Layer** có khả năng gọi dữ liệu Search thật, trình bày trace, xử lý lỗi và hỗ trợ debug tích hợp.

Mức độ hoàn thiện hiện tại phù hợp để demo Search/BM25 và kiến trúc explainability. Để demo đầy đủ Hybrid RAG end-to-end, frontend còn cần backend ổn định `/hybrid_search`, trả context text thật và cung cấp citation có provenance đầy đủ.
