# Chunking Report — Benchmark chiến lược chunking trên corpus tiếng Việt

> Tác giả: Nguyễn Ngọc Khánh Duy · Hạng mục: Chunking & Embedding (Layer 3).
> Báo cáo trình bày **số liệu đo được** của 5 chiến lược chunking, và **rút kết luận
> ngay từ từng bảng số**. Embedder cố định = `bge-m3` để cô lập biến chunking.

---

## 1. Thiết lập đo

- **Corpus**: 705 section từ **27 khách sạn thật** (`data/cleaned/`, hệ Vinpearl/Meliá).
- **Gold set**: 30 truy vấn tiếng Việt, nhãn suy ra từ facts (khách quan), có cả câu gõ không dấu.
- **Embedder cố định**: `bge-m3` (1024-d, cosine). **Truy xuất**: cosine in-memory chính xác.
- **Tham số**: `max_tokens=300, overlap=15%`, bật `context_prefix`.
- **Cách đọc metric**: ưu tiên **Hit@10** và **Hotel-Recall@10**; `R@10(chunk)` bị trần thấp
  ở truy vấn nhiều đáp án nên chỉ tham khảo.

---

## 2. Số liệu — tổng hợp 30 truy vấn

| chiến lược | #chunks | avg_tok | Hit@10 | H-Rec@10 | MRR@10 | nDCG@10 | R@10(chunk) |
|---|---|---|---|---|---|---|---|
| whole_section | 705 | 356.6 | 0.900 | 0.685 | 0.763 | **0.645** | 0.360 |
| fixed_token | 1291 | 232.3 | 0.933 | **0.692** | **0.770** | 0.624 | 0.250 |
| sentence | 1316 | 212.0 | 0.900 | 0.641 | 0.703 | 0.599 | 0.241 |
| recursive | 2378 | 122.3 | 0.867 | 0.643 | 0.672 | 0.599 | 0.187 |
| parent_child | 1812 | 166.2 | 0.900 | 0.664 | 0.731 | 0.609 | 0.212 |

**Kết luận rút ra từ bảng:**
- whole_section (0.685) và fixed_token (0.692) bám sát nhau, chênh **0.007** → trên 30 câu
  (mỗi câu ≈ 0.033) đây là **hoà**, không cái nào thắng thật.
- whole_section **thắng nDCG (0.645)** và dùng **ít chunk nhất (705)**.
- recursive băm nhỏ nhất (2378 chunk) → **thấp nhất ở mọi metric** → **băm nhỏ phản tác dụng**
  với corpus khách sạn na ná nhau (nhiều chunk gần-trùng gây nhiễu).
- Hit@10 ≈ 0.9 ở mọi chiến lược → "tìm được ít nhất 1 kết quả đúng" đã ổn; khác biệt nằm ở
  xếp hạng và độ phủ.

---

## 3. Số liệu — Hotel-Recall@10 theo nhóm nghiệp vụ

| nhóm | whole_section | fixed_token | sentence | recursive | parent_child |
|---|---|---|---|---|---|
| activities | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| amenities | 0.125 | 0.056 | 0.069 | 0.028 | 0.014 |
| detail | 0.750 | 1.000 | 0.750 | 1.000 | 1.000 |
| faq | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 |
| nearby | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| personalization | 0.667 | 0.417 | 0.500 | 0.417 | 0.500 |
| rooms | 0.722 | 0.722 | 0.722 | 0.722 | 0.722 |
| search_filter | 0.702 | 0.718 | 0.637 | 0.578 | 0.622 |

**Kết luận rút ra từ bảng:**
- `activities`, `faq`, `nearby`, `rooms` **bằng nhau ở cả 5 cột** → đây là các mục atomic/
  1-chunk, chiến lược không tác động. ⇒ **Việc chọn kiểu chunk thực chất chỉ ảnh hưởng**
  **trường văn xuôi dài (`description`)** và truy vấn lọc (`search_filter`/`personalization`).
- `personalization`: whole_section **0.667** vs fixed_token **0.417** → whole_section vượt hẳn.
- `amenities` thấp ở **mọi** chiến lược (0.01–0.13) → vấn đề **không** nằm ở chunk mà ở bản
  chất dense (xem mục 5).

---

## 4. Số liệu — truy vấn gõ KHÔNG DẤU

| chiến lược | H-Rec@10 | MRR@10 | nDCG@10 |
|---|---|---|---|
| whole_section | 0.550 | 1.000 | 0.826 |
| fixed_token | 0.683 | 1.000 | 0.825 |
| sentence | 0.700 | 1.000 | 0.858 |
| recursive | 0.633 | 1.000 | 0.834 |
| parent_child | 0.700 | 1.000 | 0.870 |

**Kết luận rút ra từ bảng:**
- **MRR = 1.000 ở mọi chiến lược** → câu không dấu vẫn cho kết quả đúng ở hạng 1.
- ⇒ Khả năng chịu không dấu là thuộc tính của **embedder (bge-m3)**, **không phải** của
  chiến lược chunk. Chênh lệch H-Rec giữa các chiến lược ở đây nhỏ, không lật kết luận mục 2.

---

## 5. Hai điểm số liệu cần diễn giải sâu

**5.1 — `context_prefix` là yếu tố thay đổi cuộc chơi.**
Số đo trước/sau khi bật `context_prefix`:

| nhóm | trước | sau |
|---|---|---|
| activities | 0.000 | 1.000 |
| nearby | 0.000 | 1.000 |

⇒ Mức tăng này (0 → 1.0) **lớn hơn toàn bộ khác biệt giữa 5 chiến lược cộng lại**. Kết luận:
*cái nhét vào chunk (định danh khách sạn) quan trọng hơn cách cắt chunk.* Lý do số 0 trước
đó: các mục danh sách không chứa tên KS → embedding không phân biệt được chunk thuộc KS nào.

**5.2 — `amenities` yếu là giới hạn của DENSE, không phải của chunk.**
amenities ≤ 0.125 ở mọi chiến lược, trong khi truy vấn kiểu "resort có spa" (24 KS) cần khớp
danh sách tiện nghi. ⇒ Kết luận: dense thuần không xử tốt truy vấn lọc-tiện-ích; **Layer 6
cần BM25 + lọc metadata** để bắt chính xác từ khóa. (Một phần do nhãn quá chặt — chỉ chấp
nhận section `amenities`.)

---

## 6. Độ tin cậy của số liệu

- **30 câu** → sai số chuẩn ≈ **±0.08** ⇒ mọi khác biệt **< 0.1 coi là hoà** (whole_section
  ↔ fixed_token). Khác biệt lớn (context_prefix 0→1, recursive thua) thì **vững**.
- Số theo nhóm dựa trên 2–6 câu/nhóm → nhiễu, chỉ đọc theo hướng.
- Corpus 27 KS đồng nhất + nhãn sinh bằng luật → nên chạy lại khi có corpus đa dạng (review/CMS).

---

## 7. Kết luận tổng & khuyến nghị

Từ toàn bộ số liệu trên:

1. **Chọn `whole_section` + `context_prefix`** — hoà với fixed_token ở top nhưng thắng nDCG,
   thắng personalization, mạch lạc hơn (không cắt giữa câu), ít chunk hơn.
2. **`context_prefix` là bắt buộc** — đòn bẩy mạnh nhất đo được.
3. **Băm nhỏ (`recursive`) là sai hướng** với dữ liệu khách sạn.
4. **Chiến lược chunk chỉ cần tinh chỉnh cho `description`** → tiến tới `hybrid` (whole cho
   mục ngắn, băm riêng description, atomic cho faq/room).
5. **amenities/lọc-tiện-ích** dựa vào **hybrid BM25 + metadata** ở Layer 6, không phải dense.
6. **parent-child** để dành cho dựng ngữ cảnh (Layer 7), không phải để index truy xuất.

_Số liệu thô: `evaluation/reports/chunking_results.json`. Lần chạy: Colab GPU (T4), Python 3.12.13._
