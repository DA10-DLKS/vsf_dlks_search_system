# PostgreSQL — Sử dụng & Chia sẻ dữ liệu

## Giới thiệu

Dữ liệu khách sạn đã làm sạch được lưu trong PostgreSQL (container chạy cùng dự án).
Team có thể query trực tiếp bằng SQL qua:
- Kết nối trực tiếp tới PostgreSQL (port `5432`)
- API server (FastAPI chưa implement endpoint — cần làm thêm)

## Kết nối

### Thông tin

| Param | Giá trị |
|---|---|
| Host | `localhost` (local) hoặc tên service `postgres` (Docker network) |
| Port | `5432` |
| Database | `da10` |
| User | `da10` |
| Password | `da10` |
| URL | `postgresql://da10:da10@localhost:5432/da10` |

### Python (SQLAlchemy)

```python
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://da10:da10@localhost:5432/da10")

with engine.connect() as conn:
    rows = conn.execute(text("SELECT name, city, review_score FROM hotels"))
    for row in rows:
        print(row)
```

### Python (psycopg2 trực tiếp)

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="da10",
    user="da10",
    password="da10",
)
cur = conn.cursor()
cur.execute("SELECT name, city, review_score FROM hotels LIMIT 5")
for row in cur.fetchall():
    print(row)
```

### CLI (psql)

```bash
# Docker container
docker compose exec postgres psql -U da10 -d da10

# Hoặc psql local (nếu cài)
psql postgresql://da10:da10@localhost:5432/da10
```

## Schema

### Tables

| Table | Rows | Mô tả |
|---|---|---|
| `hotels` | ~50 | 1 row / khách sạn |
| `rooms` | ~500 | 1 row / loại phòng |
| `nearby_places` | ~500 | Địa điểm lân cận |
| `activities` | ~500 | Hoạt động giải trí |

### Hotel columns

| Column | Type | Ví dụ |
|---|---|---|
| `id` | `INTEGER` PK | `65153` |
| `name` | `VARCHAR(255)` | `Vinpearl Resort Nha Trang` |
| `star_rating` | `FLOAT` | `5.0` |
| `review_score` | `FLOAT` | `8.7` |
| `review_count` | `INTEGER` | `1280` |
| `city` | `VARCHAR(100)` | `Nha Trang` |
| `latitude` / `longitude` | `FLOAT` | `12.22` / `109.24` |
| `amenities` | `TEXT[]` | `['WiFi miễn phí', 'Hồ bơi']` |
| `amenities_general` | `TEXT[]` | Tiện ích chung |
| `amenities_leisure` | `TEXT[]` | Tiện ích giải trí |
| `amenities_dining` | `TEXT[]` | Tiện ích ăn uống |
| `amenity_groups` | `JSONB` | Toàn bộ groups gộp |
| `useful_info` | `JSONB` | Thông tin bổ sung key-value |
| `reviews_detail` | `JSONB` | Điểm + tag đánh giá |
| `images` | `TEXT[]` | URL ảnh |
| `description` | `TEXT` | Mô tả khách sạn |

### Room columns

| Column | Type | Ví dụ |
|---|---|---|
| `hotel_id` | `INTEGER` FK | Khóa ngoại → hotels.id |
| `room_type_id` | `INTEGER` | ID loại phòng gốc |
| `name` | `VARCHAR(255)` | `Deluxe King` |
| `price` | `FLOAT` | `1500000` (VND) |
| `room_amenities` | `TEXT[]` | Tiện ích phòng |
| `max_occupancy` | `INTEGER` | `2` |
| `bed_type` | `VARCHAR(255)` | `Queen` |

## Query mẫu

### Lấy khách sạn theo thành phố, sắp xếp theo điểm

```sql
SELECT name, star_rating, review_score, review_count
FROM hotels
WHERE city = 'Nha Trang'
ORDER BY review_score DESC;
```

### JOIN hotels + rooms, lọc theo giá

```sql
SELECT h.name AS hotel, r.name AS room, r.price, r.room_size
FROM hotels h
JOIN rooms r ON r.hotel_id = h.id
WHERE h.city = 'Nha Trang' AND r.price BETWEEN 1000000 AND 3000000
ORDER BY r.price;
```

### Unnest amenities (tách mảng thành từng row)

```sql
SELECT h.name, unnest(h.amenities) AS amenity
FROM hotels h
WHERE h.city = 'Đà Nẵng'
LIMIT 20;
```

### Thống kê amenity phổ biến nhất

```sql
SELECT unnest(amenities) AS amenity, COUNT(*) AS cnt
FROM hotels
GROUP BY amenity
ORDER BY cnt DESC
LIMIT 10;
```

### Query JSONB (amenity_groups)

```sql
SELECT name, amenity_groups->>'general' AS general
FROM hotels
LIMIT 3;
```

### Export kết quả ra pandas DataFrame

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://da10:da10@localhost:5432/da10")
df = pd.read_sql("SELECT city, COUNT(*) AS hotels, ROUND(AVG(review_score), 2) AS avg_score FROM hotels GROUP BY city", engine)
print(df)
```

## Chia sẻ cho team khác

### Cách 1: Docker Compose (đơn giản nhất)

Team clone repo, chạy PostgreSQL:

```bash
docker compose up -d postgres
# Dữ liệu được mount vào volume postgres_data
# Database đã tạo sẵn (trống, cần chạy pipeline hoặc restore)
```

### Cách 2: Kết nối từ xa

Nếu PostgreSQL chạy trên server có IP public:

```bash
psql postgresql://da10:da10@<server-ip>:5432/da10
```

### Cách 3: API (khi team không muốn cài Python)

Dùng FastAPI có sẵn (chưa implement endpoint — cần làm thêm).

## Tự build database từ cleaned data

Nếu muốn tự build lại PostgreSQL từ cleaned JSON:

```bash
# Khởi động PostgreSQL
docker compose up -d postgres

# Apply migration (tạo bảng)
alembic upgrade head

# Export cleaned JSON → PostgreSQL
python scripts/run_ingest.py --skip-clean --skip-dedup --skip-validate
```

Hoặc chạy full pipeline:

```bash
docker compose up -d postgres
alembic upgrade head
python scripts/run_ingest.py
```

## Migration

Dùng Alembic để quản lý schema:

```bash
# Tạo migration mới (sau khi sửa models.py)
alembic revision --autogenerate -m "mô tả thay đổi"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Yêu cầu

- Docker (chạy PostgreSQL container)
- Hoặc PostgreSQL instance riêng với connection string trong `.env`
- Python packages: `psycopg2-binary`, `sqlalchemy`, `alembic`
