# Báo cáo 02 — Ontology & Knowledge Engineering

Ontology là "bộ não khái niệm" của hệ thống: nó biến văn bản tự do (mô tả khách sạn, review) và câu hỏi tiếng Việt ("khách sạn yên tĩnh gần biển cho gia đình") thành **concept có cấu trúc** mà tầng retrieval lọc/xếp hạng được. Báo cáo này mô tả thiết kế ontology, quy trình knowledge engineering (KE), và cách tri thức được "đính" vào index.

---

## 1. Cấu trúc thư mục & vai trò

```
ontology/
  core/                  ← nguồn chân lý do người duyệt (tiers Core)
    amenity.yaml         tiện ích (AMEN_*)
    style.yaml           phong cách/cảm nhận (STYLE_*)
    aspect.yaml          khía cạnh đánh giá (ASPECT_*, 7 cái)
    setting.yaml         bối cảnh vị trí (SETTING_*)
    purpose.yaml         mục đích chuyến đi (PURPOSE_*)
    object_type.yaml     loại hình lưu trú (OBJ_*)
    price_tier.yaml      bậc giá (PRICE_*)
    location*.yaml       địa danh (tự sinh: country/province/city/area/landmark)
  candidate/             ← concept ứng viên chờ duyệt (chưa vào Core)
  relations/             ← quan hệ giữa concept (curated / candidates / generated / rejected)
  facets.yaml            nhóm facet cho filter
  query_expansion.yaml   mở rộng truy vấn
  synonym_dictionary.yaml  ← SINH RA, nguồn concept DUY NHẤT cho retrieval
  metadata_schema.yaml   schema metadata
```

KE (`knowledge_engineering/`) là phần **code** vận hành ontology: trích xuất thực thể, làm giàu (enrichment), gom relation, governance.

---

## 2. Thiết kế ontology (v2)

### 2.1 Hai tầng concept: Core và Candidate

- **Core tier**: concept đã duyệt, ổn định, người chịu trách nhiệm — nằm trong `ontology/core/*.yaml`.
- **Candidate tier**: concept đào được từ dữ liệu, **chưa** vào Core; chờ duyệt rồi mới "promote".

Tách hai tầng để retrieval luôn chạy trên vocabulary ổn định, còn việc mở rộng diễn ra có kiểm soát.

### 2.2 Phân loại concept theo prefix

| Prefix | Loại | Vai trò trong retrieval |
|---|---|---|
| `AMEN_*` | Amenity (tiện ích) | **filter cứng** (hard) |
| `SETTING_*` | Setting (bối cảnh vị trí) | **filter cứng** (hard) |
| `STYLE_*` | Style (phong cách/cảm nhận) | **filter mềm / rerank** (feel) |
| `ASPECT_*` | Aspect (7 khía cạnh đánh giá) | **rerank** (feel) |
| `PURPOSE_*` | Purpose (mục đích) | **chỉ ưu tiên ranking, không lọc cứng** |
| `OBJ_*` | Object type | lookup candidate |
| `PRICE_*` | Price tier | lookup + price_fit |
| location/landmark | Địa danh | lookup + rank theo km |

> Phân biệt cốt lõi: **attributes là filter, không phải concept**. `label` (định danh) khác `surface_forms` (cách viết người dùng gõ).

### 2.3 fact_type: hard vs soft

Mỗi fact (concept gắn vào khách sạn) có `fact_type`:
- **hard**: sự thật khẳng định được (có hồ bơi, gần biển) → dùng filter cứng.
- **soft**: cảm nhận/độ (yên tĩnh, lãng mạn) → dùng rerank, không loại cứng.

### 2.4 Quan hệ (`relations/`)

Bốn tệp tách trạng thái rõ ràng:
- `curated.yaml` — quan hệ người duyệt.
- `candidates.yaml` — ứng viên (status `pending`/`approved`/`rejected`).
- `generated.cooccurrence.yaml` — sinh tự động từ đồng xuất hiện.
- `rejected.yaml` — đã loại.

**Quy trình duyệt relation** theo pattern STYLE: sửa `status` trong `candidates.yaml` rồi chạy `apply_relation_review` (không dùng dict cứng trong code). Cách máy đào quan hệ và **tính điểm (lift)** xem mục **4.4**.

---

## 3. Synonym dictionary — cầu nối ngôn ngữ ↔ concept

`ontology/synonym_dictionary.yaml` là **nguồn concept DUY NHẤT** mà tầng retrieval đọc, được **sinh** từ `core/*.yaml` bằng `build_synonym_index`.

- Quy mô thực tế: **3.927 concept** có surface_forms (đếm trong repo).
- Mỗi concept_id ↔ danh sách cách viết tiếng Việt (có dấu / không dấu có kiểm soát).
- Nguyên tắc bất biến: **không tự build synonym riêng ở tầng retrieval** → tránh lệch giữa KE và search. Sửa `core/*.yaml` thì **phải build lại** synonym.

> ⚠ Bẫy đồng âm: fold dấu sinh đồng âm khác thanh (`mạng`→`mang`). Guard `_is_risky_short` chặn từ đơn âm tiết rủi ro; cụm dài vẫn cần rà tay.

---

## 4. Knowledge Engineering pipeline (`knowledge_engineering/`)

### 4.1 Máy tự sinh ontology Location & Landmark (`build_locations.py`)

Nguyên tắc xuyên suốt: **data-driven, không đoán** — chỉ sinh concept khi dữ liệu thực sự có; không suy diễn cái dữ liệu không nói rõ. Kết quả: **1 country / 14 province / 69 city / 126 area / 153 landmark**.

**(a) Cây Location (LOC_\*) — 4 tầng.** Quét toàn bộ `data/cleaned/hotel_*.json`, đọc field địa lý thật và đếm số hotel ở mỗi cấp:

```
country  (kind: country)  ← field `country`        → luôn = LOC_VIETNAM
  province (kind: place)  ← TÁCH từ "City (Tỉnh)"  → "Quy Nhơn (Bình Định)" ⇒ tỉnh Bình Định
    city   (kind: place)  ← field `city`           (gộp `province` field vì Agoda lẫn lộn)
      area (kind: area)   ← field `area`           (gộp `district`, vì area == district)
```

Ba điểm thiết kế đáng nói:
- **Tách tỉnh tự động, không bịa**: chỉ sinh tầng tỉnh khi tên city có tỉnh trong ngoặc `(...)` hoặc trước dấu `/`. Không có dấu hiệu → gắn thẳng vào LOC_VIETNAM.
- **Gộp field trùng**: Agoda crawl `province == city` và `district == area` gần 100% → giữ đúng "độ phân giải thật", không sinh tầng trùng vô nghĩa.
- **ID ổn định qua registry 3 tầng** (`location_id_registry.yaml`, append-only): (1) `external_id` = Agoda `city_id` (bền nhất, dù text đổi vẫn đúng ID) → (2) alias/slug đã từng thấy → (3) không khớp thì cấp ID mới + log duyệt. ID đã cấp **không bao giờ đổi** → tham chiếu ở `ontology.yaml`/golden không vỡ khi corpus mở rộng.

**(b) Landmark (LMK_\*) — tự sinh từ `nearby_places`.** Dữ liệu không có "danh sách landmark"; máy suy ra từ field `nearby_places[].name/type/distance_km` của từng hotel, qua nhiều lớp lọc:

- **Lọc theo type**: chỉ giữ ~26 loại có giá trị du lịch/định vị (bãi biển, đảo, vịnh, công viên giải trí, bảo tàng, đền chùa…); bỏ tiện ích đời thường (bệnh viện, ngân hàng, siêu thị).
- **Ngưỡng số-hotel ĐỘNG theo type** (điểm cốt lõi): type **cứng** (du lịch thật) giữ từ **≥1 hotel**; type **mềm** (công viên/hồ/sân bay — dễ lẫn rác) cần **≥2 hotel**. Lý do: "phổ biến toàn cục" KHÔNG đo đúng "có đáng là landmark" — một địa danh đặc sản vùng vốn chỉ gần vài hotel. Ngưỡng cứng cũ ≥4 từng giết oan VinWonders Nam Hội An, Bãi biển Nhật Lệ…
- **Khử rác 3 tầng**: blacklist tên generic ("công viên", "cầu") + regex chặn rác xuyên type (café/bar/CLB bị gán nhầm) + khử alias nhập nhằng (lõi đụng ≥2 landmark → loại khỏi tất cả).
- **Suy `located_in` gián tiếp**: lấy city xuất hiện ở nhiều hotel chứa landmark đó nhất (tie-break tất định để không dao động giữa các lần chạy).
- **Guard `loc_surface_norms` (pha 5)**: chặn alias lõi nuốt tên LOC — lõi "phú quốc" (từ "sân bay quốc tế phú quốc") trùng LOC_PHU_QUOC nên không thêm, kẻo query "phú quốc" lại ra sân bay.

> **Chuỗi rebuild bắt buộc khi đổi landmark**: `build_locations → build_relations → build_synonym_index → build_objects`. Quên `build_synonym_index` thì query mất landmark.

Các script khác: `build_location_setting.py`, `build_relations.py`, `build_relation_candidates.py`, `apply_relation_review.py`, `build_domain_stats.py` (xem 4.4 cho relation).

### 4.2 ABSA — LLM đọc review & cách tính điểm

Đây là Sprint 2 (làm giàu, không phải chunk/embed). Điểm cần nhấn mạnh: **LLM KHÔNG chấm điểm**. Quy trình tách 2 bước, 2 file, 2 nhiệm vụ:

| Bước | File | Nhiệm vụ | Có LLM? |
|---|---|---|---|
| Trích | `absa.py` | review → list `{concept, sentiment, span}` | Có (gpt-4o-mini) |
| Tính điểm | `profile_builder.py` | đếm pos/neg → ra score | Không — chỉ toán |

**(a) Bước trích (LLM).** Mỗi review → JSON. Ví dụ "Phòng sạch nhưng hơi ồn về đêm":

```json
{"items": [
  {"concept": "ASPECT_CLEANLINESS", "sentiment": "positive", "span": "Phòng sạch"},
  {"concept": "STYLE_QUIET",        "sentiment": "negative", "span": "hơi ồn về đêm"}]}
```

Ràng buộc: vocab **khóa cứng** (chỉ chọn concept có sẵn trong `ontology/core/*.yaml`, facet aspect/style); **trung tính** ("hơi ồn" → `STYLE_QUIET` + `negative`, KHÔNG bịa `STYLE_NOT_QUIET`); span trích nguyên văn để giải thích; mỗi review tối đa 1 phiếu/concept. Vận hành: batch 20 review/request, `temperature=0`, resume theo `review_id` + `prompt_version`, tính cả RPD (~10k/ngày), không chỉ tiền. **LLM dừng ở đây** — mới chỉ là dữ liệu thô đã gán nhãn.

**(b) Bước tính điểm — Wilson lower bound.** Với mỗi concept, gom hết review của hotel: `pos` = số phiếu khen, `n` = tổng phiếu (pos + neg), `p̂ = pos/n`. Điểm (z = 1.96):

```
            p̂ + z²/(2n)  −  z · √( (p̂·(1−p̂) + z²/(4n)) / n )
score  =  ─────────────────────────────────────────────────────
                          1 + z²/n
```

**Vì sao không dùng thẳng `p̂ = pos/n`?** Vì tỷ lệ thô "overconfident" khi ít data. Wilson **trừng phạt sự thiếu bằng chứng** — đúng cái cần khi xếp hạng hotel:

| Hotel | pos | n | p̂ thô | Wilson |
|---|---|---|---|---|
| A | 1 | 1 | 1.00 | ~0.21 |
| B | 8 | 10 | 0.80 | ~0.49 |
| C | 80 | 100 | 0.80 | ~0.71 |

A khen 1/1 (100%) nhưng chỉ 1 phiếu → điểm thấp; B và C cùng 80% nhưng C nhiều bằng chứng hơn → điểm cao hơn.

**(c) Phân vai 2 nguồn** (sau khi đo thấy review crawl thiên về điểm thấp):
- **ASPECT_\* (7 khía cạnh)**: score KHÔNG dùng ABSA — lấy thẳng từ Agoda `rating_breakdown` (`score = điểm/10`, là trung bình TOÀN BỘ review, đã cân bằng). ABSA chỉ thêm **span** dẫn chứng.
- **STYLE_\***: Agoda không có → ABSA là nguồn duy nhất, tính Wilson. **Chỉ đếm positive, bỏ negative** vì style là cặp đối nghĩa (sôi động ↔ yên tĩnh), không phải thang tốt↔xấu — "chê ồn" không có nghĩa "kém yên tĩnh". Score style = **mức độ HIỆN DIỆN của phong cách**. Cần `pos ≥ 3` mới công nhận.
- **`negative_style_profile`**: chê style tính Wilson riêng trên `neg/(pos+neg)`, cần ≥3 review chê, giữ tối đa 5 span — để hiển thị mặt trái.

**(d) Các thành phần enrichment khác:**
- **Candidate mining / discovery** (`candidate_mining.py`, `discovery_cluster.py`, `discovery_suggest.py`): đào concept mới. Bài học: n-gram + trần IDF **không đủ** (top ngập nhiễu đa ngôn ngữ); cách đúng = **LLM trích + embedding cluster (bge-m3) + LLM đề xuất**.
- **`profile_builder.py`** dựng `semantic_profile`, `negative_style_profile`; **`build_objects.py`** sinh `knowledge_objects.json` (**520 object**, 1/hotel) + `nearby_landmarks` (rank theo km).
- **`implicit_intent.py`** (common): query mô tả hoàn cảnh ("đi 2 con") → surface_forms tĩnh + RULES regex. PURPOSE chỉ ưu tiên ranking, không lọc cứng.

### 4.3 Governance (`governance/`)

- `audit_relations.py`, `relation_quality.py` — kiểm chất lượng quan hệ.
- `evaluate_query_expansion.py` — đo hiệu quả mở rộng truy vấn.
- `verify_relation_golden.py` — đối chiếu relation với golden.

### 4.4 Relation — quy trình & cách tính điểm

Có **2 loại relation khác hẳn nhau**:

**(a) `near` — hotel ↔ landmark** (`build_relations.py`). Quan hệ object-level (vật lý), KHÔNG có điểm, chỉ có khoảng cách:
1. Đọc tất cả LMK_\* trong ontology (label + surface_forms).
2. Với mỗi `nearby_places.name` → **khớp CHẶT**: tên phải BẰNG ĐÚNG một form landmark, không nhận cụm con (tránh "Bệnh viện Bãi Cháy" → "Bãi Cháy").
3. Một hotel trùng nhiều tên cho cùng landmark → giữ `distance_km` **nhỏ nhất**.
4. Output: `{from: acc_123, rel: near, to: LMK_BAI_DAI, distance_km: 0.5}` → trả lời "gần biển/gần sân bay", rank theo km.

**(b) `cooccurs_with` — concept ↔ concept** (`build_relation_candidates.py`). Đào cặp concept hay đi cùng nhau (vd "hồ bơi vô cực" thường đi với "phong cách sang trọng") bằng **association rule mining**, chỉ số chính là **lift**.

Với mỗi cặp a → b (N = tổng số hotel):
```
support(a)   = số hotel có concept a
probability  = P(b|a) = (số hotel có CẢ a&b) / support(a)   ← trong nhóm có a, bao nhiêu % cũng có b
base         = P(b)   = (số hotel có b) / N                 ← b phổ biến cỡ nào trên toàn corpus
lift         = probability / base
confidence   = min(0.7, 0.3 + 0.1 × lift)
```

Đọc **lift**: `=1` độc lập (tình cờ, bỏ); `>1` có a thì khả năng có b cao hơn nền → liên hệ thật; `<1` loại trừ nhau. Ví dụ: 100 hotel, 20 có `POOL_INFINITY`, trong đó 15 cũng có `STYLE_LUXURY`; toàn corpus 30 hotel `STYLE_LUXURY`:
```
probability = 15/20 = 0.75 ;  base = 30/100 = 0.30 ;  lift = 0.75/0.30 = 2.5  → mạnh, giữ
```

**Ngưỡng per-facet, không phẳng**: mỗi cặp loại facet có ngưỡng (support, prob, lift) riêng — vd `style→amenity` cần support≥3/lift≥1.3, `object_type→amenity` chặt hơn (support≥8/lift≥1.5); một số cặp bị block (`price_tier→style` chỉ curated tay). Cặp phải vượt CẢ 3 ngưỡng mới sinh candidate; mỗi concept giữ tối đa 5 cạnh.

**2 nguồn tín hiệu** (`--source=both`, đọc từ `knowledge_objects.json` — không phải hotel_tags): `metadata` (nhãn có/không) + `profile` (`semantic_profile` score ≥ 0.6, tức **dùng lại điểm Wilson ở 4.2** — đây là chỗ ABSA nối vào relation). LMK_\*/LOC_\* bị loại (object-level).

**Có người duyệt**: candidate sinh ở `status: pending`, KHÔNG tự vào ontology. Người sửa `approved`/`rejected` rồi chạy `apply_relation_review.py`; chạy lại generator giữ nguyên mọi quyết định đã có.

---

### 4.5 Sơ đồ luồng tổng (ABSA → profile → relation)

```
ABSA (4.2):
  review  →[LLM trích]→  {concept, sentiment, span}  →[đếm pos/n]→  Wilson  →  semantic_profile (score)
                                                                                      │
Relation (4.4):                                                                       │ score ≥ 0.6
  near:      nearby_places  →[khớp tên chặt]→  hotel—near→LMK (distance_km)            │
  cooccurs:  semantic_metadata + semantic_profile  ←───────────────────────────────────┘
                  →[tính lift]→  ngưỡng per-facet  →  candidate (pending)  →[người duyệt]→ ontology
```

| Phần | Máy làm gì | "Điểm" tính bằng |
|---|---|---|
| Location/LMK (4.1) | Quét data, đếm hotel, lọc type + ngưỡng động, ID ổn định | Không có điểm — ngưỡng số-hotel để lọc |
| ABSA (4.2) | LLM **chỉ trích**; máy chấm | **Wilson lower bound** (z=1.96); aspect lấy điểm Agoda/10 |
| Relation near (4.4a) | Khớp tên chặt landmark | Khoảng cách km nhỏ nhất |
| Relation cooccurs (4.4b) | Đào cặp concept | **lift = P(b\|a) / P(b)**, ngưỡng per-facet, rồi người duyệt |

---

## 5. Output tri thức: `knowledge_objects.json` → index

`knowledge_objects.json` (520 object) là **đầu ra cuối** của KE. Nó được đính vào chunk khi index qua `attach_ke_labels` (xem báo cáo 03), gồm:

| Trường | Dùng cho |
|---|---|
| `ontology_concepts` | filter cứng (Node 3) |
| `strong_feel_concepts` | rerank |
| `semantic_profile` | profile boost (Node 7) |
| `negative_style_profile` | tránh kết quả ngược ý |
| `nearby_landmarks` | rank theo khoảng cách |
| `location_concept` | lookup địa danh |
| `range_filters` | star/review_score (thật), price (placeholder) |

Đây là **khâu nối "KE → index"**: text chunk lấy từ `data/cleaned` (phong phú), còn NHÃN lấy từ KE. Nếu KE chưa có nhãn cho hotel nào thì bỏ qua, không phá payload.

---

## 6. Quy trình làm việc & nguyên tắc

- **Sequential sprint tasks**: làm tuần tự, không bịa input thiếu, hỏi người dùng khi thiếu.
- **Cấu trúc cố định**: config → `ontology/`; code + output → `knowledge_engineering/`. Đổi cấu trúc phải hỏi.
- **Đo bằng golden, không soi span tay**: đánh giá recall STYLE bằng `golden_set_v1.json`. Recall thấp → **backfill (batch ABSA)** là đúng thuốc, KHÔNG hạ ngưỡng / sửa công thức Wilson.
