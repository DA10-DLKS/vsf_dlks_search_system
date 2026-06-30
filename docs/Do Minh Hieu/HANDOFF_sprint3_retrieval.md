# HANDOFF — Sprint 3: Hybrid Retrieval Pipeline (cho coding agent máy khác)

_Nhánh: `feature/sprint3-ke-index-bridge`. Cập nhật: 2026-06-16._

Tài liệu này cho coding agent tiếp nhận trên máy KHÁC biết: đã làm gì, còn gì phải làm, chạy
ra sao, và các bẫy đã gặp. **Đọc hết phần "BẮT ĐẦU TỪ ĐÂU" trước khi code.**

---

## 0. Bối cảnh 1 phút

DA10 = Knowledge & Retrieval Platform. Pipeline retrieval 9 node (intent → filter → candidate
→ BM25+vector → fusion → rerank → context → LLM answer) đã được **viết đầy đủ và verify bằng
logic/offline**, NHƯNG phần chạy thật với embedding bge-m3 + index đầy đủ **chưa hoàn tất trên
máy cũ vì ổ C đầy 99%** (OpenSearch bị disk-block, embed treo ở tải model). Máy mới (ổ trống)
cần **chạy index thật + bật lại các verify cần service**.

Mô hình hybrid (QUAN TRỌNG, đừng phá): text chunk lấy từ `data/cleaned` (mô tả phong phú);
NHÃN ontology (amenity/setting/style/aspect/landmark + profile) JOIN từ
`knowledge_engineering/enrichment/knowledge_objects.json` theo `hotel_id`. Vector chỉ là một
nửa; filter/rerank dùng nhãn KE là nửa kia. KHÔNG index `data/cleaned` thô mà bỏ nhãn KE.

---

## 1. ĐÃ LÀM (code xong + verify, KHÔNG cần làm lại)

| Tầng | Module | Trạng thái verify |
|---|---|---|
| Bridge KE→Index | `knowledge_engineering/common/ke_labels.py` | ✅ loader nhãn theo hotel_id (520 hotel) |
| Chunking đính nhãn | `knowledge_engineering/chunking/strategies.py` (`attach_ke_labels`) | ✅ chunk mang 41 concept |
| BM25 đính nhãn | `indexing/bm25_index/index_bm25.py` + `index_mapping.json` | ✅ iter_docs có nhãn (mapping đã thêm field) |
| Node 1 Intent | `retrieval/query_processing/intent_parser.py` | ✅ parse + bẫy fold + implicit |
| Node 2/3/4 Filter | `retrieval/filtering/{concept_index,hard_filter}.py` | ✅ khớp golden, in-memory (không cần DB) |
| Node 6B Vector | `indexing/vector_index/qdrant_index.py` + `retrieval/vector_search/qdrant_service.py` | ✅ smoke test Qdrant (offline embed) chạy |
| Node 6A BM25 fusion | `retrieval/lexical_search/service.py` (`search_for_fusion`) | ⏳ code xong, CHƯA chạy thật (OpenSearch disk-block) |
| Node 7/7B/7C | `retrieval/reranking/{fusion,neural_rerank}.py` | ✅ logic verify đầy đủ |
| Node 8 Context | `context/context_package.py` | ✅ ContextPackage + prompt |
| Node 9 LLM answer | `context/answer_generator.py` + `llm.py:complete_text` | ✅ chạy THẬT với OpenAI gpt-4o-mini |
| Orchestrator | `retrieval/hybrid_search/pipeline.py` (`run_hybrid_search`) | ✅ end-to-end Node 1→9 |
| API | `api/main.py` (`/hybrid_search?q=&answer=`) | ✅ TestClient 200 |
| Golden v2 | `data/golden_dataset/golden_set_v2.json` + builder | ✅ 59 active / 11 excluded |
| Eval harness | `evaluation/retrieval_metrics/eval_golden.py` | ✅ chạy v2 (P@10=0.69, MRR=0.89) |

Triết lý thiết kế: mỗi node **chạy được khi service vắng** (fallback). `run_hybrid_search` nếu
không truyền vector/bm25 service thì xếp hạng bằng candidate + nhãn KE — nên verify được offline.

---

## 2. CÒN PHẢI LÀM (theo thứ tự ưu tiên)

### 🔴 2.1. Index THẬT với bge-m3 (việc chính của máy mới)
Embed bge-m3 (~2GB, nên để cache trên ổ trống) rồi index vào Qdrant + OpenSearch.

```bash
# Vector (Qdrant) — KHÔNG offline:
QDRANT_COLLECTION=vsf_travel \
HF_HOME=<ổ_trống>/hf SENTENCE_TRANSFORMERS_HOME=<ổ_trống>/hf \
python -X utf8 -m indexing.vector_index.qdrant_index
# kỳ vọng: ~15k chunk, vector dim 1024. Kiểm: GET localhost:6333/collections/vsf_travel

# BM25 (OpenSearch) — tạo index trước rồi nạp:
curl -X PUT localhost:9200/vsf_hotels_bm25_current \
  -H 'Content-Type: application/json' --data-binary @indexing/bm25_index/index_mapping.json
BM25_INDEX=vsf_hotels_bm25_current BM25_TARGET_INDEX=vsf_hotels_bm25_current \
  python -X utf8 -m indexing.bm25_index.index_bm25
```
Sau khi index xong, `run_hybrid_search` với `vector_service`/`bm25_service` thật sẽ có text
trong kết quả (hiện fallback trả text rỗng).

### 🔴 2.2. Điền relevant_chunk_ids cho golden v2 (RAG chunk-level)
Chạy SAU 2.1 (cần Qdrant có chunk):
```bash
python -X utf8 -m evaluation.test_queries.add_chunk_ids
```

### 🟠 2.3. Đo lại eval với service thật
`eval_golden.evaluate(vector_service=..., bm25_service=...)` để có số hybrid đầy đủ (số hiện
tại P@10=0.69 là CHƯA có text retrieval — chỉ filter+rerank). So sánh trước/sau để chứng minh
vector đóng góp.

### 🟠 2.4. Verify lại các node cần service (đã code, chưa chạy thật)
- BM25 `search_for_fusion` trên OpenSearch thật (mới verify logic, chưa chạy do disk-block).
- `run_hybrid_search` full với cả 2 service → kiểm fusion thật sự trộn 2 nguồn.

### 🟡 2.5. Golden v3 — mở rộng (đề xuất, chưa làm)
v2 mới *làm sạch* v1. Còn thiếu: câu cho 56 city long-tail, place-intent ("Đà Nẵng có gì chơi"),
negative cases (query không có đáp án đúng), bẫy ngôn ngữ. Xem `docs/reports/evaluation/golden_dataset_review.md` mục 5.

### 🟡 2.6. STYLE_VINTAGE/AESTHETIC enrichment
3 câu golden bị `excluded: no_signal` vì ABSA chưa đủ data các style này (review thưa). Khi
backfill đủ, chúng tự active lại (build_golden_v2 chạy lại).

---

## 3. HẠ TẦNG cần có trên máy mới

| Service | Cấu hình (.env) | Ghi chú |
|---|---|---|
| Qdrant | `QDRANT_URL=http://localhost:6333` `QDRANT_COLLECTION=vsf_travel` | `docker compose up -d qdrant` |
| OpenSearch | `OPENSEARCH_URL=http://localhost:9200` `BM25_INDEX=vsf_hotels_bm25_current` | `docker compose up -d opensearch`; CẦN ổ >15% trống (watermark) |
| Embedding | `EMBEDDING_MODEL=BAAI/bge-m3` | tải ~2GB; trỏ HF_HOME sang ổ trống |
| LLM (Node 9) | `LLM_PROVIDER=openai` `LLM_MODEL=gpt-4o-mini` `OPENAI_API_KEY=...` | đa-provider qua `knowledge_engineering/enrichment/llm.py` |
| Postgres | `DATABASE_URL=...` | **TÙY CHỌN** — Node 2 dùng in-memory được; SQL filter (`hard_filter.sql_hard_filter`) cần DB `da10` có data |

`docker compose up -d opensearch qdrant` (KHÔNG bật postgres nếu cổng 5432 đã có Postgres khác).

---

## 4. BẪY ĐÃ GẶP (đừng lặp lại)

1. **OpenSearch disk-block**: ổ >95% đầy → cluster khóa tạo index (`FORBIDDEN/10`). KHÔNG nới
   watermark để bypass — phải giải phóng đĩa. Máy cũ docker chiếm ~125GB (47GB rác `docker system prune`).
2. **Qdrant API**: dùng `client.query_points(...)` (trả `.points`), KHÔNG phải `client.search` (đã bỏ ở v1.18).
3. **Qdrant point id**: phải uuid/int — `qdrant_index._point_id` map chunk_id(sha1) → uuid5.
4. **`load_ke_labels` có `lru_cache`**: đổi knowledge_objects.json phải chạy process mới (test mới load lại).
5. **bge-m3 dim = 1024**: collection Qdrant tạo với size 1024; offline HashEmbedding = 32 (chỉ smoke test).
6. **3 test fail có sẵn từ trước** (`test_chunking` x2, `test_ke_enrichment` x1) — KHÔNG phải do
   Sprint 3, đã xác minh bằng git stash. Đừng tưởng mình làm hỏng.

---

## 5. CHẠY NHANH (smoke, không cần index — để xác nhận môi trường OK)

```bash
# pipeline offline (fallback candidate + nhãn KE), có LLM answer:
python -X utf8 -c "from retrieval.hybrid_search import run_hybrid_search; \
import json; print(json.dumps(run_hybrid_search('resort 5 sao gần biển ở Nha Trang', top_n=3, generate_answer=True)['answer'], ensure_ascii=False, indent=2))"

# eval offline (chưa service):
python -X utf8 -m evaluation.retrieval_metrics.eval_golden
```

## 6. Quy ước git
- Đang ở nhánh `feature/sprint3-ke-index-bridge`. **KHÔNG commit thẳng develop/main** (chủ
  project yêu cầu commit phải được duyệt).
- Embed/index trên ổ trống; KHÔNG commit model/cache/`.docker_volumes`.
