# Kịch bản họp mentor — Knowledge Engineering (DA10) — Sprint 1 + Sprint 2 (đang làm)

> Người trình bày: Trương Anh Long. Thời lượng: ~8–10 phút.
> Cách dùng: kịch bản NÓI, không đọc nguyên văn. Mỗi mục có ý chính + ví dụ cụ thể + 1 câu chốt.
> **In đậm** = từ khóa cần nhấn. `(nếu mentor hỏi)` = dự phòng.
> Cập nhật 2026-06-08: bao trùm Sprint 1 (Foundation) đã xong + Sprint 2 (Enrichment) đang chạy.

---

## 0. Mở đầu — đặt khung (30 giây)

"Em phụ trách **Knowledge Engineering** trong DA10 — xây **bộ não từ vựng** để hệ thống *hiểu nghĩa*
câu hỏi người dùng, chứ không chỉ so khớp từ khóa. Em đã xong **Sprint 1 — Semantic Foundation**
(dựng vốn từ vựng) và đang ở giữa **Sprint 2 — Semantic Enrichment** (gắn vốn từ đó lên 520 khách
sạn thật). Em trình bày 4 phần: *vấn đề*, *thiết kế cốt lõi*, *kết quả Sprint 1 & 2*, *cái gì chưa xong*."

---

## 1. Vấn đề giải quyết (1 phút) — mở bằng ví dụ

"Người dùng gõ: ***'resort yên tĩnh gần biển cho gia đình ở Nha Trang dưới 3 triệu'***.
Máy phải tách ra: *resort*=loại hình, *yên tĩnh*=cảm nhận, *gần biển*=bối cảnh, *gia đình*=nhóm khách,
*Nha Trang*=địa danh lọc cứng, *dưới 3 triệu*=lọc giá.

Hai cái khó: **(1) mỗi người gõ một kiểu** — 'hồ bơi' / 'bể bơi' / 'pool', có dấu hay không;
**(2) mỗi nguồn (Agoda/Booking) lại dùng từ khác** — Agoda ghi 'Bể bơi' nhưng người miền Nam gõ
'hồ bơi'. Em xây lớp quy mọi cách diễn đạt đó về **cùng một khái niệm chuẩn**."

> **Câu chốt:** "Đây là **trần chất lượng** của cả hệ thống — tầng này sai thì mọi tầng search phía
> sau đều sai. Nên em làm kỹ phần nền trước."

---

## 2. Ba ý tưởng thiết kế cốt lõi (1.5 phút)

1. **Khái niệm trung tính về cảm xúc.** "Mỗi nghĩa gắn 1 mã, tách khỏi ngôn ngữ. Ví dụ `STYLE_QUIET`
   gom 'yên tĩnh', 'yên bình', 'quiet', 'yen tinh' không dấu. Em **cố ý không tạo** `STYLE_NOT_QUIET` —
   tốt/xấu để ở trường *sentiment* riêng. Nhét cảm xúc vào mã thì số khái niệm nổ gấp đôi."

2. **Hard fact vs Soft fact.** "*Có hồ bơi* là **sự thật cứng** → lọc cứng. *Yên tĩnh* là **cảm nhận
   từ review** → chỉ tăng/giảm điểm xếp hạng, không lọc cứng vì có thể sai."

3. **Core vs Candidate.** "Khái niệm chuẩn ngành dùng ngay (Core). Từ lạ trong review/data **không tự
   thêm** — đẩy vào hàng đợi Candidate, **chờ người duyệt + kiểm golden set**. Để ontology không phình
   loạn. Ví dụ thật tuần này: em phát hiện 'karaoke', 'sân tennis' trong data → đưa vào hàng đợi →
   **em duyệt tay** → mới cho lên Core. Còn 'đổi ngoại tệ' tuy 514 khách sạn có, em **từ chối** vì
   khách sạn nào cũng có, không giúp lọc gì."

> **Câu chốt:** "Ba nguyên tắc này đến từ một lượt em **tự phản biện theo chuẩn search thực tế**,
> không chỉ làm theo bản kế hoạch gốc."

---

## 3A. Kết quả SPRINT 1 — bộ não từ vựng (1.5 phút)

"Em phân tích **520 khách sạn Việt Nam thật** từ Agoda, sản xuất:
- **419 khái niệm Core** = ~68 khái niệm ngữ nghĩa viết tay (7 nhóm: loại hình, tiện ích, bối cảnh,
  giá, nhóm khách, phong cách, khía cạnh) + **351 địa danh TỰ SINH** (1 quốc gia / tỉnh / thành phố /
  khu / **142 landmark**). Hard/soft: **399 hard / 20 soft**.
- **~1.500 cách gõ** trong từ điển đồng nghĩa — bàn giao tầng search.
- **1.093 quan hệ 'gần'** giữa khách sạn ↔ landmark, trả lời 'gần VinWonders không' bằng **đồ thị**.
- **1 hợp đồng dữ liệu** (metadata schema) — 1 trong 3 contract chốt của team, có **pydantic** kiểm tự động.
- **4 script tự sinh**: corpus đã đi 27 → 51 → 555 → **520** mà chỉ cần **chạy lại script**, không gõ tay."

> **Câu chốt:** "Điểm em tâm đắc là **scale**: không hard-code, dữ liệu tăng 10–20 lần vẫn chạy lại được."

`(nếu mentor hỏi 'scale thế nào')`: "3 lớp — **Lớp A** tự sinh từ data (chạy script); **Lớp B** khái
niệm mới (hàng đợi + người duyệt); **Lớp C** đổi cấu trúc (hỏi chủ dự án)."

---

## 3B. Kết quả SPRINT 2 — gắn vốn từ lên khách sạn (2 phút) ⭐ phần mới

"Sprint 1 dựng *vốn từ*. Sprint 2 em **dùng vốn từ đó gắn nhãn cho cả 520 khách sạn thật**. Đã làm:

**Bước 0 — khảo sát data:** quét 520 file, đo vocabulary nguồn. Phát hiện quan trọng: **review KHÔNG
thiếu như em tưởng** — 520/520 có điểm review, **518 khách sạn có review chi tiết, tổng 112.000 review
thật, trung vị 250 review/khách sạn**. Đủ để phân tích cảm xúc.

**Bước 1 — bản đồ tag nguồn (Tầng 0):** map vocabulary Agoda → khái niệm. Ví dụ 'Bể bơi'→`AMEN_POOL`,
'Gia đình có trẻ nhỏ'→`PURPOSE_FAMILY`. **Phủ 99% khách sạn** chỉ bằng lớp này, gần như miễn phí.

**Bước 2 — bộ gắn nhãn lai (ontology_mapper):** chạy nhiều tầng từ rẻ đến đắt:
- *Tầng 0* dùng bản đồ trên (tin 95%).
- *Tầng 1* quét text mô tả qua từ điển đồng nghĩa, **biết xử lý phủ định** — 'có hồ bơi' thì gắn,
  'KHÔNG có hồ bơi' thì bỏ.
- *Tầng 2 (embedding)* em để **khung model-tham-số** — vì bạn phụ trách embedding chưa chốt model,
  em thiết kế để cắm model nào cũng được, đổi model không phải viết lại.
→ Kết quả: **520/520 khách sạn được gắn nhãn, ~10.600 nhãn, trung vị 22 nhãn/khách sạn**.

Một ví dụ em tâm đắc về **chất lượng**: lúc đầu bộ gắn nhãn bắt nhầm — mọi khách sạn đều bị gán
'trung tâm thành phố' vì mô tả nào cũng có chữ 'gần trung tâm'. Em phát hiện **520/520 = rõ ràng sai**,
nên **chặn không cho luật text đoán bừa các nhãn cảm tính**; nhãn vị trí chỉ lấy từ dữ liệu cấu trúc."

> **Câu chốt:** "Giờ câu hỏi *'khách sạn có hồ bơi ở Đà Nẵng'* đã **trả lời được** — trước Sprint 2
> thì chưa, vì khách sạn chưa được gắn nhãn khái niệm nào."

`(nếu mentor hỏi 'hard/soft xử lý sao trong mapper')`: "Em thêm mô hình **hybrid**: cùng một nhãn
'gia đình' — nếu đến từ trường có-sẵn của Agoda thì là *presence* (chắc chắn, lọc được); nếu sau này
đến từ review thì là *experience* (cảm nhận, kèm sentiment). Phân biệt bằng một trường `nature`."

---

## 4. Ví dụ xuyên suốt — 'resort sang gần biển' chạy tới đâu (1 phút)

"Để thầy/cô thấy hệ thống *hiểu liên kết ngữ nghĩa* thật, em lấy từ 'sang':
- **Đồng nghĩa:** 'sang', 'xịn', 'luxury', 'sang trọng', 'đẳng cấp' → đều quy về nhóm `PRICE_LUXURY` /
  `STYLE_LUXURY`. Tuần này em vừa **audit có hệ thống** bổ sung ~45 cách gõ còn thiếu (như 'sang' trần,
  'tuần trăng mật', 'ăn sáng').
- **Liên kết khái niệm:** 'luxury' còn **kéo thêm** 'spa', 'hồ bơi riêng', 'view biển' (luật mở rộng).
- **Cố ý KHÔNG nhồi bừa:** '5 sao' em **không** map thành 'luxury' — vì số sao là **bộ lọc khoảng**,
  và có resort 5 sao giá tầm trung. Map vào sẽ sai về chất."

> **Câu chốt:** "Em phân biệt rõ *cái gì là khái niệm ngữ nghĩa* với *cái gì là bộ lọc số* — đây là
> lỗi thiết kế thường gặp mà em tránh."

---

## 5. Điều chỉnh so với kế hoạch gốc (45 giây)

"Em **điều chỉnh vài điểm** vì bản gốc đơn giản hơn thực tế:
- **Tách ontology nhiều file** thay vì một file — một file vỡ khi lên cả nghìn khái niệm.
- **Bỏ field kiểu `near_vinwonders`** — không scale; thay bằng `nearby_places` (loại địa điểm + khoảng cách).
- **Số sao/giá/khoảng cách KHÔNG là khái niệm** — là bộ lọc khoảng, để riêng ở schema.
- **Đảo thứ tự Sprint 2:** làm bản-đồ-tag-nguồn TRƯỚC bộ gắn nhãn (data Agoda giàu sẵn, phủ 99% rẻ trước)."

> **Câu chốt:** "Em ghi đầy đủ điều chỉnh kèm lý do trong báo cáo, để team sau truy được *tại sao*."

---

## 6. Cái gì CHƯA xong — và tại sao (1 phút) ⚠ phần quan trọng nhất

"Em **cố ý chưa đánh dấu hoàn thành** mấy chỗ:
1. **Query expansion (21 luật)** để trạng thái ***unverified*** — DA10 yêu cầu mỗi luật phải kiểm trên
   golden set, mà bước A/B đo Recall cần **tầng retrieval** (bạn khác làm) mới chạy được. Golden set
   em **đã tự chuẩn bị** (32 câu có nhãn). Trung thực thay vì khai khống.
2. **Phân tích cảm xúc review (ABSA) + hồ sơ ngữ nghĩa khách sạn** — đây là phần SOFT của Sprint 2,
   em đang làm. Có 112k review rồi nên **không bị chặn**, chỉ là chưa tới bước đó.
3. **Tầng 2 embedding của bộ gắn nhãn** — chờ bạn embedding chốt model. Nhưng phần cứng đã phủ 99%
   nên không chặn tiến độ."

> **Câu chốt:** "Phần chưa xong đều có **lý do phụ thuộc rõ ràng** (chờ tầng search / chờ chốt model),
> không phải bỏ sót."

---

## 7. Kế hoạch còn lại của Sprint 2 (30 giây)

"Còn 4 bước: **Bước 3** đối chiếu mâu thuẫn dữ liệu (ví dụ Agoda ghi `is_luxury=false` cho resort 5 sao
Gold Circle → em tự suy lại phân khúc giá, không tin cờ nguồn mù); **Bước 4** đóng gói thành knowledge
object hoàn chỉnh cho 520 khách sạn; **Bước 5** phân tích cảm xúc review → hồ sơ ngữ nghĩa; **Bước 6**
hợp nhất + bàn giao."

> **Câu chốt kết:** "Tóm lại: Sprint 1 em xây xong **bộ não từ vựng**; Sprint 2 đang **gắn nó lên dữ
> liệu thật** — đã gắn xong phần cứng cho cả 520 khách sạn. Em sẵn sàng nghe góp ý ạ."

---

## Phụ lục — câu hỏi mentor có thể hỏi & cách trả lời ngắn

| Mentor hỏi | Trả lời 1 câu |
|---|---|
| "Số liệu có thật không?" | "Tất cả từ **520 file JSON Agoda thật** + **112k review** trong repo; script tự sinh nên **tái lập được**." |
| "Sao chỉ Việt Nam?" | "Team chốt VN (từng có 555 gồm quốc tế, lọc về 520 VN). Thiết kế giữ tầng country + auto-slug để mở rộng nước ngoài sau mà không đập lại." |
| "Hệ thống hiểu đồng nghĩa thật chưa?" | "Có ở tầng từ vựng — 'sang/xịn/luxury'→cùng nhóm luxury, tra được thật. Liên kết khái niệm (luxury→spa/pool) đã viết, chờ tầng search verify." |
| "Khó nhất là gì?" | "Bộ gắn nhãn bắt nhầm nhãn cảm tính từ marketing (mọi khách sạn thành 'trung tâm thành phố'). Em phát hiện nhờ con số 520/520 vô lý, rồi chặn luật text đoán bừa." |
| "Làm sao biết ontology đúng?" | "Phần cứng: pydantic + kiểm không trùng mã / không tham chiếu chết (0 lỗi). Phần mềm (expansion): **chưa dám nói đúng** — chờ golden set." |
| "Candidate duyệt tay không scale?" | "Phần *phát hiện + lọc + xếp hạng* sẽ tự động (Sprint 4). Phần *người ký duyệt* cố ý giữ làm van chặn rác — và nhẹ vì ontology là tập hữu hạn, cạn dần. Giờ em duyệt tay vì mới 520 khách sạn." |
| "Phụ thuộc ai?" | "Cần **tầng retrieval** verify expansion; **chốt model embedding** cho Tầng 2; nhận **clean data** từ Data Quality; bàn giao synonym→search, schema→DA09." |

---

### Mẹo trình bày
- **Mở bằng ví dụ câu query**, đừng mở bằng định nghĩa.
- Phần **chưa xong nói thẳng** — mentor đánh giá cao trung thực.
- Nếu quá giờ: bỏ mục 5 (điều chỉnh) + 4 (ví dụ 'sang'), giữ 1-2-3A-3B-6-7.
- Nếu thừa giờ: thêm ví dụ bug 'trung tâm thành phố' (mục 3B) — mentor thích chỗ tự phát hiện lỗi.
