# Kịch bản họp mentor — Sprint 1 (Knowledge Engineering, DA10)

> Người trình bày: Trương Anh Long. Thời lượng: ~5–7 phút.
> Cách dùng: đây là kịch bản NÓI, không phải đọc nguyên văn. Mỗi mục có [thời lượng] +
> ý chính + 1 câu chốt. Phần **in đậm** là từ khóa cần nhấn. Phần `(nếu mentor hỏi)` để dự phòng.

---

## 0. Mở đầu — đặt khung (30 giây)

"Em xin báo cáo phần việc tuần vừa rồi. Em phụ trách **Knowledge Engineering** trong DA10 —
nói nôm na là xây **bộ não từ vựng** để hệ thống *hiểu nghĩa* câu hỏi người dùng, chứ không chỉ
so khớp từ khóa. Tuần này em hoàn thành **Sprint 1 — Semantic Foundation**, gồm 8 task.
Em xin trình bày 3 phần: *làm gì*, *kết quả ra sao*, và *cái gì chưa xong cùng kế hoạch tiếp theo*."

---

## 1. Vấn đề Sprint 1 giải quyết (1 phút)

Lấy 1 ví dụ cho mentor hình dung ngay:

"Ví dụ người dùng gõ: ***'resort yên tĩnh gần biển cho gia đình ở Nha Trang'***.
Máy phải tách ra: *resort* là loại hình, *yên tĩnh* là cảm nhận, *gần biển* là vị trí,
*gia đình* là nhóm khách, *Nha Trang* là địa danh lọc cứng.

Vấn đề là **mỗi người gõ một kiểu** — 'hồ bơi', 'bể bơi', hay 'pool'; có dấu hay không dấu —
và **mỗi nguồn dữ liệu Agoda/Booking lại dùng từ khác nhau**. Sprint 1 của em xây lớp quy mọi
cách diễn đạt đó về **cùng một khái niệm chuẩn**."

> **Câu chốt:** "Đây là **trần chất lượng** của cả hệ thống — tầng này sai thì mọi tầng tìm kiếm phía sau đều sai, nên em làm kỹ phần nền này trước."

---

## 2. Ba ý tưởng thiết kế cốt lõi (1.5 phút)

Nói 3 cái này để mentor thấy có *tư duy thiết kế*, không phải làm cho có:

1. **Khái niệm trung tính.** "Mỗi nghĩa gắn 1 mã, tách khỏi ngôn ngữ. Ví dụ `STYLE_QUIET` gom cả
   'yên tĩnh', 'quiet', 'yen tinh' không dấu. Em **cố ý không tạo** mã kiểu `STYLE_NOT_QUIET` —
   tốt/xấu để ở một trường *sentiment* riêng. Nếu nhét cảm xúc vào mã thì số khái niệm nổ gấp đôi."

2. **Hard fact vs Soft fact.** "*Có hồ bơi*, *5 sao* là **sự thật cứng** → dùng **lọc cứng**.
   Còn *yên tĩnh*, *lãng mạn* là **cảm nhận từ review** → chỉ dùng **tăng/giảm điểm xếp hạng**,
   không lọc cứng, vì nó là suy luận có thể sai."

3. **Core vs Candidate.** "Khái niệm chuẩn ngành thì dùng ngay (Core). Còn từ lạ phát hiện trong
   review thì **không tự thêm** — đẩy vào hàng đợi Candidate, **chờ người duyệt**. Để ontology
   không phình loạn theo thời gian."

> **Câu chốt:** "Ba nguyên tắc này đến từ một lượt em **tự phản biện theo chuẩn search thực tế**, không chỉ làm theo bản kế hoạch gốc."

---

## 3. Kết quả — con số cụ thể (1.5 phút)

Đọc chậm, nhấn từng số:

"Em đã phân tích **520 khách sạn Việt Nam thật** crawl từ Agoda, và sản xuất ra:
- **414 khái niệm Core** = **63 khái niệm ngữ nghĩa viết tay** (7 nhóm: loại hình, tiện ích, bối cảnh,
  giá, nhóm khách, phong cách, khía cạnh) + **351 khái niệm địa danh TỰ SINH** từ data (quốc gia / tỉnh /
  thành phố / khu / 142 landmark). Hard/soft: **394 hard / 20 soft**.
- **1.365 cách gõ** trong từ điển đồng nghĩa — bàn giao cho bạn làm tầng tìm kiếm.
- **1.093 quan hệ 'gần'** giữa khách sạn và landmark, để trả lời 'gần VinWonders không' bằng **đồ thị**.
- **1 hợp đồng dữ liệu** (metadata schema) — **1 trong 3 contract chốt** của cả team, có code kiểm tra
  tự động bằng pydantic (load 414 concept, validate object mẫu).
- Và **4 script tự sinh**: khi corpus đổi — đã đi 27 → 51 → 555 → **520** — thì **chạy lại script thay
  vì sửa tay**. Đặc biệt địa danh + landmark đều tự sinh nên scale 1.000+ khách sạn không phải gõ tay."

> **Câu chốt:** "Điểm em tâm đắc nhất là phần **scale**: em không hard-code, mà thiết kế để khi dữ liệu tăng 10–20 lần thì vẫn chạy lại được, không phải làm lại từ đầu."

`(nếu mentor hỏi 'scale cụ thể thế nào')`: "Em chia 3 lớp — **Lớp A** tự sinh từ data (chạy lại script);
**Lớp B** khái niệm mới (vào hàng đợi, người duyệt); **Lớp C** đổi cấu trúc (hỏi chủ dự án). Mỗi
loại thay đổi có một quy trình riêng."

---

## 4. Điều chỉnh so với kế hoạch gốc (1 phút)

Cho mentor thấy có *chính kiến*, không làm máy móc. Chọn 2–3 cái mạnh nhất:

"Trong lúc làm em có **điều chỉnh vài điểm so với bản hướng dẫn gốc**, vì bản gốc đơn giản hơn
thực tế search:
- Em **tách ontology thành nhiều file** thay vì một file — vì một file sẽ vỡ khi lên cả nghìn khái niệm.
- Em **bỏ cách làm field kiểu `near_vinwonders`** — vì mỗi địa danh mới lại phải thêm một field,
  không scale. Em thay bằng mô hình `nearby_places` gồm *loại địa điểm + khoảng cách*.
- Em **không coi số sao / giá / khoảng cách là khái niệm** — chúng là bộ lọc dạng khoảng, nên để
  riêng ở schema."

> **Câu chốt:** "Em ghi lại đầy đủ 9 điều chỉnh kèm lý do trong báo cáo, để team sau truy được *tại sao làm vậy*."

---

## 5. Cái gì CHƯA xong — và tại sao (1 phút) ⚠ phần quan trọng nhất với mentor

Phải nói thẳng, đây là chỗ thể hiện sự trung thực:

"Có 3 hạng mục em **cố ý chưa đánh dấu hoàn thành**:
1. **Query expansion** — em viết được **21 luật** mở rộng truy vấn, nhưng để nguyên trạng thái
   ***unverified***. Vì DA10 yêu cầu mỗi luật phải **kiểm trên bộ test golden** — luật nào không
   tăng độ phủ thì bỏ. Golden set em **đã tự chuẩn bị** (có cột `expansion_should_help`), nhưng bước
   A/B đo Recall cần **tầng retrieval Sprint 2** mới chạy được nên em **chưa đánh dấu 'đã kiểm'** —
   trung thực thay vì khai khống.
2. **Nhóm golden query theo facet** — em đã TỰ TẠO golden set KE (`golden_query_concepts.md`, 32 câu
   có nhãn facet/concept), nên bước này đã có input; chạm đủ 8/8 facet.
3. **Verify pipeline metadata trên dữ liệu thật** — mới validate được object *mẫu*, đúng-thật chỉ
   kiểm được khi Sprint 2 (ontology_mapper) chạy gắn nhãn cả 520 khách sạn."

> **Câu chốt:** "Phần verify expansion chờ **pipeline retrieval Sprint 2** để chạy A/B đo Recall —
> không phải bỏ sót, mà cần tầng search chạy mới đo được. Golden set thì em đã tự chuẩn bị."

`(nếu mentor hỏi 'còn review thì sao')`: "Review **chưa crawl xong**, nhưng nó **không chặn Sprint 1** —
vì ontology nền lấy từ **dữ liệu cấu trúc**, không cần review. Review chỉ cần cho **Sprint 2** (phân tích
cảm xúc + hồ sơ ngữ nghĩa khách sạn). Em đang crawl dần, hiện đã có vài trăm khách sạn có review."

---

## 6. Kế hoạch Sprint 2 (30–45 giây)

"Bước tiếp theo em đã chuẩn bị sẵn: viết **ontology_mapper** — tự động gắn 414 khái niệm này lên
cả 520 khách sạn, sinh ra **knowledge object hoàn chỉnh** cho tầng chunking/embedding dùng.
Em đã làm **một object mẫu gán tay** để chốt hình dạng trước khi code. Phần này **làm được ngay**,
không cần chờ gì. Còn phần phân tích review (ABSA) thì làm song song khi crawl xong."

> **Câu chốt kết:** "Tóm lại Sprint 1 em đã xây xong **bộ não từ vựng** — chuẩn hóa, có kiểm soát,
> mở rộng được, và đã bàn giao 3 contract cho các bạn trong team. Em sẵn sàng nghe góp ý của thầy/cô ạ."

---

## Phụ lục — câu hỏi mentor có thể hỏi & cách trả lời ngắn

| Mentor hỏi | Trả lời 1 câu |
|---|---|
| "Số liệu này lấy từ đâu, có thật không?" | "Tất cả từ **520 file JSON Agoda thật** (khách sạn VN) trong repo; 4 script tự sinh nên **tái lập được**, không gõ tay." |
| "Sao chỉ Việt Nam?" | "Team chốt phạm vi VN (đã từng có 555 gồm quốc tế, sau lọc về 520 VN). Thiết kế vẫn giữ tầng country + cơ chế auto-slug để mở ra nước ngoài sau mà không đập lại." |
| "Có gì khó nhất tuần này?" | "Một bug chuẩn hóa tiếng Việt: bản không dấu và bản tách-từ không khớp nhau → query trượt. Em phát hiện và sửa ở hàm normalize." |
| "Làm sao biết ontology đúng?" | "Phần *cứng* validate bằng pydantic + kiểm không trùng mã/không tham chiếu chết. Phần *mềm* (expansion) **chưa dám nói đúng** — chờ golden set kiểm." |
| "Phụ thuộc ai?" | "Cần **pipeline retrieval (Sprint 2)** để verify expansion (golden set em tự có rồi); nhận **clean data** từ Data Quality; bàn giao synonym cho tầng search và metadata schema cho DA09." |

---

### Mẹo trình bày
- **Mở bằng ví dụ câu query**, đừng mở bằng định nghĩa — mentor nắm ngay.
- Phần **chưa xong nói thẳng** — mentor đánh giá cao sự trung thực hơn là báo cáo đẹp.
- Nếu quá giờ: bỏ mục 4 (điều chỉnh), giữ mục 1-2-3-5-6.
- Nếu thừa giờ: thêm chi tiết "3 Lớp scale" ở mục 3.