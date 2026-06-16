# Đánh giá query_demo trên golden_set_v1 (Sprint 2)

**Ngày:** 2026-06-16
**Người chạy:** Trương Anh Long (KE, DA10)
**Công cụ:** `knowledge_engineering/enrichment/query_demo.py` (hàm `search`, top_k=10)
**Ground-truth:** `data/golden_dataset/golden_set_v1.json` (70 query, đều `hotel_search`, đều có `relevant_hotel_ids`)
**Mục đích:** đo chất lượng nhãn STYLE/concept sau đợt ABSA backfill (nhánh `feature/sprint2-absa-style-recall`), và phân định lỗi nào do hệ thống vs do golden.

> ⚠️ Đây là đo **chất lượng filter theo concept** (mô phỏng tầng search bằng metadata), KHÔNG phải đo retrieval cuối (chưa có embedding/hybrid). Nhiều câu "mô tả ngữ nghĩa" (style, giá) lẽ ra do vector đảm nhận — kết quả thấp ở các nhóm đó KHÔNG có nghĩa hệ thống cuối sẽ thấp.

---

## 1. Kết quả tổng

| Chỉ số | Giá trị |
|---|---|
| Recall@5 trung bình | **33.8%** |
| Recall@10 trung bình | **54.2%** |
| Query lỗi nặng (rec@10 < 30%) | **18 / 70** |

### Theo nhóm chức năng

| Nhóm | Query | Rec@10 | Lỗi nặng | Nhận định |
|---|---|---|---|---|
| A. LMK/Location (GS-001–010) | 10 | **90%** | 0 | ✅ Tốt |
| D. Amenity (GS-031–040) | 10 | **89%** | 0 | ✅ Tốt |
| G. Quality/Service (GS-061–070) | 10 | **74%** | 0 | ✅ Khá |
| C. Purpose/demographics (GS-021–030) | 10 | 34% | 3 | ⚠️ Trung bình |
| F. Combo (GS-051–060) | 10 | 38% | 5 | ❌ Yếu |
| E. Price tier (GS-041–050) | 10 | 33% | 5 | ❌ Yếu |
| B. STYLE thuần (GS-011–020) | 10 | 22% | 5 | ❌ Yếu |

**Quan sát chính:** các nhóm dựa trên dữ liệu structured rõ ràng (location, amenity, quality) đạt 74–90%. Các nhóm dựa trên *cảm nhận ngữ nghĩa* (style, price tier, combo) thấp — đây là vùng lẽ ra do embedding/vector đảm nhận, không phải metadata-filter.

---

## 2. Phân định nguyên nhân 18 query lỗi nặng

### 2.1. LỖI DO GOLDEN — trộn STYLE ↔ PRICE cho cùng từ ngữ (nghiêm trọng nhất)

Golden dùng các câu **gần như đồng nghĩa** nhưng gán hotel theo **tiêu chí khác nhau** (xem `notes` của labeler):

| Query | Câu | Golden chấm theo |
|---|---|---|
| GS-013 | "sang trọng, đẳng cấp **xa hoa**" | `STYLE_LUXURY` (review) |
| GS-047 | "sang trọng, **xa hoa** đẳng cấp" | `PRICE_LUXURY` (giá) |
| GS-045 | "**cao cấp**, hạng sang premium" | `PRICE_UPSCALE` (tier giá) |
| GS-046 | "**cao cấp** ở Nha Trang" | `PRICE_UPSCALE` (giá) |

**Bằng chứng:**
- GS-013 vs GS-047 câu chữ gần giống hệt → query_demo parse **y hệt** (cùng concept, cùng 54 hit) nhưng golden chỉ trùng 3/10 hotel.
- GS-046 golden gán hotel có `STYLE_LUXURY = 0.0` (463095, 36919571, 869046…) — tức chấm theo giá, không theo phong cách review.
- query_demo trả hotel có STYLE_LUXURY cao 0.7–0.84 (đúng nghĩa "phong cách sang") → lệch golden vì golden đo *giá*.

**Kết luận:** từ "sang trọng / cao cấp" vốn **nhập nhằng STYLE↔PRICE**; người dùng thật không phân biệt được. Golden ép mỗi câu một tiêu chí → không phản ánh ý người dùng. **Cần thống nhất lại với labeler.**

Query dính: GS-013, GS-045, GS-046, GS-047, GS-049, GS-052, GS-057, GS-059, GS-060.

### 2.2. LỖI DO TA — concept corpus thiếu / chưa làm (đã biết, có kế hoạch)

| Query | Concept | Tình trạng |
|---|---|---|
| GS-015 | STYLE_LIVELY | corpus gần như không có hotel "sôi động" (đã xác nhận) |
| GS-019 | STYLE_VINTAGE | corpus thiếu (1 hotel duy nhất vintage) |
| GS-016 | STYLE_AESTHETIC | phủ surface_form chỉ 7% → chưa backfill (cần embedding) |
| GS-020 | STYLE_BOUTIQUE | recall ổn (97%) nhưng chỉ ~9 hotel toàn corpus → ít kết quả |

→ Hướng giải: các concept "thưa/đa dạng" này thuộc về **embedding tầng retrieval**, không ép bằng STYLE score. AESTHETIC tạm gác.

### 2.3. GS-011 — đa-STYLE: ĐÃ SỬA logic, phần còn lại là golden lệch

**GS-011** "khách sạn yên tĩnh, ít ồn ào **để nghỉ dưỡng**": ban đầu rec@10 = 0%.

**Chuỗi nguyên nhân (từ form "nghỉ dưỡng" thêm đợt này):** "nghỉ dưỡng" map đa-concept → kéo theo `STYLE_RELAXING` + `PURPOSE_WELLNESS`. Ba tầng tác động đẩy hotel yên-tĩnh-thuần xuống:
1. **Lọc:** AND mọi STYLE (QUIET∧RELAXING ≥0.6) → loại hotel quiet-cao/relaxing-thấp.
2. **Rank (feel):** feel_score cộng dồn QUIET+RELAXING → hotel relaxing-cao vượt lên.
3. **Rank (purpose):** PURPOSE_WELLNESS → purpose_amen={AMEN_SPA, STYLE_QUIET}; hotel có cả SPA+QUIET-tag được purpose_hit cao hơn.

**ĐÃ SỬA (query_demo.py) tầng 1+2:**
- Lọc STYLE: hotel chỉ cần đạt style MẠNH NHẤT ≥ ngưỡng (max thay vì AND); ASPECT giữ AND.
- Rank STYLE: `_feel_scores` dùng max(STYLE) + `STYLE_RANK_EPS`·(phần còn lại) thay vì cộng dồn.
- Kết quả: GS-048 50%→67%, GS-011 0%→10%, KHÔNG query nào tụt (tổng 54.2%→54.6%).

**KHÔNG sửa tiếp tầng 3** (purpose_amen) — vì kiểm chứng net-review cho thấy **golden GS-011 KHÔNG chuẩn hơn search**: GS-011 không có location filter (toàn quốc) → RẤT nhiều hotel yên tĩnh đạt chuẩn; golden chọn 10, search chọn 10 khác (top search 36224135 net+33, 338256 net+17 — yên tĩnh thật, chỉ KHÔNG trùng golden). Recall thấp ở đây = "nhiều đáp án đúng, hai bên chọn khác", KHÔNG phải search sai. Sửa purpose_amen để ép khớp golden = tối ưu mù + hại các query wellness khác. (Lỗi nhỏ thật: hotel 44777877 net−2 lọt top do quiet-score=0.95 nhưng thực tế ồn — vấn đề chất-lượng-score-1-hotel, không phải ranking.)

### 2.4. LỖI HỖN HỢP — Purpose romantic/business thưa

GS-023/024 ("cặp đôi hẹn hò / tuần trăng mật", nHit=1), GS-029 ("công tác"): concept STYLE_ROMANTIC/PURPOSE thưa + golden gán rộng. Một phần do recall thưa (giống RELAXING/ROMANTIC ở 2.2), một phần golden gán hotel ít tín hiệu.

---

## 3. Dấu hiệu bất thường về số kết quả (nHit)

| nHit | Query | Ý nghĩa |
|---|---|---|
| 520 (không lọc) | GS-016, GS-041, GS-043 | concept "chết"/feel_skipped → không lọc được gì, trả cả corpus |
| 0–2 (lọc quá chặt) | GS-015, GS-020, GS-023, GS-024, GS-049, GS-059, GS-060 | feel ≥0.6 + concept thưa → gần như rỗng |

→ Hai cực này đều là triệu chứng "metadata-filter không hợp với câu ngữ nghĩa", củng cố nhận định: style/price cần embedding.

---

## 4. Kết luận & khuyến nghị

1. **Hệ thống vững ở phần có dữ liệu structured** (LMK 90%, Amenity 89%, Quality 74%) — không có lỗi nặng nào.

2. **Phần lớn 18 lỗi nặng KHÔNG phải hệ thống sai:**
   - 9 query do **golden trộn STYLE↔PRICE** (lỗi thiết kế nhãn) → cần thống nhất với labeler.
   - 4 query do concept corpus thiếu/chưa làm (đã có kế hoạch embedding).

3. **Một regression thật cần sửa: GS-011** — form "nghỉ dưỡng" thêm vào RELAXING làm loãng query QUIET. Cách cộng feel_score đa-STYLE cần xem lại.

4. **Phản hồi cho người gán golden (Kiên):**
   - Nhóm Price/Luxury (GS-013/045/046/047/049…): thống nhất "sang trọng/cao cấp" đo theo STYLE hay PRICE — hiện mỗi câu một kiểu.
   - Cân nhắc bỏ/đánh dấu các concept corpus không có (LIVELY, VINTAGE) để không tính là miss oan.

> Lưu ý phương pháp: golden_set_v1 phần lớn được sinh TỪ chính pipeline (xem notes labeler dùng STYLE/PRICE score hiện có), nên thừa hưởng vài thiếu sót của pipeline. Khi đối chiếu, ưu tiên kiểm chứng bằng **review thật** (net-review) cho các ca nghi ngờ, không tin golden tuyệt đối.
