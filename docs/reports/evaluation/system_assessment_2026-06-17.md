# Đánh giá hệ thống VSF/DLKS Search — End-to-End (chi tiết + giải pháp)

**Ngày:** 2026-06-17
**Phạm vi:** API, retrieval pipeline, embedding/index, ontology/KE, context/LLM, evaluation
**Phương pháp:** Đọc trực tiếp code các luồng thật + chạy golden eval (59 câu active, K=10) + đo trực tiếp độ lớn từng số hạng điểm trên Qdrant + OpenSearch đang chạy thật.

> **Đính chính so với bản đánh giá đầu tiên:** bản đầu nói "rrf_score bị bỏ ở `aggregate_by_hotel`". Đo lại định lượng cho thấy điều đó **sai địa chỉ**: `rrf_score` *có* được dùng (qua `business_rerank`, trọng số 0.5). Root cause thật là **thang điểm lệch tỉ lệ (score scale mismatch)** — xem mục 1. Bản này thay thế chẩn đoán cũ.

---

## TL;DR

**Độ khả thi đạt kỳ vọng production: 4.5/10**

Hệ thống chạy end-to-end, kiến trúc tầng vẽ "đúng sách", và ontology/KE thực sự mạnh. Nhưng đo trên golden set + index thật: **toàn bộ tầng retrieval đắt tiền (bge-m3 + Qdrant 13.838 chunk-vector + BM25 520 hotel-doc) chỉ thêm 0.9% recall** so với baseline chỉ-nhãn-KE. Nguyên nhân không phải code chết mà là **lỗi chuẩn hóa điểm**: tín hiệu text retrieval bị review_score chèn ép ~24 lần ở bước fuse. Đây là lỗi sửa được, không phải lỗi thiết kế gốc — nhưng tới khi sửa, hệ thống thực chất là *search bằng nhãn ontology*, không phải *hybrid semantic search*.

---

## Bằng chứng cứng

### A. Golden eval (59 câu active, K=10)

| Cấu hình | Recall@10 | Precision@10 | Hit@10 | MRR |
|---|---|---|---|---|
| **FULL** (vector + BM25 + rerank) | **0.5177** | 0.7051 | 0.9661 | 0.9042 |
| **NO-SERVICE** (chỉ nhãn KE) | **0.5090** | 0.6983 | 0.9492 | 0.8941 |
| **Chênh lệch** | **+0.0087** | +0.0068 | +0.017 | +0.010 |

### B. Đo độ lớn từng số hạng điểm (query "sôi động, nhộn nhịp", 100 candidate)

| Số hạng | Trọng số | Giá trị thực | Đóng góp tối đa vào `business_score` |
|---|---|---|---|
| `rrf_score` (text retrieval) | 0.5 | max **0.0164**, mean 0.0108 | **≈ 0.0082** |
| `review_score`/10 | 0.2 | tới 1.0 | **0.20** |
| `review_count` (log-norm) | 0.1 | tới 1.0 | 0.10 |
| `price_fit` | 0.1 | 0/1 | 0.10 |
| `concept_match` | 0.1 | 0..1 | 0.10 |

**Text retrieval đóng góp tối đa 0.008 trong khi review đóng góp 0.20 — chênh ~24 lần.** Lý do: RRF theo công thức `1/(60+rank)` luôn nằm trong khoảng [0, 0.016], trong khi các feature khác đã chuẩn hóa về [0, 1]. Cộng thẳng hai thang khác cỡ → thang nhỏ bị nuốt.

### C. Bằng chứng hành vi

- **Overlap top-10 giữa 2 query trái ngược** ("sôi động" vs "yên tĩnh nghỉ dưỡng") = **1/10** → ranking *có* phân biệt query, nhưng nhờ `apply_profile_boost` + `concept_match` (tín hiệu **KE**), không nhờ text retrieval.
- **Overlap top-10 ON vs OFF text retrieval** (cùng query) = **8/10** → bật cả vector+BM25 chỉ xáo 2/10 vị trí ở rìa. Đúng khớp với Recall chỉ +0.9%.

→ Kết luận: vector+BM25 hiện chỉ "rung nhẹ" thứ hạng, không đủ lực kéo hotel relevant từ ngoài top-10 vào trong.

---

## Phân tích & giải pháp chi tiết theo từng vấn đề

### Vấn đề 1 — Score scale mismatch: text retrieval bị review_score nuốt ⭐ (đòn bẩy lớn nhất)

**Triệu chứng:** FULL ≈ NO-SERVICE; overlap ON/OFF = 8/10.
**Vị trí:** `retrieval/reranking/fusion.py` → `business_rerank`, dòng `neural = doc.get("fused_score", doc.get("rrf_score", 0.0))` rồi `business_score = 0.5*neural + 0.2*review + ...`.
**Cơ chế:** `rrf_score` raw ∈ [0, 0.016] cộng thẳng với các feature ∈ [0,1]. Sau nhân trọng số, text retrieval max 0.008 vs review 0.20.

**Giải pháp (chuẩn hóa text-signal về [0,1] TRƯỚC khi fuse — min-max trên tập candidate):**

```python
# fusion.py, trong business_rerank, trước vòng for tính business_score:
rrf_vals = [d.get("fused_score", d.get("rrf_score", 0.0)) for d in fused]
rmin, rmax = min(rrf_vals, default=0.0), max(rrf_vals, default=0.0)
def _norm_text(d):
    v = d.get("fused_score", d.get("rrf_score", 0.0))
    return (v - rmin) / (rmax - rmin) if rmax > rmin else 0.0
# ... trong vòng for:
neural = _norm_text(doc)          # thay cho neural = fused_score raw
```

Sau chuẩn hóa, `neural ∈ [0,1]` → đóng góp tối đa 0.5 (đúng như ý đồ trọng số), ngang tầm review.

**Kỳ vọng:** đây là phép thử bản lề — nếu Recall@10 nhảy đáng kể (vd > 0.55) thì hạ tầng vector có giá trị; nếu vẫn ~0.51 thì vấn đề nằm ở recall của tầng candidate (Vấn đề 4), không phải ranking.
**Rủi ro:** min-max nhạy với outlier; nếu thấy bất ổn, đổi sang z-score hoặc rank-based normalization. **Phải chạy lại golden eval sau khi sửa** — không suy đoán.

---

### Vấn đề 2 — Cross-encoder reranker là code chết

**Triệu chứng:** model bge-reranker-v2-m3 (~2GB) chưa từng chạy trong luồng thật.
**Vị trí:** `pipeline.py` gọi `neural_rerank(..., use_model=use_reranker_model)` với mặc định `use_reranker_model=False`; grep toàn repo không nơi nào truyền `True`.
**Hệ quả:** Node 7B luôn rơi xuống fallback keyword-density (`sum(w in text)/len(qwords)`) — gần như vô nghĩa khi `text` rỗng (candidate-doc có `text=""`).

**Giải pháp (2 phần):**

1. **Bật có điều kiện + cache + chỉ rerank top-N** (cross-encoder đắt, không chạy trên toàn bộ fused):
```python
# pipeline.py
reranked = neural_rerank(query, fused, top_k=len(fused),
                         use_model=os.getenv("USE_RERANKER", "0") == "1")
```
Chỉ nên chạy cross-encoder trên ~50 doc đầu đã có `text` thật, không trên candidate-doc rỗng.

2. **Thứ tự đúng:** chạy cross-encoder *sau* khi đã có chunk text thật (sau `_merge_text_signal`), và output của nó (`rerank_score`) phải được đưa vào `business_score` thay cho `neural` — hiện `business_rerank` ghi chú "neural = fused_score (chưa có cross-encoder)" nên dù bật reranker, điểm của nó vẫn không vào business. Cần nối: `neural = doc.get("rerank_score", _norm_text(doc))`.

**Kỳ vọng:** cross-encoder thường +5–15% MRR/nDCG trên câu mô tả. **Đo bằng A/B trên golden** trước khi bật mặc định (chi phí latency: ~50–200ms/query trên GPU, có thể > 1s trên CPU → cân nhắc chỉ bật khi có GPU).

---

### Vấn đề 3 — Candidate rỗng → trả về 0 kết quả

**Triệu chứng:** query không khớp concept/city nào → màn hình trắng.
**Vị trí:** `build_candidates` trả `[]`; trong `pipeline.py`, `fused = _candidates_as_docs([])` = rỗng; BM25/Qdrant coi `candidate_hotel_ids=[]` là "không filter" → search toàn bộ, nhưng `_merge_text_signal` merge vào nền rỗng → 0 doc sống sót.

**Giải pháp (fallback broad semantic search khi candidate rỗng):**
```python
# pipeline.py, sau build_candidates:
if not candidates:
    # Không có hard/concept signal → để vector quyết định, lấy hotel từ chính kết quả text.
    if vector_service is not None:
        vr = vector_service.search(query, candidate_hotel_ids=None, top_k=candidate_pool)["results"]
        candidates = list(dict.fromkeys(h["hotel_id"] for h in vr if h.get("hotel_id")))
    # nếu vẫn rỗng (vector down) → fallback toàn bộ 520 (đừng trả trắng)
    if not candidates:
        candidates = review_top_hotels(cap=candidate_pool)
```
Khi đó base `fused` không rỗng → `_merge_text_signal` có chỗ gắn rrf → kết quả hiển thị.

**Kỳ vọng:** loại bỏ hoàn toàn nhóm "0 kết quả" cho query lạ; đây là điều kiện cần để hệ thống dùng được với truy vấn tự do của người dùng thật.

---

### Vấn đề 4 — Recall trần ~0.52 do thiết kế đo + tầng candidate

**Triệu chứng:** trung bình 17.4 hotel đúng/câu, trả top-10 → recall toán học tối đa ~0.57. Câu nhiều ground-truth:
- GS-021 "HCM gia đình trẻ nhỏ" (40 đúng) → recall 0.20.
- GS-060 "resort sang trọng Phú Quốc tuần trăng mật" (38 đúng) → recall 0.18.

**Phân tích:** đây là vấn đề **kép**, phải tách:
1. *Đo:* Recall@10 với ground-truth 38–40 hotel là chỉ số sai. Nên báo cáo **Recall@20/@50** song song, và thêm **nDCG@10** (quan tâm thứ hạng, không phạt vì không gói hết 40 hotel vào 10 ô).
2. *Thực chất:* khi ground-truth là "mọi resort sang ở Phú Quốc", bài toán là **lọc theo filter**, recall thấp ở K=10 là kỳ vọng được. Câu này không đo được năng lực semantic.

**Giải pháp:**
- Thêm cột Recall@20, Recall@50, nDCG@10, MAP vào `eval_golden.py`.
- Phân loại golden theo `intent_type` (filter-heavy vs semantic) và báo cáo metric **riêng từng nhóm** — gộp chung đang che giấu cả điểm mạnh lẫn điểm yếu.
- Với câu filter-heavy nhiều ground-truth: chấp nhận, hoặc tăng top_n hiển thị.

---

### Vấn đề 5 — Mù với query cảm xúc / ngoài ontology

**Triệu chứng:**
- GS-015 "khách sạn sôi động, nhộn nhịp, nhiều hoạt động" → recall 0.00, hit 0.
- "chỗ yên tĩnh để chữa lành sau chia tay" → chỉ bắt `STYLE_QUIET`, mất sắc thái.

**Phân tích:** đây chính là loại câu mà **vector phải gánh** — nhưng vì Vấn đề 1, vector không đủ lực. Sửa Vấn đề 1 là điều kiện cần. Ngoài ra: candidate cho câu này = toàn bộ 520 (không city) → vector phải phân biệt trong 520, nhưng rrf bị nuốt → thua.

**Giải pháp:**
- Phụ thuộc Vấn đề 1 (chuẩn hóa) + Vấn đề 2 (cross-encoder) — hai cái này trực tiếp cứu nhóm câu này.
- Bổ sung **query expansion bằng concept ontology**: "sôi động" → bơm thêm surface form đồng nghĩa vào BM25 query (đã có synonym_dictionary, chỉ cần nối vào lexical query).
- Cân nhắc **HyDE** (sinh 1 đoạn mô tả giả từ query bằng LLM rồi embed) cho câu cảm xúc — tăng recall vector đáng kể với câu trừu tượng.

---

### Vấn đề 6 — `/context` không grounding theo dữ liệu search (nguy cơ bịa)

**Triệu chứng:** `/context` lấy thẳng `knowledge_object.content` của hotel được click rồi bảo LLM "giải thích vì sao phù hợp".
**Vị trí:** `api/frontend_adapter.py` → `build_hotel_context`.
**Rủi ro:** input chỉ là content marketing của hotel → LLM tâng bốc, không có review thật để cân bằng → vi phạm nguyên tắc "không bịa ngoài ngữ cảnh" dù prompt có dặn.

**Giải pháp:**
- `build_hotel_context` nên kéo **các chunk review/ABSA thật** của hotel đó (đã có trong index/knowledge_objects) làm ngữ cảnh, không chỉ `content`.
- Đưa cả **mặt tiêu cực** (negative aspect từ ABSA) vào context để câu trả lời cân bằng, đáng tin.
- Truyền **query gốc của user** vào (hiện hard-code "Vì sao X phù hợp?") để câu trả lời bám đúng nhu cầu.

---

### Vấn đề 7 — Cấu hình & API rủi ro vận hành

| Vấn đề | Vị trí | Giải pháp |
|---|---|---|
| `.env` `BM25_INDEX=travel_bm25` nhưng index thật `vsf_hotels_bm25_current` (chỉ chạy nhờ default trong `main.py`) | `.env` vs `api/main.py` | Sửa `.env` cho khớp; thêm health-check fail-fast nếu index không tồn tại lúc khởi động (đừng để 503 mơ hồ lúc request). |
| 2 route trùng tên `/search` (GET `search_bm25` + POST `fe_search`) | `api/main.py` | Đổi GET baseline thành `/search/bm25` hoặc gộp; tránh nhầm lẫn contract. |
| Thiếu auth, rate limit, pagination, request-id | `api/main.py` | Thêm trước production: API key/JWT, slowapi rate limit, `offset/limit`, middleware gắn `X-Request-ID` cho trace. |
| Qdrant collection `vectors_count: None, status: grey` | Qdrant `vsf_travel` | Kiểm tra `optimizer_status`; chạy lại optimize/index; xác nhận `status: green` trước khi đo SLA. |
| `allow_origins=["*"]` | CORS | Giới hạn origin thật trước production. |

---

### Vấn đề 8 — Evaluation chưa đủ để bắt regression

**Triệu chứng:** lỗi scale-mismatch tồn tại lâu vì **chưa ai chạy A/B FULL-vs-NO-SERVICE** — chính phép so đó mới phơi bày tầng vector vô dụng.
**Giải pháp:**
- Thêm script A/B (FULL vs NO-SERVICE vs BM25-only vs vector-only) chạy 1 lệnh, in bảng so sánh — biến nó thành **CI gate**: nếu FULL không > NO-SERVICE quá ngưỡng → fail.
- Thêm nDCG@10, Recall@20/@50, MAP (Vấn đề 4).
- Thêm ~10 câu "no-hard-signal" (cảm xúc thuần, không city/concept) vào golden để đo đúng năng lực semantic — hiện golden thiên về câu có filter rõ.
- Log per-query score breakdown (rrf vs review vs concept) để debug ranking nhanh.

---

## Vấn đề MỚI phát hiện sâu (đợt 2 — đào bằng đo thực, chưa ai biết)

> Đợt này tập trung các vùng chưa kiểm tra: cấu trúc index, analyzer, latency, test, embedding. Tất cả số liệu dưới đây là đo trực tiếp trên hệ thống đang chạy.

### Vấn đề 9 — Granularity mismatch: BM25 (document-level) vs Qdrant (chunk-level) ⭐⭐ (lỗi semantic của fusion)

**Phát hiện:** BM25 index `vsf_hotels_bm25_current` có **520 doc = 1 doc/hotel** (field `name/description/amenities/reviews_detail`, text mỗi doc dài **12–14k ký tự** = cả hotel). Qdrant có **13.838 point = chunk nhỏ** (field `text/section/chunk_id` thật). **Hai store không cùng đơn vị truy xuất.**

**Hệ quả:** `reciprocal_rank_fusion` dedupe theo `chunk_id`. BM25 trả `chunk_id="bm25_hotel_<id>"` (tổng hợp, 1/hotel), Qdrant trả chunk_id thật → **không bao giờ trùng nhau** → RRF **không bao giờ cộng dồn điểm** của cùng thực thể từ 2 nguồn. Mà reward "xuất hiện ở cả 2 nguồn" chính là *toàn bộ lý do dùng RRF*. Hiện fusion chỉ là **nối 2 danh sách rank độc lập**, không phải hợp nhất thật.

**Giải pháp (chọn 1):**
- **(A, đúng nhất)** Fuse ở **cấp hotel**: trước RRF, gom kết quả mỗi nguồn về `hotel_id` (lấy rank tốt nhất của hotel trong mỗi nguồn), rồi RRF trên `hotel_id`. Khi đó hotel xuất hiện ở cả BM25 lẫn vector được cộng dồn đúng.
```python
# thay vì RRF trên chunk_id, RRF trên hotel_id:
def _by_hotel_rank(results):
    seen={}
    for rank,d in enumerate(results,1):
        h=d.get("hotel_id")
        if h is not None and h not in seen: seen[h]=(rank,d)
    return [d for _,d in sorted(seen.values())]
# reciprocal_rank_fusion(_by_hotel_rank(bm25), _by_hotel_rank(vector))  với doc_id = hotel_id
```
- **(B)** Index BM25 ở cấp chunk (cùng chunk_id với Qdrant) — nặng hơn, nhưng cho fusion chuẩn cấp chunk.

**Lưu ý:** đây cũng là lý do tiềm ẩn khiến BM25 yếu: 1 doc 14k ký tự làm BM25 length-normalization (b=0.75) phạt nặng, và term "loãng" trong văn bản dài → điểm BM25 kém phân biệt.

---

### Vấn đề 10 — BM25 dùng `analyzer=standard`, KHÔNG phải analyzer tiếng Việt ⭐⭐

**Phát hiện:** mapping field `name/description` đều `analyzer=standard`. Standard analyzer tách token theo khoảng trắng/Unicode, **không hiểu tiếng Việt**: không xử lý từ ghép ("khách sạn" = 2 token rời), không chuẩn hóa dấu, không stem. → BM25 match kém, đặc biệt câu nhiều từ ghép.

**Giải pháp:**
- Cài analyzer tiếng Việt cho OpenSearch (vd plugin `analysis-vietnamese` hoặc ICU + custom) và **reindex** với analyzer đó cho field text.
- Tối thiểu: thêm `icu_tokenizer` + `lowercase` + `asciifolding` (đã có asciifolding giúp match có/không dấu).
- Đồng bộ analyzer giữa lúc index và lúc search (nếu khác → match sai âm thầm).

---

### Vấn đề 11 — Latency p50 ~1.9s/query (chưa tính LLM) → VI PHẠM SLA ⭐⭐⭐

**Phát hiện (đo 5 query, đã warm):** p50 = **1.927ms**, max = 2.369ms — **chưa tính Node 9 (LLM)**. Bóc tách 1 query:

| Stage | Thời gian | Ghi chú |
|---|---|---|
| `parse_intent` | **948ms (cold) / 2ms (warm)** | xem V12 |
| concept lookup | 132ms | |
| hard filter | 165ms | in-memory, có thể tối ưu |
| BM25 search | 311ms | |
| **Vector search** | **1.100ms** | embed 263ms + **Qdrant 840ms** |

**Qdrant 840ms là bất thường** cho 13.838 point. Đo riêng: `with_payload=True` = **244ms** vs `with_payload=False` = **30ms** → kéo full payload làm chậm **8×**. Service đang lấy TOÀN BỘ payload (60+ field: `image_urls`, `parent_text`, `raw_text`...) cho 100 hit/query, trong khi chỉ cần `chunk_id/hotel_id/text/section`.

**Giải pháp:**
```python
# qdrant_service.py search(): chỉ lấy payload cần
self.client.query_points(..., with_payload=["chunk_id","hotel_id","text","section","source_type"])
```
→ Vector search ~1.100ms → **~290ms**. Tổng query (warm) từ ~1.9s → **~1.0s**, còn phòng để tối ưu BM25/filter xuống <500ms.
Production: SLA search thường <300–500ms. Phải xếp việc này ưu tiên cao nếu hướng tới production thật.

---

### Vấn đề 12 — `parse_intent` cold-start 978ms (mỗi worker, request đầu)

**Phát hiện:** `parse_intent` lần đầu = **978ms**, các lần sau = **2ms**. Nguyên nhân: `_load_synonyms` (`lru_cache`) load + parse YAML 177KB / 3.927 synonym lần đầu. Trong API multi-worker, **request đầu của MỖI worker bị +1s**.

**Giải pháp:** preload synonym lúc startup (FastAPI `lifespan`/startup event gọi `_load_synonyms()` + `_max_gram()` một lần), không để lazy theo request đầu. Cân nhắc cache đã-parse ra pickle để load nhanh hơn YAML.

---

### Vấn đề 13 — Test phủ SAI chỗ: 0 test cho fusion/ranking; test_pgvector test sai backend ⭐⭐

**Phát hiện:** 68 test collect được, nhưng **grep `business_rerank|reciprocal_rank|run_hybrid|aggregate_by_hotel` trong tests/ = 0 kết quả**. Toàn bộ tầng quyết định chất lượng (chính chỗ có lỗi scale-mismatch V1 và mismatch V9) **không có một test nào**. Thêm: `test_pgvector_index.py`, `test_pgvector_search.py` test **pgvector** trong khi production dùng **Qdrant** → test xanh nhưng không bảo vệ code chạy thật.

**Giải pháp:**
- Thêm unit test cho `reciprocal_rank_fusion` (doc ở cả 2 nguồn phải > doc ở 1 nguồn — test này sẽ FAIL ngay với V9, phơi bày lỗi), `business_rerank` (scale các số hạng), `aggregate_by_hotel`, và 1 integration test `run_hybrid_search` end-to-end với dữ liệu giả.
- Thêm test cho `qdrant_service` (backend thật) hoặc xóa/đánh dấu skip test pgvector để không gây ảo giác an toàn.
- Biến golden A/B thành smoke test trong CI (V8).

---

### Vấn đề 14 — Qdrant: `indexed_vectors (12.556) < points (13.838)` — 9% chưa index

**Phát hiện:** collection `vsf_travel`: points=13.838 nhưng indexed_vectors=12.556 → **~1.282 vector (9%) nằm trong segment chưa build HNSW index** (`optimizer_status: ok` nhưng status tổng `grey`). Point chưa index vẫn search được (brute-force) nên không lỗi rõ, nhưng: (a) chậm hơn, (b) dấu hiệu optimize chưa hoàn tất.

**Giải pháp:** trigger optimize (`update_collection` với `optimizer_config`, hoặc chờ indexing threshold), xác nhận `indexed_vectors == points` và `status: green` trước khi đo SLA/đưa lên prod.

---

### Vấn đề 15 — Embedding device hard-code `mps` (Mac), không có nhánh CUDA

**Phát hiện:** `indexing/embedding/models.py`: `device = "mps" if mps_available else "cpu"`. Trên Windows máy có GPU NVIDIA, code **luôn rơi về CPU** (embed query 263ms) — bỏ phí GPU. Đây là một phần của latency V11.

**Giải pháp:** `device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")`. Cho phép override qua env `EMBEDDING_DEVICE`.

---

## Đánh giá từng module

| Module | Điểm | Ghi chú |
|---|---|---|
| **Ontology / KE** | 8/10 | Điểm sáng nhất. 3.927 surface form, 520 hotel có nhãn, location tự sinh, xử lý homograph VN, implicit intent. Coverage 520/520/520 đồng bộ cả 3 store (KO/BM25/Qdrant) — điểm cộng. `parse_intent` gần như hoàn hảo trên câu có cấu trúc. Nghịch lý: chính vì KE mạnh nên baseline nhãn-KE đạt 0.509 recall, che giấu việc vector vô dụng. |
| **Retrieval pipeline** | 2.5/10 | Score mismatch (V1) vô hiệu tầng vector; reranker chưa nối (V2); candidate rỗng = 0 kết quả (V3); **fusion không hợp nhất thật do granularity mismatch (V9)**; 0 test cho cả tầng (V13). |
| **Embedding / Index** | 5/10 | Coverage đủ, nhưng **BM25 document-level vs Qdrant chunk-level (V9)**, **BM25 analyzer=standard không hợp tiếng Việt (V10)**, 9% vector chưa index (V14), device không dùng CUDA (V15). |
| **Retrieval latency** | 3/10 | **p50 ~1.9s chưa tính LLM (V11)** — vi phạm SLA search. Phần lớn do Qdrant kéo full payload (+813ms) và cold-start parse_intent (V12). |
| **API** | 5/10 | Chạy được, có Prometheus/CORS/lazy-load/graceful degrade. Nhưng route trùng, .env lệch index, thiếu auth/rate-limit/pagination (V7). |
| **Context / LLM** | 5/10 | Sạch, nhưng `/context` không grounding theo review thật → nguy cơ bịa (V6). |
| **Evaluation** | 5/10 | Golden 70 câu + metric đúng (thứ cứu dự án), nhưng thiếu A/B gate, nDCG, câu semantic thuần (V8), và **0 test cho fusion/ranking, test_pgvector test sai backend (V13)**. |

---

## Lộ trình sửa theo thứ tự đòn bẩy

| # | Việc | Effort | Đòn bẩy | Phụ thuộc |
|---|---|---|---|---|
| 1 | Chuẩn hóa text-signal [0,1] trước fuse (V1) | ~10 dòng | ⭐⭐⭐ Cao nhất | — |
| 2 | RRF hợp nhất ở cấp hotel_id (V9) | ~15 dòng | ⭐⭐⭐ | nên làm cùng #1 |
| 3 | Qdrant chỉ lấy payload cần → cắt ~800ms (V11) | ~3 dòng | ⭐⭐⭐ (SLA) | — |
| 4 | Fallback broad vector khi candidate rỗng (V3) | ~10 dòng | ⭐⭐ | — |
| 5 | Đồng bộ `.env` index + dọn route trùng (V7) | nhỏ | ⭐⭐ (chặn sự cố deploy) | — |
| 6 | Test fusion/ranking + A/B gate CI (V13, V8) | trung bình | ⭐⭐ (bắt regression; test V9 fail ngay) | — |
| 7 | Analyzer tiếng Việt cho BM25 + reindex (V10) | cao (reindex) | ⭐⭐ | — |
| 8 | Nối + bật cross-encoder có điều kiện (V2) | trung bình | ⭐⭐ (sau #1) | #1 |
| 9 | Preload synonym lúc startup (V12) | nhỏ | ⭐ (cold-start) | — |
| 10 | Optimize Qdrant (indexed==points) (V14) | nhỏ | ⭐ | — |
| 11 | Device CUDA path cho embedding (V15) | nhỏ | ⭐ | — |
| 12 | Query expansion + HyDE cho câu cảm xúc (V5) | cao | ⭐ | #1 |
| 13 | `/context` grounding theo review/ABSA thật (V6) | trung bình | ⭐ (chất lượng answer) | — |
| 14 | Auth/rate-limit/pagination/CORS (V7) | trung bình | ⭐ (cần trước prod) | — |

> **Nguyên tắc:** làm #1+#2+#3 cùng đợt (đều nhỏ, đụng cùng vùng fusion + qdrant_service), chạy lại golden eval + đo latency ngay. Con số sau đó quyết định chiến lược còn lại — nếu recall vẫn không cải thiện sau khi đã chuẩn hóa + fuse đúng, bài toán chuyển từ "ranking" sang "recall của tầng candidate".

---

## Tổng hợp 15 vấn đề (tra nhanh)

| # | Vấn đề | Mức | Loại |
|---|---|---|---|
| V1 | Text-signal bị review nuốt do thang lệch ~24× | 🔴 Chí mạng | Ranking |
| V2 | Cross-encoder reranker chưa nối vào điểm | 🟠 Cao | Ranking |
| V3 | Candidate rỗng → 0 kết quả | 🟠 Cao | Recall |
| V4 | Recall@10 sai chỉ số (GT 38–40 hotel) | 🟡 TB | Đo |
| V5 | Mù query cảm xúc / ngoài ontology | 🟠 Cao | Recall |
| V6 | `/context` không grounding → nguy cơ bịa | 🟡 TB | LLM |
| V7 | .env lệch index, route trùng, thiếu auth | 🟡 TB | Vận hành |
| V8 | Eval thiếu A/B gate, nDCG, câu semantic | 🟡 TB | Đo |
| V9 | BM25 doc-level vs Qdrant chunk-level → RRF không hợp nhất | 🔴 Chí mạng | Fusion |
| V10 | BM25 analyzer=standard, không hợp tiếng Việt | 🟠 Cao | Index |
| V11 | Latency p50 ~1.9s (Qdrant full payload) | 🔴 Chí mạng | SLA |
| V12 | parse_intent cold-start 978ms | 🟡 TB | SLA |
| V13 | 0 test fusion/ranking; test pgvector sai backend | 🟠 Cao | Chất lượng |
| V14 | 9% vector chưa index | 🟡 TB | Index |
| V15 | Embedding không dùng CUDA | 🟡 TB | Hiệu năng |
| V16 | BM25 `_source` thiếu field → `GET /search` trả description null | 🟡 TB | API (từ DEEP_CODE_FIRST) |
| V17 | Môi trường không tái lập (requirements thiếu) | 🟠 Cao | Vận hành (từ DEEP_CODE_FIRST) |

> V16, V17 lấy từ `DEEP_CODE_FIRST_PROJECT_AUDIT.md` — xem mục "Đối chiếu" ở cuối báo cáo để biết phần nào của audit đó dùng được, phần nào lỗi thời.

---

## Cách tái lập số liệu

```bash
# Docker (Qdrant + OpenSearch) phải đang chạy
PYTHONPATH=. .venv/Scripts/python.exe -X utf8 -m evaluation.retrieval_metrics.eval_golden

# A/B FULL vs NO-SERVICE: chạy evaluate() có/không vector+bm25 service
#   FULL  : evaluate(vector_service=vec, bm25_service=bm25)
#   NO-SVC: evaluate(vector_service=None, bm25_service=None)
# Index thật: vsf_hotels_bm25_current = 520 hotel-doc; vsf_travel = 13.838 chunk-point (cùng 520 hotel)
# LƯU Ý: BM25_INDEX trong .env hiện sai (travel_bm25) — set vsf_hotels_bm25_current khi đo.
```

**Đo độ lớn số hạng điểm** (để xác nhận V1): in `rrf_score` raw vs `review_score` cho top-N sau `business_rerank` — kỳ vọng thấy rrf ~0.01 vs review ~1.0 (chênh ~24×) như mục B.

---

## Đối chiếu với `DEEP_CODE_FIRST_PROJECT_AUDIT.md` (2026-06-18)

Một audit thứ hai tồn tại trong repo. Tôi đã đối chiếu từng khẳng định lớn của nó với code thật + git history. **Kết luận: audit đó LỖI THỜI / ĐỌC SAI NHÁNH CODE ở các kết luận quan trọng nhất, nhưng ĐÚNG ở tầng hạ tầng/cấu hình.** Phải đọc nó với cảnh báo này — nếu không sẽ kết luận sai rằng dự án "chưa có hybrid retrieval".

### Vì sao audit đó sai phần lớn

Các module mà audit nói "không tồn tại / skeleton only" thực ra đã được commit ở `19cdd43` **(2026-06-16, feat: hybrid pipeline Node 1→9)** — **trước** ngày audit ghi (2026-06-18). Audit hoặc chạy trên bản cũ, hoặc nhìn nhầm file (vd nhìn `scripts/run_eval.py` thay vì `evaluation/retrieval_metrics/eval_golden.py`; nhìn `vector_search/service.py` pgvector thay vì `qdrant_service.py`).

### Bảng đối chiếu khẳng định của audit vs thực tế (đã verify)

| Khẳng định trong DEEP_CODE_FIRST_AUDIT | Thực tế (verify bằng code/chạy) | Phán quyết |
|---|---|---|
| "Hybrid retrieval **không implement**" | `retrieval/hybrid_search/pipeline.py` **188 dòng**, đã chạy golden eval qua nó | ❌ SAI (lỗi thời) |
| "Reranking/fusion **skeleton only**; `fusion.py`, `business_rerank`, `reciprocal_rank_fusion`, `aggregate_by_hotel` **không tìm thấy**" | `retrieval/reranking/fusion.py` **131 dòng**, có đủ 4 hàm đó + `neural_rerank.py` | ❌ SAI (lỗi thời) |
| "Context layer **không implement**, chỉ README+`__init__`" | `context/` có **201 dòng** code; `context_package.py`+`answer_generator.py` chạy được | ❌ SAI (lỗi thời) |
| "Evaluation engine **không implement** (`run_eval.py` NotImplemented)" | `scripts/run_eval.py` ĐÚNG là NotImplemented, NHƯNG `evaluation/retrieval_metrics/eval_golden.py` (**90 dòng**) chạy được — nhìn nhầm file | ⚠️ NỬA ĐÚNG |
| "Code dùng **pgvector**, Qdrant chỉ docs/legacy" | `api/main.py` + pipeline import `qdrant_service` thật; Qdrant đang chạy **13.838 vector** | ❌ SAI (lỗi thời) |
| "API chỉ có `GET /search`" | Có **6 route**: `/health`, `/metrics`, `GET /search`, `GET /hybrid_search`, `POST /search`, `POST /context` | ❌ SAI (lỗi thời) |
| "BM25 analyzer=standard, yếu cho tiếng Việt" | Đúng y hệt **V10** của báo cáo này | ✅ ĐÚNG (trùng ta) |
| "`.env` BM25 index mismatch (`travel_bm25`)" | Đúng y hệt **V7** của ta | ✅ ĐÚNG (trùng ta) |
| "BM25 source fields thiếu (description null, thiếu source_url/amenities/images...)" | Bug thật — `_map_hit` trả `description` nhưng `_source` không gồm; ta CHƯA ghi → **bổ sung V16** | ✅ ĐÚNG (mới) |
| "Golden set cần human review (6 hard-filter mismatch, 46 query thiếu candidate)" | Liên quan **V4/V8**; con số cụ thể hữu ích | ✅ ĐÚNG (bổ trợ) |
| "Thiếu dependency reproducibility (`underthesea`, `prometheus_client`)" | Vấn đề env thật → **bổ sung V17** | ✅ ĐÚNG (mới) |
| "Frontend đi trước backend contract; React chưa có runtime" | Đúng; ngoài phạm vi retrieval của ta nhưng hợp lệ | ✅ ĐÚNG (bổ trợ) |

### Hai vấn đề ĐÚNG mà audit đó phát hiện, ta chưa ghi → thêm vào danh sách

**Vấn đề 16 — BM25 `_source` thiếu field → `/search` baseline trả `description: null` + thiếu metadata hiển thị.**
`DEFAULT_SOURCE_FIELDS` không gồm `description`, `source_url`, `amenities`, `review_count`, `images`, `lat/long`, nhưng `_map_hit()` cố đọc `description`. → endpoint `GET /search` (baseline cũ) trả thẻ nghèo nàn. *Lưu ý:* luồng frontend mới đi qua `POST /search` → `frontend_adapter` lấy metadata từ `ke_labels`/`knowledge_objects` nên **không bị** lỗi này; nhưng `GET /search` baseline thì có. **Giải pháp:** thêm các field vào `DEFAULT_SOURCE_FIELDS` + test khẳng định `description` không null.

**Vấn đề 17 — Môi trường không tái lập được (`requirements.txt` thiếu/không khớp).**
Audit chạy fail vì thiếu `underthesea`, `prometheus_client`. Đây là rủi ro thật cho onboarding/CI: người mới clone về không chạy nổi. **Giải pháp:** pin đầy đủ dependency vào `requirements.txt` (gồm `underthesea`, `prometheus_client`, `sentence-transformers`, `qdrant-client`, `opensearch-py`), thêm smoke test "import được mọi entrypoint", và một lệnh setup tài liệu hóa.

### Bài học rút ra cho team

1. **Hai audit mâu thuẫn nhau là dấu hiệu nguy hiểm.** Bản này dựa trên **chạy code + đo số liệu**; bản DEEP_CODE_FIRST dựa trên đọc tĩnh và (nhiều khả năng) bản cũ hơn. Khi trình bày với mentor, dùng bản này làm trạng thái retrieval hiện tại, và chỉ lấy từ DEEP_CODE_FIRST các điểm hạ tầng/frontend đã đánh dấu ✅ ở trên.
2. **Audit tĩnh không bắt được lỗi chất lượng thật.** DEEP_CODE_FIRST chấm Retrieval 48/100 vì "chưa kết nối", nhưng KHÔNG phát hiện được lỗi nghiêm trọng hơn: pipeline ĐÃ kết nối nhưng tín hiệu vector bị nuốt (V1) và fusion không hợp nhất (V9). Chỉ chạy golden A/B mới lộ ra. → Ưu tiên xây **eval harness chạy được** hơn là viết thêm audit.
3. Điểm tổng "48–55%" của audit đó phản ánh **độ phủ tính năng** (feature completeness), KHÔNG phải **độ khả thi production** (4.5/10 của bản này). Hai thước đo khác nhau: dự án "có gần đủ module" nhưng "module cốt lõi đang chạy sai" — nên đừng nhầm hai con số.
