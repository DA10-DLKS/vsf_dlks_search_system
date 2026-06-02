# configs/ — Cấu hình crawl cho từng site (Layer 1)

Mỗi site có **một file `<site>.yaml`** khai báo *cách* crawl site đó, để logic
trong `spiders/` không hardcode gì. Thêm site mới = thêm `<site>.yaml` ở đây +
`spiders/<site>.py`.

## Mỗi file YAML khai báo gì

| Khoá | Ý nghĩa |
|------|---------|
| `base_url`, `locale`, `user_agent` | URL gốc, ngôn ngữ, user-agent trình duyệt |
| `autocomplete_api` | Endpoint API search (keyword → danh sách hotel) |
| `region_hints` | Các hậu tố địa điểm để gom đủ KS một chuỗi ở nhiều nơi |
| `detail_query`, `checkin_offset_days`, `los_nights` | Tham số URL trang chi tiết (tiền tệ, ngày check-in/out…) |
| `capture_endpoints` | Các nguồn cần **bắt** ở trang detail: `tên_nội_bộ → chuỗi nhận diện trong URL` |
| `rate_limit` | Giới hạn tốc độ (delay/random sleep) để lịch sự, tránh bị chặn |
| `viewport` | Kích thước cửa sổ trình duyệt |

## Dùng trong code

```python
from crawler.configs import load_config
cfg = load_config("agoda")        # đọc agoda.yaml (có cache)
cfg["base_url"], cfg["rate_limit"]["between_details"]
```

## Thêm site mới (ví dụ Booking)

1. Tạo `configs/booking.yaml` theo đúng các khoá trên.
2. Tạo `spiders/booking.py` với `class BookingSpider(BaseSpider)`.
3. Đăng ký vào `spiders/__init__.py` (`SPIDERS["booking"] = BookingSpider`).
