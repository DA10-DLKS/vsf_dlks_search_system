# Sprint 2 — Bước 1b: Audit & vá surface_forms

> Trả lời câu hỏi "ontology đã hiểu liên kết đồng nghĩa chưa" (vd 'sang/xịn/luxury'→luxury).
> Audit CÓ HỆ THỐNG (không đoán lẻ) các surface form còn thiếu, duyệt, vá. Ngày: 2026-06-08.

## Cách audit (3 nguồn, theo quyết định user)
1. **Data corpus** — tag/description 520 hotel (văn phong formal nhà bán).
2. **Golden query** — 32 câu (văn phong người dùng). *Lưu ý:* n-gram thô trên golden tạo
   nhiều noise (tên riêng "vinpearl"/"phú quốc", token vỡ "khach"/"san", intent "vui chơi")
   → KHÔNG nhồi thẳng; chỉ dùng để soi cụm thật sự thiếu.
3. **Biến thể tiếng Việt** — sinh per-concept có kiểm soát (từ trần vs ghép, viết tắt, khẩu ngữ).

→ Bài học: "vá hết" KHÔNG làm bằng quét cơ học rồi nhồi (sẽ nhồi tên riêng + stopword).
Làm bằng probe per-concept: với mỗi concept hay-bị-hỏi, đối chiếu biến thể thường gặp của
riêng nó → 59 ứng viên sạch.

## Duyệt: thêm ~45 / bỏ ~14
**✅ Thêm (rõ nghĩa, đúng concept):** PRICE_LUXURY(sang, siêu sang, vip, xa xỉ, đẳng cấp quốc tế) ·
PRICE_UPSCALE(khá sang) · PRICE_MID(vừa tiền, giá vừa) · PRICE_BUDGET(rẻ, giá mềm, phải chăng,
giá sinh viên) · STYLE_LUXURY(sang, xịn sò, hoành tráng) · STYLE_QUIET(yên bình, ít ồn) ·
STYLE_MODERN(tân tiến, trẻ trung) · STYLE_ROMANTIC(tình tứ, hẹn hò, tuần trăng mật) ·
OBJ_RESORT(khu resort, resort nghỉ dưỡng) · OBJ_HOMESTAY(ở nhà dân) · OBJ_VILLA(biệt thự biển,
villa nghỉ dưỡng) · AMEN_SEA_VIEW(phòng view biển) · AMEN_SPA(tắm khoáng) · AMEN_WIFI(wi fi) ·
AMEN_RESTAURANT(ăn sáng, buffet) · AMEN_PET_FRIENDLY(cho mang thú cưng, mang chó mèo) ·
PURPOSE_FAMILY(con nhỏ) · PURPOSE_ROMANTIC(tuần trăng mật) · SETTING_COASTAL(ngay biển).

**❌ Bỏ — kèm lý do:**
- **"5 sao / 4 sao / 3 sao..."**: số sao là **range_filter** (star_rating), KHÔNG phải concept giá.
  "5 sao"≠luxury (có resort 5 sao giá trung). Map vào PRICE = sai chất → xử lý ở Bước 3.
- **"đỉnh / chất / mới / tĩnh / vắng / cao cấp nhất"**: quá mơ hồ/đa nghĩa → dễ match nhầm.
- **"bơi"** (trần): quá ngắn → match "bơi lội/biết bơi"; giữ "hồ bơi/bể bơi".

## Kết quả
- Ví dụ gốc user: **"sang" → [PRICE_LUXURY, STYLE_LUXURY]** ✅ (trước = None).
- synonym_dictionary: 1432 → **1497 form**. core vẫn 419 concept, 0 ID trùng, 0 target sai.
- "5 sao" vẫn → None (đúng chủ đích).
- mapper tag KHÔNG đổi: form mới là cách *query* gõ (ích lợi ở tầng hiểu-query của Anh Tài),
  không xuất hiện trong description hotel nên không tăng tagging.

## Còn lại
Đây là vá ĐỢT 1 (nhóm hay-bị-hỏi: price/style/object/amenity phổ biến). Vốn từ là tập mở —
đợt sau bổ sung khi có **query log thật** (DA09) cho thấy cách gõ thực tế chưa phủ.
