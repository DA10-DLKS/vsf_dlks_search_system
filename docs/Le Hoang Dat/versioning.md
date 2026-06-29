# Quy Tắc Đặt Tên Và Đánh Version Các Index

Tài liệu này quy định cách đặt tên, đánh version và quản lý vòng đời các index trong hệ thống tìm kiếm.

## 1. Nguyên Tắc Chung

- Tên index phải rõ nghĩa, thể hiện đúng ngữ cảnh dữ liệu và mục đích sử dụng.
- Mọi thay đổi có khả năng ảnh hưởng schema, mapping, analyzer, embedding model, pipeline tạo dữ liệu hoặc chất lượng truy vấn phải tạo version mới.
- Không cập nhật trực tiếp vào index production đang phục vụ truy vấn nếu thay đổi có rủi ro làm sai kết quả.
- Ứng dụng nên truy vấn qua alias ổn định thay vì hard-code tên index version.

## 2. Cấu Trúc Tên Index

Định dạng khuyến nghị:

```text
<domain>_<dataset>_<purpose>_v<major>_<minor>_<patch>
```

Trong đó:

- `domain`: nhóm nghiệp vụ hoặc hệ thống, viết thường, không dấu.
- `dataset`: loại dữ liệu chính của index.
- `purpose`: mục đích index, ví dụ `search`, `semantic`, `hybrid`, `logs`, `bm25`.
- `v<major>_<minor>_<patch>`: version index theo semantic versioning.

Ví dụ:

```text
dlks_documents_hybrid_v1_0_0
dlks_products_search_v2_1_0
vsf_faq_semantic_v1_3_2
```

## 3. Quy Tắc Ký Tự

- Chỉ dùng chữ thường `a-z`, số `0-9` và dấu gạch dưới `_`.
- Không dùng dấu cách, tiếng Việt có dấu, ký tự đặc biệt hoặc chữ hoa trong tên index.
- Không đặt tên quá chung chung như `index_v1`, `data_search`, `test_index`.
- Không dùng ngày tháng làm version chính, trừ khi đó là index snapshot hoặc batch theo ngày.

## 4. Quy Tắc Đánh Version

Dùng dạng:

```text
v<major>_<minor>_<patch>
```

### Tăng major

Tăng `major` khi có thay đổi không tương thích ngược:

- Đổi mapping hoặc kiểu dữ liệu của field quan trọng.
- Đổi analyzer, tokenizer hoặc normalizer làm thay đổi cách index/search.
- Đổi embedding model hoặc kích thước vector.
- Đổi logic chunking, ranking, boost hoặc reranking ở mức làm thay đổi hành vi kết quả lớn.
- Loại bỏ field mà code hoặc người dùng đang phụ thuộc.

Ví dụ:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v2_0_0
```

### Tăng minor

Tăng `minor` khi thêm khả năng mới nhưng vẫn tương thích ngược:

- Thêm field mới.
- Thêm analyzer phụ trợ trong khi analyzer cũ vẫn giữ.
- Thêm metadata dùng để filter hoặc ranking.
- Cải tiến pipeline nhưng không phá vỡ contract hiện tại.

Ví dụ:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v1_5_0
```

### Tăng patch

Tăng `patch` khi sửa lỗi nhỏ hoặc reindex lại cùng schema:

- Sửa lỗi dữ liệu sai.
- Bổ sung tài liệu thiếu.
- Reindex do pipeline lỗi tạm thời.
- Điều chỉnh nhỏ không ảnh hưởng schema và contract truy vấn.

Ví dụ:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v1_4_3
```

## 5. Alias

Mỗi index production nên có alias ổn định:

```text
<domain>_<dataset>_<purpose>_current
```

Ví dụ:

```text
dlks_documents_hybrid_current -> dlks_documents_hybrid_v1_5_0
```

Ứng dụng chỉ nên truy vấn alias `*_current`. Khi release version mới, cập nhật alias sang index mới sau khi validate thành công.

## 6. Quy Tắc Riêng Cho BM25 Hotel Index

BM25 hotel index dùng chuẩn:

```text
vsf_hotels_bm25_v<major>_<minor>_<patch>
```

Alias runtime ổn định:

```text
vsf_hotels_bm25_current
```

Ví dụ:

```text
vsf_hotels_bm25_current -> vsf_hotels_bm25_v1_0_0
```

Quy ước biến môi trường:

- `BM25_INDEX`: alias runtime mà API dùng để search, ví dụ `vsf_hotels_bm25_current`.
- `BM25_TARGET_INDEX`: index version mà indexer nạp data vào, ví dụ `vsf_hotels_bm25_v1_0_0`.
- `BM25_ALIAS`: alias sẽ được promote sau validation, mặc định `vsf_hotels_bm25_current`.
- `BM25_PROMOTE_ALIAS`: chỉ promote alias khi đặt `true`.

`travel_bm25` là tên legacy, không dùng cho release mới.

## 7. Index Môi Trường

Nếu cần tách môi trường, thêm suffix môi trường sau `purpose`:

```text
<domain>_<dataset>_<purpose>_<env>_v<major>_<minor>_<patch>
```

Giá trị `env` hợp lệ:

- `dev`
- `staging`
- `prod`

Ví dụ:

```text
dlks_documents_hybrid_dev_v1_5_0
dlks_documents_hybrid_staging_v1_5_0
dlks_documents_hybrid_prod_v1_5_0
```

Nếu hệ thống đã tách cluster theo môi trường, có thể bỏ qua `env` trong tên index để tránh dài dòng.

## 8. Snapshot Hoặc Batch Index

Với index sinh theo batch ngày, dùng ngày ở cuối tên sau version:

```text
<domain>_<dataset>_<purpose>_v<major>_<minor>_<patch>_<yyyymmdd>
```

Ví dụ:

```text
dlks_logs_search_v1_0_0_20260608
```

Không dùng batch date thay cho version vì ngày tạo index không thể hiện mức độ thay đổi schema.

## 9. Metadata Bắt Buộc

Mỗi index nên lưu metadata release kèm theo:

- `index_name`
- `version`
- `created_at`
- `created_by`
- `source_dataset`
- `schema_hash`
- `pipeline_version`
- `embedding_model`, nếu có vector search
- `release_note`

## 10. Quy Trình Release Index

1. Tạo index mới với version mới.
2. Nạp dữ liệu vào index mới.
3. Chạy validation schema, document count, sample queries và quality checks.
4. So sánh kết quả với index current.
5. Cập nhật alias sang index mới nếu đạt yêu cầu.
6. Ghi release note và người thực hiện.
7. Giữ index cũ trong thời gian rollback đã thống nhất.

## 11. Quy Tắc Rollback

- Rollback bằng cách trỏ alias về version index cũ gần nhất đã validate.
- Không xóa index cũ ngay sau release.
- Chỉ xóa index cũ khi đã hết thời gian retention và không còn phụ thuộc rollback.

## 12. Checklist Trước Khi Chuyển Alias

- Tên index đúng format.
- Version tăng đúng loại thay đổi.
- Mapping/schema đã được validate.
- Số lượng document nằm trong ngưỡng kỳ vọng.
- Các query mẫu cho kết quả chấp nhận được.
- Latency và resource usage không vượt ngưỡng.
- Có release note và thông tin rollback.

