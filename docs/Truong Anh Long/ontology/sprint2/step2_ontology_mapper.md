# Sprint 2 — Bước 2: Ontology Mapper (tagger lai, Tầng 0+1)

> **Sản phẩm:** [knowledge_engineering/enrichment/ontology_mapper.py](../../../../knowledge_engineering/enrichment/ontology_mapper.py)
> + output [hotel_tags.json](../../../../knowledge_engineering/enrichment/hotel_tags.json) (520 hotel).
> Gắn concept HARD/presence cho mỗi hotel. Ngày: 2026-06-08.

## Kiến trúc cascade (rẻ → đắt)

| Tầng | Nguồn | Conf | Trạng thái |
|---|---|---|---|
| 0 source-tag | field structured qua `source_tag_map.yaml` (amenities/suitable_for/view_types/accommodation_type) | 0.95 | ✅ chạy |
| 1 rule | quét text cô đọng (description_short/highlights/tags) qua `synonym_dictionary` + **xử lý phủ định** | 0.90 | ✅ chạy |
| 2 embedding | cosine text vs anchor concept | f(sim) | ⏸ khung sẵn, **model-tham-số**, chờ team chốt model |
| 3 LLM | ca khó/mâu thuẫn | — | ⏸ chưa bật |
| Fuse | gom 1 tag/concept; ≥2 tầng đồng thuận → +0.05 conf; ghi mọi source | | ✅ |

**Tầng 2 model-tham-số:** `EmbeddingTagger(model_name, threshold)` — model là tham số cắm vào,
ngưỡng ở config. Đổi model = đổi config + regenerate anchor + re-calibrate ngưỡng, KHÔNG sửa
logic mapper. Cho phép dùng model team đang test ngay, swap khi chốt mà không phải viết lại.

## Kết quả trên 520 hotel

- **520/520 hotel có ≥1 tag** (100%). 11,139 tag. Median **22 tag/hotel** (min 2, max 36).
- Tag theo facet: **amenity 7304 · purpose 2442 · object_type 574 · setting 258**.
- 5555 tag có ≥2 sources (source_tag + rule đồng thuận → +conf).
- 48 concept riêng biệt được gắn; 0 concept lạ (đều tồn tại trong core).

## Hai quyết định thiết kế quan trọng

### (1) Mô hình HYBRID presence/experience — trường `nature` trên mỗi tag
PURPOSE_* đánh `fact_type: soft` (Sprint 1), nhưng mapper tag chúng từ `suitable_for` —
structured Agoda **khẳng định**, tin cao như hard. Giải: thêm `nature` ở cấp TAG (không đổi
fact_type concept):
- `nature: presence` — khẳng định từ structured/text. Dùng được như hard filter. (Tầng 0/1 chỉ sinh cái này.)
- `nature: experience` — cảm nhận từ review (Bước 5 ABSA), kèm sentiment.

→ Cùng PURPOSE_FAMILY có thể có cả presence (từ suitable_for) lẫn experience (từ review) sau này,
phân biệt qua `nature` + `sources`. Concept vẫn trung tính, schema không đổi.

### (2) Lọc facet khỏi rule — chống nhiễu text marketing
Rule quét text tự do bắt nhầm nhiều. Đã loại khỏi Tầng 1 (`RULE_ALLOWED_FACETS`):
| Facet | Lý do loại khỏi rule |
|---|---|
| `aspect` | SOFT thuần (ABSA review). Rule bắt "phòng"/"vị trí"/"ăn uống" = rác (hotel nào chả có). |
| `style` | cảm nhận khách → chờ review. Description là lời tự quảng cáo. |
| `location` | đã có từ structured (area/city), không đoán từ text. |
| `setting` | text "gần/cách trung tâm" làm `SETTING_CITY_CENTER` over-tag **520/520** = rác. Setting chỉ lấy từ source_tag (view_types) + location structured. |

> Trước lọc: aspect 2184, location 1174, setting 819 (đầy nhiễu). Sau lọc: setting còn 258
> (NATURE 126/RIVERSIDE 68/MOUNTAIN 64 — đều từ view_types, sạch); aspect/style/location = 0
> (đúng — chờ review / lấy từ structured ở Bước 4).

## Phủ định (negation)
Cửa sổ 3 token trước surface form, manh mối {không, ko, chưa, thiếu, không có...}.
Test: "có hồ bơi"→AMEN_POOL; "không có hồ bơi"/"chưa có hồ bơi"→bỏ. ✅

## Còn lại / chưa làm
- **Setting đầy đủ** (CITY_CENTER/COASTAL/ISLAND): lấy từ `related` của location concept (Sprint 1)
  khi **build knowledge_object (Bước 4)**, không phải việc mapper text.
- **Tầng 2/3**: bật khi chốt model + có Claude key. Chỉ vét phần đuôi (~1%), HARD đã phủ 99%+.
- **SOFT/experience** (style, aspect, purpose-experience): Bước 5 (ABSA + profile).

→ Bước tiếp: Bước 3 (metadata_pipeline: map/validate/reconcile is_luxury) + Bước 4 (build object HARD).
