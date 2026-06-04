# Báo cáo Sprint 2 — Đỗ Minh Hiếu

> Thời gian: 08/06/2026 — 18/06/2026
> Vai trò: Data Quality Engineer (Layer 2 — Data Pipeline)

## Mục tiêu Sprint 2

1. Chuyển từ DuckDB → PostgreSQL theo yêu cầu mentor
2. Xử lý dữ liệu thiếu: occupancy imputer + price mocker
3. Mở rộng pipeline lên 51 hotels (merge từ nhánh develop)
4. Đạt metrics: Missing Rate 0%, Duplicate Rate 0%

## Công việc đã làm

### 1. Chuyển DuckDB → PostgreSQL

| Công việc | File / Commit | Mô tả |
|---|---|---|
| Add PostgreSQL service | `docker-compose.yml` | postgres:16, port 5432 |
| Tạo ORM models | `db/__init__.py`, `db/models.py` | SQLAlchemy engine + 4 models: Hotel, Room, NearbyPlace, Activity |
| Thiết lập Alembic | `alembic init migrations` | Tự động quản lý schema |
| Migration 1 | `53b4d4b91081` | Tạo 4 bảng ban đầu |
| Migration 2 | `050871f2e5bc` | `price` → `price_per_night`, thêm `original_price` |
| Export script | `scripts/export_db.py` | Cleaned JSON → PostgreSQL, dedup composite PK, xoá child trước parent |
| Remove DuckDB | — | Xoá `data/da10.duckdb`, xoá `docs/duckdb_usage.md` |

### 2. Occupancy Imputer (`ingestion/cleaning/occupancy_imputer.py`)

**Vấn đề:** ~90% rooms (đặc biệt Muong Thanh hotels) thiếu `max_occupancy`.

**Giải pháp:** 4-step fallback chain:

1. Dùng `max_occupancy_raw` nếu có (> 0)
2. Parse `max_occupancy_text` — regex lấy số đầu tiên
3. Parse `bed_types[]` / `bed_type`:
   - `"và"` (AND) → tổng sức chứa
   - `"/"` / `"hoặc"` (OR) → max
   - Map: đơn=1, đôi/lớn/siêu lớn/king/queen=2, tầng=2, sofa=1
4. Fallback = 2 (mặc định)

**Kết quả:** 0/463 rooms null max_occupancy ✅

### 3. Price Mocker (`ingestion/cleaning/price_mocker.py`)

**Vấn đề:** Agoda không trả giá phòng (dynamic JS).

**Giải pháp:** Deterministic mock price qua MD5 hash:

```
price = base_mid(stars) × brand_factor × room_type_factor × city_factor × size_factor
clamp(star_min, star_max), round 10k
original_price = price × discount (MD5 hash → [1.20, 1.80])
```

**Kết quả:** 0/463 rooms null price_per_night ✅

### 4. Cập nhật Pipeline

- `scripts/clean_pipeline.py`: Thêm `_clean_room()` shared function, xử lý cả `room_grid.rooms[]` (dữ liệu duplicate từ raw)
- `scripts/export_db.py`: Map `price_per_night` + `original_price`, xoá FK child trước parent
- `contracts/data_schema.json`: `price` → `price_per_night`, thêm `original_price`
- `docs/04_ingestion.md`: Cập nhật schema + pipeline diagram + occupancy + price mocker
- `docs/database_usage.md`: PostgreSQL connection guide (thay thế DuckDB docs)

### 5. Mở rộng dữ liệu

- Merge từ nhánh develop: +27 raw hotels mới
- Tổng cộng: 51 hotels (27 Vinpearl/A25/FLC/Marriott + 22 Muong Thanh cũ)
- Chạy lại pipeline full: 51 cleaned → 51 deduped (0 remove) → 51 validated (0 invalid)

## Kết quả Sprint 2

| Metric | Sprint 1 | Sprint 2 | Target |
|---|---|---|---|
| Total documents | ~20 | 51 | — |
| Missing rate | ~3% | 0.0% | < 5% ✅ |
| Duplicate rate | 0% | 0.0% | < 2% ✅ |
| Validation errors | 0 | 0 | 0 ✅ |
| PostgreSQL hotels | 0 | 51 | — |
| PostgreSQL rooms | 0 | 463 | — |
| PostgreSQL nearby_places | 0 | 497 | — |
| PostgreSQL activities | 0 | 507 | — |
| Null max_occupancy | ~90% | 0/463 | 0 ✅ |
| Null price_per_night | 100% | 0/463 | 0 ✅ |
| Storage | DuckDB | PostgreSQL | Real-time sharing |

## Khó khăn

- **PostgreSQL FK constraints**: Phải xoá child rows (`activities` → `nearby_places` → `rooms`) trước `hotels` để tránh violation. Thêm composite PK dedup trước insert.
- **`room_grid.rooms` là dữ liệu duplicate**: Agoda raw có cả `rooms[]` và `room_grid.rooms[]` với cùng dữ liệu. Xử lý cả 2 để tránh mất phòng.
- **recrawl_queue.json**: File JSON array (không phải hotel dict) nằm trong thư mục raw → thêm guard `isinstance(data, dict)` trong `read_raw()`.

## Kế hoạch Sprint 3

- Wire Layer 3 (chunking) + Layer 4 (embedding, indexing)
- Viết unit test cho occupancy_imputer + price_mocker
- Handle cross-source dedup nếu có multi-source data (Agoda + Booking.com)

## File liên quan

| File | Vai trò |
|---|---|
| `db/__init__.py` | SQLAlchemy engine + session |
| `db/models.py` | 4 ORM models |
| `ingestion/cleaning/occupancy_imputer.py` | 4-step fallback occupancy |
| `ingestion/cleaning/price_mocker.py` | MD5 deterministic price |
| `scripts/export_db.py` | PostgreSQL export |
| `scripts/clean_pipeline.py` | Shared `_clean_room()`, room_grid handler |
| `docker-compose.yml` | PostgreSQL service |
| `alembic.ini` + `migrations/` | Schema migration |
| `docs/04_ingestion.md` | Full pipeline docs |
| `docs/database_usage.md` | PostgreSQL guide |
