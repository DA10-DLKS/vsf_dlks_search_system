# Va chạm ID location — curated (Sprint 1) vs generated (toàn cầu)

> **Bối cảnh:** corpus 51 → 555 hotel / 39 nước. Đã viết `build_locations.py` (Lớp A) tự sinh
> `location.generated.yaml` (country>city>area) từ data. Vấn đề: `location.yaml` (gõ tay Sprint 1,
> 19 tỉnh VN) chồng lấn với generated. File này liệt kê **toàn bộ va chạm** để chốt cách gộp.
> **CHƯA xóa/sửa location.yaml** — chờ quyết định.

---

## Tình trạng hiện tại (đã chạy, đã validate)

| File | Vai trò | Concept |
|---|---|---|
| `location.generated.yaml` | TỰ SINH từ data (Lớp A) | 39 country + 202 city + 333 area = **574** |
| `location.yaml` | Gõ tay Sprint 1 (curated) | 19 place + 6 landmark = **25** |

`build_locations.py` đã có sẵn 2 override curated: `VN_PROVINCE` (Khánh Hòa→Nha Trang) và
`CURATED_AREA_SKIP` (Hòn Tre/Gành Dầu/Cửa Đại — skip để curated giữ ID ngắn).

---

## 3 nhóm va chạm

### [A] Trùng ID y hệt — 12 concept
generated sinh ID **giống hệt** curated (vì tên thành phố trùng). An toàn xóa khỏi curated, generated lo:
```
LOC_NHA_TRANG  LOC_HOI_AN  LOC_HO_CHI_MINH  LOC_HA_TINH  LOC_HA_LONG  LOC_DA_NANG
LOC_HUE  LOC_THANH_HOA  LOC_TAY_NINH  LOC_BAC_NINH  LOC_HAI_PHONG  LOC_KHANH_HOA
```
> `LOC_KHANH_HOA` nay do generated sinh qua `VN_PROVINCE` override (kind=place, parent VN).
> 11 cái còn lại generated sinh trực tiếp từ field city. **Không cái nào có `related`/alias curated riêng** (trừ Nha Trang có parent Khánh Hòa — đã chuyển vào override).

### [B] Trùng NGỮ NGHĨA, ID KHÁC — 7 concept ⚠ (đây là nút thắt)
generated slug theo tên thật trong data (Agoda kèm "Đảo/Biển/Đồng Hới") → **2 ID cho cùng 1 nơi**:

| Curated (Sprint 1) | Generated (từ data) | Nơi |
|---|---|---|
| `LOC_PHU_QUOC` | `LOC_DAO_PHU_QUOC` | Phú Quốc |
| `LOC_CUA_LO` | `LOC_BIEN_CUA_LO` | Cửa Lò |
| `LOC_QUANG_BINH` | `LOC_DONG_HOI_QUANG_BINH` | Đồng Hới |
| `LOC_HA_NAM` | `LOC_PHU_LY_HA_NAM` | Phủ Lý |
| `LOC_HON_TRE` | `LOC_NHA_TRANG__HON_TRE` | Hòn Tre (area) |
| `LOC_GANH_DAU` | `LOC_DAO_PHU_QUOC__GANH_DAU` | Gành Dầu (area) |
| `LOC_CUA_DAI` | `LOC_HOI_AN__CUA_DAI` | Cửa Đại (area) |

> **Hệ quả nếu để cả hai:** hotel gắn ID generated, nhưng `related: SETTING_ISLAND` và landmark
> `located_in` lại trỏ ID curated → filter "Phú Quốc" lệch tập. Đây là lý do KHÔNG thể giữ song song.

### [C] Chỉ có ở curated — 6 landmark (generated KHÔNG sinh landmark)
```
LMK_VINWONDERS_NHA_TRANG  LMK_VINWONDERS_PHU_QUOC  LMK_GRAND_WORLD_PHU_QUOC
LMK_BAI_DAI  LMK_VIEN_HAI_DUONG_HOC  LMK_DINH_BAO_DAI
```
> **Phải giữ.** Đây là phần curated không tự sinh được (dùng cho quan hệ `near` Task 1.5).
> Mỗi landmark có `located_in` trỏ tới một place — cần đảm bảo place đó tồn tại (ở generated).

---

## Ai tham chiếu ID nhóm B (chi phí nếu đổi ID)

| File | ID nhóm B dùng |
|---|---|
| `ontology.yaml` (quan hệ near) | LOC_PHU_QUOC, LOC_HON_TRE, LOC_GANH_DAU, LOC_CUA_DAI, LOC_KHANH_HOA |
| `facets.yaml` (values_places/landmarks) | cả 8 |
| `query_expansion.yaml` | LOC_PHU_QUOC, LOC_HON_TRE |
| `golden_query_concepts.md` | LOC_PHU_QUOC (Q5-04, Q6-03, Q7-02) |
| `synonym_dictionary.yaml` | tự sinh — rebuild là xong |

→ Nếu bỏ ID curated nhóm B, phải sửa tham chiếu ở 4 file (synonym tự rebuild).

---

## Hai phương án

### Phương án 1 — Generated làm chủ TOÀN BỘ place, location.yaml chỉ còn landmark ✅ (khuyến nghị)
- Chuyển `related` (Phú Quốc→ISLAND, Cửa Lò→COASTAL...), parent tỉnh, sub-area vào **bảng override
  trong `build_locations.py`** (giống `VN_PROVINCE` đã làm). Generated sinh place + tự gắn quan hệ.
- `location.yaml` chỉ còn 6 landmark `LMK_*`.
- **Đổi ID nhóm B** sang ID generated ở 4 file tham chiếu (`ontology.yaml`, `facets.yaml`,
  `query_expansion.yaml`, `golden_query_concepts.md`). HOẶC giữ ID đẹp bằng cách thêm override
  "đổi tên slug" trong script (vd ép `LOC_DAO_PHU_QUOC` → `LOC_PHU_QUOC`).
- **Ưu:** 1 ID/nơi, 1 nguồn sự thật, scale sạch. **Nhược:** sửa tham chiếu 4 file (1 lần).

### Phương án 2 — Curated làm chủ place VN, generated skip nơi đã curated
- Mở rộng `CURATED_AREA_SKIP` thành map đầy đủ: mọi city/area VN đã curated → script SKIP, giữ ID ngắn.
- Phải map tay (city tên data → ID curated) cho từng nơi nhóm A+B.
- Generated chỉ lo nước ngoài + VN chưa curated.
- **Ưu:** giữ nguyên ID Sprint 1, không sửa tham chiếu. **Nhược:** map tay nhiều, dễ sót; 2 quy ước
  đặt tên song song (VN ngắn / nước ngoài theo-data) — không nhất quán.

---

## Khuyến nghị

**Phương án 1 + giữ ID đẹp bằng override slug.** Tức: generated là nguồn duy nhất, nhưng thêm bảng
`SLUG_OVERRIDE` trong script ép vài nơi về ID quen thuộc (`LOC_DAO_PHU_QUOC`→`LOC_PHU_QUOC`,
`LOC_BIEN_CUA_LO`→`LOC_CUA_LO`...). Vừa 1 ID/nơi, vừa không phải sửa tham chiếu, vừa nhất quán
(mọi nơi qua 1 cơ chế). location.yaml rút còn landmark thuần.
