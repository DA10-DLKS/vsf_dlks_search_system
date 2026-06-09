# KE Sprint 2 — BACKLOG (đã làm / còn nợ)

> File ghi nhớ việc, để không quên. Cập nhật mỗi khi làm xong / phát sinh việc mới.
> Owner: Trương Anh Long. Cập nhật: 2026-06-09.

---

## ✅ ĐÃ LÀM (Sprint 2)

| Bước | Sản phẩm | Trạng thái |
|---|---|---|
| 0 | Khảo sát data (step0) | xong |
| 1 | source_tag_map.yaml + audit surface_forms (đợt 1+2) | xong |
| 1b | implicit_intent.py (intent ngầm "2 con"→FAMILY) | xong |
| 2 | ontology_mapper Tầng 0+1 (HARD) — 520 hotel | xong |
| 3 | metadata_pipeline (reconcile is_luxury, price_capped) | xong |
| 4 | build_objects (HARD object 520, pydantic pass) | xong |
| 5.0 | llm.py đa-provider (openai/gemini/ollama/claude) + cache + safe (max_tokens, FatalLLMError, estimate, resume) | xong |
| 5.2 | profile_builder SEED (aspect từ Agoda grades) | xong |
| 5.3 | absa.py ABSA per-review — **chạy thật 1 hotel (805030)** | một phần |
| 5.4 | merge_absa (aspect span + style từ ABSA, đối nghĩa→chỉ positive) | xong (1 hotel) |
| — | query_expansion TỰ SINH (related + co-occurrence + lift) | xong |
| — | Fix: dedup tỉnh trùng (Phú Thọ/Vĩnh Phúc); suy location→SETTING từ data (COASTAL 0→180) | xong |
| — | absa: dedupe concept/review + prompt đa ngôn ngữ + metadata (prompt_version) | xong |

---

## ⬜ CÒN NỢ — ưu tiên cao (cần để CHỐT Sprint 2)

1. **Chạy ABSA cả corpus** — hiện 0 hotel có evidence (đã xóa 805030 v1). Batch dry-run:
   **504 hotel, 92k review, ~$10.96** (limit 250). Chỉ còn chờ QUYẾT ĐỊNH chi phí.
   - Sau khi chạy: STYLE_* (MODERN/LUXURY/ROMANTIC/LIVELY/ECO) hết "chết" + có span.
2. ~~Batch runner ABSA~~ ✅ **XONG** — `--all --max-hotels --limit --budget-usd --dry-run`.
   Budget cap chặn cứng chi phí (test: cap $2 → tự cắt còn 73 hotel).
3. **Bước 6 — hợp nhất + báo cáo Sprint 2 tổng kết** + cập nhật handover (JSON là seed, production dùng DB).

## ⬜ CÒN NỢ — ưu tiên trung bình

4. **Lưu negative style riêng** (hotel bị chê "ồn"/"không thư giãn") — để giải thích + tránh recommend sai. Hiện negative style bị bỏ khi tính score (đúng), nhưng chưa lưu lại.
5. **PURPOSE_WELLNESS không gắn hotel nào** — cân nhắc suy từ AMEN_SPA (hotel có spa → hợp wellness?).
6. **Gắn LOC concept_id vào object** — location hiện chỉ text+toạ độ, chưa có `LOC_*` trong semantic_metadata. Cần cho quan hệ near + filter location chuẩn (known limitation Bước 4).
7. **Verify query_expansion trên golden set** — 54 cạnh đang `unverified`. Cần retrieval pipeline (Sprint 3+) đo Recall, bỏ cạnh không giúp.

## ⬜ CÒN NỢ — Sprint 4 / dài hạn

8. **Candidate mining từ review** (mode RIÊNG, tách ABSA) — phát hiện concept MỚI (boutique/vintage/traditional) từ review. ABSA hiện ràng buộc chỉ chọn concept có sẵn nên KHÔNG phát hiện candidate. Thuộc vòng phản hồi ontology Sprint 4.
9. **Tự động hóa candidate queue** — phát hiện/lọc/xếp hạng keyword lạ tự động, người chỉ duyệt (Sprint 4).
10. **Test tự động (pytest)** cho normalize/mapper/expansion — hiện lỗi chỉ phát hiện nhờ test tay. Production cần regression test.
11. **Coverage/quality report tự động** — % hotel đủ tag, % confidence thấp, hotel thiếu data → giám sát.

## ⚠ PHỤ THUỘC NGOÀI (không phải việc KE, nhưng chặn/ảnh hưởng)

- **Model embedding** (Khánh Duy chốt) → mở khóa Tầng 2 ontology_mapper (embedding tagger).
- **Giá thật** (Data Quality crawl) → hiện giá cap 5tr placeholder, lọc-giá chưa tin được.
- **Review crawl** sort low_first → ABSA phải sample cân bằng (đã xử ở `_sample_balanced`).
- **Hạ tầng production** (Đạt: Postgres/Qdrant/ES) → JSON hiện là seed/contract, KHÔNG phải nơi lưu chính.

## 📌 GHI CHÚ QUAN TRỌNG (dễ quên)

- **Đổi prompt SYSTEM trong absa.py → cache LLM vô hiệu → phải chạy lại** (tốn tiền). `prompt_version` đánh dấu bản. Hiện v2-multilang. Evidence 805030 cũ là v1 (mixed Ollama+OpenAI) → cần chạy lại nếu muốn đồng nhất v2.
- **Profile: aspect score TỪ SEED (Agoda 10k review), KHÔNG từ ABSA** (ABSA mẫu nhỏ lệch). ABSA chỉ thêm span (aspect) + style (mới).
- **STYLE tính score chỉ từ POSITIVE** (cặp đối nghĩa, không phải tốt/xấu).
- **Mọi output .json (tags/metadata/profile/objects/evidence) gitignore** — derived, tái sinh bằng script.
