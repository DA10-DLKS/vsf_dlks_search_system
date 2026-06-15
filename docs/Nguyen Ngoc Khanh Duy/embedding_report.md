# Embedding Report — So sánh model embedding cho tiếng Việt (bge-m3 vs others)

> Tác giả: Nguyễn Ngọc Khánh Duy · Hạng mục: Chunking & Embedding (Layer 4).
> Báo cáo trình bày **số liệu đo được** của 3 model, và **rút kết luận ngay từ từng bảng số**.
> Cùng tập chunk (chiến lược cố định = `fixed_token`, 1291 chunk) để cô lập biến model.
> **Không** dùng OpenAI mặc định.

---

## 1. Thiết lập đo

- **Corpus / Gold**: 27 khách sạn thật · 30 truy vấn tiếng Việt (như chunking_report).
- **Tập chunk dùng chung** cho cả 3 model → so sánh công bằng.
- **Truy xuất**: cosine in-memory chính xác (chỉ dense — chưa bật sparse/BM25/rerank).
- **Tiền xử lý bắt buộc theo model**: bge-m3 (thô) · vietnamese-embedding (tách từ, ctx 256)
  · multilingual-e5 (prefix `query:`/`passage:`, ctx 512). Sai cấu hình → điểm tụt giả tạo.

---

## 2. Số liệu — tổng hợp 30 truy vấn

| model | dim | enc_docs(s) | Hit@10 | H-Rec@10 | MRR@10 | nDCG@10 | R@10(chunk) |
|---|---|---|---|---|---|---|---|
| bge-m3 | 1024 | 77.1 | 0.933 | 0.692 | **0.770** | **0.624** | 0.250 |
| multilingual-e5 | 1024 | 77.5 | 0.933 | **0.744** | 0.636 | 0.527 | 0.237 |
| vietnamese-embedding | 768 | **29.1** | 0.733 | 0.571 | 0.520 | 0.402 | 0.166 |

**Kết luận rút ra từ bảng:**
- **e5 thắng recall** (Hotel-Recall 0.744) — lùa nhiều KS vào top-10 nhất.
- **bge-m3 thắng xếp hạng** (MRR 0.770, nDCG 0.624) — kết quả đúng nằm ở vị trí đầu, cao hơn
  e5 rõ rệt (MRR +0.13, nDCG +0.10).
- ⇒ Quyết định **chẻ đôi**: e5 mạnh ở "phủ", bge-m3 mạnh ở "xếp đúng lên đầu". Trong search,
  vị trí đầu (MRR/nDCG) là cái người dùng cảm nhận trực tiếp → lợi thế nghiêng về bge-m3.
- vietnamese-embedding nhanh nhất (29s, 768-d nhẹ index) nhưng **thua mọi mặt chất lượng**.

---

## 3. Số liệu — Hotel-Recall@10 theo nhóm nghiệp vụ

| nhóm | bge-m3 | multilingual-e5 | vietnamese-embedding |
|---|---|---|---|
| activities | 1.000 | 1.000 | **0.000** |
| amenities | 0.056 | 0.028 | 0.000 |
| detail | 1.000 | 1.000 | 1.000 |
| faq | 0.667 | 1.000 | 1.000 |
| nearby | 1.000 | 1.000 | 1.000 |
| personalization | 0.417 | **0.750** | 0.500 |
| rooms | 0.722 | **0.833** | 0.556 |
| search_filter | **0.718** | 0.648 | 0.495 |

**Kết luận rút ra từ bảng:**
- e5 mạnh nhất ở `personalization` (0.750) và `rooms` (0.833); bge-m3 mạnh nhất ở
  `search_filter` (0.718) → mỗi model có vùng sở trường, củng cố nhận định "chẻ đôi".
- vietnamese-embedding **= 0.000 ở `activities` và `amenities`** → thất bại với mục danh sách
  dài bị cắt 256 token → bằng chứng giới hạn context ngắn của PhoBERT.
- `amenities` thấp ở **cả ba** → giới hạn của dense, không phải của model (xem chunking_report).

---

## 4. Số liệu — truy vấn gõ KHÔNG DẤU (trục quyết định)

| model | H-Rec@10 | MRR@10 |
|---|---|---|
| bge-m3 | **0.683** | **1.000** |
| multilingual-e5 | 0.633 | 0.389 |
| vietnamese-embedding | 0.083 | 0.083 |

**Kết luận rút ra từ bảng:**
- bge-m3 gần như **không suy giảm** (MRR 1.000) — tokenizer đa ngữ xử lý tốt văn bản không dấu.
- e5 tìm được KS nhưng **xếp hạng sụp** (MRR 0.389).
- vietnamese-embedding **sập hoàn toàn** (0.083) — PhoBERT cần tiếng Việt có dấu + tách từ;
  query không dấu là ngoài phân phối.
- ⇒ Vì search tiếng Việt thật có **rất nhiều câu gõ thiếu dấu**, đây là trục có sức nặng cao.
  bge-m3 thắng tuyệt đối → **loại vietnamese-embedding khỏi vai trò model chính.**

---

## 5. Số liệu chi phí

| model | dim (chi phí index) | enc 1291 chunk |
|---|---|---|
| bge-m3 | 1024 | 77.1s |
| multilingual-e5 | 1024 | 77.5s |
| vietnamese-embedding | 768 | 29.1s |

**Kết luận:** vietnamese-embedding rẻ nhất (~2.6× nhanh hơn, index nhẹ hơn) — nhưng cái rẻ
đó không bù được việc sập khi không dấu. bge-m3 và e5 ngang chi phí.

---

## 6. Tổng điểm có trọng số

Trọng số theo ưu tiên search tiếng Việt production: xếp hạng 30% · recall 25% ·
chịu-không-dấu 25% · vận hành 10% · chi phí 10%.

| Model | Điểm tổng |
|---|---|
| **bge-m3** | **0.93** |
| multilingual-e5 | 0.75 |
| vietnamese-embedding | 0.55 |

---

## 7. Độ tin cậy của số liệu

- **30 câu** → sai số ≈ **±0.08** ⇒ chênh lệch **< 0.1 coi là hoà** (vd recall bge-m3 0.692
  ↔ e5 0.744 chưa đủ kết luận chắc).
- Nhưng khác biệt **lớn vẫn vững**: không-dấu của vietnamese-embedding (0.083 vs 1.000), và
  ưu thế MRR/nDCG của bge-m3 — mang tính bản chất.
- Benchmark **chỉ dùng dense** → chưa đo hết lợi thế **sparse** của bge-m3 (production hybrid còn cao hơn).
- Corpus 27 KS đồng nhất, nhãn sinh bằng luật → chạy lại khi có corpus đầy đủ.

---

## 8. Kết luận tổng & khuyến nghị

Từ toàn bộ số liệu trên — **chọn `bge-m3` làm model chính**, vì:
1. **Xếp hạng tốt nhất** (MRR 0.770, nDCG 0.624) — quan trọng nhất với UX.
2. **Bền nhất với gõ không dấu** (MRR 1.000) — yếu tố sống còn cho tiếng Việt.
3. **Lợi thế vận hành**: 8192 ctx, dense+sparse (hợp hybrid), reranker đồng bộ `bge-reranker-v2-m3`.

| Hạng mục | Khuyến nghị |
|---|---|
| Model chính | **`bge-m3`** |
| Dự phòng | `multilingual-e5` **+ reranker** (tận dụng recall cao, bù điểm yếu xếp hạng) |
| Loại khỏi vai trò chính | `vietnamese-embedding` (sập khi không dấu) |
| Lập chỉ mục | dense bge-m3 → Qdrant; bật thêm sparse + BM25 cho hybrid (Layer 6) |

_Số liệu thô: `evaluation/reports/embedding_results.json`. Lần chạy: Colab GPU (T4), Python 3.12.13._
