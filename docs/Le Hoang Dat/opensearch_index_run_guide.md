# Run guide: index data vào OpenSearch

Tài liệu này hướng dẫn tạo BM25 index version mới, nạp dữ liệu sạch từ `data/cleaned/` vào OpenSearch, validate, rồi promote alias cho runtime search.

## 1. Quy Ước Tên BM25 Index

Chuẩn mới:

```text
Versioned index: vsf_hotels_bm25_v<major>_<minor>_<patch>
Runtime alias:   vsf_hotels_bm25_current
```

Ví dụ:

```text
vsf_hotels_bm25_v1_0_0
vsf_hotels_bm25_v1_1_0
vsf_hotels_bm25_current -> vsf_hotels_bm25_v1_1_0
```

`travel_bm25` là tên legacy, không dùng cho release mới.

## 2. File Liên Quan

- Mapping OpenSearch: `indexing/bm25_index/index_mapping.json`
- Script index: `indexing/bm25_index/index_bm25.py`
- Thư mục data nguồn: `data/cleaned/`
- OpenSearch Dashboard: `http://localhost:5601`

## 3. Biến Môi Trường

Các biến cần có trong `.env`:

```env
OPENSEARCH_URL=http://localhost:9200
BM25_INDEX=vsf_hotels_bm25_current
BM25_TARGET_INDEX=vsf_hotels_bm25_v1_0_0
BM25_ALIAS=vsf_hotels_bm25_current
BM25_PROMOTE_ALIAS=false
CLEANED_DATA_DIR=data/cleaned
BULK_CHUNK_SIZE=25
BULK_MAX_CHUNK_BYTES=2097152
```

Trong đó:

- `BM25_INDEX`: alias runtime mà API dùng để search.
- `BM25_TARGET_INDEX`: index version đích mà indexer sẽ nạp dữ liệu vào.
- `BM25_ALIAS`: alias ổn định sẽ được promote sang target index.
- `BM25_PROMOTE_ALIAS`: chỉ promote alias khi đặt `true`.

## 4. Start OpenSearch

```powershell
docker compose up -d opensearch opensearch-dashboard
```

Kiểm tra OpenSearch:

```powershell
curl.exe http://localhost:9200
```

## 5. Tạo Index Version Mới

Ví dụ tạo version đầu tiên:

```powershell
curl.exe -X PUT "http://localhost:9200/vsf_hotels_bm25_v1_0_0" `
  -H "Content-Type: application/json" `
  -d "@indexing/bm25_index/index_mapping.json"
```

Không tạo dữ liệu mới trực tiếp vào alias `vsf_hotels_bm25_current`. Alias chỉ dùng để runtime search và rollback/promote.

## 6. Index Data Vào Target Version

Set biến môi trường:

```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="vsf_hotels_bm25_current"
$env:BM25_TARGET_INDEX="vsf_hotels_bm25_v1_0_0"
$env:BM25_ALIAS="vsf_hotels_bm25_current"
$env:BM25_PROMOTE_ALIAS="false"
$env:CLEANED_DATA_DIR="data/cleaned"
$env:BULK_CHUNK_SIZE="25"
$env:BULK_MAX_CHUNK_BYTES="2097152"
```

Chạy indexer:

```powershell
venv\Scripts\python.exe indexing\bm25_index\index_bm25.py
```

Lưu ý quan trọng: khi index data, bắt buộc set `BM25_TARGET_INDEX` là index version thật, ví dụ `vsf_hotels_bm25_v1_0_0`. Không index trực tiếp vào alias `vsf_hotels_bm25_current`. Alias này chỉ tồn tại sau bước promote.

Kết quả mong đợi:

```text
Runtime BM25 index/alias: vsf_hotels_bm25_current
Target BM25 index: vsf_hotels_bm25_v1_0_0
Alias promotion: False (vsf_hotels_bm25_current -> vsf_hotels_bm25_v1_0_0)
Indexed: <n> successfully. Failed: 0
Done.
```

## 7. Validate Trước Khi Promote

Kiểm tra số document:

```powershell
curl.exe "http://localhost:9200/vsf_hotels_bm25_v1_0_0/_count"
```

Test search nhanh trên target version:

```powershell
curl.exe -X GET "http://localhost:9200/vsf_hotels_bm25_v1_0_0/_search" `
  -H "Content-Type: application/json" `
  -d '{ \"query\": { \"match\": { \"description\": \"khach san gan bien\" } }, \"size\": 5 }'
```

Trong PowerShell, các dấu nháy kép bên trong JSON cần được escape như mẫu trên để tránh lỗi parse JSON hoặc lỗi `curl: Could not resolve host`.

## 8. Promote Alias Sau Khi Validate Đạt

Chỉ promote khi index thành công và validation đạt:

```powershell
$env:BM25_PROMOTE_ALIAS="true"
venv\Scripts\python.exe indexing\bm25_index\index_bm25.py
```

Script chỉ promote alias khi bulk không có failed docs. Nếu có lỗi, alias sẽ không đổi.

Kiểm tra alias:

```powershell
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
```

Sau khi promote, API vẫn dùng:

```env
BM25_INDEX=vsf_hotels_bm25_current
```

## 9. Rollback

Rollback bằng cách trỏ alias về version cũ:

```powershell
curl.exe -X POST "http://localhost:9200/_aliases" `
  -H "Content-Type: application/json" `
  -d '{ \"actions\": [ { \"remove\": { \"index\": \"*\", \"alias\": \"vsf_hotels_bm25_current\" } }, { \"add\": { \"index\": \"vsf_hotels_bm25_v1_0_0\", \"alias\": \"vsf_hotels_bm25_current\" } } ] }'
```

Không xóa index cũ ngay sau release để còn rollback.

## 10. Khi Nào Tăng Version

- Tăng `major`: đổi mapping, analyzer, kiểu dữ liệu field hoặc thay đổi breaking.
- Tăng `minor`: thêm field, thêm data source tương thích, thêm metadata phục vụ filter/ranking.
- Tăng `patch`: reindex cùng schema, sửa dữ liệu, bổ sung dữ liệu thiếu.

Ví dụ:

```text
vsf_hotels_bm25_v1_0_0 -> vsf_hotels_bm25_v1_0_1
vsf_hotels_bm25_v1_0_1 -> vsf_hotels_bm25_v1_1_0
vsf_hotels_bm25_v1_1_0 -> vsf_hotels_bm25_v2_0_0
```

## 11. Troubleshooting

### Lỗi 404 `vsf_hotels_bm25_current`

Lỗi này thường xảy ra trong 2 trường hợp:

1. Alias `vsf_hotels_bm25_current` chưa được promote lần nào.
2. Khi chạy indexer, bạn chưa set `BM25_TARGET_INDEX`, nên script fallback sang `BM25_INDEX=vsf_hotels_bm25_current` và cố index vào alias chưa tồn tại.

Cách xử lý đúng:

1. Tạo index version thật:

```powershell
curl.exe -X PUT "http://localhost:9200/vsf_hotels_bm25_v1_0_0" `
  -H "Content-Type: application/json" `
  -d "@indexing/bm25_index/index_mapping.json"
```

2. Set target index là version thật, chưa promote alias:

```powershell
$env:BM25_INDEX="vsf_hotels_bm25_current"
$env:BM25_TARGET_INDEX="vsf_hotels_bm25_v1_0_0"
$env:BM25_ALIAS="vsf_hotels_bm25_current"
$env:BM25_PROMOTE_ALIAS="false"
venv\Scripts\python.exe indexing\bm25_index\index_bm25.py
```

3. Validate count trên index version:

```powershell
curl.exe "http://localhost:9200/vsf_hotels_bm25_v1_0_0/_count"
```

4. Promote alias sau khi validate đạt:

```powershell
$env:BM25_PROMOTE_ALIAS="true"
venv\Scripts\python.exe indexing\bm25_index\index_bm25.py
```

5. Kiểm tra alias:

```powershell
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
```

### Lỗi target index chưa tồn tại

Nếu script báo:

```text
Index vsf_hotels_bm25_v1_0_0 does not exist.
```

Cần tạo index bằng mapping trước khi chạy indexer.

### Lỗi 429 circuit_breaking_exception

Giảm batch size:

```powershell
$env:BULK_CHUNK_SIZE="10"
$env:BULK_MAX_CHUNK_BYTES="1048576"
venv\Scripts\python.exe indexing\bm25_index\index_bm25.py
```

### Search qua API trả rỗng

Kiểm tra alias có đang trỏ đúng index không:

```powershell
curl.exe "http://localhost:9200/_alias/vsf_hotels_bm25_current"
```

Kiểm tra runtime env:

```powershell
$env:BM25_INDEX
```
