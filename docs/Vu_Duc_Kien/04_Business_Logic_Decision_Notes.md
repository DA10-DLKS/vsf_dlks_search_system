# 04 — Business Logic / Decision Notes

> Các **quy tắc nghiệp vụ đã hardcode** và **lý do thiết kế** trong phạm vi `api/`
> (`main.py`, `frontend_adapter.py`) và các điểm neo quan trọng ở tầng dưới mà API phụ thuộc.
> Đây là tài liệu **quan trọng nhất cho việc bàn giao**: những con số/quy tắc dưới đây không
> hiển nhiên từ code, dễ bị sửa nhầm nếu không biết lý do.

---

## A. Trong `api/frontend_adapter.py`

### A1. Map "hạng giá" (price tier) → dải số VND khi query không nêu giá cụ thể

Trong `to_search_response()`:

```python
if price_min is None and price_max is None:
    tiers = set(intent.get("price_tiers") or [])
    if "PRICE_BUDGET" in tiers:
        price_max = 800000        # "bình dân" → tối đa 800k/đêm
    elif "PRICE_LUXURY" in tiers:
        price_min = 2000000       # "sang trọng" → từ 2 triệu/đêm trở lên
```

- **Quy tắc:** khi intent parser không rút ra được `price_min/price_max` số học từ query,
  nhưng có **hạng giá** (concept `PRICE_*`), thì áp ngưỡng cứng:
  - `PRICE_BUDGET` → `price_max = 800_000`
  - `PRICE_LUXURY` → `price_min = 2_000_000`
- ⚠️ `PRICE_MID` và `PRICE_UPSCALE` **không** được map (không set ngưỡng nào) — chủ ý, vì dải
  giữa mơ hồ, để rerank lo.
- **Ảnh hưởng:** ngưỡng này quyết định danh sách `rooms_matching[]` và `price_from` trả cho
  frontend. Sửa 2 con số này = đổi hành vi lọc phòng cho toàn bộ query kiểu "phòng bình dân",
  "khách sạn sang". Cần cân nhắc theo mặt bằng giá dữ liệu.

### A2. `rooms` bị **ghi đè** bằng danh sách phòng đã lọc giá

```python
if price_min is not None or price_max is not None:
    merged["rooms"] = filter_rooms(hid, min_price=price_min, max_price=price_max)
    prices = [r["price_per_night"] for r in merged["rooms"] if r.get("price_per_night")]
    merged["price_from"] = min(prices) if prices else None
else:
    merged["rooms"] = get_rooms(hid)
merged["rooms_matching"] = merged["rooms"]
```

- **Quyết định:** khi query có dải giá, frontend **chỉ thấy các phòng nằm trong dải** (không
  thấy phòng ngoài tầm giá). `price_from` cũng tính lại theo các phòng đã lọc.
- `rooms_matching` = alias của `rooms` sau lọc (frontend đọc field này để highlight).
- **Lưu ý bàn giao:** nếu một khách sạn có tất cả phòng ngoài dải giá → `rooms` rỗng,
  `price_from = None`. Khách sạn **vẫn xuất hiện** trong `results` (không bị loại), vì việc chọn
  hotel là ở pipeline; adapter chỉ lọc phòng để hiển thị.

### A3. Nguồn dữ liệu hotel = **file cache local**, KHÔNG gọi OTA API

```python
KO_JSON = "knowledge_engineering/enrichment/knowledge_objects.json"
# và hotel_detail_cache.json qua knowledge_engineering/common/hotel_data.py
```

- **Quyết định thiết kế (ghi trong docstring):** thay OTA (Supabase) API bằng
  `hotel_detail_cache.json` (~6.6MB, 520 hotel) dựng từ dữ liệu đã làm sạch.
  - **Lý do:** nhanh hơn, không cold-start, không phụ thuộc Render.com/HTTP ngoài.
- Cache đọc lazy + `lru_cache(maxsize=1)` → nạp 1 lần vào RAM. Đường dẫn override bằng
  `HOTEL_CACHE_PATH`.
- **Hệ quả:** dữ liệu hotel là **snapshot tĩnh**. Muốn cập nhật thông tin khách sạn phải build
  lại cache (không phải sửa API).

### A4. Evidence "grounded" từ ABSA — điểm mạnh/yếu THẬT từ review

`_grounded_evidence()` đọc `semantic_profile` (tích cực) và `negative_style_profile` (tiêu cực)
từ nhãn KE (`labels_for(hotel_id)`), rồi:

- **Sắp xếp ưu tiên concept KHỚP nhu cầu user:** khóa sort `_pos_key` đặt concept có trong
  `query_concepts` lên trước, sau đó theo `score` giảm dần. `matched=True` cho concept khớp.
- **positives:** tối đa `max_pos=5`, chỉ lấy concept có `evidence_count >= 1` (bỏ concept không
  có bằng chứng review).
- **negatives:** lấy tối đa **2 span trích dẫn** review thật cho mỗi concept (`top_spans[:2]`).
- **Lý do:** để câu trả lời LLM (Node 9) **bám bằng chứng thật**, không "chém" — và ưu tiên nói
  về đúng tiêu chí user hỏi (matched), rồi mới tới điểm mạnh nổi bật khác.

### A5. `context_chunks` để hiển thị — 3 loại chunk

`_evidence_chunks()` dựng danh sách chunk cho UI theo thứ tự:
1. `hotel_content` — 400 ký tự đầu mô tả khách sạn (nếu có).
2. `absa_positive` — mỗi điểm mạnh, **matched xếp trước** không-matched.
3. `absa_negative` — mỗi điểm yếu **có span** (bỏ điểm yếu không có trích dẫn), matched trước.

Text được format tiếng Việt cố định (VD: `"Điểm mạnh (khớp nhu cầu): Vị trí — đánh giá tích
cực 0.82 từ 40 lượt review."`). Đây là **template hiển thị**, không phải LLM sinh.

### A6. Bảng dịch concept → tiếng Việt (hardcode)

Các dict `_AMEN_VI`, `_PURPOSE_VI`, `_PRICE_VI`, `_ASPECT_VI` map concept_id → nhãn tiếng Việt
(VD `AMEN_POOL` → "Hồ bơi", `PRICE_LUXURY` → "Sang trọng"). `_concept_vi()` tra lần lượt
aspect → purpose → amenity, fallback trả nguyên concept_id.

- **Cắt bớt hiển thị:** `amenities[:8]`, `best_for[:3]` trong `_hotel_metadata()`.
- **Bàn giao:** thêm amenity/concept mới ở ontology mà **quên thêm vào các dict này** → frontend
  hiển thị mã thô (`AMEN_XYZ`) thay vì tiếng Việt. Đây là điểm dễ sót khi mở rộng ontology.

### A7. `price_level` và `ranking_info`

```python
price_level = next((_PRICE_VI[c] for c in concepts if c in _PRICE_VI), "Unknown")
# ranking_info gộp sao + điểm: "4★ · điểm 8.5/10"
```
Nếu không có concept giá → `"Unknown"`. Nếu thiếu sao/điểm → `"No ranking information"`.

---

## B. Trong `api/main.py`

### B1. `POST /search` KHÔNG sinh LLM answer; `POST /context` mới sinh

```python
# fe_search:
result = run_hybrid_search(..., generate_answer=False)   # cố ý False
```

- **Quyết định:** trang danh sách kết quả phải nhanh → **không** gọi LLM ở `POST /search`.
  Câu trả lời (chậm) chỉ sinh khi user mở chi tiết 1 khách sạn (`POST /context`).
- **Lý do:** LLM có thể mất vài giây; nếu chờ answer cho cả danh sách thì trang tìm kiếm ì.
  Đây là lý do tách 2 endpoint. `CONTEXT_DURATION` có buckets tới 120s vì LLM chậm.

### B2. `filters` trong `SearchRequest` nhận nhưng chưa xử lý

```python
class SearchRequest(BaseModel):
    query: str
    filters: dict | None = None      # ← khai báo
    top_n: int = Field(default=10, ge=1, le=10)
```
Handler `fe_search` **không** truyền `filters` xuống `run_hybrid_search`. Lọc thực tế **suy ra
từ `query`** qua intent parser (giá/sao/city/concept).

- **Trạng thái:** đây là field dự trù cho hard-filter từ UI, **chưa nối**. Nếu người kế nhiệm
  cần lọc cứng theo UI (city/price từ dropdown), phải: (1) đọc `filters`, (2) truyền vào pipeline
  (pipeline có sẵn `inmemory_hard_filter(city=…, price_min=…, …)`). Ghi rõ để tránh tưởng đã hoạt động.

### B3. `top_n` frontend giới hạn `1..10`, các GET debug tới `20`

- `SearchRequest.top_n`: `ge=1, le=10` (frontend).
- `GET /hybrid_search top_n`, `GET /search size`, `GET /hotel/{id}/ask top_k`: `1..20`.
- **Lý do:** frontend hiển thị tối đa 10 card; debug cần xem rộng hơn.

### B4. `result_id` phải dạng `"hotel_<id>"`

```python
hotel_id = result_id.replace("hotel_", "")
```
- Đây là **hợp đồng ngầm** giữa `POST /search` (trả `hotel_id`) và frontend (gửi lại
  `"hotel_<id>"`). Nếu frontend gửi sai prefix, `hotel_id` sẽ sai → context nghèo. Không có
  validation chặt (không ném 404).

### B5. Warmup model ở startup — tránh crash torch (exit 139)

Xem chi tiết ở [01_API_Overview_Architecture.md](01_API_Overview_Architecture.md#6-vòng-đời-ứng-dụng-startup--request--shutdown).
Tóm tắt: route hybrid là hàm `def` → chạy ở threadpool. Model torch (bge-m3, cross-encoder) mà
lazy-load lần đầu trong thread con → **native crash exit 139** trên CPU/Windows. Nên ép khởi tạo
ở main thread lúc startup. **Đừng đổi route sang lazy-init model** nếu không hiểu điều này.

### B6. `USE_RERANKER` mặc định **off**

- Cross-encoder rerank chỉ bật khi `USE_RERANKER=1`. Mặc định off vì **đắt và đã đo là không
  kéo recall** (mục tiêu là MRR/thứ hạng). Khi off, pipeline rơi về "density-fallback" rerank.
- `rerank_method` trong response cho biết chế độ **thực tế đã chạy** — kể cả khi bật nhưng model
  load lỗi thì tự là `density_fallback` (phản ánh đúng thực tế).

### B7. Metrics: 2 bộ registry gộp chung

- `search_bm25_*` (cũ, khai báo trong `main.py`) và `da10_*` (observability) cùng đăng ký vào
  **`REGISTRY` chung** → `/metrics` trả cả hai trong 1 `generate_latest`. Đừng tạo registry riêng.
- `SEARCH_ZERO_RESULTS` được đếm theo `search_mode` (`hybrid`/`frontend`/`hotel_ask`) khi kết
  quả rỗng → dùng để cảnh báo "search trả màn hình trắng".

### B8. Degraded mode được đếm, không giấu

Pipeline vẫn `200` khi thiếu vector/BM25 (tụt candidate-only), nhưng đếm
`da10_search_degraded_total{source=bm25|vector|both}` để dashboard phát hiện. Triết lý: **thà
phục vụ kết quả kém còn hơn lỗi, nhưng phải nhìn thấy được** khi đang kém.

---

## C. Quy tắc parse (tầng dưới — `retrieval/query_processing/intent_parser.py`)

> API phụ thuộc trực tiếp vào các quy tắc này (qua `parse_intent`). Ghi ở đây vì đây chính là
> "parse giá trên/dưới X triệu" mà nhiệm vụ yêu cầu, và nó quyết định hành vi `POST /search`.

### C1. Đơn vị tiền → hệ số nhân
```python
_UNIT_MULT = {"k": 1_000, "nghìn": 1_000, "nghin": 1_000, "tr": 1_000_000, "triệu": 1_000_000}
```
- `k` / `nghìn` = ×1.000; `tr` / `triệu` = ×1.000.000.

### C2. Cú pháp "1tr2" = 1.200.000
- `_TR_INFIX_RE` chuẩn hóa `<N>tr<M>` → `<N>.<M> triệu` (M là phần trăm-nghìn, 1 chữ số).
  VD `1tr2` → `1.2 triệu` = 1.200.000; `2tr5` → 2.500.000.

### C3. Các mẫu giá (thứ tự ưu tiên)
1. **Range kép** (ưu tiên cao nhất): `từ 800k đến 1tr2`, `800 nghìn - 1.2 triệu` →
   `price_min` + `price_max`. Nếu vế đầu thiếu đơn vị thì **mượn đơn vị vế sau** ("1 đến 2 triệu").
2. **`tầm/khoảng/cỡ/xấp xỉ X triệu`** → khoảng ±30%: `price_min = X*0.7`, `price_max = X*1.3`.
3. **`dưới / < / không quá / tối đa X triệu`** → chỉ `price_max` (xóa `price_min`).
4. **`trên / > / hơn / cao hơn X triệu`** → chỉ `price_min` (xóa `price_max`).
5. Tương tự cho đơn vị **nghìn/k**: "không quá X nghìn", "trên X nghìn".
- **Superlative:** `rẻ nhất` → `sort=price_asc`; `đắt nhất/sang nhất/xịn nhất` → `sort=price_desc`.

### C4. Điểm review & số sao
- `trên/> /từ X điểm` → `score_min = X`.
- `N sao` → `star_eq = N`.

### C5. Các quy tắc "khử nhiễu" concept (dễ bị bỏ sót khi bảo trì)
- **Gia đình đè lãng mạn:** câu vừa có `PURPOSE_FAMILY` vừa `PURPOSE_ROMANTIC` → bỏ ROMANTIC
  **trừ khi** có cue romantic mạnh (trăng mật/honeymoon/lãng mạn/hẹn hò/người yêu). Tránh
  "2 vợ chồng + 2 con" bị gán nhầm romantic.
- **Suppress `PRICE_BUDGET`** khi "ngân sách/budget" đi kèm **số tiền** (đó là khai báo ngân
  sách, không phải phân khúc giá rẻ).
- **Negation:** concept trong vế phủ định ("không có trẻ em", "không sát đường") → đưa vào
  `exclude_concepts`, loại khỏi `concepts`. Ở pipeline, exclude chỉ **loại cứng** concept
  HARD/PURPOSE/OBJ; concept feel (STYLE_/ASPECT_) để rerank phạt mềm.
- **City hardcode:** danh sách `_CITIES` (18 thành phố VN phổ biến) dùng để bắt city cho SQL
  filter. Thành phố ngoài list sẽ không được nhận diện là city.

---

## D. Điểm nghiệp vụ ở pipeline mà API dựa vào (tham chiếu nhanh)

> Chi tiết ở `retrieval/hybrid_search/pipeline.py`. Liệt kê để người tiếp nhận biết vì sao kết
> quả `POST /search` / `GET /hybrid_search` ra như vậy.

- **Semantic-only boost:** câu cảm tính thuần (không city/concept/giá/sao/brand) → vector đề cử
  top-40 hotel (điểm cosine ≥ `SEMANTIC_VECTOR_FLOOR = 0.5`) vào pool, và rerank nâng trọng số
  neural (`{"neural": 0.4, "review": 0.1}`) để hotel "hiểu đúng ngữ nghĩa" lên top thay vì
  "review cao chung chung".
- **OBJ soft filter:** "khách sạn" (`OBJ_HOTEL`) = mọi loại lưu trú, **không lọc**; chỉ lọc khi
  nêu loại cụ thể (resort/villa) mà không kèm `OBJ_HOTEL`.
- **Không bao giờ trả màn hình trắng:** candidate rỗng → dùng vector broad; vector vắng → top
  hotel theo review score.
- **Fusion không thay thế candidate:** vector/BM25 chỉ **bổ sung tín hiệu rerank**; hotel
  candidate không có chunk text vẫn ở lại (giữ recall).

---

## E. Tổng hợp "magic numbers" cần biết khi chỉnh

| Giá trị | Ở đâu | Ý nghĩa | Rủi ro khi sửa |
|---------|-------|---------|----------------|
| `800_000` / `2_000_000` | `frontend_adapter.to_search_response` | Ngưỡng PRICE_BUDGET / PRICE_LUXURY | Đổi phòng hiển thị cho query theo hạng giá |
| `max_pos=5` | `_grounded_evidence` | Số điểm mạnh tối đa | Nhiều/ít evidence cho LLM |
| `top_spans[:2]` | `_grounded_evidence` | Số trích review tiêu cực/concept | Độ dày dẫn chứng |
| `content[:400]`, `[:600]`, `[:160]` | adapter | Cắt text hiển thị/citation | Độ dài UI |
| `amenities[:8]`, `best_for[:3]` | `_hotel_metadata` | Số nhãn hiển thị | UI |
| `top_n le=10` / `le=20` | `main.py` | Giới hạn kết quả FE vs debug | Số card |
| `USE_RERANKER=0` | env | Bật cross-encoder | Tốc độ vs thứ hạng |
| `DEP_PROBE_INTERVAL=30` | env | Chu kỳ probe deps | Độ tươi gauge |
| `0.7` / `1.3` | intent_parser | Biên ±30% cho "tầm X triệu" | Độ rộng dải giá |
| `SEMANTIC_VECTOR_N=40`, `FLOOR=0.5` | pipeline | Vector đề cử câu cảm tính | Recall câu semantic |

---

## F. Nợ kỹ thuật / việc còn dở (bàn giao)

1. **`api/app`, `api/routes`, `api/schemas` rỗng** — kế hoạch tách router/schema khỏi `main.py`
   (comment `TODO: register routers`). Chưa làm. `main.py` hiện ~590 dòng chứa tất cả.
2. **`SearchRequest.filters` chưa nối** (B2) — cần nối UI hard-filter xuống pipeline.
3. **Bản đề xuất schema `/api/v1/*`** (`VuDucKien_api_schema_proposal.md`) **không khớp** code
   thật (không có prefix `/api/v1`, không có `query_id`, `parsed_intent` shape khác…). Giữ làm
   tham chiếu lịch sử, **không dùng làm spec**.
4. **Không có auth** — CORS mở `*`, không có API key. OK cho nội bộ/dev, cần bổ sung nếu public.
5. **Dữ liệu hotel tĩnh** (A3) — cập nhật phải build lại cache.
