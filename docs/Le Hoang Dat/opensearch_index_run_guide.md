# Run guide: index data vao OpenSearch

Tai lieu nay huong dan tao index va nap data sach tu `data/cleaned/` vao OpenSearch bang script BM25 hien co.

## 1. File lien quan

- Mapping OpenSearch: `indexing/bm25_index/index_mapping.json`
- Script index: `indexing/bm25_index/index_bm25.py`
- Thu muc data nguon: `data/cleaned/`
- Index mac dinh: `travel_bm25`
- OpenSearch Dashboard: `http://localhost:5601`

## 2. Bien moi truong

Cac bien can co trong `.env`:

```env
OPENSEARCH_URL=http://localhost:9200
BM25_INDEX=travel_bm25
CLEANED_DATA_DIR=data/cleaned
BULK_CHUNK_SIZE=25
BULK_MAX_CHUNK_BYTES=2097152
```

Trong do:

- `OPENSEARCH_URL`: endpoint OpenSearch.
- `BM25_INDEX`: ten index BM25 can nap data.
- `CLEANED_DATA_DIR`: thu muc chua file JSON da lam sach.
- `BULK_CHUNK_SIZE`: so document gui trong moi bulk request.
- `BULK_MAX_CHUNK_BYTES`: kich thuoc toi da cua moi bulk request, tinh bang byte.

Gia tri `BULK_CHUNK_SIZE=25` va `BULK_MAX_CHUNK_BYTES=2097152` duoc chon de tranh loi circuit breaker khi OpenSearch chay voi heap nho.

## 3. Start OpenSearch

Chay OpenSearch va Dashboard:

```powershell
docker compose up -d opensearch opensearch-dashboard
```

Kiem tra OpenSearch:

```powershell
curl.exe http://localhost:9200
```

Neu OpenSearch tra ve thong tin cluster/name/version la da san sang.

## 4. Tao index bang mapping

Tao index `travel_bm25`:

```powershell
curl.exe -X PUT "http://localhost:9200/travel_bm25" `
  -H "Content-Type: application/json" `
  -d "@indexing/bm25_index/index_mapping.json"
```

Neu index da ton tai va can tao lai tu dau:

```powershell
curl.exe -X DELETE "http://localhost:9200/travel_bm25"
```

Sau do chay lai lenh `PUT` o tren.

Luu y: xoa index se lam mat toan bo document da index trong index do.

## 5. Chay indexer

Set bien moi truong trong PowerShell:

```powershell
$env:OPENSEARCH_URL="http://localhost:9200"
$env:BM25_INDEX="travel_bm25"
$env:CLEANED_DATA_DIR="data/cleaned"
$env:BULK_CHUNK_SIZE="25"
$env:BULK_MAX_CHUNK_BYTES="2097152"
```

Chay script:

```powershell
python indexing/bm25_index/index_bm25.py
```

Ket qua mong doi:

```text
Indexing documents from data/cleaned into travel_bm25...
Bulk chunk size: 25, max chunk bytes: 2097152
Indexed: <n> successfully. Failed: 0
Done.
```

## 6. Kiem tra so document

```powershell
curl.exe "http://localhost:9200/travel_bm25/_count"
```

Neu index thanh cong, `count` phai lon hon `0`.

## 7. Test search nhanh

```powershell
curl.exe -X GET "http://localhost:9200/travel_bm25/_search" `
  -H "Content-Type: application/json" `
  -d "{ `"query`": { `"match`": { `"description`": `"khach san gan bien`" } }, `"size`": 5 }"
```

## 8. Xu ly loi thuong gap

### Loi 429 circuit_breaking_exception

Loi mau:

```text
TransportError(429, 'circuit_breaking_exception', '[parent] Data too large ...')
```

Nguyen nhan: bulk request qua lon so voi heap OpenSearch.

Cach xu ly: giam kich thuoc batch.

```powershell
$env:BULK_CHUNK_SIZE="10"
$env:BULK_MAX_CHUNK_BYTES="1048576"
python indexing/bm25_index/index_bm25.py
```

Neu van gap loi, tiep tuc giam:

```powershell
$env:BULK_CHUNK_SIZE="5"
$env:BULK_MAX_CHUNK_BYTES="524288"
python indexing/bm25_index/index_bm25.py
```

### Count bang 0 sau khi index

Kiem tra theo thu tu:

1. OpenSearch co dang chay khong:

```powershell
curl.exe http://localhost:9200
```

2. Index da duoc tao chua:

```powershell
curl.exe "http://localhost:9200/_cat/indices?v"
```

3. Script dang index vao dung index chua:

```powershell
$env:BM25_INDEX
```

4. Thu muc data co JSON khong:

```powershell
Get-ChildItem data/cleaned -Filter *.json
```

### Loi strict dynamic mapping

Mapping dang dung:

```json
"dynamic": "strict"
```

Neu document co field la hoac sai kieu du lieu, OpenSearch se reject document. Can sua script map field trong `indexing/bm25_index/index_bm25.py` hoac cap nhat mapping neu field moi la hop le.

## 9. Ghi chu van hanh

- Script dung `_id = hotel_id`, nen chay lai se update/upsert document cung hotel thay vi tao trung.
- Khong nen bulk qua lon khi OpenSearch chay local voi heap `512m`.
- Nen tao index bang mapping truoc khi chay script index.
- Khi thay doi mapping/analyzer/schema, nen tao index version moi thay vi sua truc tiep index dang dung.

