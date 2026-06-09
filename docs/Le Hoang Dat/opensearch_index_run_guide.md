# Run guide: index data vào OpenSearch

Tài liệu này hướng dẫn tạo index và nạp dữ liệu sạch từ `data/cleaned/` vào OpenSearch bằng script BM25 hiện có.

## 1. File liên quan

- Mapping OpenSearch: `indexing/bm25_index/index_mapping.json`
- Script index: `indexing/bm25_index/index_bm25.py`
- Thư mục data nguồn: `data/cleaned/`
- Index mặc định: `travel_bm25`
- OpenSearch Dashboard: `http://localhost:5601`

## 2. Biến môi trường

Các biến cần có trong `.env`:

```env
OPENSEARCH_URL=http://localhost:9200
BM25_INDEX=travel_bm25
CLEANED_DATA_DIR=data/cleaned
BULK_CHUNK_SIZE=25
BULK_MAX_CHUNK_BYTES=2097152
```

Trong đó:

- `OPENSEARCH_URL`: endpoint OpenSearch.
- `BM25_INDEX`: tên index BM25 cần nạp data.
- `CLEANED_DATA_DIR`: thư mục chứa file JSON đã làm sạch.
- `BULK_CHUNK_SIZE`: số document gửi trong mỗi bulk request.
- `BULK_MAX_CHUNK_BYTES`: kích thước tối đa của mỗi bulk request, tính bằng byte.

Giá trị `BULK_CHUNK_SIZE=25` và `BULK_MAX_CHUNK_BYTES=2097152` được chọn để tránh lỗi circuit breaker khi OpenSearch chạy local với heap nhỏ.

## 3. Start OpenSearch

Chạy OpenSearch và Dashboard:

```powershell
docker compose up -d opensearch opensearch-dashboard
```

Kiểm tra OpenSearch:

```powershell
curl.exe http://localhost:9200
```

Nếu OpenSearch trả về thông tin cluster, name hoặc version thì service đã sẵn sàng.

## 4. Tạo index bằng mapping

Tạo index `travel_bm25`:

```powershell
curl.exe -X PUT "http://localhost:9200/travel_bm25" `
  -H "Content-Type: application/json" `
  -d "@indexing/bm25_index/index_mapping.json"
```

Nếu index đã tồn tại và cần tạo lại từ đầu:

```powershell
curl.exe -X DELETE "http://localhost:9200/travel_bm25"
```

Sau đó chạy lại lệnh `PUT` ở trên.

Lưu ý: xóa index sẽ làm mất toàn bộ document đã index trong index đó.

## 5. Chạy indexer

Set biến môi trường trong PowerShell:

```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="travel_bm25"
$env:CLEANED_DATA_DIR="data/cleaned"
$env:BULK_CHUNK_SIZE="25"
$env:BULK_MAX_CHUNK_BYTES="2097152"
```

Chạy script:

```powershell
python indexing/bm25_index/index_bm25.py
```

Kết quả mong đợi:

```text
Indexing documents from data/cleaned into travel_bm25...
Bulk chunk size: 25, max chunk bytes: 2097152
Indexed: <n> successfully. Failed: 0
Done.
```

## 6. Kiểm tra số document

```powershell
curl.exe "http://localhost:9200/travel_bm25/_count"
```

Nếu index thành công, `count` phải lớn hơn `0`.

## 7. Test search nhanh

```powershell
curl.exe -X GET "http://localhost:9200/travel_bm25/_search" `
  -H "Content-Type: application/json" `
  -d '{ \"query\": { \"match\": { \"description\": \"khach san gan bien\" } }, \"size\": 5 }'
```

Trong PowerShell, nên bọc JSON bằng dấu nháy đơn `'...'` để giữ nguyên dấu nháy kép `"` bên trong JSON. Nếu dùng dấu nháy kép bên ngoài JSON, PowerShell có thể làm mất quote và OpenSearch sẽ báo lỗi `json_parse_exception`.

## 8. Xử lý lỗi thường gặp

### Lỗi 429 circuit_breaking_exception

Lỗi mẫu:

```text
TransportError(429, 'circuit_breaking_exception', '[parent] Data too large ...')
```

Nguyên nhân: bulk request quá lớn so với heap OpenSearch.

Cách xử lý: giảm kích thước batch.

```powershell
$env:BULK_CHUNK_SIZE="10"
$env:BULK_MAX_CHUNK_BYTES="1048576"
python indexing/bm25_index/index_bm25.py
```

Nếu vẫn gặp lỗi, tiếp tục giảm:

```powershell
$env:BULK_CHUNK_SIZE="5"
$env:BULK_MAX_CHUNK_BYTES="524288"
python indexing/bm25_index/index_bm25.py
```

### Count bằng 0 sau khi index

Kiểm tra theo thứ tự:

1. OpenSearch có đang chạy không:

```powershell
curl.exe http://localhost:9200
```

2. Index đã được tạo chưa:

```powershell
curl.exe "http://localhost:9200/_cat/indices?v"
```

3. Script đang index vào đúng index chưa:

```powershell
$env:BM25_INDEX
```

4. Thư mục data có JSON không:

```powershell
Get-ChildItem data/cleaned -Filter *.json
```

### Lỗi strict dynamic mapping

Mapping đang dùng:

```json
"dynamic": "strict"
```

Nếu document có field lạ hoặc sai kiểu dữ liệu, OpenSearch sẽ reject document. Cần sửa script map field trong `indexing/bm25_index/index_bm25.py` hoặc cập nhật mapping nếu field mới là hợp lệ.

### Lỗi JSON parse khi test search

Nếu gặp lỗi dạng:

```text
json_parse_exception
curl: Could not resolve host
```

Nguyên nhân thường là quote JSON sai trong PowerShell. Dùng lại mẫu ở phần "Test search nhanh", trong đó JSON được bọc bằng dấu nháy đơn `'...'`.

## 9. Ghi chú vận hành

- Script dùng `_id = hotel_id`, nên chạy lại sẽ update hoặc upsert document cùng hotel thay vì tạo trùng.
- Không nên bulk quá lớn khi OpenSearch chạy local với heap `512m`.
- Nên tạo index bằng mapping trước khi chạy script index.
- Khi thay đổi mapping, analyzer hoặc schema, nên tạo index version mới thay vì sửa trực tiếp index đang dùng.
