# Validation Rules — Quy tắc kiểm định schema & chất lượng

> Owner: Đỗ Minh Hiếu (Data Quality) — Sprint 1
> Nguồn schema: `contracts/data_schema.json` (CONTRACT với DA09).
> Metric cam kết: **Missing Rate < 5%**, **Duplicate Rate < 2%**.

## TODO(hieudm): Hoàn thiện rule bên dưới

### 1. Validate schema bắt buộc
- [ ] Mọi `required` field trong `data_schema.json` phải tồn tại & không rỗng.
- [ ] Type check: string / number / boolean / array / object theo schema.
- [ ] Enum check: giá trị phải nằm trong tập cho phép.
- [ ] Format check: `date` (ISO 8601), `url`, `email`...

### 2. Phân loại severity
- [ ] **Error** (drop doc): thiếu field bắt buộc, sai type, vi phạm enum.
- [ ] **Warning** (giữ doc): field optional bị thiếu, độ dài vượt khuyến nghị.

### 3. Quy tắc riêng theo doc_type
- [ ] **hotel/resort**: bắt buộc có `name`, `address`, `latitude`, `longitude`, `star_rating`.
- [ ] **attraction**: bắt buộc có `name`, `category`, `location`.
- [ ] **faq**: bắt buộc có `question`, `answer`.
- [ ] **review**: cảnh báo nếu `rating` ngoài [1, 5].

### 4. Đo Missing Rate
- [ ] Công thức: `missing_count / (total_docs * num_required_fields)`.
- [ ] Báo cáo chi tiết theo từng field (`missing_by_field`).
- [ ] Cảnh báo khi `> 3%` (gần ngưỡng 5%).

### 5. Đo Duplicate Rate
- [ ] Dùng kết quả từ `scripts/dedup_pipeline.py` (`data/dedup_groups.json`).
- [ ] Công thức: `(tổng doc bị loại vì trùng) / total_docs`.
- [ ] Báo cáo số nhóm trùng (`duplicate_group_count`).

### 6. Quarantine
- [ ] Doc lỗi error được ghi vào `data/quarantine/` cùng lý do (JSON).
- [ ] Doc cảnh báo warning vẫn đi tiếp nhưng flag trong metadata.

## Tham chiếu
- Code: `ingestion/validation/schema_validator.py`, `ingestion/validation/quality_checks.py`
- Pipeline: `scripts/validation_pipeline.py`
- Báo cáo: `quality_report_mock.md` (Sprint 2), `data_quality_report.md` (Sprint 3)
