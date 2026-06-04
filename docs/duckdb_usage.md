# DuckDB — Sử dụng & Chia sẻ dữ liệu

## Giới thiệu

`data/da10.duckdb` là file chứa toàn bộ dữ liệu khách sạn đã được làm sạch, lưu dưới dạng DuckDB (single-file SQL engine). Team có thể query trực tiếp bằng SQL mà không cần cài server.

## Cài đặt

```bash
pip install duckdb
```

## Kết nối

```python
import duckdb
conn = duckdb.connect("da10.duckdb")
```

File `da10.duckdb` nằm tại `data/da10.duckdb` trong repo; khi deploy có thể copy ra ngoài.

## Schema

### Tables

| Table | Rows | Mô tả |
|---|---|---|
| `hotels` | ~50 | 1 row / khách sạn |
| `rooms` | ~500 | 1 row / loại phòng |
| `nearby_places` | ~500 | Địa điểm lân cận |
| `activities` | ~500 | Hoạt động giải trí |

### Hotels columns

| Column | Type | Ví dụ |
|---|---|---|
| `id` | `INTEGER` | `65153` |
| `name` | `VARCHAR` | `Vinpearl Resort Nha Trang` |
| `star_rating` | `FLOAT` | `5.0` |
| `review_score` | `FLOAT` | `8.7` |
| `city` | `VARCHAR` | `Nha Trang` |
| `latitude` / `longitude` | `DOUBLE` | `12.22` / `109.24` |
| `amenities` | `VARCHAR[]` | `['WiFi miễn phí', 'Hồ bơi']` |
| `amenities_general` | `VARCHAR[]` | Tiện ích chung |
| `amenities_leisure` | `VARCHAR[]` | Tiện ích giải trí |
| `amenities_dining` | `VARCHAR[]` | Tiện ích ăn uống |
| `amenity_groups` | `JSON` | Toàn bộ groups gộp |
| `useful_info` | `JSON` | Thông tin bổ sung key-value |
| `reviews_detail` | `JSON` | Điểm + tag đánh giá |
| `images` | `VARCHAR[]` | URL ảnh |
| `description` | `VARCHAR` | Mô tả khách sạn |

### Rooms columns

| Column | Type | Ví dụ |
|---|---|---|
| `hotel_id` | `INTEGER` | FK → hotels.id |
| `name` | `VARCHAR` | `Deluxe King` |
| `price` | `FLOAT` | `1500000` (VND) |
| `room_amenities` | `VARCHAR[]` | Tiện ích phòng |
| `max_occupancy` | `INTEGER` | `2` |
| `bed_type` | `VARCHAR` | `Queen` |

## Query mẫu

```python
import duckdb
conn = duckdb.connect("da10.duckdb")
```

### Lấy khách sạn theo thành phố, sắp xếp theo điểm

```python
conn.sql("""
    SELECT name, star_rating, review_score, review_count
    FROM hotels
    WHERE city = 'Nha Trang'
    ORDER BY review_score DESC
""").show()
```

### JOIN hotels + rooms, lọc theo giá

```python
conn.sql("""
    SELECT h.name AS hotel, r.name AS room, r.price, r.room_size
    FROM hotels h
    JOIN rooms r ON r.hotel_id = h.id
    WHERE h.city = 'Nha Trang' AND r.price BETWEEN 1000000 AND 3000000
    ORDER BY r.price
""").show()
```

### Unnest amenities (tách mảng thành từng row)

```python
conn.sql("""
    SELECT h.name, unnest(h.amenities) AS amenity
    FROM hotels h
    WHERE h.city = 'Đà Nẵng'
    LIMIT 20
""").show()
```

### Thống kê amenity phổ biến nhất

```python
conn.sql("""
    SELECT unnest(amenities) AS amenity, COUNT(*) AS cnt
    FROM hotels
    GROUP BY amenity
    ORDER BY cnt DESC
    LIMIT 10
""").show()
```

### Query JSON (amenity_groups)

```python
conn.sql("""
    SELECT name, amenity_groups->>'$.general' AS general
    FROM hotels LIMIT 3
""").show()
```

### Export kết quả ra pandas DataFrame

```python
df = conn.sql("SELECT city, COUNT(*) AS hotels, ROUND(AVG(review_score), 2) AS avg_score FROM hotels GROUP BY city").fetchdf()
print(df)
```

## Chia sẻ cho team khác

### Cách 1: Git (đơn giản nhất)

File `data/da10.duckdb` đã được commit trong repo. Team clone về là có ngay:

```bash
git clone <repo_url>
cd vsf_dlks_search_system
pip install duckdb
python -c "
import duckdb
conn = duckdb.connect('data/da10.duckdb')
print(conn.sql('SELECT COUNT(*) FROM hotels').fetchone())
"
```

### Cách 2: Copy file (khi file > 50MB)

```bash
# Host gửi
scp data/da10.duckdb user@team-server:/path/to/

# Hoặc upload lên S3 / Google Drive
```

### Cách 3: API (khi team không muốn cài Python)

Dùng FastAPI có sẵn (chưa implement endpoint — cần làm thêm).

## Tự generate DuckDB từ cleaned data

Nếu muốn tự build lại DuckDB từ cleaned JSON:

```bash
python scripts/export_duckdb.py
```

Hoặc chạy full pipeline:

```bash
python scripts/run_ingest.py
```

## Yêu cầu

- Python ≥ 3.10
- `duckdb` (`pip install duckdb`)
- Nếu tự build: cleaned hotel JSONs trong `data/cleaned/`
