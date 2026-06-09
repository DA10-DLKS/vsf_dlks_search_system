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
python -m crawler.main --keys "Vinpearl,Muong Thanh,Fusion" --limit 10 --site agoda
```

`main.py` tự nhận diện: bắt đầu bằng `http(s)://` → **nhánh link**; còn lại → **nhánh
từ khóa**. Nhánh link tự chọn spider theo domain; nhánh từ khóa dùng `--site` (mặc
định `agoda`).

| Tham số | Ý nghĩa |
|---------|---------|
| `--site <tên>` | Site cho nhánh từ khóa (mặc định `agoda`) |
| `--limit N` | Giới hạn số khách sạn (nhánh từ khóa) |
| `--headful` | Hiện trình duyệt (mặc định chạy ẩn) |
| `--keys`, `--keywords` | Crawl nhiều từ khóa, phân tách bằng dấu phẩy |

Agoda spider chỉ lưu record có `country` thuộc `allowed_countries` trong
`crawler/configs/agoda.yaml`. Khách sạn nước ngoài vẫn có thể xuất hiện ở
autocomplete, nhưng sẽ bị skip ở tầng detail trước khi ghi vào dataset.

## Crawl REVIEW chi tiết (tool riêng)

Crawl KS ở trên chỉ kèm `sample_comments` (~10 review). Để lấy NHIỀU review (nuôi
ABSA + hotel semantic profile cho DA10 KE) dùng tool riêng — **tách hẳn**, chạy trên
các KS đã crawl:

```powershell
# 1 KS theo hotel_id (đọc URL từ file KS đã crawl trong data/raw/hotels/)
python scripts/run_crawl_reviews.py --id 1973

# hàng loạt: mọi KS trong data/raw/hotels/ (tự bỏ qua KS đã có file review)
python scripts/run_crawl_reviews.py --all
python scripts/run_crawl_reviews.py --all --limit 5 --force

# từ 1 link trực tiếp
python scripts/run_crawl_reviews.py "https://www.agoda.com/...hotel=1973..."
```

| Tham số | Ý nghĩa |
|---------|---------|
| `--id N` | 1 hotel_id (tìm URL trong file KS đã crawl) |
| `--all` | Mọi KS trong `data/raw/hotels/`; **resume được** (bỏ qua KS đã có review) |
| `--limit N` | Giới hạn số KS (đi với `--all`) |
| `--force` | Crawl lại cả KS đã có file review (mặc định bỏ qua) |
| `--headful` `--site` | Như trên |

**Cơ chế** (hướng C): mở trang lấy session + payload mẫu (có `reviewProviderIds` +
token), rồi `page.request.post()` lặp phân trang endpoint `review/HotelReviews`.
Chiến lược 2 vòng sort: **điểm thấp trước** (sort=3, vét review chê — hiếm + quý cho
ABSA) → **mới nhất** (sort=1) tới đủ cap. Dedup theo `hotelReviewId` (review_id thật).

**Cap động** (config `review_crawl` trong `agoda.yaml`): `review_count` ≥
`flagship_min_reviews` → `cap_flagship` (400); n ≤ `cap_normal` → lấy hết;
n > `cap_normal` → 250; seed thiếu số → cap_normal (`unknown`).

> ⚠ **Trần dữ liệu Agoda:** `comments_count` trang quảng cáo (vd 584) chỉ là marketing;
> API thực chỉ cho truy cập ~100–250 review unique. Tool lấy hết trong trần đó là đúng,
> không phải thiếu sót. Giữ review có text HOẶC positives/negatives (`require_content`).

Output: `data/raw/reviews/hotel_<id>_reviews.json` (file riêng, **không** đụng file KS;
`sample_comments` giữ nguyên làm preview).

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
                       + parse_review_comment (tool review)
```

Tool review nằm ở `scripts/run_crawl_reviews.py` + `AgodaSpider.crawl_reviews`
(spider) + `pipelines.save_reviews` (I/O).

Dữ liệu xuất ra `data/raw/` (cùng cấp với `crawler/`):
- `data/raw/hotels_list.json` — danh sách KS (tầng 1)
- `data/raw/hotels_detail.json` — checkpoint gộp (resume được)
- `data/raw/hotels/hotel_<id>_<slug>.json` — kết quả cuối, mỗi KS 1 file
- `data/raw/reviews/hotel_<id>_reviews.json` — review chi tiết (tool review riêng)
- `data/raw/failed.json` — các KS lỗi

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
