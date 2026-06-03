# Cleaning Rules — Quy tắc làm sạch văn bản

> Owner: Đỗ Minh Hiếu (Data Quality) — Sprint 1
> Áp dụng cho: tất cả tài liệu đi vào `data/cleaned/`.
> Nguồn schema: `contracts/data_schema.json` (CONTRACT với DA09).

## TODO(hieudm): Hoàn thiện rule bên dưới

### 1. Chuẩn hóa Unicode
- [ ] Áp dụng **NFC normalization** cho toàn bộ text.
- [ ] Quy ước: text tiếng Việt **giữ nguyên dấu** (không strip diacritics).

### 2. Xử lý HTML
- [ ] Parser mặc định: `BeautifulSoup(html, "lxml")`.
- [ ] Loại bỏ thẻ: `<script>`, `<style>`, `<iframe>`, `<noscript>`.
- [ ] Giữ lại block: `<p>`, `<li>`, `<br>`, `<h1-6>` — nối bằng `\n`.
- [ ] Trích `src` của `<img>` vào `image_urls`.
- [ ] Trích `(text, href)` của `<a>` vào `links`.

### 3. Ký tự điều khiển & whitespace
- [ ] Loại bỏ ký tự thuộc Unicode category `Cc` (trừ `\n`, `\t` hợp lệ).
- [ ] Collapse nhiều khoảng trắng / xuống dòng liên tiếp thành 1 space.
- [ ] Strip đầu-cuối (mặc định **bật**, có thể tắt bằng `strip=False`).

### 4. Dấu câu & ký tự đặc biệt
- [ ] Thống nhất `'` `'` `"` `"` `…` `--`...
- [ ] Chuẩn hóa dấu gạch nối Unicode (U+2010..U+2015) về ASCII `-` **có chọn lọc** (giữ nguyên nếu thuộc tên riêng).

### 5. Tiếng Việt
- [ ] Không lowercase bắt buộc (`preserve_case=True` mặc định) để giữ tên riêng.
- [ ] Cân nhắc tách `vd:`, `ví dụ:`, `i.e.`... thành token chuẩn.

### 6. Edge cases cần xử lý
- [ ] HTML rỗng / chỉ chứa ảnh.
- [ ] Text chỉ chứa whitespace / control chars.
- [ ] Text có emoji — **giữ nguyên**.
- [ ] Text dài > 1 MB — cảnh báo + tách thành nhiều chunk trước khi đẩy xuống layer 3.

## Tham chiếu
- Code: `ingestion/cleaning/text_normalizer.py`, `ingestion/cleaning/html_stripper.py`
- Pipeline: `scripts/clean_pipeline.py`
