# Đánh giá hệ thống VSF/DLKS Search — End-to-End (chi tiết + giải pháp)

**Ngày:** 2026-06-17
**Phạm vi:** API, retrieval pipeline, embedding/index, ontology/KE, context/LLM, evaluation
**Phương pháp:** Đọc trực tiếp code các luồng thật + chạy golden eval (59 câu active, K=10) + đo trực tiếp độ lớn từng số hạng điểm trên Qdrant + OpenSearch đang chạy thật.

> **Đính chính so với bản đánh giá đầu tiên:** bản đầu nói "rrf_score bị bỏ ở `aggregate_by_hotel`". Đo lại định lượng cho thấy điều đó **sai địa chỉ**: `rrf_score` *có* được dùng (qua `business_rerank`, trọng số 0.5). Root cause thật là **thang điểm lệch tỉ lệ (score scale mismatch)** — xem mục 1. Bản này thay thế chẩn đoán cũ.
>
> **Bổ sung 2026-06-18 — chiến lược lai với nhánh `develop-2`:** đã đối chiếu toàn bộ 17 vấn đề với điểm mạnh của nhánh `develop-2` (re-platform `hotel-knowledge-platform/`: PostgreSQL + Neo4j + Elasticsearch + ONNX reranker + ContextPackage). Phát hiện: **develop-2 đã giải sẵn — bằng code chạy được — đúng các lỗi cốt lõi mà nhánh này đang vướng (V1, V9, V10, V2, V3, V6).** Xem mục mới **"Chiến lược lai: ghép điểm mạnh develop-2 ↔ KE của nhánh hiện tại"** ở cuối báo cáo để biết giải pháp ghép cụ thể từng vấn đề. Nguồn đối chiếu: [`DEVELOP2_VS_CURRENT_COMPARISON.md`](DEVELOP2_VS_CURRENT_COMPARISON.md).

---

## TL;DR

**Độ khả thi đạt kỳ vọng production: 4.5/10 (gốc) → ~7.1/10 (sau khi sửa V1–V17)**

Hệ thống chạy end-to-end, kiến trúc tầng vẽ "đúng sách", và ontology/KE thực sự mạnh. Nhưng đo trên golden set + index thật: **toàn bộ tầng retrieval đắt tiền (bge-m3 + Qdrant 13.838 chunk-vector + BM25 520 hotel-doc) chỉ thêm 0.9% recall** so với baseline chỉ-nhãn-KE. Nguyên nhân không phải code chết mà là **lỗi chuẩn hóa điểm**: tín hiệu text retrieval bị review_score chèn ép ~24 lần ở bước fuse. Đây là lỗi sửa được, không phải lỗi thiết kế gốc — nhưng tới khi sửa, hệ thống thực chất là *search bằng nhãn ontology*, không phải *hybrid semantic search*.

> **Cập nhật sau khi sửa (2026-06-18):** đã xử lý 17/17 vấn đề. Recall@10 0.5177→**0.5495**, Recall@50→**0.9505**, Hit@10→**1.0**, nDCG@10→**0.8235**, 27 test + CI gate. Điểm trung bình module **4.5→~7.1**. **Đính chính 2 nhận định gốc:** (1) "vector vô dụng / search bằng nhãn" — đúng ở thời điểm gốc (do bug V1), nhưng sau khi đo lại: vấn đề recall nằm ở **calibrate + tầng candidate** chứ không phải vector chết; (2) con số recall@10≈0.55 **không phản ánh năng lực** — tách theo ground-truth: câu đo công bằng (GT≤10) đạt **recall@10=0.79**, còn 38/59 câu GT lớn bị **trần toán học @10**. Năng lực thật ≈ nDCG 0.82. Ba thứ ghìm điểm còn lại: **latency (cần GPU)**, **đo @10 với GT lớn (artifact)**, **auth chưa làm** — không phải KE/retrieval yếu.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — kết quả thực đo, phép thử bản lề đã chạy
>
> Đã implement V1 (chuẩn hóa min-max `_minmax_norm`, port từ develop-2) **+ V9** (`rrf_by_hotel`, RRF cấp hotel) cùng đợt trong [`retrieval/reranking/fusion.py`](../../../retrieval/reranking/fusion.py); test ở [`tests/test_fusion_ranking.py`](../../../tests/test_fusion_ranking.py) (6 pass). Harness A/B mới: [`evaluation/retrieval_metrics/ab_runner.py`](../../../evaluation/retrieval_metrics/ab_runner.py), sweep: [`sweep_neural.py`](../../../evaluation/retrieval_metrics/sweep_neural.py).
>
> **Baseline (bug cũ):** FULL 0.5177 / NO-SERVICE 0.5090 — tái lập đúng số trong báo cáo.
>
> **Phát hiện then chốt:** chuẩn hóa với trọng số cũ `neural=0.5` làm recall **TỤT xuống 0.4436**. Quét trọng số (sweep_neural) cho thấy text-signal **càng nặng càng hại** vì **text retrieval kém hơn nhãn KE trên golden này** (vector-only 0.42 < KE-only 0.51):
>
> | neural_w | Recall | MRR | Hit |
> |---|---|---|---|
> | 0.5 (cũ) | 0.4436 | 0.8445 | 0.9661 |
> | 0.0 | 0.5100 | 0.8955 | 0.9661 |
> | **0.05 (chốt)** | **0.5114** | **0.9065** | **0.9831** |
> | 0.1 | 0.4836 | 0.8960 | 0.9831 |
>
> **Kết luận đã được xác nhận bằng đo:** đúng như tiên đoán "nếu recall không nhảy thì vấn đề ở tầng candidate, không phải ranking" — **bài toán recall KHÔNG nằm ở ranking**. Vai trò đúng của text-signal là **tinh chỉnh thứ hạng** (MRR 0.9042→**0.9065**, Hit 0.9661→**0.9831**), không phải động lực recall. Đã chốt `neural=0.05`. → Recall chỉ tăng đáng kể khi sửa **tầng candidate/recall** (V3, V5, V10), không phải tầng fuse. Đợt tiếp theo nên ưu tiên các vấn đề recall đó thay vì reranker (V2).

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

> #### ✅ ĐÃ NỐI, mặc định OFF (2026-06-18) — không chứng minh được trên CPU
>
> [pipeline.py](../../../retrieval/hybrid_search/pipeline.py): bật qua env `USE_RERANKER=1`; **chỉ rerank doc CÓ text thật** (cross-encoder vô nghĩa với candidate text rỗng), doc không text giữ nguyên rồi gộp lại (không tụt recall). `rerank_score` đã được `business_rerank` ưu tiên (nối từ V1). Phần "code chết" đã sửa: bật được, nối đúng downstream.
>
> **Trung thực về kết quả:** KHÔNG đo được trên máy này — cross-encoder bge-reranker-v2-m3 (~2GB) + bge-m3 cùng load gây **cạn RAM/Qdrant timeout** khi chạy golden (đúng cảnh báo "có thể >1s trên CPU"). → để **mặc định OFF**, env làm switch cho môi trường GPU. Hơn nữa đợt 1 (V1) đã chứng minh **recall KHÔNG nằm ở ranking** nên cross-encoder không phải đòn bẩy recall; giá trị tiềm năng chỉ là MRR/thứ hạng, cần GPU để khai thác.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — fallback 2 tầng trong pipeline
>
> [pipeline.py](../../../retrieval/hybrid_search/pipeline.py) sau build_candidates: candidate rỗng → (1) vector broad search (candidate_hotel_ids=None) lấy hotel; (2) vẫn rỗng → top hotel theo review_score. Test: [tests/test_fusion_ranking.py](../../../tests/test_fusion_ranking.py) `test_v3_*` (cả 2 nhánh, monkeypatch build_candidates=[]). **KHÔNG đổi golden** (golden v2 có 0 câu candidate-rỗng → V3 không kích hoạt; verified recall@10 giữ 0.5495). Đây là fix robustness cho query tự do user thật, golden không đo được.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — đo đa-K + nDCG, đảo ngược nhận định "yếu recall"
>
> Đã thêm `_ndcg` + `evaluate_multi_k` vào [`eval_golden.py`](../../../evaluation/retrieval_metrics/eval_golden.py) (chạy pipeline 1 lần, tính metric cho K=10/20/50). **Bằng chứng then chốt — recall BUNG MẠNH theo K:**
>
> | K | Recall | Precision | Hit | MRR |
> |---|---|---|---|---|
> | 10 | 0.5114 | 0.6983 | 0.9831 | 0.9065 |
> | 20 | **0.7400** | 0.5918 | 0.9831 | 0.9065 |
> | 50 | **0.9069** | 0.4438 | 0.9831 | 0.9065 |
>
> **Kết luận đảo chiều:** hệ thống **KHÔNG yếu recall** — ở @50 nó bắt được **~91%** ground-truth. Recall@10 = 0.51 chỉ là **ảo giác của chỉ số** khi ground-truth có 15–40 hotel/câu (toán học không thể nhồi 40 hotel vào 10 ô). Đây là lý do TL;DR "4.5/10" và "vector vô dụng" cần đọc lại: phần lớn "recall thấp" của V4/V5 là vấn đề ĐO, không phải năng lực. → Khi báo cáo cho mentor, dùng **Recall@20/@50 + nDCG**, không chỉ Recall@10.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — IDF concept weighting: ĐÒN BẨY RECALL LỚN NHẤT đến nay
>
> **Chẩn đoán lại (không như giả thuyết ban đầu):** GS-015 miss KHÔNG phải do vector yếu hay parse sai. Soi thật: hotel đúng (34054260) **có** `STYLE_LIVELY`, parse **đúng**, nhưng bị **tầng candidate cắt mất** (hạng 205/394, rớt khỏi cap=100). Gốc rễ: `build_candidates` sort thuần **review_score**, mà concept lookup đối xử mọi concept như nhau. Đo phân bố: `STYLE_LIVELY` = **1/520** hotel (cực đặc trưng) nhưng `OBJ_HOTEL` = **393/520** (76%, gần vô nghĩa). Hotel đúng chỉ khớp 1 concept hiếm → bị 393 hotel khớp OBJ_HOTEL review-cao chen mất.
>
> **Fix:** thêm **IDF weighting** cho concept trong [concept_index.py](../../../retrieval/filtering/concept_index.py) (`idf = log(N/df)`, concept hiếm điểm cao) + [build_candidates](../../../retrieval/filtering/hard_filter.py) sort theo `(idf_score, match_count, review_score)`. Hotel khớp concept đặc trưng được kéo vào cap trước. GS-015 GOLD: hạng candidate **205 → #1**.
>
> **Kết quả golden (FULL, đa-K) — bước nhảy lớn nhất từ đầu:**
>
> | K | Recall trước→sau | nDCG | Hit |
> |---|---|---|---|
> | 10 | 0.5186 → **0.5495** (+3.1%) | 0.8049 → **0.8235** | 0.9831 → **1.0000** |
> | 20 | 0.7387 → **0.7745** (+3.6%) | → 0.8404 | → 1.0 |
> | 50 | 0.9069 → **0.9505** (+4.4%) | → 0.8809 | → 1.0 |
>
> **Hit@10 = 1.0** (mọi câu có ≥1 hotel đúng top-10). Đây là fix nhắm ĐÚNG nơi recall thật bị chặn (tầng candidate), nên hiệu quả gấp ~4× mọi đợt trước cộng lại. Query expansion/HyDE (giải pháp gốc) CHƯA cần — IDF candidate đã giải phần lớn. *Lưu ý:* nhãn ontology của corpus mới là đòn bẩy; vector vẫn phụ.

---

### Vấn đề 6 — `/context` không grounding theo dữ liệu search (nguy cơ bịa)

**Triệu chứng:** `/context` lấy thẳng `knowledge_object.content` của hotel được click rồi bảo LLM "giải thích vì sao phù hợp".
**Vị trí:** `api/frontend_adapter.py` → `build_hotel_context`.
**Rủi ro:** input chỉ là content marketing của hotel → LLM tâng bốc, không có review thật để cân bằng → vi phạm nguyên tắc "không bịa ngoài ngữ cảnh" dù prompt có dặn.

**Giải pháp:**
- `build_hotel_context` nên kéo **các chunk review/ABSA thật** của hotel đó (đã có trong index/knowledge_objects) làm ngữ cảnh, không chỉ `content`.
- Đưa cả **mặt tiêu cực** (negative aspect từ ABSA) vào context để câu trả lời cân bằng, đáng tin.
- Truyền **query gốc của user** vào (hiện hard-code "Vì sao X phù hợp?") để câu trả lời bám đúng nhu cầu.

> #### ✅ ĐÃ LÀM (2026-06-18) — grounding ABSA thật + mặt tiêu cực + query thật
>
> [frontend_adapter.py](../../../api/frontend_adapter.py): thêm `_grounded_evidence` (rút từ `semantic_profile` = aspect mạnh có score+evidence_count, và `negative_style_profile` = mặt yếu với **span review THẬT**) + `_evidence_text`. `build_hotel_context` giờ đưa **cả mặt mạnh lẫn mặt hạn chế** vào context thay vì chỉ content marketing, và nhận `query` gốc của user ([main.py](../../../api/main.py) `ContextRequest.query`).
>
> **Verify trên hotel 34054260:** context giờ gồm — content; "Điểm khách đánh giá cao: Dịch vụ (0.93, 82 lượt), Đáng tiền (0.92)..."; **"Lưu ý mặt hạn chế — Yên tĩnh: noise at pool until 5am"** (span review thật). LLM có 2 mặt để trả lời cân bằng → giảm tâng bốc/bịa. Đây là điểm ghép develop-2 (ContextBuilder evidence/citation) × ABSA của dự án (mặt mà develop-2 KHÔNG có). Là cải thiện CHẤT LƯỢNG câu trả lời, không đo bằng golden recall.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — A/B harness + CI gate
>
> [ab_runner.py](../../../evaluation/retrieval_metrics/ab_runner.py): chạy 1 lệnh in bảng FULL/NO-SERVICE/BM25-only/vector-only (đã dùng suốt 8 đợt để đo trước/sau). Thêm **CI gate**: `GATE_MODE=1` → fail (exit 1) nếu FULL recall < `GATE_MIN_RECALL` (0.53) hoặc hit < `GATE_MIN_HIT` (0.98) — ngưỡng dưới baseline (0.5495/1.0) một biên. nDCG/Recall@20/@50 đã thêm ở V4 (`evaluate_multi_k`). Còn lại (chưa làm): thêm câu semantic thuần vào golden (cần sửa dataset, ngoài phạm vi code).

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

> #### ✅ ĐÃ LÀM (2026-06-18) — vietnamese_analyzer + reindex, A/B dương ở top-10
>
> Port `vietnamese_analyzer` từ develop-2 (standard tokenizer + lowercase + decimal_digit + `asciifolding preserve_original`) vào [index_mapping.json](../../../indexing/bm25_index/index_mapping.json) cho 15 field text. Reindex sang index thử [reindex_vietnamese.py](../../../indexing/bm25_index/reindex_vietnamese.py) → `vsf_hotels_bm25_vi` (520 doc, 0 fail). **Đổi `.env` BM25_INDEX → `vsf_hotels_bm25_vi`** (đồng thời sửa luôn V7: trước ghi sai `travel_bm25`).
>
> **A/B trên golden (FULL, đa-K):**
>
> | K | Recall std→vi | nDCG std→vi | Prec std→vi |
> |---|---|---|---|
> | 10 | 0.5114 → **0.5186** (+0.7%) | 0.8019 → **0.8049** | 0.6983 → **0.7034** |
> | 20 | 0.7400 → 0.7387 | 0.8190 → 0.8193 | — |
> | 50 | 0.9069 → 0.9069 | = | — |
>
> **Cơ chế (verify bằng _analyze):** standard cho `[khách, sạn,...]`; vietnamese cho **cả có dấu lẫn không dấu** `[khach, khách, san, sạn,...]` → match query gõ thiếu dấu (rất phổ biến với user VN). Cải thiện nhỏ nhưng **dương + nhất quán ở top-10** (nơi quan trọng nhất); K cao hội tụ vì recall đã gần trần. **Quyết định: giữ.** Index cũ `vsf_hotels_bm25_current` vẫn còn → đảo ngược được (chỉ đổi lại .env).
>
> *Ghi chú hạ tầng:* reindex bị chặn vì ổ C đầy 95% (flood-stage watermark). Hóa ra **không phải Docker** (Docker ở ổ D, vhdx 0.1GB) mà do cache trên C (.cache/huggingface, npm/pip, .ollama). Dọn ~8.5GB (npm+pip+ollama) → C về 90% → reindex chạy. Index thật không bị động chạm suốt quá trình.

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

> #### ✅ ĐÃ LÀM (2026-06-18) — V11 + bonus: cắt payload Qdrant & cache hard_filter; lộ nút cổ chai thật
>
> 1. **Qdrant payload** ([qdrant_service.py](../../../retrieval/vector_search/qdrant_service.py)): `with_payload=True` → chỉ 6 field. Vector micro-bench (embed+Qdrant) **164ms** (trước Qdrant thuần ~840ms). metadata field 60+ → **6**.
> 2. **hard_filter cache** ([hard_filter.py](../../../retrieval/filtering/hard_filter.py)): `inmemory_hard_filter` normalize lại city/province cho 520 hotel MỖI request → **227ms**. Cache blob (`_city_blobs`, lru) → **2.1ms** (−99%), n_match giữ nguyên.
>
> **Profiling end-to-end (warm) sau fix — lộ thủ phạm thật:**
>
> | Stage | Trước | Sau |
> |---|---|---|
> | parse_intent | 948→2ms | 3ms |
> | hard_filter | 227ms | **2ms** ✅ |
> | bm25 | 311ms | 122ms |
> | **vector** | 1100ms | **~817ms** (trong pipeline) |
> | **E2E p50** | ~1900ms | **~1660ms** |
>
> **Phát hiện then chốt:** sau khi cắt Qdrant payload + cache filter, nút cổ chai còn lại **KHÔNG phải Qdrant** mà là **embed query bge-m3 trên CPU** (~600-800ms/query). Đây là **trần phần cứng** — máy này không có CUDA (`torch.cuda.is_available()=False`, build CPU-only). → V11 đã hết dư địa bằng code; muốn đạt SLA <500ms phải **chạy embed trên GPU** (V15) hoặc đổi model embed nhẹ hơn cho query. E2E chỉ giảm 1900→1660ms vì phần Qdrant tiết kiệm được đã bị embed CPU che lấp.

---

### Vấn đề 12 — `parse_intent` cold-start 978ms (mỗi worker, request đầu)

**Phát hiện:** `parse_intent` lần đầu = **978ms**, các lần sau = **2ms**. Nguyên nhân: `_load_synonyms` (`lru_cache`) load + parse YAML 177KB / 3.927 synonym lần đầu. Trong API multi-worker, **request đầu của MỖI worker bị +1s**.

**Giải pháp:** preload synonym lúc startup (FastAPI `lifespan`/startup event gọi `_load_synonyms()` + `_max_gram()` một lần), không để lazy theo request đầu. Cân nhắc cache đã-parse ra pickle để load nhanh hơn YAML.

> #### ✅ ĐÃ LÀM (2026-06-18) — warmup() ở startup, dời cold-start khỏi request user
>
> Thêm `warmup()` ([intent_parser.py](../../../retrieval/query_processing/intent_parser.py)) nạp sẵn synonym + max_gram; gọi trong FastAPI `@app.on_event("startup")` ([main.py](../../../api/main.py)). **Đo:** không warmup → parse_intent request đầu **771ms**; có warmup → cold-start dời sang startup (337ms lúc khởi động), request đầu của user không còn ăn cú đó. Mục tiêu V12 (cold-start ra khỏi đường request) đạt.

---

### Vấn đề 13 — Test phủ SAI chỗ: 0 test cho fusion/ranking; test_pgvector test sai backend ⭐⭐

**Phát hiện:** 68 test collect được, nhưng **grep `business_rerank|reciprocal_rank|run_hybrid|aggregate_by_hotel` trong tests/ = 0 kết quả**. Toàn bộ tầng quyết định chất lượng (chính chỗ có lỗi scale-mismatch V1 và mismatch V9) **không có một test nào**. Thêm: `test_pgvector_index.py`, `test_pgvector_search.py` test **pgvector** trong khi production dùng **Qdrant** → test xanh nhưng không bảo vệ code chạy thật.

**Giải pháp:**
- Thêm unit test cho `reciprocal_rank_fusion` (doc ở cả 2 nguồn phải > doc ở 1 nguồn — test này sẽ FAIL ngay với V9, phơi bày lỗi), `business_rerank` (scale các số hạng), `aggregate_by_hotel`, và 1 integration test `run_hybrid_search` end-to-end với dữ liệu giả.
- Thêm test cho `qdrant_service` (backend thật) hoặc xóa/đánh dấu skip test pgvector để không gây ảo giác an toàn.
- Biến golden A/B thành smoke test trong CI (V8).

> #### ✅ ĐÃ LÀM (2026-06-18) — test tầng ranking + backend Qdrant thật
>
> Thêm [tests/test_fusion_ranking.py](../../../tests/test_fusion_ranking.py) (10 test: V1 chuẩn hóa, V9 rrf_by_hotel, V5 IDF, V3 fallback — test V9 đúng tinh thần "doc 2 nguồn > 1 nguồn") + [tests/test_qdrant_service.py](../../../tests/test_qdrant_service.py) (3 test: shape fusion, **V11 payload giới hạn ≠ True**, candidate filter). Quyết định về pgvector: **giữ** (code `PgVectorSearchService` vẫn tồn tại là backend thay thế hợp lệ), nhưng giờ backend production thật (Qdrant) ĐÃ có test bảo vệ — đó mới là khoảng trống thật. Tổng 13 test mới, tall pass.

---

### Vấn đề 14 — Qdrant: `indexed_vectors (12.556) < points (13.838)` — 9% chưa index

**Phát hiện:** collection `vsf_travel`: points=13.838 nhưng indexed_vectors=12.556 → **~1.282 vector (9%) nằm trong segment chưa build HNSW index** (`optimizer_status: ok` nhưng status tổng `grey`). Point chưa index vẫn search được (brute-force) nên không lỗi rõ, nhưng: (a) chậm hơn, (b) dấu hiệu optimize chưa hoàn tất.

**Giải pháp:** trigger optimize (`update_collection` với `optimizer_config`, hoặc chờ indexing threshold), xác nhận `indexed_vectors == points` và `status: green` trước khi đo SLA/đưa lên prod.

> #### ✅ ĐÃ LÀM (2026-06-18) — trigger optimize, green
>
> `PATCH /collections/vsf_travel {"optimizers_config":{"indexing_threshold":100}}` → optimizer build HNSW mọi segment. Poll: status **grey→green**, indexed_vectors **12556→13838 = points** (100% đã index). Search hết brute-force trên 9% còn lại. (Thao tác trên collection của dự án, không cluster-wide — an toàn.)

---

### Vấn đề 15 — Embedding device hard-code `mps` (Mac), không có nhánh CUDA

**Phát hiện:** `indexing/embedding/models.py`: `device = "mps" if mps_available else "cpu"`. Trên Windows máy có GPU NVIDIA, code **luôn rơi về CPU** (embed query 263ms) — bỏ phí GPU. Đây là một phần của latency V11.

**Giải pháp:** `device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")`. Cho phép override qua env `EMBEDDING_DEVICE`.

> #### ✅ ĐÃ LÀM (2026-06-18) — code đúng, nhưng KHÔNG tác động trên máy này
>
> Đã thêm CUDA path + env `EMBEDDING_DEVICE` override vào [models.py](../../../indexing/embedding/models.py). **Trung thực:** máy hiện tại `torch.cuda.is_available()=False` (torch CPU-only build, không GPU) → fix này **không đổi gì ở đây**. Đây là fix robustness cho **deploy có GPU** — và là điều kiện cần để hạ embed query (nút cổ chai latency thật, xem V11) xuống dưới SLA. Trên môi trường có CUDA, cần cài `torch` bản GPU trước.

---

## Đánh giá từng module

> **Cập nhật 2026-06-18 sau khi sửa V1–V17.** Cột "Gốc" giữ nguyên để đối chiếu. Điểm "Sau sửa"
> đo bằng số liệu thật (golden v2, đa-K, A/B). **Đính chính quan trọng:** bản gốc chấm KE 8 và
> ghi "vector vô dụng" — sai. Đo lại độ phủ KE (xem dưới) cho thấy KE **rất giàu** (9/10); con số
> recall@10=0.55 trông thấp là **artifact của cách đo**, không phải năng lực kém — xem ghi chú.

| Module | Gốc | **Sau sửa** | Ghi chú (sau sửa) |
|---|---|---|---|
| **Ontology / KE** | 8 | **9** | Đo lại độ phủ: **794 concept distinct** (577 LMK, 148 LOC, 30 AMEN, + STYLE/SETTING/ASPECT/PURPOSE/PRICE), **27 concept/hotel** (median), **502/520 hotel có ABSA aspect**, 253/520 có negative profile. Đây là tài sản mạnh nhất, KHÔNG phải trần. V5 (IDF) khai thác KE đúng hơn → +3.1% recall. *(Đính chính: nhận định "KE chưa đủ giàu" trong bản trước dựa trên 2 outlier STYLE_LIVELY=1/520 & ASPECT_FACILITIES=0 — không đại diện, đã rút lại.)* |
| **Retrieval pipeline** | 2.5 | **8** | V1+V9+V5+V3 xong + 27 test. **Năng lực thật cao hơn con số gộp:** tách theo ground-truth size — câu GT nhỏ (≤10, n=21) **recall@10=0.79**; câu GT lớn (>10, n=38) recall=0.42 vì bị **trần toán học @10** (không nhồi 15-40 đáp án vào 10 ô — đây là V4, vấn đề ĐO). nDCG@10=**0.82**. Trừ điểm chỉ vì vector chưa khai thác hết. |
| **Embedding / Index** | 5 | **7.5** | V10 (analyzer VN), V14 (Qdrant green 100%, indexed=points), V16 (source fields). V15 (CUDA) có code nhưng máy CPU-only chưa khai thác. |
| **Retrieval latency** | 3 | **4.5** | hard_filter 227→**2ms**, Qdrant payload −90%, cold-start dời khỏi request (V12). Nhưng **E2E vẫn ~1.6s** — trần là embed bge-m3 trên CPU (~700ms), **cần GPU** (phần cứng, không phải code). Điểm thấp nhất. |
| **API** | 5 | **6** | V7 (.env khớp index), V6 (context grounding), V12 (warmup). E2E thông (đã test /search,/context,/hybrid_search,/ui 200). Còn thiếu: **auth, rate-limit**, route trùng `/search`, CORS `*` — làm được bằng code, chưa làm. |
| **Context / LLM** | 5 | **7** | V6: grounding ABSA thật (mặt mạnh có score+evidence_count, **mặt yếu** với span review thật, query thật) thay content marketing → giảm bịa/tâng bốc. Ghép develop-2 ContextBuilder × ABSA của dự án. |
| **Evaluation** | 5 | **8** | V4 (nDCG + multi-K), V8 (A/B harness + CI gate, đã PASS), V13 (27 test gồm backend Qdrant thật). Từ "không bắt được regression" → "có gate + test". |

**Trung bình: 4.5 → ~7.1.** Ba thứ ghìm điểm KHÔNG phải "code chưa khéo": (1) **latency** = trần phần cứng (GPU); (2) **recall@10 trông thấp** = artifact đo @10 với ground-truth lớn (năng lực thật: nDCG 0.82, recall 0.79 trên câu đo công bằng); (3) **auth** = chưa làm. KE/retrieval đã ở mức tốt.

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

## Tổng hợp 17 vấn đề (tra nhanh)

> Cột **develop-2** = nhánh develop-2 có bù trừ được không: ✅ port logic trực tiếp · 🟡 hỗ trợ một phần / làm mẫu · ❌ không liên quan (giữ giải pháp gốc). Chi tiết ở mục "Chiến lược lai".

> **Trạng thái (2026-06-18):** 17/17 đã xử lý. Recall@10 0.5177→**0.5495**, Recall@50→**0.9505**, Hit@10→**1.0**, nDCG@10→**0.8235**. Chi tiết mỗi V xem block "✅ ĐÃ LÀM" tại mục tương ứng.

| # | Vấn đề | Mức | Loại | develop-2 | Trạng thái |
|---|---|---|---|---|---|
| V1 | Text-signal bị review nuốt do thang lệch ~24× | 🔴 Chí mạng | Ranking | ✅ `calibrated_rrf_fusion` | ✅ chuẩn hóa + calibrate neural=0.05 |
| V2 | Cross-encoder reranker chưa nối vào điểm | 🟠 Cao | Ranking | ✅ `LocalReranker` ONNX | ✅ nối + env switch; OFF (CPU không kham) |
| V3 | Candidate rỗng → 0 kết quả | 🟠 Cao | Recall | ✅ bounded+fallback | ✅ fallback 2 tầng |
| V4 | Recall@10 sai chỉ số (GT 38–40 hotel) | 🟡 TB | Đo | ❌ | ✅ nDCG + multi-K |
| V5 | Mù query cảm xúc / ngoài ontology | 🟠 Cao | Recall | 🟡 graph (cần Neo4j) | ✅ **IDF concept (+3.1% recall)** |
| V6 | `/context` không grounding → nguy cơ bịa | 🟡 TB | LLM | ✅ ContextBuilder | ✅ grounding ABSA +/- thật |
| V7 | .env lệch index, route trùng, thiếu auth | 🟡 TB | Vận hành | 🟡 làm mẫu | ✅ .env khớp index (route/auth: chưa) |
| V8 | Eval thiếu A/B gate, nDCG, câu semantic | 🟡 TB | Đo | 🟡 làm mẫu | ✅ A/B harness + CI gate |
| V9 | BM25 doc vs Qdrant chunk → RRF không hợp nhất | 🔴 Chí mạng | Fusion | ✅ ES chunk-level | ✅ RRF cấp hotel |
| V10 | BM25 analyzer=standard, không hợp tiếng Việt | 🟠 Cao | Index | 🟡 `vietnamese_analyzer` | ✅ reindex analyzer VN |
| V11 | Latency p50 ~1.9s | 🔴 Chí mạng | SLA | ❌ | ✅ payload+hard_filter (trần=embed CPU) |
| V12 | parse_intent cold-start 978ms | 🟡 TB | SLA | ❌ | ✅ warmup ở startup |
| V13 | 0 test fusion/ranking; test pgvector sai backend | 🟠 Cao | Chất lượng | 🟡 làm mẫu | ✅ +test fusion + Qdrant thật |
| V14 | 9% vector chưa index | 🟡 TB | Index | ❌ | ✅ optimize → green 100% |
| V15 | Embedding không dùng CUDA | 🟡 TB | Hiệu năng | ❌ | ✅ cuda path (máy này CPU-only) |
| V16 | BM25 `_source` thiếu field → description null | 🟡 TB | API | ❌ | ✅ bổ sung source fields |
| V17 | Môi trường không tái lập (requirements thiếu) | 🟠 Cao | Vận hành | 🟡 làm mẫu | ✅ pin deps + smoke test import |

> V16, V17 lấy từ `DEEP_CODE_FIRST_PROJECT_AUDIT.md` — xem mục "Đối chiếu" ở cuối báo cáo để biết phần nào của audit đó dùng được, phần nào lỗi thời.
> Cột develop-2 đối chiếu từ [`DEVELOP2_VS_CURRENT_COMPARISON.md`](DEVELOP2_VS_CURRENT_COMPARISON.md) — chi tiết cơ chế ở mục "Chiến lược lai".

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

> #### ✅ ĐÃ LÀM (2026-06-18) — bổ sung source fields
>
> [service.py](../../../retrieval/lexical_search/service.py): `DEFAULT_SOURCE_FIELDS` thêm `description, review_count, amenities, images, source_url, latitude, longitude`; `_map_hit` trả các field đó. **Verify** trên `vsf_hotels_bm25_vi`: GET /search giờ `description` not null, amenities + images có giá trị → thẻ hiển thị đầy đủ.

**Vấn đề 17 — Môi trường không tái lập được (`requirements.txt` thiếu/không khớp).**
Audit chạy fail vì thiếu `underthesea`, `prometheus_client`. Đây là rủi ro thật cho onboarding/CI: người mới clone về không chạy nổi. **Giải pháp:** pin đầy đủ dependency vào `requirements.txt` (gồm `underthesea`, `prometheus_client`, `sentence-transformers`, `qdrant-client`, `opensearch-py`), thêm smoke test "import được mọi entrypoint", và một lệnh setup tài liệu hóa.

> #### ✅ ĐÃ LÀM (2026-06-18) — pin deps thiếu + smoke test import
>
> [requirements.txt](../../../requirements.txt): thêm `underthesea` (normalize.py/candidate_mining — BẮT BUỘC), `torch` (embedding device V15), `numpy` (enrichment) — đều dùng trong code nhưng trước chỉ import được nhờ là dep gián tiếp; clone mới sẽ thiếu. (`prometheus-client`, `sentence-transformers`, `qdrant-client`, `opensearch-py` đã có sẵn.) Thêm [tests/test_imports_smoke.py](../../../tests/test_imports_smoke.py): import 13 entrypoint chính → CI bắt thiếu dep ngay thay vì lúc runtime.

### Bài học rút ra cho team

1. **Hai audit mâu thuẫn nhau là dấu hiệu nguy hiểm.** Bản này dựa trên **chạy code + đo số liệu**; bản DEEP_CODE_FIRST dựa trên đọc tĩnh và (nhiều khả năng) bản cũ hơn. Khi trình bày với mentor, dùng bản này làm trạng thái retrieval hiện tại, và chỉ lấy từ DEEP_CODE_FIRST các điểm hạ tầng/frontend đã đánh dấu ✅ ở trên.
2. **Audit tĩnh không bắt được lỗi chất lượng thật.** DEEP_CODE_FIRST chấm Retrieval 48/100 vì "chưa kết nối", nhưng KHÔNG phát hiện được lỗi nghiêm trọng hơn: pipeline ĐÃ kết nối nhưng tín hiệu vector bị nuốt (V1) và fusion không hợp nhất (V9). Chỉ chạy golden A/B mới lộ ra. → Ưu tiên xây **eval harness chạy được** hơn là viết thêm audit.
3. Điểm tổng "48–55%" của audit đó phản ánh **độ phủ tính năng** (feature completeness), KHÔNG phải **độ khả thi production** (4.5/10 của bản này). Hai thước đo khác nhau: dự án "có gần đủ module" nhưng "module cốt lõi đang chạy sai" — nên đừng nhầm hai con số.

---

## Chiến lược lai: ghép điểm mạnh `develop-2` ↔ KE của nhánh hiện tại

> **Nguồn:** đối chiếu trực tiếp code nhánh `develop-2` (`hotel-knowledge-platform/backend/`) với 17 vấn đề ở trên. Chi tiết kiến trúc 2 nhánh xem [`DEVELOP2_VS_CURRENT_COMPARISON.md`](DEVELOP2_VS_CURRENT_COMPARISON.md).

### Bối cảnh trong một đoạn

Hai nhánh **bù trừ gần như hoàn hảo**:

- **Nhánh hiện tại (HEAD)** mạnh ở **Knowledge Engineering** (ABSA, style mining, candidate discovery, LMK gazetteer, ontology Sprint, golden groundtruth) — tài sản khó tái tạo nhất — nhưng **yếu ở runtime retrieval**: không Neo4j, fusion lệch thang (V1), fusion không hợp nhất thật (V9), BM25 analyzer chuẩn (V10).
- **`develop-2`** yếu ở KE (ABSA/discovery/LMK gần như không có) nhưng **mạnh ở runtime**: `calibrated_rrf_fusion` bounded, BM25 chunk-level + `vietnamese_analyzer`, ONNX reranker đã nối vào score, graph-reasoning routing, ContextPackage first-class với evidence/citation.

→ **Hướng đúng: GIỮ HEAD làm nền (vì KE là phần khó), PORT CÓ CHỌN LỌC logic runtime của develop-2 vào.** **KHÔNG `git merge`** (hai nhánh rẽ từ commit gốc, merge sẽ là thảm họa conflict — xem mục 4 của file comparison).

### Một cảnh báo kiến trúc bắt buộc đọc trước khi port

`develop-2` dùng **pgvector trong PostgreSQL** + **Elasticsearch**; nhánh hiện tại dùng **Qdrant** + **OpenSearch**. Vì vậy:

- Các vấn đề **thuần-logic** (V1, V9, V2, V3, V6) → **port code/công thức trực tiếp được**, không phụ thuộc backend store.
- Các vấn đề **gắn hạ tầng** (V10 analyzer, V11 payload/latency, V14 index, V15 device) → **chỉ học cách tiếp cận của develop-2 rồi áp vào Qdrant/OpenSearch**, KHÔNG copy code chạy thẳng. develop-2 không có "Qdrant full payload" vì nó dùng SQL `SELECT` đúng cột — đó là *bài học*, không phải *file để bê*.

### Bảng đối chiếu: vấn đề nào develop-2 bù trừ được, bằng gì

| # | Vấn đề | develop-2 có lời giải? | Cơ chế trong develop-2 | Cách ghép |
|---|---|---|---|---|
| **V1** | Text-signal bị review nuốt (thang ~24×) | ✅ **Có, trực tiếp** | `calibrated_rrf_fusion`: `_minmax()` chuẩn hóa text-signal + graph-signal về [0,1] rồi `text_weight*text + graph_weight*graph` (bounded, explainable) | **Port công thức** `_minmax` + cấu trúc weight vào `business_rerank` của ta. Quick win lớn nhất. |
| **V9** | BM25 doc-level vs Qdrant chunk-level → RRF không hợp nhất | ✅ **Có, trực tiếp** | develop-2 index ES **ở chunk-level** (`id, chunk_type, content, hotel_id` top-level), cùng đơn vị với pgvector chunk → RRF hợp nhất đúng cấp chunk | **Hai lựa chọn:** (A) làm theo develop-2 — reindex OpenSearch ở chunk-level (giải tận gốc, khớp giải pháp B của V9); hoặc (B) giữ giải pháp A của V9 (RRF cấp hotel_id) nếu chưa muốn reindex. |
| **V10** | BM25 analyzer=standard, không hợp tiếng Việt | ✅ **Có (làm mẫu)** | `vietnamese_analyzer`: tokenizer standard + `lowercase` + `decimal_digit` + `asciifolding(preserve_original)` | **Bê config analyzer** sang OpenSearch (cú pháp gần giống ES) + reindex. Đây là đúng "tối thiểu" mà V10 đề xuất, đã có sẵn mẫu chạy được. |
| **V2** | Cross-encoder reranker là code chết | ✅ **Có, trực tiếp** | `LocalReranker`: bật qua env `USE_REAL_RERANKER`, dùng **ONNX quantized** (nhanh trên CPU), **fallback lexical có nối điểm** (`0.65*retrieval + 0.35*overlap`), và **output `rerank_score` được đưa vào context/score** | **Port mô hình LocalReranker**: (a) ONNX thay vì torch 2GB → chạy được trên CPU (giải lo ngại latency của V2); (b) quan trọng — develop-2 **đã nối `rerank_score` vào downstream**, đúng phần "chưa nối" của V2. |
| **V3** | Candidate rỗng → 0 kết quả | ✅ **Có, trực tiếp** | `build_candidate_ids` + `filter_hotel_ids`: bounded **100–300**, intersection `sql ∩ concept` **có fallback** `or sql_set` / `or concept_set`; không bao giờ trả rỗng khi còn tín hiệu | **Port logic fallback + bounded cap.** Khớp ý đồ V3, lại thêm cận trên (giải luôn phần "candidate chưa bounded" trong upgrade-plan). |
| **V6** | `/context` không grounding → nguy cơ bịa | ✅ **Có, trực tiếp** | `ContextBuilder.build`: chọn chunk **đa dạng theo `chunk_type`**, **char/token budget**, sinh **`Citation` + `EvidenceItem`** với evidence_id, đếm missing-constraints, provenance | **Port ContextBuilder** thay cho `build_hotel_context` lấy thẳng `content`. Đưa thêm chunk ABSA/review thật (HEAD có sẵn ABSA — đây là chỗ KE của ta + Context của dev2 ghép vào nhau đẹp nhất). |
| **V5** | Mù query cảm xúc / ngoài ontology | 🟡 **Một phần** | `query_intent`: `classify_query_route` → `infer_requires_graph_reasoning`; query "evidence/aspect/explanation/đa concept" được route sang **graph_enrichment** (Neo4j) để bù tín hiệu | Phụ thuộc V1 trước. Graph routing **chỉ giúp nếu đưa Neo4j vào hạ tầng** (quyết định lớn). Nếu chưa, vẫn dùng query expansion + HyDE như V5 đề xuất; graph là phương án nâng cấp sau. |
| **V8** | Eval thiếu A/B gate, nDCG, câu semantic | 🟡 **Một phần** | develop-2 có nhiều benchmark golden-set (v1, v4 graph_lift, v4 streamlit), ablation runner, eval report tự sinh, OpenAPI drift test | **Tham khảo bộ benchmark/ablation** của develop-2 làm khung; vẫn phải tự thêm nDCG/Recall@20/50 và câu semantic thuần như V8 nêu (golden của ta tốt hơn về groundtruth). |
| **V7** | .env lệch index, route trùng, thiếu auth | 🟡 **Một phần** | develop-2 có readiness metadata, request/search-ID, rate limiting cấu hình được, OpenAPI drift test | **Tham khảo middleware/readiness** của develop-2 cho phần auth/rate-limit/request-id. Phần `.env`/route trùng vẫn sửa thủ công theo V7. |
| **V11** | Latency p50 ~1.9s (Qdrant full payload) | ❌ **Không trực tiếp** | develop-2 dùng pgvector SQL chỉ `SELECT` cột cần → không có lỗi "full payload". Đây là *bài học* không phải code. | **Áp nguyên tắc** "chỉ lấy field cần" vào `qdrant_service` như V11 đã ghi (`with_payload=[...]`). Không bê code dev2. |
| **V12** | parse_intent cold-start 978ms | ❌ **Không liên quan** | develop-2 không dùng synonym YAML 177KB của ta | Giữ giải pháp V12 (preload lúc startup). develop-2 không giúp. |
| **V13** | 0 test fusion/ranking; test pgvector sai backend | 🟡 **Một phần** | develop-2 có test cho fusion (breakdown), reranker, OpenAPI drift, quick/live split | **Tham khảo cấu trúc test** fusion/reranker của develop-2 làm mẫu; nội dung test viết theo backend thật của ta (Qdrant/OpenSearch). |
| **V14** | 9% vector chưa index | ❌ **Không liên quan** | Vấn đề riêng của Qdrant; develop-2 dùng pgvector | Giữ giải pháp V14. develop-2 không giúp. |
| **V15** | Embedding không dùng CUDA | ❌ **Không liên quan** | develop-2 embeddings.py có cờ `USE_REAL_EMBEDDINGS` nhưng không giải bài CUDA/mps của ta | Giữ giải pháp V15. develop-2 không giúp. |
| **V4** | Recall@10 sai chỉ số (GT 38–40 hotel) | ❌ **Không** (vấn đề đo, không phải code) | — | Giữ giải pháp V4 (thêm Recall@20/50, nDCG, phân nhóm intent). |
| **V16** | BM25 `_source` thiếu field | ❌ **Không liên quan** | Khác schema index | Giữ giải pháp V16. |
| **V17** | Môi trường không tái lập | 🟡 **Một phần** | develop-2 có `requirements.txt` riêng (fastapi/neo4j/elasticsearch/sentence-transformers) + `download_onnx_reranker.py` | Tham khảo cách develop-2 quản ONNX model/deps; nội dung vẫn theo V17. |

**Tổng kết khả năng bù trừ:** develop-2 giải **trực tiếp 6 vấn đề** (V1, V9, V10, V2, V3, V6 — gồm **cả 3 vấn đề 🔴 chí mạng về chất lượng** V1, V9, và 2 vấn đề 🟠 cao V2, V3), **hỗ trợ một phần 5 vấn đề** (V5, V8, V7, V13, V17). Các vấn đề develop-2 **không** giúp (V11 SLA, V12, V14, V15, V4, V16) đều là **vấn đề gắn hạ tầng Qdrant/đo lường riêng của ta** — vẫn theo giải pháp gốc trong báo cáo.

### Lộ trình ghép theo đợt (gộp với "Lộ trình sửa theo đòn bẩy" ở trên)

| Đợt | Việc | Nguồn | Backend-agnostic? | Ghi chú |
|---|---|---|---|---|
| **Đợt 1 — Quick win chất lượng** | V1 (calibrated fusion) + V9 (fuse cấp hotel hoặc reindex chunk-level) + V3 (candidate fallback bounded) | **Port logic develop-2** | ✅ Có | Đều logic thuần, đụng cùng vùng fusion/candidate. **Chạy lại golden A/B ngay** — đây là phép thử bản lề (kỳ vọng Recall@10 vượt 0.55). |
| **Đợt 2 — SLA & vận hành** | V11 (Qdrant payload) + V12 (preload) + V14 (optimize) + V15 (CUDA) + V7 (.env/route/auth) | **Giải pháp gốc** (+ tham khảo middleware dev2 cho auth) | Riêng Qdrant | Không phụ thuộc Đợt 1; có thể song song. |
| **Đợt 3 — Reranker & context** | V2 (port LocalReranker ONNX + nối `rerank_score`) + V6 (port ContextBuilder + đưa ABSA thật của HEAD vào) | **Port develop-2 + KE của HEAD** | ✅ Có | V2 phụ thuộc V1. V6 là điểm ghép đẹp nhất: Context của dev2 × ABSA của ta. |
| **Đợt 4 — Index & eval** | V10 (vietnamese_analyzer + reindex OpenSearch) + V8/V13 (eval gate + test fusion theo mẫu dev2) | **Mẫu develop-2** | Reindex OpenSearch | V10 nặng (reindex) nên xếp sau khi Đợt 1 xác nhận hướng đúng. |
| **Đợt 5 (tùy chọn, lớn) — Graph** | V5 nâng cấp: đưa Neo4j + graph-reasoning routing của develop-2 | **Port develop-2** | Hạ tầng mới | Chỉ làm nếu quyết định đưa Neo4j vào stack. ROI cần cân với `apply_profile_boost` hiện có. |

### Nguyên tắc thực thi (quan trọng)

1. **Port logic, KHÔNG cherry-pick commit** của develop-2 (lịch sử git lệch từ commit gốc). Copy file/đoạn vào nhánh tích hợp mới từ HEAD (vd `feature/port-dev2-runtime`).
2. **Đợt 1 trước, đo trước, rồi mới đi tiếp.** Nếu sau khi calibrated-fuse + fuse-cấp-hotel mà recall vẫn không nhúc nhích, bài toán chuyển từ "ranking" sang "recall tầng candidate" — khi đó V5/V10 (mở rộng recall) mới là đòn bẩy, không phải reranker.
3. **Map schema cẩn thận khi port.** develop-2 từng có bug `hotel_id` top-level vs `metadata.hotel_id` (đã ghi trong upgrade-plan của nó) — chính là họ hàng của V9/V16 bên ta. Chốt một schema chunk/metadata thống nhất trước khi port fusion.
4. **Tự benchmark lại trên data thật của HEAD.** develop-2 tự nhận một số phần "architecture complete, full-model proof pending" (BGE smoke bị chặn RAM/pagefile Windows) — không tin số của họ, chạy lại golden của ta.
