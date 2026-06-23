# API chính — DA10 Search Platform

Tài liệu mô tả 3 API nghiệp vụ chính trong `api/main.py`, được xây dựng **trực tiếp từ code**.

Base URL (local): `http://localhost:8000`

---

## 1. GET /hybrid_search

### Chức năng

Chạy toàn bộ pipeline hybrid retrieval (Node 1 → 8, tuỳ chọn Node 9). Pipeline gồm:
- **Node 1**: parse intent từ câu hỏi tiếng Việt (tách concept, city, range filter).
- **Node 2–4**: lọc hard filter + concept lookup → xây danh sách candidate hotel.
- **Node 6**: text retrieval song song qua BM25 (OpenSearch) và vector search (Qdrant) trên tập candidate.
- **Node 7**: RRF fusion + profile boost + neural rerank + business rerank → chọn top hotel.
- **Node 8**: dựng ContextPackage + prompt RAG.
- **Node 9** (tuỳ chọn): gọi LLM sinh câu trả lời.

Endpoint này trả output **thô** của pipeline, phù hợp để debug/test. Frontend chính dùng `POST /search` thay vì endpoint này.

### Request

```
GET /hybrid_search?q=<câu_hỏi>&top_n=<số>&answer=<bool>
```

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|-------|----------|----------|-------|
| `q` | string | **Có** | — | Câu hỏi tiếng Việt của người dùng |
| `top_n` | integer | Không | 5 | Số hotel trả về sau rerank (1–20) |
| `answer` | boolean | Không | false | `true` = gọi LLM sinh câu trả lời (Node 9) |

### Response

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `intent` | object | Kết quả parse intent từ câu hỏi (Node 1) |
| `intent.query` | string | Câu hỏi gốc |
| `intent.concepts` | string[] | Tất cả concept ID parse được, sorted (vd `AMEN_POOL`, `PURPOSE_FAMILY`) |
| `intent.hard_concepts` | string[] | Concept dùng filter cứng — prefix `AMEN_` hoặc `SETTING_` |
| `intent.feel_concepts` | string[] | Concept dùng rerank mềm — prefix `STYLE_` hoặc `ASPECT_` |
| `intent.object_types` | string[] | Loại hình lưu trú — prefix `OBJ_` (vd `OBJ_RESORT`) |
| `intent.purposes` | string[] | Mục đích chuyến đi — prefix `PURPOSE_` |
| `intent.price_tiers` | string[] | Phân khúc giá — prefix `PRICE_` |
| `intent.landmarks` | string[] | Địa danh/landmark — prefix `LMK_` |
| `intent.location_concepts` | string[] | Vùng/tỉnh thành — prefix `LOC_` |
| `intent.city` | string \| null | Tên thành phố thô (cho SQL filter), null nếu không nhận diện được |
| `intent.range` | object | Range filter số: `price_min`, `price_max`, `score_min`, `star_eq` (chỉ có trường nào parse được) |
| `intent.implicit` | object | Concept suy luận ngầm từ mô tả hoàn cảnh (vd "đi với con nhỏ" → `PURPOSE_FAMILY`) |
| `n_candidates` | integer | Số hotel candidate sau bước lọc (Node 4) |
| `n_fused` | integer | Số doc sau bước fusion (thường bằng `n_candidates`) |
| `rerank_method` | string | Phương pháp rerank đã dùng thực tế: `"density-fallback"` hoặc `"cross-encoder"` |
| `top_hotels` | object[] | Danh sách top hotel sau rerank, mỗi phần tử là một doc đại diện |
| `top_hotels[].hotel_id` | integer | ID khách sạn |
| `top_hotels[].chunk_id` | string | ID chunk đại diện (vd `"cand_1015998"`) |
| `top_hotels[].text` | string | Nội dung text chunk (có thể rỗng nếu chỉ có candidate KE) |
| `top_hotels[].source` | string | Nguồn gốc chunk: `"candidate"`, `"bm25"`, hoặc `"vector"` |
| `top_hotels[].rrf_score` | float | Điểm RRF fusion (0 nếu hotel không có chunk text retrieval) |
| `top_hotels[].bm25_rank` | integer \| null | Thứ hạng BM25 của hotel (null nếu không có kết quả BM25) |
| `top_hotels[].vector_rank` | integer \| null | Thứ hạng vector search của hotel (null nếu không có kết quả vector) |
| `top_hotels[].rerank_score` | float | Điểm neural rerank (cross-encoder hoặc density-fallback) |
| `top_hotels[].rerank_method` | string | Phương pháp rerank cấp doc: `"density-fallback"` hoặc `"cross-encoder"` |
| `top_hotels[].text_signal_norm` | float | Text signal sau chuẩn hóa [0,1] — dùng tính business_score |
| `top_hotels[].business_score` | float | Điểm business rerank tổng hợp |
| `top_hotels[].final_score` | float | Điểm cuối cùng sau aggregate (= `business_score` + bonus chunk count) |
| `top_hotels[].matched_chunks` | integer | Số chunk text khớp hotel này |
| `top_hotels[].metadata` | object | Metadata KE: `hotel_name`, `ontology_concepts`, `semantic_profile`, `city`, `ke_review_score`, `ke_star_rating`, `ke_price_min_vnd` |
| `context_package` | object | Gói ngữ cảnh chuẩn cho LLM (Node 8) |
| `context_package.query` | string | Câu hỏi gốc |
| `context_package.chunks[]` | object[] | Danh sách chunk đã chọn, mỗi chunk có `chunk_id`, `hotel_id`, `hotel_name`, `text`, `score`, `citation_index`, `source_type` |
| `context_package.metadata` | object | Metadata gói: `total_hotels`, `intent` (bản copy intent) |
| `prompt` | string | Prompt RAG đã dựng sẵn (có thể copy vào LLM) |
| `answer` | object \| *không có* | **Chỉ xuất hiện khi `answer=true`** |
| `answer.answer` | string | Câu trả lời LLM sinh ra (rỗng nếu LLM lỗi) |
| `answer.citations` | object[] | Danh sách hotel đã trích dẫn: `index`, `hotel_id`, `hotel_name`, `score` |
| `answer.model` | string | Provider/model đã dùng (vd `"google/gemini-2.0-flash"`) |
| `answer.error` | string \| null | Lỗi LLM nếu có, null nếu thành công |

### Ví dụ với data thực

**Request:**

```bash
curl "http://localhost:8000/hybrid_search?q=resort%20c%C3%B3%20h%E1%BB%93%20b%C6%A1i%20cho%20gia%20%C4%91%C3%ACnh%20%E1%BB%9F%20H%E1%BA%A1%20Long&top_n=2&answer=false"
```

**Response:**

```json
{
  "intent": {
    "query": "resort có hồ bơi cho gia đình ở Hạ Long",
    "concepts": ["AMEN_POOL", "LOC_HA_LONG", "OBJ_RESORT", "PURPOSE_FAMILY"],
    "hard_concepts": ["AMEN_POOL"],
    "feel_concepts": [],
    "object_types": ["OBJ_RESORT"],
    "purposes": ["PURPOSE_FAMILY"],
    "price_tiers": [],
    "landmarks": [],
    "location_concepts": ["LOC_HA_LONG"],
    "city": "hạ long",
    "range": {},
    "implicit": {}
  },
  "n_candidates": 45,
  "n_fused": 45,
  "rerank_method": "density-fallback",
  "top_hotels": [
    {
      "chunk_id": "cand_1015998",
      "hotel_id": 1015998,
      "text": "Vinpearl Resort & Spa Hạ Long - Nghỉ dưỡng tuyệt vời tại Hạ Long\n\nVinpearl Resort & Spa Hạ Long là một khách sạn 5 sa...",
      "source": "candidate",
      "rrf_score": 0.0318,
      "bm25_rank": 2,
      "vector_rank": 4,
      "rerank_score": 0.9810,
      "rerank_method": "density-fallback",
      "text_signal_norm": 0.9769,
      "business_score": 0.4288,
      "final_score": 0.4288,
      "matched_chunks": 1,
      "metadata": {
        "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
        "ontology_concepts": ["AMEN_POOL", "AMEN_SPA", "AMEN_SEA_VIEW", "PURPOSE_FAMILY", "OBJ_RESORT"],
        "semantic_profile": {},
        "city": "Hạ Long",
        "ke_review_score": 9.0,
        "ke_star_rating": 5.0,
        "ke_price_min_vnd": 5000000
      }
    }
  ],
  "context_package": {
    "query": "resort có hồ bơi cho gia đình ở Hạ Long",
    "chunks": [
      {
        "chunk_id": "cand_1015998",
        "hotel_id": 1015998,
        "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
        "text": "Đỗ xe và Wi-Fi luôn miễn phí...",
        "score": 0.82,
        "citation_index": 1,
        "source_type": null
      }
    ],
    "metadata": {
      "total_hotels": 2,
      "intent": { "...": "..." }
    }
  },
  "prompt": "Bạn là trợ lý tư vấn du lịch của DA10 Travel Assistant. Trả lời câu hỏi DỰA TRÊN thông tin ngữ cảnh dưới đây.\n\nNgữ cảnh:\n---\n[1] Vinpearl Resort & Spa Hạ Long (tại Hạ Long, 5★, điểm 9/10)\nNội dung: Đỗ xe và Wi-Fi luôn miễn phí...\n---\n\nCâu hỏi: \"resort có hồ bơi cho gia đình ở Hạ Long\""
}
```

---

## 2. POST /search

### Chức năng

API search chính cho **frontend**. Frontend gửi câu hỏi qua JSON body, backend chạy hybrid retrieval pipeline (giống `GET /hybrid_search` nhưng luôn `generate_answer=false` để giữ tốc độ nhanh), rồi dùng `frontend_adapter.to_search_response()` chuyển đổi output pipeline sang format frontend chuẩn.

Kết quả trả về đã được enrich thêm metadata hiển thị (location, amenities tiếng Việt, price_level, best_for) từ knowledge engineering labels.

### Request

```
POST /search
Content-Type: application/json
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|-------|----------|-------|
| `query` | string | **Có** | Câu hỏi tìm kiếm tiếng Việt |
| `filters` | object \| null | Không | Bộ lọc bổ sung (hiện tại nhận vào nhưng chưa được truyền xuống pipeline — logic lọc dựa hoàn toàn trên `query`) |

### Response

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `query` | string | Câu hỏi gốc từ request |
| `results` | object[] | Danh sách kết quả (tối đa 10) |
| `total` | integer | Tổng số kết quả trả về (= `len(results)`) |

Mỗi phần tử trong `results[]`:

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `id` | string | ID dạng `"hotel_<hotel_id>"` — dùng gửi tiếp cho `POST /context` |
| `title` | string | Tên khách sạn |
| `snippet` | string | Đoạn mô tả ngắn (200 ký tự đầu từ text chunk hoặc content knowledge object) |
| `score` | float | Điểm xếp hạng cuối cùng (final_score, làm tròn 4 chữ số) |
| `metadata` | object | Thông tin hiển thị trên UI |
| `metadata.location` | string | Vị trí hiển thị (city, province — bỏ trùng nếu city == province) |
| `metadata.category` | string | Loại hình lưu trú: `"Resort"`, `"Hotel"`, `"Homestay"`, ... (lấy từ `object_type`, bỏ prefix `OBJ_`) |
| `metadata.amenities` | string[] | Tiện ích bằng tiếng Việt, tối đa 8 mục (vd `"Hồ bơi"`, `"Spa"`, `"Wi-Fi"`) |
| `metadata.ranking_info` | string | Chuỗi hiển thị hạng sao + điểm review (vd `"5★ · điểm 9/10"`) |
| `metadata.price_level` | string | Phân khúc giá tiếng Việt: `"Bình dân"` / `"Tầm trung"` / `"Cao cấp"` / `"Sang trọng"` / `"Unknown"` |
| `metadata.best_for` | string[] | Phù hợp cho nhóm nào, tối đa 3 (vd `"Gia đình"`, `"Cặp đôi"`) |
| `citations` | object[] | Mảng 1 phần tử — trích dẫn nguồn |
| `citations[].id` | string | ID citation dạng `"cit_<hotel_id>"` |
| `citations[].source_document_id` | string | ID document dạng `"doc_<hotel_id>"` |
| `citations[].chunk_id` | string | ID chunk gốc |
| `citations[].label` | string | Tên khách sạn (hiển thị) |
| `citations[].url` | string | URL nguồn (Agoda/Booking) — rỗng nếu không có |
| `citations[].quote` | string | Trích dẫn ngắn (120 ký tự đầu) |
| `source_documents` | object[] | Mảng 1 phần tử — thông tin document gốc |
| `source_documents[].id` | string | ID document dạng `"doc_<hotel_id>"` |
| `source_documents[].title` | string | Tên khách sạn |
| `source_documents[].type` | string | Luôn là `"hotel_detail"` |
| `source_documents[].url` | string | URL nguồn |
| `context_chunks` | object[] | Mảng 1 phần tử — nội dung chunk ngữ cảnh |
| `context_chunks[].id` | string | ID chunk |
| `context_chunks[].source_document_id` | string | ID document tương ứng |
| `context_chunks[].text` | string | Nội dung text chunk |
| `context_chunks[].rank` | integer | Thứ hạng (citation_index, bắt đầu từ 1) |

### Ví dụ với data thực

**Request:**

Linux / macOS:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "resort có hồ bơi cho gia đình ở Hạ Long", "filters": null}'
```

Windows (PowerShell / Git Bash):

```bash
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d "{\"query\": \"resort có hồ bơi cho gia đình ở Hạ Long\", \"filters\": null}"
```

**Response:**

```json
{
  "query": "resort có hồ bơi cho gia đình ở Hạ Long",
  "results": [
    {
      "id": "hotel_1015998",
      "title": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "snippet": "Đỗ xe và Wi-Fi luôn miễn phí, vì vậy quý khách có thể giữ liên lạc, đến và đi tùy ý. Nằm ở vị trí trung tâm tại Hạ Long của Hạ Long, chỗ nghỉ này đặt quý khách ở gần các điểm thu hút và tùy chọn ăn uống thú ",
      "score": 0.8200,
      "metadata": {
        "location": "Hạ Long",
        "category": "Resort",
        "amenities": ["Sát biển", "Hồ bơi", "Hồ bơi vô cực", "Hồ bơi trẻ em", "Spa", "Phòng gym", "Sân golf", "Kids club"],
        "ranking_info": "5★ · điểm 9/10",
        "price_level": "Sang trọng",
        "best_for": ["Gia đình", "Cặp đôi", "Công tác"]
      },
      "citations": [
        {
          "id": "cit_1015998",
          "source_document_id": "doc_1015998",
          "chunk_id": "cand_1015998",
          "label": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
          "url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998",
          "quote": "Đỗ xe và Wi-Fi luôn miễn phí, vì vậy quý khách có thể giữ liên lạc, đến và đi tùy ý. Nằm ở vị trí trung tâm tại Hạ Long"
        }
      ],
      "source_documents": [
        {
          "id": "doc_1015998",
          "title": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
          "type": "hotel_detail",
          "url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998"
        }
      ],
      "context_chunks": [
        {
          "id": "cand_1015998",
          "source_document_id": "doc_1015998",
          "text": "Đỗ xe và Wi-Fi luôn miễn phí, vì vậy quý khách có thể giữ liên lạc, đến và đi tùy ý...",
          "rank": 1
        }
      ]
    }
  ],
  "total": 1
}
```

---

## 3. POST /context

### Chức năng

Lấy context chi tiết + câu trả lời LLM cho **một khách sạn cụ thể** mà user đã chọn từ kết quả `POST /search`.

Endpoint này **không search lại** — nó lấy thẳng knowledge object của hotel theo `result_id`, enrich thêm bằng chứng ABSA (Aspect-Based Sentiment Analysis) từ review thật, rồi gọi LLM sinh câu trả lời. Nếu request có `query`, evidence sẽ ưu tiên các aspect khớp nhu cầu user lên đầu.

Luồng xử lý:
1. Trích `hotel_id` từ `result_id` (bỏ prefix `"hotel_"`)
2. Load knowledge object + KE labels
3. Nếu có `query`: parse intent → lấy concept → ưu tiên evidence ABSA khớp query
4. Dựng context gồm content marketing + bằng chứng review thật (cả tích cực lẫn tiêu cực)
5. Gọi LLM (Node 9) sinh `llm_context`
6. Trả response với `llm_context`, citations, evidence chi tiết, các chunk hiển thị

### Request

```
POST /context
Content-Type: application/json
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|-------|----------|-------|
| `result_id` | string | **Có** | ID khách sạn dạng `"hotel_<id>"` (lấy từ field `id` trong kết quả `POST /search`) |
| `query` | string \| null | Không | Câu hỏi gốc của user — giúp LLM trả lời bám nhu cầu và ưu tiên evidence khớp query. Nếu null thì LLM giới thiệu chung |

### Response

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `result_id` | string | Echo lại `result_id` từ request |
| `llm_context` | string | Câu trả lời LLM sinh ra — mô tả hotel phù hợp tới đâu với nhu cầu user, có dẫn chứng cân bằng (mặt mạnh + hạn chế). Rỗng nếu LLM lỗi |
| `citations` | object[] | Mảng 1 phần tử — trích dẫn nguồn |
| `citations[].id` | string | ID citation dạng `"cit_<hotel_id>"` |
| `citations[].source_document_id` | string | ID document dạng `"doc_<hotel_id>"` |
| `citations[].label` | string | Tên khách sạn |
| `citations[].url` | string | URL nguồn (Agoda/Booking) |
| `citations[].quote` | string | Trích dẫn ngắn content (160 ký tự đầu) |
| `source_documents` | object[] | Mảng 1 phần tử — thông tin document gốc |
| `source_documents[].id` | string | ID document dạng `"doc_<hotel_id>"` |
| `source_documents[].title` | string | Tên khách sạn |
| `source_documents[].type` | string | Luôn là `"hotel_detail"` |
| `source_documents[].url` | string | URL nguồn |
| `context_chunks` | object[] | Nhiều chunk hiển thị, gồm tổng quan + evidence ABSA tách riêng |
| `evidence` | object | Bằng chứng ABSA đầy đủ từ review thật |

Chi tiết `context_chunks[]` — có 3 loại `source_type`:

**Loại `"hotel_content"` (chunk tổng quan):**

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `chunk_id` | string | Dạng `"chunk_<hotel_id>_overview"` |
| `hotel_name` | string | Tên khách sạn |
| `source_type` | string | `"hotel_content"` |
| `text` | string | Content marketing (400 ký tự đầu) |
| `score` | null | Không có điểm cho chunk tổng quan |
| `metadata.location` | string | Vị trí hiển thị |

**Loại `"absa_positive"` (điểm mạnh từ review):**

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `chunk_id` | string | Dạng `"chunk_<hotel_id>_pos_<concept>"` |
| `hotel_name` | string | Tên khách sạn |
| `source_type` | string | `"absa_positive"` |
| `text` | string | Mô tả điểm mạnh, vd `"Điểm mạnh (khớp nhu cầu): Hồ bơi — đánh giá tích cực 0.85 từ 81 lượt review."` |
| `score` | float | Điểm tích cực của aspect (0–1) |
| `metadata.concept` | string | Concept ID (vd `"AMEN_POOL"`) |
| `metadata.evidence_count` | integer | Số lượt đánh giá |
| `metadata.matched` | boolean | `true` nếu aspect này khớp với query user |

**Loại `"absa_negative"` (hạn chế từ review):**

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `chunk_id` | string | Dạng `"chunk_<hotel_id>_neg_<concept>"` |
| `hotel_name` | string | Tên khách sạn |
| `source_type` | string | `"absa_negative"` |
| `text` | string | Mô tả hạn chế + trích review thật, vd `"Mặt hạn chế: Yên tĩnh (điểm tiêu cực 0.29). Trích review thật: noisy corridors..."` |
| `score` | float | Điểm tiêu cực (0–1, càng cao = càng nhiều phàn nàn) |
| `metadata.concept` | string | Concept ID |
| `metadata.matched` | boolean | `true` nếu aspect này khớp với query user |
| `metadata.spans` | string[] | Các câu review nguyên văn (tối đa 2) |

Chi tiết `evidence`:

| Trường | Kiểu | Mô tả |
|--------|-------|-------|
| `evidence.positives` | object[] | Các mặt mạnh (từ `semantic_profile`) |
| `evidence.positives[].concept` | string | Concept ID (vd `"ASPECT_ROOM"`) |
| `evidence.positives[].aspect` | string | Tên tiếng Việt (vd `"Phòng"`) |
| `evidence.positives[].score` | float | Điểm tích cực (0–1) |
| `evidence.positives[].evidence_count` | integer | Số lượt đánh giá |
| `evidence.positives[].matched` | boolean | `true` nếu khớp query user |
| `evidence.negatives` | object[] | Các mặt hạn chế (từ `negative_style_profile`) |
| `evidence.negatives[].concept` | string | Concept ID |
| `evidence.negatives[].aspect` | string | Tên tiếng Việt |
| `evidence.negatives[].negative_score` | float | Điểm tiêu cực (0–1) |
| `evidence.negatives[].spans` | string[] | Trích câu review thật (tối đa 2) |
| `evidence.negatives[].matched` | boolean | `true` nếu khớp query user |

### Ví dụ với data thực

**Request:**

Linux / macOS:

```bash
curl -X POST "http://localhost:8000/context" \
  -H "Content-Type: application/json" \
  -d '{"result_id": "hotel_1015998", "query": "resort yên tĩnh cho gia đình ở Hạ Long"}'
```

Windows (PowerShell / Git Bash):

```bash
curl -X POST "http://localhost:8000/context" -H "Content-Type: application/json" -d "{\"result_id\": \"hotel_1015998\", \"query\": \"resort yên tĩnh cho gia đình ở Hạ Long\"}"
```

**Response:**

```json
{
  "result_id": "hotel_1015998",
  "llm_context": "Vinpearl Resort & Spa Hạ Long [1] là resort 5 sao tại Hạ Long, phù hợp cho gia đình với hồ bơi trẻ em, kids club và dịch vụ trông trẻ. Tuy nhiên, về tiêu chí 'yên tĩnh' cần lưu ý: dù điểm tích cực là 0.68 từ 70 lượt đánh giá, có 11 phản hồi tiêu cực về tiếng ồn — đặc biệt từ hành lang và khu vực nhà hàng vào buổi tối. Khách từng phản ánh 'noisy corridors' và 'kids running up and down corridors until late at night'. Nếu gia đình bạn cần không gian thật yên tĩnh, đây có thể là điểm cần cân nhắc.",
  "citations": [
    {
      "id": "cit_1015998",
      "source_document_id": "doc_1015998",
      "label": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998",
      "quote": "Đỗ xe và Wi-Fi luôn miễn phí, vì vậy quý khách có thể giữ liên lạc, đến và đi tùy ý. Nằm ở vị trí trung tâm tại Hạ Long của Hạ Long, chỗ nghỉ này đặt quý kh"
    }
  ],
  "source_documents": [
    {
      "id": "doc_1015998",
      "title": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "type": "hotel_detail",
      "url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998"
    }
  ],
  "context_chunks": [
    {
      "chunk_id": "chunk_1015998_overview",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "source_type": "hotel_content",
      "text": "Đỗ xe và Wi-Fi luôn miễn phí, vì vậy quý khách có thể giữ liên lạc, đến và đi tùy ý. Nằm ở vị trí trung tâm tại Hạ Long của Hạ Long, chỗ nghỉ này đặt quý khách ở gần các điểm thu hút và tùy chọn ăn uống thú vị. Đừng rời đi trước khi ghé thăm Hang Sửng Sốt nổi tiếng. Được xếp hạng 5 sao, chỗ nghỉ chất lượng cao này cho phép khách nghỉ sử dụng bể bơi trong nhà, mát-xa và bể bơi ngoài trời ngay trong khuôn viên.",
      "score": null,
      "metadata": {
        "location": "Hạ Long"
      }
    },
    {
      "chunk_id": "chunk_1015998_pos_STYLE_QUIET",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "source_type": "absa_positive",
      "text": "Điểm mạnh (khớp nhu cầu): Yên tĩnh — đánh giá tích cực 0.68 từ 70 lượt review.",
      "score": 0.68,
      "metadata": {
        "concept": "STYLE_QUIET",
        "evidence_count": 70,
        "matched": true
      }
    },
    {
      "chunk_id": "chunk_1015998_pos_PURPOSE_FAMILY",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "source_type": "absa_positive",
      "text": "Điểm mạnh (khớp nhu cầu): Gia đình — đánh giá tích cực 0.67 từ 22 lượt review.",
      "score": 0.67,
      "metadata": {
        "concept": "PURPOSE_FAMILY",
        "evidence_count": 22,
        "matched": true
      }
    },
    {
      "chunk_id": "chunk_1015998_pos_ASPECT_ROOM",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "source_type": "absa_positive",
      "text": "Điểm mạnh: Phòng — đánh giá tích cực 0.94 từ 4121 lượt review.",
      "score": 0.94,
      "metadata": {
        "concept": "ASPECT_ROOM",
        "evidence_count": 4121,
        "matched": false
      }
    },
    {
      "chunk_id": "chunk_1015998_neg_STYLE_QUIET",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "source_type": "absa_negative",
      "text": "Mặt hạn chế (khớp nhu cầu): Yên tĩnh (điểm tiêu cực 0.29). Trích review thật: but it's also very busy which is quite a shock after being on a boat with much smaller pax numbers - so much so that there were kids running up and down corridors until late at night etc. | noisy corridors or any event activity can clearly be heard in rooms",
      "score": 0.29,
      "metadata": {
        "concept": "STYLE_QUIET",
        "matched": true,
        "spans": [
          "but it's also very busy which is quite a shock after being on a boat with much smaller pax numbers - so much so that there were kids running up and down corridors until late at night etc.",
          "noisy corridors or any event activity can clearly be heard in rooms"
        ]
      }
    }
  ],
  "evidence": {
    "positives": [
      {
        "concept": "STYLE_QUIET",
        "aspect": "Yên tĩnh",
        "score": 0.68,
        "evidence_count": 70,
        "matched": true
      },
      {
        "concept": "PURPOSE_FAMILY",
        "aspect": "Gia đình",
        "score": 0.67,
        "evidence_count": 22,
        "matched": true
      },
      {
        "concept": "ASPECT_ROOM",
        "aspect": "Phòng",
        "score": 0.94,
        "evidence_count": 4121,
        "matched": false
      },
      {
        "concept": "ASPECT_CLEANLINESS",
        "aspect": "Sạch sẽ",
        "score": 0.93,
        "evidence_count": 4121,
        "matched": false
      },
      {
        "concept": "ASPECT_FACILITIES",
        "aspect": "Cơ sở vật chất",
        "score": 0.92,
        "evidence_count": 4121,
        "matched": false
      }
    ],
    "negatives": [
      {
        "concept": "STYLE_QUIET",
        "aspect": "Yên tĩnh",
        "negative_score": 0.29,
        "spans": [
          "but it's also very busy which is quite a shock after being on a boat with much smaller pax numbers - so much so that there were kids running up and down corridors until late at night etc.",
          "noisy corridors or any event activity can clearly be heard in rooms"
        ],
        "matched": true
      },
      {
        "concept": "STYLE_ROMANTIC",
        "aspect": "STYLE_ROMANTIC",
        "negative_score": 0.23,
        "spans": [
          "this left a really disappointing mark on what was supposed to be our honeymoon",
          "das schlechteste unserer Vietnamreise"
        ],
        "matched": false
      },
      {
        "concept": "STYLE_LUXURY",
        "aspect": "Sang trọng",
        "negative_score": 0.13,
        "spans": [
          "It felt like an attempt at high class luxury without the staff ever having previously been to a luxury hotel.",
          "đồ ăn trong resort rất đắt"
        ],
        "matched": false
      }
    ]
  }
}
```

---

## Luồng sử dụng

### Frontend (production)

```
User nhập câu hỏi
  → POST /search  { query: "..." }
  → Frontend render danh sách kết quả (id, title, snippet, score, metadata)
  → User click chọn 1 khách sạn
  → POST /context  { result_id: "hotel_1015998", query: "..." }
  → Frontend hiển thị llm_context, evidence, context_chunks
```

### Debug / Test

```
GET /hybrid_search?q=...&top_n=5&answer=true
  → Xem toàn bộ output pipeline: intent, candidates, rerank, context, prompt, answer
```

---

*File này được tạo dựa trên code thực tế tại `api/main.py`, `api/frontend_adapter.py`, `retrieval/hybrid_search/pipeline.py`, `retrieval/query_processing/intent_parser.py`, `context/context_package.py`, `context/answer_generator.py`. Data ví dụ lấy từ `knowledge_engineering/enrichment/knowledge_objects.json` (hotel `acc_1015998` — Vinpearl Resort & Spa Hạ Long).*
