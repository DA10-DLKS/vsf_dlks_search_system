# Báo cáo Sprint 1 — Semantic Foundation (DA10 Knowledge Engineering)

> **Người thực hiện:** Trương Anh Long — vai trò Knowledge Engineering, team DA10.
> **Phạm vi:** Sprint 1 = xây toàn bộ *nền tảng ngữ nghĩa* cho hệ thống tìm kiếm khách sạn.
> **Dữ liệu:** 51 khách sạn thật crawl từ Agoda (`data/raw/hotels/*.json`).
> **Ngày chốt báo cáo:** 2026-06-04.
> **Đối tượng đọc:** cả người trong và ngoài team — đọc xong hiểu *làm gì, tại sao, ra cái gì*.

---

## 1. Sprint 1 giải quyết vấn đề gì? (đọc phần này trước)

Hệ thống DA10 phải hiểu **ý nghĩa** câu hỏi của người dùng, không chỉ so khớp từ khóa. Ví dụ:

> Người dùng gõ: *"resort yên tĩnh gần biển cho gia đình ở Nha Trang"*

Máy phải hiểu:
- "resort" = loại hình lưu trú
- "yên tĩnh" = phong cách (một *cảm nhận*, không phải từ khóa cứng)
- "gần biển" = vị trí/tiện ích
- "gia đình" = nhóm khách
- "Nha Trang" = địa danh (lọc cứng)

Nhưng mỗi người gõ một kiểu: "hồ bơi" / "bể bơi" / "pool"; "yên tĩnh" / "yen tinh" (không dấu).
Và mỗi nguồn dữ liệu (Agoda, Booking...) lại dùng từ khác nhau cho cùng một thứ.

**Sprint 1 xây "bộ não từ vựng" để quy mọi cách diễn đạt đó về cùng một khái niệm chuẩn.**
Đây là **trần chất lượng** của cả hệ thống: nếu tầng này sai, mọi tầng tìm kiếm/gợi ý phía sau đều sai.

---

## 2. Ba khái niệm cốt lõi (hiểu 3 cái này là hiểu toàn bộ thiết kế)

### 2.1 Concept — "khái niệm trung tính"
Mỗi ý nghĩa được gán một **mã trung tính** (concept_id), tách rời khỏi ngôn ngữ:

```
STYLE_QUIET   <- "yên tĩnh" (vi) = "quiet" (en) = "yen tinh" (không dấu)
AMEN_POOL     <- "hồ bơi" = "bể bơi" = "pool"
```

**Quy tắc vàng:** concept *trung tính về cảm xúc*. Không tạo `STYLE_NOT_QUIET` hay `ROOM_CLEAN`.
Chỉ có `STYLE_QUIET`, `ASPECT_CLEANLINESS`; còn tốt/xấu để ở một trường `sentiment` riêng.
→ Lý do: nếu nhét cảm xúc vào mã, số khái niệm sẽ nổ ra gấp đôi và rối loạn tìm kiếm.

### 2.2 Hard fact vs Soft fact
- **Hard fact** = sự thật có/không, lấy từ dữ liệu cấu trúc: *có hồ bơi*, *ở Nha Trang*, *5 sao*.
  → dùng để **lọc cứng** (loại hẳn khách sạn không thỏa).
- **Soft fact** = trải nghiệm/cảm nhận, đến từ đánh giá của khách: *yên tĩnh*, *lãng mạn*, *sạch sẽ*.
  → chỉ dùng để **tăng/giảm điểm** xếp hạng, KHÔNG lọc cứng (vì là suy luận, có thể sai).

### 2.3 Core vs Candidate (ontology có kiểm soát)
- **Core** = khái niệm chuẩn ngành, đáng tin, dùng ngay. Định nghĩa từ Agoda/Booking/Google Hotels/Tripadvisor.
- **Candidate** = khái niệm *ứng viên* phát hiện từ đánh giá/log tìm kiếm. **Chưa dùng** — phải có người
  duyệt + kiểm trên bộ test mới được "lên" Core.
  → Lý do: tránh việc cứ thấy từ lạ trong review là thêm khái niệm, khiến ontology phình loạn.

---

## 3. Luồng đã làm — từng bước (làm gì → tại sao → ra cái gì)

Sprint 1 gồm 8 task. Thứ tự có chủ đích: mỗi task là đầu vào của task sau.

### Task 1.1 — Domain Analysis (Phân tích miền dữ liệu)
- **Làm gì:** đọc 51 khách sạn thật, thống kê xem dữ liệu Agoda có những trường ngữ nghĩa nào
  (loại hình, tiện ích, nhóm khách, view, tag đánh giá, địa danh lân cận).
- **Tại sao:** phải hiểu dữ liệu thật trước khi thiết kế khái niệm — không bịa từ trí tưởng tượng.
- **Ra cái gì:** `docs/reports/ontology/sprint1/domain_analysis.md` (35 khái niệm ứng viên, đều có bằng chứng nguồn).

### Task 1.2 — Concept Registry (Sổ đăng ký khái niệm)
- **Làm gì:** biến khái niệm ứng viên thành **73 concept Core** chính thức, song ngữ Việt–Anh,
  chia 8 nhóm (facet): loại hình, vị trí, tiện ích, bối cảnh, giá, nhóm khách, phong cách, khía cạnh.
- **Tại sao:** đây là "nguồn sự thật duy nhất" — mọi file khác sinh ra từ đây.
- **Ra cái gì:** `ontology/core/*.yaml` (8 file) + `ontology/_meta.yaml` (quy ước chung)
  + `ontology/candidate/candidate_queue.yaml` (hàng đợi ứng viên, hiện trống).

### Task 1.3 — Vietnamese Normalization (Chuẩn hóa tiếng Việt)
- **Làm gì:** hàm `normalize()` xử lý 3 việc: gộp dấu (NFC) → tách từ ghép ("hồ bơi"→"hồ_bơi")
  → tạo biến thể không dấu ("gần biển"→"gan bien").
- **Tại sao:** để câu người dùng gõ và nhãn trong hệ thống khớp được nhau, dù gõ có dấu hay không.
- **Ra cái gì:** `knowledge_engineering/common/normalize.py`. Áp **chung** cho cả query lẫn nhãn.

### Task 1.4 — Faceted Taxonomy (Phân loại đa chiều)
- **Làm gì:** định nghĩa 8 facet (trục phân loại độc lập), mỗi facet ghi rõ: một-giá-trị hay nhiều-giá-trị,
  ánh xạ tới "slot" của DA09, và trỏ tới trường thật trong contract metadata.
- **Tại sao:** một resort *đồng thời* thuộc nhiều trục (loại hình + vị trí + giá + phong cách...).
  Mỗi trục ánh xạ 1-1 với một bộ lọc của hệ thống tìm kiếm.
- **Ra cái gì:** `ontology/facets.yaml` (8 facet + 4 bộ lọc số: sao, điểm đánh giá, giá, khoảng cách).

### Task 1.5 — Ontology Relations (Quan hệ / đồ thị tri thức nhẹ)
- **Làm gì:** dựng quan hệ giữa các thực thể — quan trọng nhất là quan hệ **"gần"** (hotel ↔ địa danh).
  Tận dụng trường `nearby_places` (đã có sẵn khoảng cách km) trong data.
- **Tại sao:** để trả lời "gần VinWonders không?" bằng **đồ thị**, không phải so khớp từ khóa.
- **Ra cái gì:** `ontology/ontology.yaml` (6 địa danh + quan hệ thuộc-về)
  + `ontology/relations_near.generated.yaml` (**22 quan hệ "gần"**, tự sinh từ data).

### Task 1.6 — Synonym Dictionary (Từ điển đồng nghĩa)
- **Làm gì:** tự sinh bản đồ *cách-gõ-bề-mặt → concept_id* từ ontology. Mỗi cách gõ index cả 2 dạng
  (có dấu + không dấu).
- **Tại sao:** đây là thứ tầng tìm kiếm (Anh Tài) dùng để hiểu câu hỏi người dùng.
- **Ra cái gì:** `ontology/synonym_dictionary.yaml` (**543 cách gõ**). Bàn giao → Anh Tài.

### Task 1.7 — Query Expansion (Mở rộng truy vấn) — ⚠ CHƯA HOÀN TẤT
- **Làm gì:** luật mở rộng *khái niệm → khái niệm* để tăng độ phủ tìm kiếm
  (vd "gia đình" → kéo thêm "câu lạc bộ trẻ em", "hồ bơi trẻ em").
- **Tại sao:** người dùng hỏi "gia đình" thường ngầm muốn các tiện ích gia đình.
- **Ra cái gì:** `ontology/query_expansion.yaml` (**21 luật**) — nhưng **tất cả đánh dấu `unverified`**
  (xem mục 5: cần bộ test golden mới kiểm được).

### Task 1.8 — Metadata Schema (Hợp đồng dữ liệu) — 1 trong 3 contract chốt cuối Sprint 1
- **Làm gì:** chốt schema cho "đối tượng tri thức" (knowledge object) mà DA10 bàn giao cho DA09,
  + viết code kiểm tra (pydantic).
- **Tại sao:** đây là *mặt tiếp xúc* giữa DA10 và DA09 — hai bên phải thống nhất để không lệch.
- **Ra cái gì:** `ontology/metadata_schema.yaml` (contract v1.0)
  + `knowledge_engineering/metadata_extraction/schema.py` (validate được object mẫu thật).

---

## 4. Những thay đổi so với kế hoạch gốc — và TẠI SAO

Bản hướng dẫn DA10 gốc phác thảo đơn giản hơn. Trong lúc làm (và sau một lượt phản biện gắt
theo tiêu chuẩn search thực tế), đã điều chỉnh các điểm sau cho đúng/scale hơn:

| # | Thay đổi | Lý do |
|---|---|---|
| 1 | **Tách ontology thành nhiều file theo facet** (thay vì 1 file `concepts.yaml`) | 1 file sẽ vỡ khi lên 500–1000 khái niệm. |
| 2 | **Tách `label` (nhãn đại diện) khỏi `surface_forms` (cách gõ)** | Bản đầu trộn lẫn ontology với từ điển đồng nghĩa — sai về kiến trúc. |
| 3 | **Thêm tầng Location ontology** (25 địa danh + landmark) | Bản đầu thiếu hẳn — mà 90% truy vấn du lịch là theo địa danh. |
| 4 | **Thêm `fact_type` hard/soft trên mỗi khái niệm** | Để phân biệt cái nào lọc cứng, cái nào chỉ tăng điểm. |
| 5 | **Mô hình Core/Candidate** | Kiểm soát việc ontology phình loạn theo thời gian. |
| 6 | **Attribute số (sao, giá, khoảng cách) KHÔNG làm concept** | Chúng là bộ lọc dạng khoảng, không phải khái niệm ngữ nghĩa. Để ở metadata_schema. |
| 7 | **Synonym: 1 cách gõ → DANH SÁCH concept** (không phải 1-1) | "lãng mạn" thật sự vừa là nhóm khách vừa là phong cách — giữ cả hai, không bỏ sót. |
| 8 | **Sửa contract `metadata.md`: vocab phẳng → concept_id; bỏ field `near_<landmark>`** | Đồng bộ 1 nguồn từ vựng; field `near_vinwonders` là anti-pattern (mỗi landmark mới phải thêm 1 field → không scale). Thay bằng mô hình `nearby_places[]` (category + khoảng cách). |
| 9 | **3 script "tự sinh" (Lớp A)** | Khi corpus mở rộng (đã 27→51, sắp 500–1000), chạy lại script thay vì sửa tay. |

### Khái niệm "3 Lớp" khi dữ liệu mở rộng (quan trọng cho vận hành lâu dài)
- **Lớp A — tự sinh từ data:** quan hệ "gần", từ điển đồng nghĩa, thống kê domain. → chạy lại script.
- **Lớp B — khái niệm mới:** không tự thêm vào Core; vào hàng đợi Candidate → người duyệt.
- **Lớp C — đổi cấu trúc:** luôn hỏi chủ dự án trước.

---

## 5. Cái gì CHƯA xong trong Sprint 1 (và tại sao — không phải bỏ sót)

| Hạng mục | Trạng thái | Lý do |
|---|---|---|
| **Task 1.1 Bước 2** (nhóm golden query theo facet) | Chờ | Cần **golden set** (30–50 query có nhãn) do DA09 cấp — repo chưa có. |
| **Task 1.7 Query Expansion — kiểm chứng** | 21 luật ở trạng thái `unverified` | DA10 yêu cầu "mỗi luật kiểm trên golden set, không tăng độ phủ thì bỏ". Chưa có golden set nên **không đánh dấu 'đã kiểm'** — giữ trung thực thay vì bịa. |
| **Verify thật của metadata pipeline** | Mới validate object *mẫu* | Tính đúng thật chỉ kiểm được khi pipeline (Sprint 2) chạy trên 51 hotel. |

> **Lộ trình mở khóa:** khi DA09 cấp golden set → hoàn tất Task 1.1 Bước 2 → chạy A/B từng luật
> expansion → đổi `unverified` thành `verified`/bỏ.

---

## 6. Danh sách bàn giao (deliverables)

**Cấu hình ngữ nghĩa** (`ontology/`):
```
_meta.yaml                     quy ước chung + đăng ký 8 facet
core/{object_type,amenity,location,setting,price_tier,purpose,style,aspect}.yaml   73 concept
candidate/candidate_queue.yaml hàng đợi khái niệm ứng viên (trống)
facets.yaml                    8 facet + 4 bộ lọc số
ontology.yaml                  quan hệ (đồ thị tri thức nhẹ)
relations_near.generated.yaml  22 quan hệ "gần" (TỰ SINH)
synonym_dictionary.yaml        543 cách gõ → concept (TỰ SINH)   → bàn giao Anh Tài
query_expansion.yaml           21 luật mở rộng (unverified)       → bàn giao Anh Tài
metadata_schema.yaml           CONTRACT v1.0                      → bàn giao DA09/Đạt
```

**Code** (`knowledge_engineering/`):
```
common/normalize.py                    chuẩn hóa tiếng Việt
common/build_synonym_index.py          sinh synonym_dictionary
entity_extraction/build_relations.py   sinh quan hệ "gần"
entity_extraction/build_domain_stats.py sinh thống kê domain
metadata_extraction/schema.py          kiểm tra schema (pydantic)
```

**Báo cáo/đầu ra** (`docs/reports/ontology/sprint1/`):
```
domain_analysis.md   phân tích miền (số liệu tự sinh giữa marker)
domain_stats.json    thống kê thô (TỰ SINH)
SPRINT1_REPORT.md    file này
```

**Lệnh chạy lại "Lớp A" khi corpus đổi:**
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_relations
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_domain_stats
```

---

## 7. Con số tóm tắt

- **51** khách sạn thật phân tích
- **73** concept Core (8 facet; 53 hard / 20 soft)
- **543** cách gõ trong từ điển đồng nghĩa
- **22** quan hệ "gần" (hotel ↔ landmark)
- **21** luật mở rộng truy vấn (chờ kiểm chứng)
- **1** contract metadata chốt (1 trong 3 contract của team)
- **3** script tự sinh phục vụ mở rộng dữ liệu

> **Một câu tóm tắt Sprint 1:** đã xây xong "bộ não từ vựng" chuẩn hóa — biến mọi cách diễn đạt
> của người dùng và mọi nguồn dữ liệu về cùng một hệ khái niệm, có kiểm soát, mở rộng được,
> sẵn sàng cho Sprint 2 (tự động gắn nhãn + xử lý đánh giá).
