# Quy tac dat ten va danh version cac index

Tai lieu nay quy dinh cach dat ten, danh version va quan ly vong doi cac index trong he thong tim kiem.

## 1. Nguyen tac chung

- Ten index phai ro nghia, the hien dung ngu canh du lieu va muc dich su dung.
- Moi thay doi co kha nang anh huong schema, mapping, analyzer, embedding model, pipeline tao du lieu hoac chat luong truy van phai tao version moi.
- Khong cap nhat truc tiep vao index production dang phuc vu truy van neu thay doi co rui ro lam sai ket qua.
- Su dung alias de tro den version index dang active thay vi hard-code ten index version trong code ung dung.

## 2. Cau truc ten index

Dinh dang khuyen nghi:

```text
<domain>_<dataset>_<purpose>_v<major>_<minor>_<patch>
```

Trong do:

- `domain`: nhom nghiep vu hoac he thong, viet thuong, khong dau.
- `dataset`: loai du lieu chinh cua index.
- `purpose`: muc dich index, vi du `search`, `semantic`, `hybrid`, `logs`.
- `v<major>_<minor>_<patch>`: version index theo semantic versioning.

Vi du:

```text
dlks_documents_hybrid_v1_0_0
dlks_products_search_v2_1_0
vsf_faq_semantic_v1_3_2
```

## 3. Quy tac ky tu

- Chi dung chu thuong `a-z`, so `0-9` va dau gach duoi `_`.
- Khong dung dau cach, tieng Viet co dau, ky tu dac biet hoac chu hoa.
- Khong dat ten qua chung chung nhu `index_v1`, `data_search`, `test_index`.
- Khong dung ngay thang lam version chinh, tru khi do la index snapshot hoac batch theo ngay.

## 4. Quy tac danh version

Dung dang:

```text
v<major>_<minor>_<patch>
```

### Tang major

Tang `major` khi co thay doi khong tuong thich nguoc:

- Doi mapping hoac kieu du lieu cua field quan trong.
- Doi analyzer, tokenizer, normalizer lam thay doi cach index/search.
- Doi embedding model hoac kich thuoc vector.
- Doi logic chunking, ranking, boost, reranking o muc lam thay doi hanh vi ket qua lon.
- Loai bo field ma code hoac nguoi dung dang phu thuoc.

Vi du:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v2_0_0
```

### Tang minor

Tang `minor` khi them kha nang moi nhung van tuong thich nguoc:

- Them field moi.
- Them analyzer phu tro trong khi analyzer cu van giu.
- Them metadata dung de filter hoac ranking.
- Cai tien pipeline nhung khong pha vo contract hien tai.

Vi du:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v1_5_0
```

### Tang patch

Tang `patch` khi sua loi nho hoac reindex lai cung schema:

- Sua loi du lieu sai.
- Bo sung tai lieu thieu.
- Reindex do pipeline loi tam thoi.
- Dieu chinh nho khong anh huong schema va contract truy van.

Vi du:

```text
dlks_documents_hybrid_v1_4_2 -> dlks_documents_hybrid_v1_4_3
```

## 5. Alias

Moi index production nen co alias on dinh:

```text
<domain>_<dataset>_<purpose>_current
```

Vi du:

```text
dlks_documents_hybrid_current -> dlks_documents_hybrid_v1_5_0
```

Ung dung chi nen truy van alias `*_current`. Khi release version moi, cap nhat alias sang index moi sau khi validate thanh cong.

## 6. Index moi truong

Neu can tach moi truong, them suffix moi truong sau `purpose`:

```text
<domain>_<dataset>_<purpose>_<env>_v<major>_<minor>_<patch>
```

Gia tri `env` hop le:

- `dev`
- `staging`
- `prod`

Vi du:

```text
dlks_documents_hybrid_dev_v1_5_0
dlks_documents_hybrid_staging_v1_5_0
dlks_documents_hybrid_prod_v1_5_0
```

Neu he thong da tach cluster theo moi truong, co the bo qua `env` trong ten index de tranh dai dong.

## 7. Snapshot hoac batch index

Voi index sinh theo batch ngay, dung ngay o cuoi ten sau version:

```text
<domain>_<dataset>_<purpose>_v<major>_<minor>_<patch>_<yyyymmdd>
```

Vi du:

```text
dlks_logs_search_v1_0_0_20260608
```

Khong dung batch date thay cho version vi ngay tao index khong noi len muc do thay doi schema.

## 8. Metadata bat buoc

Moi index nen luu metadata release kem theo:

- `index_name`
- `version`
- `created_at`
- `created_by`
- `source_dataset`
- `schema_hash`
- `pipeline_version`
- `embedding_model`, neu co vector search
- `release_note`

## 9. Quy trinh release index

1. Tao index moi voi version moi.
2. Nap du lieu vao index moi.
3. Chay validation schema, document count, sample queries va quality checks.
4. So sanh ket qua voi index current.
5. Cap nhat alias sang index moi neu dat yeu cau.
6. Ghi release note va nguoi thuc hien.
7. Giu index cu trong thoi gian rollback da thong nhat.

## 10. Quy tac rollback

- Rollback bang cach tro alias ve version index cu gan nhat da validate.
- Khong xoa index cu ngay sau release.
- Chi xoa index cu khi da het thoi gian retention va khong con phu thuoc rollback.

## 11. Checklist truoc khi chuyen alias

- Ten index dung format.
- Version tang dung loai thay doi.
- Mapping/schema da duoc validate.
- So luong document nam trong nguong ky vong.
- Cac query mau cho ket qua chap nhan duoc.
- Latency va resource usage khong vuot nguong.
- Co release note va thong tin rollback.

