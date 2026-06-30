# Giải thích metric Golden Eval & đánh giá số liệu

> Nguồn code: [eval_golden.py](../../../evaluation/retrieval_metrics/eval_golden.py) · Endpoint UI: `GET /eval/golden` trong [api/main.py](../../../api/main.py#L248) · Dataset: [golden_set_v2.json](../../../data/golden_dataset/golden_set_v2.json)

## TL;DR — câu hỏi quan trọng nhất

**Eval hiện CHỈ chạy trên `relevant_hotel_ids`, KHÔNG dùng `relevant_chunk_ids`.**

Bằng chứng trong code:

- [eval_golden.py:65](../../../evaluation/retrieval_metrics/eval_golden.py#L65) — `relevant = g.get("relevant_hotel_ids", [])`
- [eval_golden.py:71](../../../evaluation/retrieval_metrics/eval_golden.py#L71) — `predicted = [c["hotel_id"] for c in res["context_package"]["chunks"]]`
- [eval_golden.py:34-44](../../../evaluation/retrieval_metrics/eval_golden.py#L34-L44) — toàn bộ metric so `set(predicted hotel_id)` với `set(relevant_hotel_id)`

`relevant_chunk_ids` (≈44 chunk ở GS-001) **không được đọc ở bất kỳ đâu** trong đường eval. Nó nằm trong dataset như evidence/tham chiếu nhưng không tham gia tính điểm.

Bằng chứng từ chính UI: cột **#GT** = 15, 14, 13, 12, 10, 9, 8, 7, 6 — đúng bằng **độ dài mảng `relevant_hotel_ids`** của từng câu (GS-001 có 15 hotel_id), KHÔNG phải số chunk (GS-001 có 44 chunk_id). Nếu eval đang đếm chunk thì #GT của GS-001 phải là 44.

→ Đây là **hotel-level retrieval eval** (truy hồi đúng *khách sạn*), không phải chunk-level.

---

## Cách tính từng metric

Tất cả ở mức nhị phân (relevant / không), K=10, so trên tập `hotel_id`.

Ký hiệu: `pred_k` = top-K hotel_id pipeline trả về; `rel` = tập `relevant_hotel_ids`; `hit_set = rel ∩ pred_k`.

### Recall@10
```
recall = |hit_set| / |rel|
```
Trong số *tất cả* khách sạn đúng (`|rel|` = #GT), bao nhiêu phần lọt vào top-10.
- **Trần toán học**: nếu `|rel| > 10` thì Recall@10 **không thể** đạt 1.0 dù pipeline hoàn hảo — top-10 chỉ chứa được tối đa 10 hit.
  - GS-001: |rel|=15 → trần Recall@10 = 10/15 = **0.667**. Thực đo 0.533 (8/15).
  - GS-009: |rel|=6 → trần = 1.0. Thực đo 0.833 (5/6).

### Precision@10
```
precision = |hit_set| / |pred_k|   (mẫu số = 10, hoặc số kết quả nếu < 10)
```
Trong 10 ô trả về, bao nhiêu ô là khách sạn đúng. Prec=0.8 → 8/10 ô đúng.

### Hit@10
```
hit = 1.0 nếu hit_set khác rỗng, ngược lại 0
```
Có *ít nhất một* kết quả đúng trong top-10 hay không. Toàn bộ 10 câu = 1 → mọi câu đều bắt được ≥1 hotel đúng.

### MRR (Mean Reciprocal Rank) — cột RR
```
rr = 1 / (vị trí của hit ĐẦU TIÊN trong pred_k)
```
RR=1 nghĩa là ô top-1 đã đúng. Toàn bộ = 1 → câu nào kết quả #1 cũng là khách sạn đúng. Rất mạnh về độ chính xác đầu bảng.

### nDCG@10 ([eval_golden.py:18-26](../../../evaluation/retrieval_metrics/eval_golden.py#L18-L26))
```
DCG  = Σ 1/log2(rank+1) cho mỗi hit trong top-K
IDCG = DCG lý tưởng = dồn min(|rel|, K) hit lên đầu
nDCG = DCG / IDCG
```
Đo *chất lượng thứ hạng*: hit nằm càng cao càng tốt. **Khác recall ở chỗ**: IDCG chỉ chuẩn hóa theo `min(|rel|, K)`, nên nDCG **không bị phạt** vì không gói hết 15 GT vào 10 ô — nó hỏi "trong 10 ô bạn xếp các hit tối ưu chưa", không hỏi "bạn có lấy hết 15 hotel chưa". Vì thế nDCG@10 (0.8651) cao hơn Recall@10 (0.7354) là hợp lý, không mâu thuẫn.

---

## Đánh giá: số liệu có hợp lý không?

| Metric | Giá trị | Đánh giá |
|---|---|---|
| Recall@10 | 0.7354 | **Tốt và đáng tin**, đặc biệt khi nhiều câu có #GT > 10 (trần < 1.0). |
| Precision@10 | 0.71 | Hợp lý, đồng pha với recall. |
| Hit@10 | 1.0 | Mọi câu bắt ≥1 hotel đúng — pipeline không "trượt trắng" câu nào. |
| MRR | 1.0 | Top-1 luôn đúng ở cả 10 câu. |
| nDCG@10 | 0.8651 | Thứ hạng tốt; cao hơn recall là đúng bản chất công thức. |
| Số câu | 10 | ⚠️ **Đây là điểm cần lưu ý nhất.** |

### Các quan hệ nội tại — đều NHẤT QUÁN ✅
- `Recall ≤ nDCG` khi |rel| > K: đúng (0.7354 < 0.8651), vì IDCG chỉ chuẩn theo min(|rel|,K).
- `Hit=1` và `MRR=1`: nhất quán — nếu top-1 luôn đúng thì chắc chắn có hit.
- Per-query cũng khớp: GS-001 Recall 0.533 = 8/15; GS-008 Recall 0.429 = 3/7; GS-005 mọi metric =1 (|rel|=10, lấy đủ).

### Những điểm CẦN THẬN TRỌNG ⚠️

1. **Chỉ 10/59 câu active được chạy.** Endpoint mặc định `limit=10` ([api/main.py:251](../../../api/main.py#L251)) và `evaluate()` cắt `golden[:limit]` ([eval_golden.py:60](../../../evaluation/retrieval_metrics/eval_golden.py#L59-L60)) — tức là **10 câu ĐẦU danh sách**, không phải mẫu ngẫu nhiên. 10 câu này đều là dạng "Tìm KS ở \<city\> gần \<landmark\>" — **chỉ phủ 1 intent_type**. Số liệu đẹp ở đây *chưa* đại diện cho toàn bộ golden set (style/purpose/implicit-intent…). Để kết luận năng lực thật phải chạy `limit=59`.

2. **MRR=1.0 trên cả 10 câu là dấu hiệu cần soi.** Top-1 đúng tuyệt đối thường vì các câu này có hard_filter `city` rất chặt + landmark mạnh, nên dễ. Trên các intent khó hơn (style/implicit) MRR sẽ tụt — đừng coi 1.0 là baseline chung.

3. **`use_services` mặc định = False → mode "candidate-only".** Số đang xem KHÔNG có vector(Qdrant)+BM25 thật ([api/main.py:268-269](../../../api/main.py#L268-L269)). Eval đầy đủ phải bật `use_services=true`. Theo memory dự án, FULL vector+bm25 từng cho recall thấp hơn nhiều khi text-signal lệch thang — nên con số candidate-only có thể *lạc quan hơn* bản FULL.

4. **`relevant_chunk_ids` đang bị bỏ phí.** Nếu mục tiêu là đánh giá RAG/answer (chunk nào đưa vào context), cần một eval chunk-level riêng dùng `relevant_chunk_ids`. Hiện chưa có.

### Kết luận
Với phạm vi **10 câu landmark-proximity, mode candidate-only**, các số liệu **nội tại nhất quán và đáng tin** (mọi quan hệ giữa các metric đều đúng công thức, per-query khớp ground-truth). Đây là kết quả **tốt** cho lớp câu dễ này.

**Nhưng KHÔNG nên trích dẫn như "hiệu năng hệ thống".** Để báo cáo có giá trị cần:
1. Chạy `limit=59` (toàn câu active) để phủ mọi intent_type.
2. Bật `use_services=true` để đo bản FULL vector+bm25.
3. Báo cáo đa-K (Recall@10/@20/@50 + nDCG@10) bằng `evaluate_multi_k` — vì nhiều câu có #GT 15–40, Recall@10 thấp là *kỳ vọng toán học* chứ không phải lỗi pipeline.
4. Nếu cần đánh giá tầng answer/RAG: bổ sung eval chunk-level dùng `relevant_chunk_ids`.
