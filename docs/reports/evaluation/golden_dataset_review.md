# Đánh giá & Cải thiện Golden Dataset (góc nhìn MLOps)

_Ngày: 2026-06-16. Phạm vi: `data/golden_dataset/golden_set_v1.json` (70 câu) → `golden_set_v2.json`._

## 1. Domain & mục tiêu đánh giá

DA10 là **Knowledge & Retrieval Platform**: crawl → enrich → chunk/embed → index → retrieval
(lexical/vector/hybrid) → rerank → context. Golden dataset là **thước đo** chất lượng retrieval.
Một golden tốt phải: (a) ground-truth **khách quan** (không vòng lặp với chính model), (b) đo
đúng tầng cốt lõi (RAG = chunk retrieval), (c) phủ domain (city/intent), (d) phân biệt được
hệ thống tốt/kém.

## 2. Vấn đề của v1 (đã đo, không cảm tính)

| # | Vấn đề | Bằng chứng | Tác động |
|---|---|---|---|
| 1 | **Ground-truth vòng lặp (circular)** | ≥25/70 câu định nghĩa relevant = TOP-N **sort theo 1 metric** (đếm review 'yên tĩnh', distance_km, grade_score) | Đo model bằng chính heuristic model → metric đẹp/xấu **giả** |
| 2 | **Không có chunk-level** | `relevant_chunk_ids` = 0/70 | Project là RAG nhưng golden **không đo** chunk retrieval — tầng cốt lõi |
| 3 | **Coverage lệch** | Chỉ 13/69 city, toàn city lớn; 56 city long-tail không có câu | Chỉ chứng minh "chạy tốt trên data dày" |
| 4 | **Đơn điệu** | 70/70 `hotel_search`; 1 labeler (không có inter-annotator agreement) | Không test place-intent; rủi ro bias |
| 5 | **Câu quá rộng** | "khách sạn tầm trung" (toàn quốc, 1 tiêu chí) → 131 hotel đều đúng | Không phân biệt được ranking tốt/kém |

## 3. Cải thiện ở v2

### 3.1. Sửa lỗi vòng lặp → multi-signal binary relevance
relevant(hotel) = **nhị phân**, dựa **tín hiệu độc lập**, KHÔNG sort-để-định-nghĩa:
- **A. Structured** (Agoda): amenity thật, star_rating — không từ review.
- **B. Review aspect**: `semantic_profile≥0.6` HOẶC `grade≥8.5`.
- **C. Demographics**: nhóm khách thực tế (share≥25% & count≥50).

Ví dụ PURPOSE_FAMILY: relevant = đúng city + (demographics 'Gia đình' trội C **HOẶC** amenity
kids-club A). Hai nguồn độc lập → hết vòng lặp. Thứ tự (ordering) tách riêng, không quyết định nhãn.

### 3.2. Kiểm soát chất lượng nhãn → `eval_status`
Câu không đủ tin cậy bị đánh dấu `excluded` (minh bạch, không tính metric) thay vì nhãn rác:
- `no_signal` (3 câu): enrichment chưa đủ data (STYLE_VINTAGE/AESTHETIC review thưa, 0-1 hotel đạt ngưỡng).
- `too_broad` (8 câu): >40 relevant — câu 1-tiêu-chí toàn quốc, không phân biệt ranking.

### 3.3. Chunk-level (RAG)
`add_chunk_ids.py`: relevant chunk = chunk **thuộc hotel relevant** VÀ payload mang concept câu
hỏi. Chạy sau khi index Qdrant xong (tách vì embed nặng, có thể chạy máy khác).

## 4. Kết quả v2

| Chỉ số | v1 | v2 |
|---|---|---|
| Tổng câu | 70 | 70 |
| Câu eval được (active) | 70 (nhưng nhiều câu vòng lặp) | **59 active** + 11 excluded minh bạch |
| Phương pháp nhãn | sort 1-metric (circular) | multi-signal binary |
| relevant/câu | top-N cắt cụt (4–10) | đầy đủ, median 14, max 40 (chọn lọc) |
| chunk-level | 0 | script sẵn sàng (chờ index) |
| Phủ nhóm active | — | LMK 10 / PURPOSE 11 / AMEN 10 / GRADE 10 / STYLE 8 / PRICE 6 |

## 5. Hạn chế còn lại (trung thực)

- **Coverage long-tail** chưa bổ sung câu mới cho 56 city nhỏ (v2 mới chỉ *làm sạch* v1, chưa
  *mở rộng*). Đề xuất v3: thêm câu long-tail + place-intent + negative cases.
- **STYLE_VINTAGE/AESTHETIC** excluded do enrichment thiếu — sẽ active lại khi ABSA backfill đủ.
- **Chunk_ids** chờ index Qdrant hoàn tất (embed bge-m3).
- **Single labeler**: v2 dựng nhãn tự động từ tín hiệu (giảm bias người), nhưng nên có 1 người
  spot-check ngẫu nhiên ~10 câu để xác nhận.

## 6. File

- `data/golden_dataset/golden_set_v2.json` — golden mới (giữ v1 để đối chiếu).
- `evaluation/test_queries/build_golden_v2.py` — builder multi-signal (tái lập được).
- `evaluation/test_queries/add_chunk_ids.py` — điền chunk-level sau index.
- `evaluation/retrieval_metrics/eval_golden.py` — harness đo (đã có; cần trỏ sang v2 + lọc active).
