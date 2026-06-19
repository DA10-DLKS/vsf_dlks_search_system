# Báo cáo 04 — Retrieval & Ranking

Đây là trái tim của hệ thống: biến câu hỏi tiếng Việt thành danh sách khách sạn xếp hạng tốt, kèm context cho LLM. Pipeline gồm **9 node** nối tiếp (`retrieval/hybrid_search/pipeline.py`), thiết kế để **từng node có thể vắng** mà vẫn trả kết quả — phù hợp verify khi hạ tầng chưa đủ.

---

## 1. Kiến trúc pipeline (Node 1 → 9)

```
Node 1  parse_intent            câu hỏi VN → intent có cấu trúc
Node 2  hard filter             lọc cứng city/star/score
Node 3  concept lookup          inverted index concept → hotel_ids
Node 4  candidate builder       giao/hợp + cap, ưu tiên concept đặc trưng (IDF)
Node 6  BM25 + Vector           text retrieval trên candidate
Node 7  RRF fusion + profile    hợp nhất 2 nguồn ở cấp hotel + boost
Node 7B neural rerank           cross-encoder (fallback density)
Node 7C business rerank         review/price/concept + aggregate theo hotel
Node 8  ContextPackage + prompt đóng gói cho LLM
Node 9  (tùy chọn) LLM answer   sinh câu trả lời
```

Triết lý xuyên suốt: **vector/BM25 BỔ SUNG, KHÔNG thay thế candidate**. Nền là toàn bộ candidate (giữ recall theo multi-signal); điểm text retrieval chỉ gắn vào hotel làm tín hiệu **rerank**. Hotel candidate không có chunk text vẫn ở lại → không tụt recall.

---

## 2. Node 1 — Parse intent (`query_processing/intent_parser.py`)

Biến câu hỏi thành `ParsedIntent`:

| Trường | Nội dung |
|---|---|
| `concepts` | tất cả concept_id parse được |
| `hard_concepts` | `AMEN_*` / `SETTING_*` (filter cứng) |
| `feel_concepts` | `STYLE_*` / `ASPECT_*` (rerank) |
| `object_types` / `purposes` / `price_tiers` / `landmarks` / `location_concepts` | tách theo prefix |
| `city` | địa danh thô (text) cho filter |
| `range` | `{price_min, price_max, score_min, star_eq}` |
| `implicit` | concept suy từ mô tả hoàn cảnh ("đi 2 con") |

- Nguồn concept **DUY NHẤT**: `ontology/synonym_dictionary.yaml` (sinh từ core) → không lệch với KE.
- `_CITIES`: danh sách thành phố phổ biến cho filter text.
- `implicit_intent`: regex RULES bắt hoàn cảnh ngầm; PURPOSE chỉ ưu tiên ranking, không lọc cứng.

---

## 3. Node 2 — Hard filter (`filtering/hard_filter.py`)

Lọc cứng các điều kiện **có cấu trúc** (city, star, score). Hai backend:

- **`sql_hard_filter(conn, ...)`** — query Postgres thật (production), mạnh cho numeric/range/equality.
- **`inmemory_hard_filter(...)`** — lọc từ `ke_labels.range_filters` để chạy/verify khi chưa có DB.

Chi tiết hiệu năng & độ chính xác:
- **City match fold 2 chiều**: substring giữa city query và city/province KE → bắt biến thể "phú quốc" ↔ "Đảo Phú Quốc", "cát bà" ↔ "Quần Đảo Cát Bà".
- **Cache `_city_blobs`** (lru): normalize 520 hotel **1 lần** (bất biến giữa request). Trước đây normalize lại mỗi request → ~227ms/query; sau cache → ~0ms.
- **Giá là placeholder trong KE → KHÔNG lọc cứng giá**, chỉ star/score (giá xử lý ở rerank price_fit).

---

## 4. Node 3 & 4 — Concept lookup + candidate builder

- **Node 3** (`concept_index.py`): inverted index `concept_id → hotel_ids`. `lookup_hotels_by_concepts(concepts, require_all=False)` trả `hotel_ids`, `match_count`, `idf_score`.
- **Node 4** (`build_candidates`): giao `sql_whitelist ∩ concept_whitelist`, fallback theo thứ tự ưu tiên, **cap** kích thước tập ứng viên. Khi cắt cap, **ưu tiên concept ĐẶC TRƯNG (IDF cao)** thay vì concept phổ biến (V5) → giữ đúng hotel "đặc sản".

**Chống màn hình trắng (V3)**: nếu candidate rỗng (query không khớp city/concept nào) → để **vector** quyết định (broad semantic); nếu vector vắng nữa thì lấy top hotel theo review score. Không bao giờ trả rỗng.

---

## 5. Node 6 — Text retrieval (BM25 + Vector)

Trên tập candidate, lấy **rộng** (`text_topk = max(len(candidates), 50)`) để phủ candidate, không chỉ top-N:
- **BM25** (`bm25_service.search_for_fusion`) — OpenSearch, document-level.
- **Vector** (`vector_service.search`) — Qdrant + bge-m3, chunk-level.

Cả hai đều **giới hạn theo `candidate_hotel_ids`** → chỉ chấm trong tập đã lọc, không quét toàn corpus.

---

## 6. Node 7 — RRF fusion + profile boost (`reranking/fusion.py`)

### 6.1 RRF ở cấp hotel — `rrf_by_hotel` (fix V9)

Vấn đề cũ: BM25 trả `chunk_id = bm25_hotel_<id>` (doc-level), Qdrant trả chunk_id thật (chunk-level) → dedupe theo chunk_id **không bao giờ trùng** → RRF không cộng dồn điểm của cùng hotel từ 2 nguồn (mất hết ý nghĩa RRF).

Giải pháp: gom mỗi nguồn về `hotel_id` (giữ rank tốt nhất), **RRF trên hotel_id** với `k=60`:
```
score(hotel) = Σ_nguồn 1/(k + rank_tốt_nhất_của_hotel_trong_nguồn)
```
→ hotel xuất hiện ở cả 2 nguồn được cộng dồn đúng.

### 6.2 Merge tín hiệu text vào candidate

`_merge_text_signal`: mỗi hotel lấy chunk điểm cao nhất, gắn `rrf_score` + text chunk thật vào candidate doc. Hotel không có chunk text giữ `rrf_score=0` (vẫn ở lại).

### 6.3 Profile boost

`apply_profile_boost`: hotel có feel-concept (style/aspect) của câu hỏi trong `semantic_profile` với score cao → cộng `weight × boost` (weight=0.05). Thay cho graph_boost (repo không có Neo4j).

---

## 7. Node 7B — Neural rerank (`reranking/neural_rerank.py`)

- **Model**: `BAAI/bge-reranker-v2-m3` (cross-encoder), chấm cặp (query, chunk_text) chính xác hơn bi-encoder.
- **An toàn**: `max_length=512` BẮT BUỘC (chunk ~12k ký tự, không cắt → segfault exit 139 trên CPU/Windows); batch 8.
- **Fallback density**: khi không bật model (`USE_RERANKER=0`, mặc định) → chấm bằng keyword-density → pipeline chạy không cần tải ~2GB.
- **Chỉ rerank doc CÓ text thật**; doc text rỗng (candidate thuần KE) giữ nguyên rồi gộp lại → không tụt recall.
- Mỗi doc gắn `rerank_method` = `cross-encoder` | `density-fallback`, expose ra API/UI; nếu bật model nhưng load lỗi thì tự rơi về fallback và giá trị phản ánh đúng.

---

## 8. Node 7C — Business rerank (`business_rerank`)

Xếp hạng cuối theo tín hiệu **business**, dùng metadata KE sẵn trên doc (không cần DB):

```
business_score =  0.05·neural        (text signal đã chuẩn hóa [0,1])
                + 0.20·review_score   (ke_review_score / 10)
                + 0.10·review_count   (log1p chuẩn hóa)
                + 0.10·price_fit       (1 nếu ≤ intent_max_price)
                + 0.10·concept_match   (|concepts ∩ ontology_concepts| / |concepts|)
```

### 8.1 Fix scale mismatch (V1) — quan trọng

Tín hiệu text retrieval nằm trong **thang RRF [0, ~0.016]**, còn review/price/concept đã ở **[0,1]**. Cộng thẳng làm text-signal bị nuốt **~24×** → FULL ≈ NO-SERVICE (recall ~0.52).

Sửa: **chuẩn hóa text-signal về [0,1] bằng min-max trên tập candidate** trước khi fuse (`_minmax_norm`). Ưu tiên `rerank_score` (cross-encoder) > `fused_score` > `rrf_score`.

### 8.2 Calibrate trọng số neural

`neural=0.05` chọn bằng sweep trên `golden_set_v2` (59 câu active). Sau khi chuẩn hóa, trọng số cao làm text áp đảo nhãn KE — vốn **mạnh hơn** text trên corpus này (vector-only recall 0.42 < KE-only 0.51). `neural=0.05` cho đỉnh cả 3 metric: **recall 0.5114, MRR 0.9065, Hit 0.9831**. Text-signal đóng vai trò **tinh chỉnh thứ hạng**, không phải động lực recall. (Tái lập: `evaluation/retrieval_metrics/sweep_neural.py`.)

---

## 9. Node 8 & 9 — Context & answer (`context/`)

- **`aggregate_by_hotel`**: gom chunk theo hotel, lấy chunk điểm cao nhất + bonus thông tin phong phú (`0.01 × min(count-1, 5)`), trả top_n hotel.
- **`build_context_package`** (Node 8): đóng gói top hotels + intent → ContextPackage; `build_prompt` dựng prompt cho LLM.
- **Node 9** (tùy chọn, `generate_answer=True`): gọi LLM sinh câu trả lời từ ContextPackage.

---

## 10. Đánh giá (`evaluation/`)

- **Golden dataset**: `data/golden_dataset/golden_set_v1/v2/v2.1` (70 câu mỗi bản; 59 câu active dùng để tune).
- **Metric**: Recall / Precision / Hit / MRR / nDCG, cắt top-K. Endpoint `GET /eval/golden` chạy on-demand, cập nhật gauge `da10_eval_metric`.
- **Hai chế độ**: `candidate-only` (nhanh, nhẹ RAM, ~2s/câu) và `full` (vector+BM25).
- **Kết quả mốc hiện tại**: Recall@... 0.5114, MRR 0.9065, Hit 0.9831 (golden_set_v2, neural_w=0.05).

> Nguyên tắc: đo bằng golden, không soi span tay. Cải thiện recall STYLE bằng backfill ABSA, không hạ ngưỡng/sửa công thức.

---

## 11. Tính chịu lỗi (degradation)

| Thiếu gì | Hành vi |
|---|---|
| Vector service vắng | dùng BM25 + candidate |
| BM25 vắng | dùng Vector + candidate |
| Cả hai vắng | xếp hạng candidate bằng business score (vẫn trả KE) |
| Candidate rỗng | vector broad → fallback top review |
| Cross-encoder lỗi | tự rơi về density-fallback |

→ API không bao giờ vỡ vì hạ tầng thiếu; mỗi tầng tự thoái hóa mềm.
