# Báo cáo 03 — Chunking & Embedding

Khâu này biến hồ sơ khách sạn sạch (`data/cleaned`) thành các **đơn vị truy hồi nhỏ** (chunk) có gắn nhãn tri thức, rồi nhúng thành **vector ngữ nghĩa** để vector search dùng. Báo cáo mô tả chiến lược chunking theo loại tài liệu, cách đính nhãn KE, và mô hình embedding bge-m3.

---

## 1. Chunking (`knowledge_engineering/chunking/`)

### 1.1 Triết lý: tách "prose nhúng" khỏi "metadata filter"

Nguyên tắc cốt lõi (`metadata_payload` trong `strategies.py`): **chỉ văn xuôi mới đem đi nhúng; các trường exact/filterable thì giữ trong payload**, không trộn vào text embedding.

- `TEXT_METADATA_EXCLUDES` loại các trường dài/cấu trúc (description, faq, rooms, reviews, embedding_text...) khỏi metadata phẳng.
- `metadata_payload` chỉ giữ scalar (str/int/float/bool) và list-of-scalar → đây là phần dùng để **filter** (city, star, review_score, ontology_concepts...).

Lý do: nếu nhồi giá/sao/thành phố vào prose rồi nhúng, vector sẽ "mờ" tín hiệu ngữ nghĩa và filter cứng kém chính xác. Tách ra cho mỗi tín hiệu một việc.

### 1.2 Router theo loại tài liệu — `chunk_document`

`chunk_document` tự nhận loại (`_detect_source_type`) rồi route:

| Loại | Hàm | Chiến lược |
|---|---|---|
| hotel | `chunk_hotel` | hỗn hợp (whole + recursive sentence + atomic) |
| review | `chunk_reviews` | atomic (1 review = 1 chunk) + dedupe |
| cms | `chunk_cms` | recursive sentence theo section markdown |

### 1.3 `chunk_hotel` — đa chiến lược

Một khách sạn sinh nhiều chunk theo loại nội dung:

1. **overview** (`whole_chunk`): mô tả ngắn + overview, giữ nguyên khối.
2. **description** (`recursive_sentence_chunks`): mô tả đầy đủ (~14k ký tự) cắt theo câu, gộp đến `child_token_target`, có **overlap** `child_token_overlap` để không đứt ngữ cảnh giữa hai chunk.
3. **semantic_profile** (`whole_semantic_profile`): chunk từ `embedding_text` (đoạn tổng hợp đã dựng ở crawl) — đại diện ngữ nghĩa cô đọng của khách sạn.
4. **room_type** (atomic): mỗi loại phòng 1 chunk (`_render_room`: tên, mô tả, giường, hướng, tiện nghi).
5. **faq** (atomic): mỗi cặp Q&A 1 chunk.

Mỗi chunk lọc tối thiểu `min_text_chars` để bỏ chunk rỗng/quá ngắn.

### 1.4 Cơ chế chi tiết

- **`stable_chunk_id`**: id ổn định = SHA1(các phần ghép) cắt 16 hex → **idempotent** (chạy lại không sinh trùng), cho phép resume/upsert chính xác.
- **`with_context_prefix`**: thêm tiền tố `title / section` vào text trước khi nhúng → mỗi chunk tự mang ngữ cảnh "đây là phần X của khách sạn Y" (quan trọng cho vector recall).
- **parent_id / parent_text**: chunk con của description giữ liên kết về parent (parent-child) để có thể trả ngữ cảnh rộng hơn khi cần.
- **dedupe review** (`chunk_reviews`): fingerprint theo text lowercased → bỏ review trùng trong cùng bundle.

### 1.5 Đính nhãn KE — `attach_ke_labels`

Đây là **khâu nối "KE → index"** then chốt. Với mỗi chunk hotel/review, gọi `labels_for(hotel_id)` lấy nhãn từ `knowledge_objects.json` và gắn vào metadata payload:

```
ontology_concepts, strong_feel_concepts, semantic_profile,
negative_style_profile, nearby_landmarks, location_concept,
ke_review_score / ke_star_rating / ke_price_min_vnd (range_filters)
```

- Text chunk lấy từ `data/cleaned` (phong phú); **nhãn** lấy từ KE (chuẩn ontology).
- `range_filters`: chỉ điền `ke_*` nếu cleaned chưa có (KE giá là placeholder; star/review_score thật).
- Nếu KE chưa có nhãn cho hotel → **bỏ qua, không phá payload** (pipeline vẫn chạy).

Nhờ vậy tầng retrieval đọc `ontology_concepts` để **filter cứng** và `semantic_profile` để **rerank** ngay trên payload, không cần join DB lúc query.

---

## 2. Embedding (`indexing/embedding/`)

### 2.1 Mô hình production: BAAI/bge-m3

`indexing/embedding/models.py` — `SentenceTransformerEmbeddingModel`:

- **Model**: `BAAI/bge-m3` (`BGE_M3_MODEL_NAME`), đa ngôn ngữ, mạnh với tiếng Việt.
- **Chiều vector**: **1024** (`VECTOR_DIM_DEFAULT` trong qdrant_index).
- **Chuẩn hóa**: `normalize_embeddings=True` (L2) → dùng cosine distance là tích vô hướng.
- **Chọn device tự động**: ưu tiên `cuda` → `mps` → `cpu`, override qua env `EMBEDDING_DEVICE`. Trên GPU (`cuda`/`mps`) tự nâng `batch_size` lên ≥64.
- **`torch.no_grad()`** khi encode (inference, tiết kiệm bộ nhớ).

### 2.2 Model offline cho test

`HashEmbeddingModel` — embedding xác định (seed theo SHA1 của text), 32 chiều, **chỉ dùng cho test/smoke offline**, không bao giờ là mặc định. Cho phép chạy CI/verify khi không có GPU/model thật.

### 2.3 Registry

`indexing/embedding/registry.py` + `base.py` cung cấp `get_embedding_model()` và `EmbeddingResult` (text, vector, model_name, dimension) — tách interface khỏi implementation để dễ thay model.

---

## 3. Lưu ý vận hành quan trọng

### 3.1 Tránh segfault torch trong threadpool (đã xử lý)

Các route hybrid chạy ở **threadpool** của Starlette. Nếu để model XLM-RoBERTa (bge-m3 và cross-encoder reranker) **lazy-load lần đầu trong thread con**, torch native crash (exit 139) trên CPU/Windows.

Giải pháp: **khởi tạo model ngay ở startup (main thread)** trong `api/main.py:_warmup()`, thứ tự cross-encoder trước, bge-m3 sau. Cũng giúp tránh cold-start ~978ms cho request đầu mỗi worker.

### 3.2 Idempotent & checkpoint

- `stable_chunk_id` đảm bảo cùng nội dung → cùng id → reindex an toàn.
- Index Qdrant có `data/qdrant_index_checkpoint.json` để resume.

---

## 4. Tóm tắt luồng

```
data/cleaned/*.json
   │  chunk_document()  ─ tách prose ↔ metadata
   │     ├─ chunk_hotel:  overview / description(sentence+overlap) / semantic_profile / rooms / faq
   │     ├─ chunk_reviews: atomic + dedupe
   │     └─ chunk_cms:     recursive sentence theo section
   │  attach_ke_labels() ─ đính ontology_concepts / semantic_profile / range từ knowledge_objects.json
   ▼
Chunk(text + raw_text + metadata payload)
   │  bge-m3 (1024-d, L2-normalized, cosine)
   ▼
vector  →  Qdrant   (báo cáo 05)
text    →  OpenSearch BM25 (báo cáo 05)
```
