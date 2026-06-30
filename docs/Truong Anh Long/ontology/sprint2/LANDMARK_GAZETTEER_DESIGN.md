# Thiết kế: Sinh LANDMARK (LMK_*) từ GAZETTEER thật (hướng production)

> Owner: Trương Anh Long (KE, DA10). Soạn 2026-06-14.
> **Mục đích tài liệu:** thiết kế hướng PRODUCTION cho việc sinh landmark, thay cách hiện tại
> (suy thuần từ `nearby_places` của Agoda + lọc heuristic + whitelist tay). Đủ chi tiết để code
> ở session sau. Đọc cùng [step4_knowledge_objects.md](step4_knowledge_objects.md) và memory
> `sprint2-ontology-relation-lmk`, `lmk-pipeline-rebuild-chain`.

> **TRẠNG THÁI:** CHƯA CODE. Đây là kế hoạch. Bản hiện hành (heuristic, không gazetteer) vẫn dùng
> cho Sprint 2 / demo. Whitelist tay đã bị GỠ BỎ có chủ đích (xem §1) — không tái lập.

---

## 0. Bối cảnh & quyết định gốc rễ (đọc trước)

**Cách hiện tại (đang chạy) — `entity_extraction/build_locations.py`:**
- Landmark `LMK_*` suy từ field `nearby_places[].name/type/distance_km` của hotel (nguồn Agoda).
- Lọc bằng heuristic: `LMK_TYPE_KEEP` (giữ type du lịch), ngưỡng số-hotel theo type
  (`LMK_HARD_MIN_HOTELS=1` / `LMK_SOFT_MIN_HOTELS=2`), `LMK_NAME_BLACKLIST` (tên generic),
  `LMK_NAME_PATTERN_DROP` (regex rác xuyên type).
- Kết quả corpus 520 hotel: 587 landmark, phủ 467/520 hotel có LMK.

**Vì sao cách hiện tại KHÔNG đủ cho production (gốc rễ):**
1. **Nguồn type không đáng tin.** Agoda gán type tùy tiện: "Văn Miếu Quốc Tử Giám" = "Địa điểm
   giải trí", "Tòa nhà Vietcombank" = "Núi, đồi và hang động". Mọi heuristic dựa trên type đó đều
   kế thừa lỗi gốc.
2. **Không có toạ độ landmark thật.** Ta chỉ biết "hotel X cách nơi tên Y là Z km" — KHÔNG biết Y
   ở đâu. Hệ quả: không cụm được 2 cách gọi cùng một nơi ("Bà Nà Hills" vs "Cáp treo Bà Nà"),
   không tính được khoảng cách nếu Agoda không liệt kê, không kiểm tra landmark có thật không.
3. **Heuristic không scale.** 520 hotel còn vá tay được; 50k hotel toàn VN thì số "type mềm nhưng
   đáng giữ" và "rác lọt lưới" bùng nổ. Ngưỡng/pattern/blacklist phải chỉnh tay liên tục.
4. **Whitelist tay là phản pattern.** Đã thử thêm `LMK_NAME_WHITELIST` (4 cái) rồi GỠ: nó nhét DỮ
   LIỆU vào CODE (sửa nội dung = sửa code = deploy), không có nguồn sự thật ("đã phủ đủ chưa?"),
   chỉ vá triệu chứng của lỗi #1. Quyết định: KHÔNG dùng whitelist; sửa từ gốc bằng gazetteer.

**Cách đúng (chuẩn ngành):** landmark phải đến từ một **gazetteer** (từ điển địa danh có thẩm
quyền, kèm toạ độ + loại chuẩn). `nearby_places` của Agoda chỉ còn dùng để TÍNH KHOẢNG CÁCH
(quan hệ near), KHÔNG còn là nguồn QUYẾT ĐỊNH "cái gì là landmark".

---

## 1. Quyết định đã chốt (với chủ dự án 2026-06-14)

| # | Quyết định | Chốt là |
|---|---|---|
| 1 | Whitelist tay (`LMK_NAME_WHITELIST`) | **BỎ.** Đã gỡ khỏi code. Không cố cứu vài điểm mà phá luồng/scale. |
| 2 | Nguồn landmark cho production | **Gazetteer ngoài** (OSM trước, mở rộng sau), không suy thuần từ Agoda. |
| 3 | Vai trò của `nearby_places` Agoda | Hạ xuống: chỉ dùng để KHỚP + tính `distance_km`, không quyết "là landmark". |
| 4 | Khi nào code | CHƯA. Sprint 2 giữ bản heuristic. Gazetteer làm khi corpus scale / có yêu cầu thật. |

---

## 2. Nguồn gazetteer — đề xuất OpenStreetMap (OSM)

**Vì sao OSM (ưu tiên 1):**
- Miễn phí, phủ VN tốt, có toạ độ (lat/lng) + tag loại chuẩn (`tourism=*`, `historic=*`,
  `natural=*`, `leisure=park`, `amenity=place_of_worship`...).
- Tải offline được (Geofabrik dump Việt Nam) → KHÔNG phụ thuộc rate-limit khi build hàng loạt.
- Cho phép redistribute (ODbL) — hợp pháp để nhúng vào ontology.

**Phương án lấy dữ liệu:**
- **Batch (khuyến nghị):** tải `vietnam-latest.osm.pbf` (Geofabrik), lọc các feature có tag du lịch
  → bảng gazetteer cục bộ `(name, lat, lng, osm_type, category)`. Dựng 1 lần, regenerate định kỳ.
- **Online (bổ trợ):** Nominatim/Overpass cho tra cứu lẻ khi cần — KHÔNG dùng cho build hàng loạt
  (rate-limit). Nếu dùng Nominatim public phải tôn trọng usage policy; production nên self-host.

**Nguồn dự phòng / bổ sung (ưu tiên 2, nếu OSM thiếu):** GeoNames (toạ độ hành chính + POI lớn),
hoặc Google Places API (phủ tốt, có phí + ràng buộc TOS về lưu trữ — cân nhắc pháp lý trước).

---

## 3. Pipeline mới (thay phần landmark trong build_locations.py)

```
┌─ A. BUILD GAZETTEER (1 lần / định kỳ) ────────────────────────────────────────┐
│  osm vietnam.pbf  ──lọc tag du lịch──▶  gazetteer.db/yaml                       │
│     {gid, name, surface_forms[], lat, lng, category(chuẩn), source:osm}        │
└────────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─ B. MATCH nearby_places → gazetteer ────────────────────────────────────────────┐
│  với mỗi nearby_places[].name của hotel:                                        │
│   1. chuẩn hóa tên (NFC, fold dấu) — tái dùng common/normalize.py               │
│   2. khớp gazetteer: exact trước, fuzzy (token-set ratio) sau, NGƯỠNG cao       │
│   3. (nếu có lat/lng hotel) kiểm tra khoảng cách hợp lý để loại match nhầm tên   │
│   → ánh xạ name(Agoda) → gid(gazetteer). Cache lại (name→gid) để chạy nhanh.    │
└────────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─ C. SINH LMK_* TỪ GAZETTEER (không từ Agoda type) ──────────────────────────────┐
│  landmark = các gid được ÍT NHẤT 1 hotel match tới (B).                          │
│   - category lấy từ OSM (chuẩn) — KHÔNG dùng type Agoda nữa.                     │
│   - located_in: từ toạ độ landmark → reverse-geocode về city/area của ontology  │
│     (chính xác hơn "city hotel nhiều nhất" hiện tại — vốn là suy gián tiếp).     │
│   - ID: LMK_<slug> qua registry append-only như cũ (giữ ID ổn định).            │
│   - DEDUP THẬT: "Bà Nà Hills" + "Cáp treo Bà Nà" cùng trỏ 1 gid → 1 concept,    │
│     2 tên thành surface_forms. (Hiện tại KHÔNG làm được vì thiếu toạ độ.)        │
└────────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─ D. QUAN HỆ near (relations_near) ──────────────────────────────────────────────┐
│  giữ distance_km của Agoda nếu có; nếu thiếu → tính từ toạ độ hotel ↔ landmark   │
│  (haversine). Mở rộng phủ so với hiện tại (chỉ có near khi Agoda liệt kê).       │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Điểm mấu chốt:** bộ lọc heuristic (`LMK_TYPE_KEEP`, ngưỡng số-hotel, blacklist, pattern,
whitelist) **biến mất gần hết** — thay bằng "có khớp gazetteer thật không". Rác như "Ao xóm đông",
"My spot", "Tòa nhà Vietcombank" tự loại vì KHÔNG có trong gazetteer du lịch. Landmark thật như
"Văn Miếu", "Mũi Nghinh Phong" tự giữ vì CÓ trong gazetteer — bất kể Agoda gán type gì, bất kể
chỉ 1 hotel gần.

---

## 4. Tầng curated (thay vai trò whitelist/blacklist — KHÔNG hardcode)

Gazetteer không hoàn hảo (thiếu POI mới, tên địa phương, hoặc match sai). Cần một lớp curated
NHƯNG ở DẠNG DATA, không phải code:

- `ontology/curated/landmark_overrides.yaml` (người vận hành sửa, KHÔNG cần deploy):
  - `force_keep`: gid/tên buộc giữ (POI thật gazetteer thiếu).
  - `force_drop`: gid/tên buộc bỏ (gazetteer rác).
  - `merge`: gộp nhiều gid/tên về 1 concept (alias thủ công khi dedup tự động trượt).
- `build_locations` đọc file này như input, KHÔNG chôn danh sách trong `.py`.
- Đây là cùng tinh thần `ontology/candidate/` đã có: máy đề xuất, người duyệt vào data.

→ Whitelist "Mũi Nghinh Phong" nếu vẫn cần sẽ nằm ở `force_keep` trong YAML — sửa nội dung không
đụng code. Nhưng kỳ vọng: phần lớn tự giải quyết bằng gazetteer, curated chỉ còn phần đuôi nhỏ.

---

## 5. Việc cần làm (thứ tự, khi bắt tay code)

1. **PoC match:** tải OSM VN, lọc tag du lịch, thử match `nearby_places` của ~20 hotel → đo tỷ lệ
   khớp + sai. Quyết ngưỡng fuzzy. (Đây là rủi ro lớn nhất — xác minh trước khi đầu tư tiếp.)
2. Dựng gazetteer cục bộ (bước A) + cache `name→gid`.
3. Viết `build_landmarks_from_gazetteer.py` (bước B+C+D), thay phần landmark trong build_locations.
4. Tầng curated `landmark_overrides.yaml` (§4).
5. Reverse-geocode located_in từ toạ độ.
6. Chạy lại CHUỖI 4 bước (xem memory `lmk-pipeline-rebuild-chain`): build_locations →
   build_relations → build_synonym_index → build_objects. So sánh phủ LMK trước/sau.

---

## 6. Rủi ro & lưu ý

- **Match Agoda↔OSM là phần khó nhất** (tên lệch, viết tắt, song ngữ). Fuzzy lỏng → match nhầm;
  chặt → miss. Dùng toạ độ hotel để kiểm tra khoảng cách hợp lý sẽ giảm match nhầm nhiều.
- **OSM phủ không đều:** đô thị tốt, vùng sâu thưa. Phần thiếu rơi vào `force_keep` curated.
- **Pháp lý:** OSM (ODbL) cần ghi nguồn; Google Places có ràng buộc lưu trữ — đọc TOS nếu dùng.
- **Không phá ID ổn định:** vẫn qua `location_id_registry.yaml` (append-only). ID `LMK_*` cũ đã
  phát hành phải map được sang gid mới (dùng tên + toạ độ để nối), tránh vỡ golden/relations cũ.
```
