# Compliance Notes — Ghi chú tuân thủ crawl

> Owner: Đỗ Minh Hiếu (Data Quality) — Sprint 1
> Phản hồi Mentor #8: kiểm tra **robots.txt, ToS, bản quyền, PII** cho dữ liệu crawl.

## TODO(hieudm): Hoàn thiện nội dung bên dưới

### 1. robots.txt
- [ ] Liệt kê từng domain crawl mục tiêu và trạng thái robots.txt.
- [ ] Ghi rõ `Allow` / `Disallow` path cho từng crawler (vd: `/blog` được phép, `/user/*` thì không).
- [ ] Ghi rõ `Crawl-delay` (nếu có) và áp dụng vào crawler.

### 2. Terms of Service (ToS)
- [ ] Từng website có **cho phép crawl công khai** với mục đích phi thương mại / nghiên cứu?
- [ ] Có yêu cầu xin phép / ghi credit nguồn?
- [ ] Có giới hạn số request / IP / ngày?

### 3. Bản quyền
- [ ] Xác định nội dung nào là bản quyền (bài báo, ảnh editorial).
- [ ] Chính sách sử dụng hợp lý (fair use) cho mục đích RAG nội bộ.
- [ ] Ghi nguồn (`source_url`, `crawled_at`) cho từng document.

### 4. PII (Personally Identifiable Information)
- [ ] Rà soát field `author`, `reviewer_name`, `email`, `phone` trong data crawl.
- [ ] Có cần hash / xoá trước khi lưu?
- [ ] Áp dụng regex phát hiện email/SĐT Việt Nam trong nội dung review.

### 5. Lưu trữ & truy cập
- [ ] Dữ liệu crawl lưu ở đâu, ai có quyền truy cập?
- [ ] Retention policy (vd: 12 tháng, sau đó refresh).

## Checklist trước khi crawl một domain mới
- [ ] Đã đọc `robots.txt` và ToS.
- [ ] Đã thêm domain vào danh sách được phép trong issue/PR.
- [ ] Đã bật rate-limit hợp lý (vd: 1 req/giây).
- [ ] Đã đăng ký User-Agent có email liên hệ.

## Tham chiếu
- Cập nhật: `docs/03_data_sources.md` (TODO phối hợp với team crawler)
- Code liên quan: `ingestion/connectors/`
