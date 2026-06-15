# Ranking Ground Truth — Golden Queries GS-061 → GS-070 (Review-grade test)

> 10 câu query mới dùng để đánh giá **SearchAPI** (`POST /api/v1/search`) trong
> `docs/Vu_Duc_Kien/VuDucKien_api_schema_proposal.md`.
> Tất cả `intent_type = hotel_search`, đều nhắc tới một `city`.

## Nguyên tắc xây dựng (đáp ứng yêu cầu)

1. **Nguồn ground truth = REVIEW**, lấy từ `reviews_detail.grades` trong mỗi file
  `data/cleaned/hotel_*.json`. `grades` là điểm con (sub-score) do người dùng đánh
   giá theo từng khía cạnh: `Độ sạch sẽ`, `Cơ sở vật chất`, `Vị trí`,
   `Sự thoải mái và chất lượng phòng`, `Dịch vụ`, `Đáng tiền`.
   → **KHÔNG** dùng trường `amenities`.
2. **KHÔNG chứa style** trong `ontology/core/style.yaml` — query chỉ nói về khía cạnh
  chất lượng dịch vụ/phòng/vị trí/giá trị... (review aspect), không dùng surface form
   nào của `STYLE_`*. Riêng GS-066 cố tình tránh từ `thoải mái`/`dễ chịu`
   (surface form của `STYLE_RELAXING`), chỉ dùng `chất lượng phòng / rộng rãi`.
3. **Tiêu chí ranking** (mọi query): `grade_score` **giảm dần** →
  tiebreak `review_score` **giảm dần** → tiebreak `review_count` **giảm dần**.
4. **top_k = 10** (nếu pool < 10 thì lấy hết).
5. **Query "Tìm resort..."** (GS-069, GS-070): pool đã lọc `accommodation_type == "Resort"`
  (lấy từ `hotel_*.json`), `relevant_hotel_ids` chỉ gồm Resort.

Pipeline tái lập: `data/golden_dataset/_build_review_index.py` → `_review_index.json`.
Corpus: 520 hotel.

Ký hiệu: `g` = grade_score, `s` = review_score, `rc` = review_count.

---

## GS-061 — Đà Nẵng · grade "Dịch vụ"

**Query:** "Tìm khách sạn ở Đà Nẵng có dịch vụ tốt, nhân viên phục vụ chu đáo"
**Rank theo:** grade `Dịch vụ` ↓ → review_score ↓ → review_count ↓. pool = 43.


| rank | hotel_id | g   | s   | rc   | type           | tên                                      |
| ---- | -------- | --- | --- | ---- | -------------- | ---------------------------------------- |
| 1    | 338256   | 9.6 | 9.2 | 1454 | Khách sạn      | Banyan Tree Lang Co                      |
| 2    | 82014402 | 9.5 | 9.3 | 127  | Căn hộ dịch vụ | Hampton Danang Luxury Apartment          |
| 3    | 1985160  | 9.4 | 8.9 | 3010 | Resort         | Danang Marriott Resort & Spa, Non Nuoc   |
| 4    | 73359010 | 9.3 | 9.2 | 172  | Căn hộ         | Luxury Apartment in Sheraton Building    |
| 5    | 73809693 | 9.3 | 9.1 | 1127 | Khách sạn      | Courtyard by Marriott Danang Han River   |
| 6    | 338255   | 9.3 | 8.8 | 2770 | Khách sạn      | Angsana Lang Co                          |
| 7    | 55270044 | 9.3 | 8.8 | 722  | Resort         | Langco Bay Retreat                       |
| 8    | 46045575 | 9.3 | 8.8 | 628  | Căn hộ         | The Sun Hotel & Apartment                |
| 9    | 9755468  | 9.3 | 8.8 | 192  | Khách sạn      | A25 Hotel - 137 Nguyen Du                |
| 10   | 4128513  | 9.3 | 8.7 | 2222 | Khách sạn      | Sheraton Grand Danang Beach Resort & Spa |


Ghi chú tiebreak: rank 6–9 cùng g=9.3, s=8.8 → tách bằng review_count (2770 > 722 > 628 > 192).

---

## GS-062 — Hà Nội · grade "Độ sạch sẽ"

**Query:** "Tìm khách sạn ở Hà Nội sạch sẽ, vệ sinh tốt"
**Rank theo:** grade `Độ sạch sẽ` ↓ → review_score ↓ → review_count ↓. pool = 53.


| rank | hotel_id | g   | s   | rc   | type            | tên                            |
| ---- | -------- | --- | --- | ---- | --------------- | ------------------------------ |
| 1    | 66680429 | 9.7 | 9.5 | 1059 | Khách sạn       | Hanoi Sail Hotel               |
| 2    | 86658383 | 9.6 | 9.3 | 11   | Toàn bộ căn nhà | Studio cạnh Sheraton / Tây Hồ  |
| 3    | 10964    | 9.6 | 9.2 | 2890 | Khách sạn       | Sofitel Legend Metropole Hanoi |
| 4    | 38583105 | 9.6 | 9.1 | 4477 | Khách sạn       | L7 West Lake Hanoi by Lotte    |
| 5    | 16366479 | 9.6 | 9.0 | 947  | Khách sạn       | Grand Mercure Hanoi            |
| 6    | 35354312 | 9.5 | 9.1 | 767  | Khách sạn       | Minasi Grand Hotel             |
| 7    | 73179078 | 9.5 | 9.1 | 157  | Khách sạn       | A25 Premium - 130 Bà Triệu     |
| 8    | 529354   | 9.4 | 9.1 | 1579 | Khách sạn       | JW Marriott Hotel Hanoi        |
| 9    | 6542427  | 9.2 | 8.7 | 882  | Khách sạn       | Novotel Hanoi Thai Ha          |
| 10   | 6868294  | 9.1 | 8.8 | 1867 | Khách sạn       | Wyndham Garden Hanoi           |


---

## GS-063 — Hồ Chí Minh · grade "Đáng tiền"

**Query:** "Tìm khách sạn ở Hồ Chí Minh đáng đồng tiền, giá tốt so với chất lượng"
**Rank theo:** grade `Đáng tiền` (value-for-money từ review, KHÁC price tier) ↓ → review_score ↓ → review_count ↓. pool = 49.


| rank | hotel_id | g   | s   | rc   | type      | tên                                             |
| ---- | -------- | --- | --- | ---- | --------- | ----------------------------------------------- |
| 1    | 65513469 | 9.5 | 9.2 | 1009 | Khách sạn | TalaSaiGon Hotel                                |
| 2    | 33550196 | 9.3 | 9.1 | 810  | Khách sạn | Express by M Village Điện Biên Phủ (The Tropic) |
| 3    | 64327220 | 9.1 | 8.8 | 369  | Khách sạn | Brown Dot Hotel Saigon Airport                  |
| 4    | 54795553 | 9.0 | 8.9 | 177  | Khách sạn | A25 Premium - 142 Bùi Thị Xuân                  |
| 5    | 6428322  | 8.8 | 9.1 | 2880 | Khách sạn | Vinpearl Landmark 81, Autograph Collection      |
| 6    | 47843559 | 8.8 | 9.0 | 1520 | Khách sạn | Hilton Saigon                                   |
| 7    | 16260062 | 8.8 | 8.5 | 6429 | Khách sạn | Mường Thanh Luxury Saigon                       |
| 8    | 47615938 | 8.8 | 8.4 | 1055 | Khách sạn | Haven Hut Riverside Hotel                       |
| 9    | 165511   | 8.7 | 8.9 | 2551 | Khách sạn | JW Marriott Hotel & Suites Saigon               |
| 10   | 45888608 | 8.7 | 8.7 | 631  | Khách sạn | Express by M Village ĐBP Q3                     |


Ghi chú tiebreak: rank 5–8 cùng g=8.8 → tách bằng review_score (9.1 > 9.0 > 8.5 > 8.4).

---

## GS-064 — Đà Lạt · grade "Vị trí"

**Query:** "Tìm khách sạn ở Đà Lạt có vị trí thuận tiện, dễ di chuyển"
**Rank theo:** grade `Vị trí` ↓ → review_score ↓ → review_count ↓. pool = 23.


| rank | hotel_id | g   | s   | rc   | type      | tên                          |
| ---- | -------- | --- | --- | ---- | --------- | ---------------------------- |
| 1    | 49851722 | 9.6 | 9.3 | 1346 | Khách sạn | Golden Sun Hotel - Dalat     |
| 2    | 32680041 | 9.4 | 9.2 | 1461 | Khách sạn | Tala Dalat Hotel             |
| 3    | 78233733 | 9.4 | 8.3 | 33   | Khách sạn | COCO HOUSE Đà Lạt            |
| 4    | 15896111 | 9.3 | 8.7 | 281  | Khách sạn | New Hampton Suits - Tầm Xuân |
| 5    | 179080   | 9.3 | 8.3 | 3930 | Khách sạn | TTC Hotel Ngoc Lan           |
| 6    | 41926154 | 9.2 | 9.2 | 931  | Khách sạn | Sunset Hill Hotel            |
| 7    | 23388080 | 9.2 | 9.0 | 34   | Khách sạn | A25 Hotel - 386 Hai Bà Trưng |
| 8    | 55256505 | 9.2 | 8.9 | 883  | Khách sạn | Greenview City Hotel         |
| 9    | 9698     | 9.2 | 8.3 | 1822 | Khách sạn | TTC Hotel Dalat              |
| 10   | 63447487 | 9.1 | 9.0 | 248  | Khách sạn | Dalat Roof Hotel             |


---

## GS-065 — Hạ Long · grade "Cơ sở vật chất"

**Query:** "Tìm khách sạn ở Hạ Long có cơ sở vật chất tốt, trang thiết bị đầy đủ"
**Rank theo:** grade `Cơ sở vật chất` ↓ → review_score ↓ → review_count ↓. pool = 22.


| rank | hotel_id | g   | s   | rc   | type      | tên                                        |
| ---- | -------- | --- | --- | ---- | --------- | ------------------------------------------ |
| 1    | 35444743 | 9.6 | 9.4 | 127  | Khách sạn | A25 Premium - Bãi Cháy Hạ Long             |
| 2    | 65343180 | 9.5 | 9.2 | 69   | Khách sạn | Tru by Hilton Ha Long Hon Gai Centre       |
| 3    | 38722254 | 9.4 | 9.2 | 1272 | Khách sạn | Radisson Blu Hotel, Ha Long Bay            |
| 4    | 42152643 | 9.3 | 8.9 | 914  | Khách sạn | Harmony Halong Hotel                       |
| 5    | 27874314 | 9.3 | 8.6 | 35   | Căn hộ    | Sun Flower II - Green Bay Premium condotel |
| 6    | 58958232 | 9.2 | 9.2 | 932  | Khách sạn | Wyndham Garden Legend Halong               |
| 7    | 31461091 | 9.2 | 9.1 | 467  | Khách sạn | Green Bay Hotel Ha Long                    |
| 8    | 1015998  | 9.2 | 9.0 | 4121 | Resort    | Vinpearl Resort & Spa Ha Long              |
| 9    | 46741090 | 9.0 | 9.0 | 582  | Căn hộ    | À LaCarte Ha Long (5-Star Apartment)       |
| 10   | 16360312 | 9.0 | 8.9 | 240  | Khách sạn | Muong Thanh Holiday Suoi Mo                |


---

## GS-066 — Vũng Tàu · grade "Sự thoải mái và chất lượng phòng"

**Query:** "Tìm khách sạn ở Vũng Tàu có chất lượng phòng tốt, phòng rộng rãi"
*(query né surface form `thoải mái`/`dễ chịu` của STYLE_RELAXING)*
**Rank theo:** grade `Sự thoải mái và chất lượng phòng` ↓ → review_score ↓ → review_count ↓. pool = 8 → lấy hết.


| rank | hotel_id | g   | s   | rc    | type      | tên                              |
| ---- | -------- | --- | --- | ----- | --------- | -------------------------------- |
| 1    | 25773171 | 9.5 | 9.1 | 3918  | Khách sạn | Holiday Inn Resort Ho Tram Beach |
| 2    | 6363024  | 9.4 | 9.0 | 5015  | Khách sạn | Melia Ho Tram Beach Resort       |
| 3    | 2114938  | 9.3 | 8.9 | 540   | Khách sạn | Hai Long Hotel                   |
| 4    | 48561897 | 9.1 | 8.8 | 1738  | Khách sạn | Emerald Ho Tram Resort           |
| 5    | 1122450  | 9.0 | 8.6 | 2581  | Khách sạn | Pullman Vung Tau                 |
| 6    | 161729   | 8.6 | 8.8 | 10495 | Khách sạn | The Imperial Vung Tau            |
| 7    | 462837   | 8.0 | 7.9 | 1029  | Resort    | Vietsovpetro Ho Tram Resort      |
| 8    | 412707   | 7.6 | 8.2 | 2767  | Khách sạn | Muong Thanh Holiday Vung Tau     |


---

## GS-067 — Hội An · grade "Dịch vụ"

**Query:** "Tìm khách sạn ở Hội An có dịch vụ chăm sóc khách hàng tốt"
**Rank theo:** grade `Dịch vụ` ↓ → review_score ↓ → review_count ↓. pool = 22.


| rank | hotel_id | g   | s   | rc    | type      | tên                                    |
| ---- | -------- | --- | --- | ----- | --------- | -------------------------------------- |
| 1    | 44777877 | 9.9 | 9.7 | 10551 | Khách sạn | Grand Sunrise Palace Hoi An            |
| 2    | 63917222 | 9.9 | 9.7 | 1114  | Khách sạn | Hoianese Quiet Old Town Hotel          |
| 3    | 6255260  | 9.8 | 9.4 | 167   | Khách sạn | Sunora Villa Hoi An                    |
| 4    | 1639502  | 9.7 | 9.4 | 302   | Resort    | Four Seasons Resort The Nam Hai        |
| 5    | 1193207  | 9.6 | 9.0 | 1620  | Khách sạn | Gia Huy Riverside Hotel Hoi An         |
| 6    | 36697714 | 9.5 | 9.1 | 1759  | Khách sạn | Hoianan Boutique Hotel                 |
| 7    | 1803429  | 9.5 | 9.0 | 3744  | Khách sạn | Wyndham Garden Hoi An Cua Dai Beach    |
| 8    | 6945065  | 9.4 | 9.1 | 1246  | Khách sạn | The Nam An Villa Hoi An                |
| 9    | 16375525 | 9.4 | 9.0 | 2101  | Khách sạn | New World Hoiana Hotel                 |
| 10   | 38692610 | 9.4 | 9.0 | 723   | Khách sạn | Happy Life Memories Hoi An Hotel & Spa |


Ghi chú tiebreak: rank 1–2 cùng g=9.9, s=9.7 → review_count (10551 > 1114).

---

## GS-068 — Nha Trang · grade "Độ sạch sẽ"

**Query:** "Tìm khách sạn ở Nha Trang sạch sẽ, phòng ốc gọn gàng sạch"
**Rank theo:** grade `Độ sạch sẽ` ↓ → review_score ↓ → review_count ↓. pool = 38.


| rank | hotel_id | g   | s   | rc   | type      | tên                                   |
| ---- | -------- | --- | --- | ---- | --------- | ------------------------------------- |
| 1    | 33589745 | 9.6 | 9.0 | 620  | Khách sạn | The Westin Resort & Spa Cam Ranh      |
| 2    | 263516   | 9.5 | 9.3 | 4207 | Resort    | Vinpearl Luxury Nha Trang             |
| 3    | 38775535 | 9.5 | 9.1 | 1686 | Resort    | TTC Van Phong Bay Resort              |
| 4    | 75690457 | 9.4 | 9.1 | 79   | Khách sạn | Mercure Nha Trang Beach               |
| 5    | 78340310 | 9.4 | 9.0 | 198  | Khách sạn | JW Marriott Cam Ranh Bay Resort & Spa |
| 6    | 83464707 | 9.3 | 9.0 | 141  | Khách sạn | Four Points by Sheraton Nha Trang     |
| 7    | 6421211  | 9.2 | 8.9 | 3997 | Khách sạn | Muong Thanh Luxury Vien Trieu         |
| 8    | 6359030  | 9.2 | 8.9 | 3579 | Khách sạn | Muong Thanh Luxury Khanh Hoa          |
| 9    | 1986410  | 9.2 | 8.9 | 3549 | Resort    | Meliá Vinpearl Cam Ranh Beach Resort  |
| 10   | 210187   | 9.1 | 9.0 | 4633 | Khách sạn | Sheraton Nha Trang Hotel & Spa        |


Ghi chú tiebreak: rank 7–9 cùng g=9.2, s=8.9 → review_count (3997 > 3579 > 3549).

---

## GS-069 — Đảo Phú Quốc · grade "Đáng tiền" · **RESORT-only**

**Query:** "Tìm resort ở Phú Quốc đáng đồng tiền, xứng đáng với chi phí"
**Lọc:** `accommodation_type == Resort`. **Rank theo:** grade `Đáng tiền` ↓ → review_score ↓ → review_count ↓. pool(resort) = 10 → lấy hết.


| rank | hotel_id | g   | s   | rc    | type   | tên                                 |
| ---- | -------- | --- | --- | ----- | ------ | ----------------------------------- |
| 1    | 2577124  | 9.2 | 9.1 | 7298  | Resort | Lahana Resort Phu Quoc & Spa        |
| 2    | 4462454  | 9.1 | 9.1 | 2396  | Resort | Thien Thanh Phu Quoc Resort         |
| 3    | 10247322 | 9.0 | 8.8 | 3610  | Resort | Vida Loca Phu Quoc Resort           |
| 4    | 6377313  | 8.9 | 8.7 | 8864  | Resort | Vinpearl Wonderworld Phu Quoc       |
| 5    | 625168   | 8.8 | 8.8 | 10504 | Resort | Vinpearl Resort & Spa Phu Quoc      |
| 6    | 1032420  | 8.6 | 8.8 | 2468  | Resort | Sheraton Phu Quoc Long Beach Resort |
| 7    | 1158643  | 8.4 | 8.4 | 1700  | Resort | Tropicana Resort Phu Quoc           |
| 8    | 11013    | 8.3 | 8.4 | 3496  | Resort | Saigon Phu Quoc Resort and Spa      |
| 9    | 30897715 | 7.4 | 7.4 | 831   | Resort | Sun Viet Resort Phu Quoc            |
| 10   | 296330   | 7.2 | 7.2 | 2590  | Resort | Arcadia Phu Quoc Resort             |


---

## GS-070 — Nha Trang · grade "Dịch vụ" · **RESORT-only**

**Query:** "Tìm resort ở Nha Trang có dịch vụ tốt, nhân viên thân thiện"
**Lọc:** `accommodation_type == Resort`. **Rank theo:** grade `Dịch vụ` ↓ → review_score ↓ → review_count ↓. pool(resort) = 6 → lấy hết.


| rank | hotel_id | g   | s   | rc    | type   | tên                                      |
| ---- | -------- | --- | --- | ----- | ------ | ---------------------------------------- |
| 1    | 263516   | 9.7 | 9.3 | 4207  | Resort | Vinpearl Luxury Nha Trang                |
| 2    | 1986410  | 9.3 | 8.9 | 3549  | Resort | Meliá Vinpearl Cam Ranh Beach Resort     |
| 3    | 38775535 | 9.1 | 9.1 | 1686  | Resort | TTC Van Phong Bay Resort                 |
| 4    | 805030   | 9.1 | 8.8 | 10862 | Resort | Vinpearl Resort & Spa Nha Trang Bay      |
| 5    | 65153    | 8.9 | 8.7 | 8281  | Resort | Vinpearl Resort Nha Trang                |
| 6    | 6251087  | 8.9 | 8.7 | 3429  | Resort | Nha Trang Marriott Resort & Spa, Hon Tre |


Ghi chú tiebreak: rank 3–4 cùng g=9.1 → review_score (9.1 > 8.8); rank 5–6 cùng g=8.9, s=8.7 → review_count (8281 > 3429).

---

## Tổng kết kiểm tra yêu cầu


| Yêu cầu                                                                      | Trạng thái                |
| ---------------------------------------------------------------------------- | ------------------------- |
| Tất cả `intent_type = hotel_search`                                          | ✔                         |
| Mỗi query đều nhắc tới `city`                                                | ✔                         |
| Ground truth lấy từ **review** (`reviews_detail.grades`), không từ amenities | ✔                         |
| Query KHÔNG chứa style trong `ontology/core/style.yaml`                      | ✔ (GS-066 né `thoải mái`) |
| `relevant_hotel_ids` đã sắp theo độ liên quan (grade ↓ → s ↓ → rc ↓)         | ✔                         |
| top_k = 10 (pool < 10 thì lấy hết: GS-066=8, GS-070=6)                       | ✔                         |
| Query "Tìm resort..." chỉ gồm `accommodation_type=Resort`                    | ✔ (GS-069, GS-070)        |


