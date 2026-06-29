# Vietnam Crawl Keywords

Mục tiêu: mở rộng dataset khách sạn Việt Nam từ khoảng 226 record lên khoảng 520 record.

Crawler hiện đã có bộ lọc:

- Chỉ lưu record có `country` thuộc Việt Nam.
- Bỏ qua `hotel_id` đã có trong `data/raw/hotels`.
- Có thể dừng theo tổng số bằng `--target-total 520`.

## Keyword Set Ưu Tiên

### Batch 1 - Điểm đến còn ít dữ liệu

```text
Sa Pa,Lào Cai,Hà Giang,Cao Bằng,Bắc Kạn,Thái Nguyên,Tuyên Quang,Yên Bái,Mộc Châu,Sơn La,Điện Biên,Hòa Bình,Ninh Bình,Tam Đảo,Vĩnh Phúc
```

### Batch 2 - Miền Trung và biển đảo

```text
Quảng Bình,Đồng Hới,Phong Nha,Huế,Lăng Cô,Quảng Trị,Quảng Ngãi,Lý Sơn,Tam Kỳ,Quảng Nam,Đà Nẵng,Hội An,Cù Lao Chàm,Quy Nhơn,Phú Yên,Tuy Hòa,Ninh Thuận,Phan Rang,Bình Thuận,Phan Thiết,Mũi Né
```

### Batch 3 - Tây Nguyên

```text
Đà Lạt,Bảo Lộc,Lâm Đồng,Buôn Ma Thuột,Đắk Lắk,Gia Lai,Pleiku,Kon Tum,Măng Đen,Đắk Nông
```

### Batch 4 - Nam Bộ và miền Tây

```text
Cần Thơ,An Giang,Châu Đốc,Long Xuyên,Kiên Giang,Rạch Giá,Hà Tiên,Phú Quốc,Bạc Liêu,Cà Mau,Sóc Trăng,Trà Vinh,Vĩnh Long,Bến Tre,Tiền Giang,Mỹ Tho,Tây Ninh,Bình Dương,Đồng Nai,Biên Hòa,Vũng Tàu,Hồ Tràm,Hồ Cốc,Côn Đảo
```

### Batch 5 - Brand/chuỗi có nhiều cơ sở tại Việt Nam

```text
Mường Thanh,Vinpearl,FLC,Melia,Novotel,Mercure,Pullman,Sheraton,Marriott,Hilton,Wyndham,Ibis,Muong Thanh Luxury,Muong Thanh Grand,SOJO,Minasi,A25,Sen Hotel,TTC Hotel,Liberty Hotel,Saigon Hotel
```

### Batch 6 - Loại hình lưu trú phổ biến

```text
khách sạn trung tâm,resort biển,khách sạn gần biển,homestay,condotel,apartment hotel,boutique hotel,villa resort,khách sạn gia đình,khách sạn công tác,khách sạn 4 sao,khách sạn 5 sao
```

## Lệnh Khuyến Nghị

Chạy từng batch để dễ quan sát log và tránh Agoda chặn request.

```powershell
python -m crawler.main --keys "Sa Pa,Lào Cai,Hà Giang,Cao Bằng,Bắc Kạn,Thái Nguyên,Tuyên Quang,Yên Bái,Mộc Châu,Sơn La,Điện Biên,Hòa Bình,Ninh Bình,Tam Đảo,Vĩnh Phúc" --site agoda --limit 8 --target-total 520
```

```powershell
python -m crawler.main --keys "Quảng Bình,Đồng Hới,Phong Nha,Huế,Lăng Cô,Quảng Trị,Quảng Ngãi,Lý Sơn,Tam Kỳ,Quảng Nam,Đà Nẵng,Hội An,Cù Lao Chàm,Quy Nhơn,Phú Yên,Tuy Hòa,Ninh Thuận,Phan Rang,Bình Thuận,Phan Thiết,Mũi Né" --site agoda --limit 8 --target-total 520
```

```powershell
python -m crawler.main --keys "Đà Lạt,Bảo Lộc,Lâm Đồng,Buôn Ma Thuột,Đắk Lắk,Gia Lai,Pleiku,Kon Tum,Măng Đen,Đắk Nông" --site agoda --limit 8 --target-total 520
```

```powershell
python -m crawler.main --keys "Cần Thơ,An Giang,Châu Đốc,Long Xuyên,Kiên Giang,Rạch Giá,Hà Tiên,Phú Quốc,Bạc Liêu,Cà Mau,Sóc Trăng,Trà Vinh,Vĩnh Long,Bến Tre,Tiền Giang,Mỹ Tho,Tây Ninh,Bình Dương,Đồng Nai,Biên Hòa,Vũng Tàu,Hồ Tràm,Hồ Cốc,Côn Đảo" --site agoda --limit 8 --target-total 520
```

```powershell
python -m crawler.main --keys "Mường Thanh,Vinpearl,FLC,Melia,Novotel,Mercure,Pullman,Sheraton,Marriott,Hilton,Wyndham,Ibis,Muong Thanh Luxury,Muong Thanh Grand,SOJO,Minasi,A25,TTC Hotel,Liberty Hotel,Saigon Hotel" --site agoda --limit 8 --target-total 520
```

```powershell
python -m crawler.main --keys "khách sạn trung tâm,resort biển,khách sạn gần biển,homestay,condotel,apartment hotel,boutique hotel,villa resort,khách sạn gia đình,khách sạn công tác,khách sạn 4 sao,khách sạn 5 sao" --site agoda --limit 8 --target-total 520
```

## Kiểm Tra Số Lượng Sau Khi Crawl

```powershell
$env:PYTHONIOENCODING='utf-8'; python -c "from pathlib import Path; print(len(list(Path('data/raw/hotels').glob('hotel_*.json'))))"
```

## Sau Khi Crawl Xong

Chạy lại clean pipeline để tạo `data/cleaned` từ `data/raw` nếu pipeline của team yêu cầu:

```powershell
python scripts/clean_pipeline.py
```

Sau đó kiểm tra dataset cleaned chỉ còn Việt Nam:

```powershell
$env:PYTHONIOENCODING='utf-8'; python -c "import json; from pathlib import Path; from collections import Counter; c=Counter(json.loads(p.read_text(encoding='utf-8')).get('country') for p in Path('data/cleaned').glob('hotel_*.json')); print(c)"
```
