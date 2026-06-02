# crawler/ — Package crawl dữ liệu khách sạn (đa-site, config-driven)

Crawl chi tiết khách sạn từ các trang OTA (hiện hỗ trợ **Agoda**) qua Playwright +
bắt response GraphQL/API, gom thành record JSON sạch. Thiết kế tách **"khung điều
phối"** khỏi **"phần riêng từng site"** để thêm site mới (Booking, Traveloka…) chỉ
cần thêm config + 1 spider, không sửa khung.

## Chạy

```powershell
# 1) Từ 1 LINK khách sạn  -> crawl đúng 1 KS -> 1 file json
python -m crawler.main "https://www.agoda.com/.../hotel.html?hotel=65153&..."

# 2) Từ TỪ KHÓA           -> search hàng loạt -> nhiều file json
python -m crawler.main "Vinpearl"
python -m crawler.main "Muong Thanh" --limit 5 --headful --site agoda
```

`main.py` tự nhận diện: bắt đầu bằng `http(s)://` → **nhánh link**; còn lại → **nhánh
từ khóa**. Nhánh link tự chọn spider theo domain; nhánh từ khóa dùng `--site` (mặc
định `agoda`).

| Tham số | Ý nghĩa |
|---------|---------|
| `--site <tên>` | Site cho nhánh từ khóa (mặc định `agoda`) |
| `--limit N` | Giới hạn số khách sạn (nhánh từ khóa) |
| `--headful` | Hiện trình duyệt (mặc định chạy ẩn) |

## Kiến trúc

```
crawler/
├── main.py        Entry point: điều phối 2 nhánh (link / từ khóa)
├── browser.py     Context manager Playwright dùng chung (launch + context)
├── pipelines.py   I/O: slugify, lưu/tách record, checkpoint. DATA_DIR = ../data
├── configs/       Layer 1 — config crawl theo site (xem configs/README.md)
│   ├── __init__.py    load_config(site)  (có cache)
│   └── agoda.yaml     base_url, autocomplete_api, region_hints,
│                      capture_endpoints, rate_limit, viewport...
├── spiders/       Logic crawl theo site
│   ├── base.py        BaseSpider (abstract): crawl_list / resolve_slugs /
│   │                  crawl_detail / parse_url / is_site_url
│   ├── agoda.py       AgodaSpider — hiện thực 3 tầng + nhánh link
│   └── __init__.py    SPIDERS = {"agoda": AgodaSpider}
└── parsers/       Bóc tách response thô -> record sạch
    └── agoda.py       5 nguồn (details/rooms/reviews/secondary/activities/faq)
                       + build_record() gom thành 1 record + embedding_text
```

Dữ liệu xuất ra `data/` (cùng cấp với `crawler/`):
- `data/hotels_list.json` — danh sách KS (tầng 1)
- `data/hotels_detail.json` — checkpoint gộp (resume được)
- `data/hotels/hotel_<id>_<slug>.json` — kết quả cuối, mỗi KS 1 file
- `data/failed.json` — các KS lỗi

## Luồng xử lý

**Nhánh từ khóa** (3 tầng, cùng 1 tiến trình, có checkpoint sau mỗi KS):
1. `crawl_list(keyword)` — gọi autocomplete với nhiều biến thể → lọc theo keyword.
2. `resolve_slugs(hotels)` — mở trang từng KS, bắt `citySearch` → gom `property_page`.
3. `crawl_detail(hotel)` — mở trang chi tiết, cuộn, bắt 6 nguồn → `build_record`.
   → lưu checkpoint → tách ra `data/hotels/`.

**Nhánh link** — parse `hotel_id` (`?hotel=`) + `property_page` (path) từ URL → gọi
thẳng `crawl_detail`, **bỏ qua tầng 1 & 1.5**. Lưu ý: `city_id` = null vì link
không mang thông tin này.

## Thêm site mới (ví dụ Booking)

1. `configs/booking.yaml` — theo các khóa như `agoda.yaml` (xem `configs/README.md`).
2. `spiders/booking.py` — `class BookingSpider(BaseSpider)` hiện thực các method abstract.
3. `parsers/booking.py` — parser cho response của Booking → record cùng schema.
4. Đăng ký vào `spiders/__init__.py`: `SPIDERS["booking"] = BookingSpider`.

`main.py`, `browser.py`, `pipelines.py`, `BaseSpider` **dùng lại nguyên**, không sửa.

## Cài đặt

```powershell
pip install -r requirements.txt   # playwright + pyyaml
python -m playwright install chromium
```
