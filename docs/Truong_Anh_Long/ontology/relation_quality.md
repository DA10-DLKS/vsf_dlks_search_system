# Relation Quality Report (Bước 10 roadmap)

> Sinh bởi `knowledge_engineering/governance/relation_quality.py`. Read-only.
> Ngày: 2026-06-15. Tổng relation (sau dedup): 90.

## 1. Theo status

| status | số |
|---|---|
| candidate | 16 |
| pending | 39 |
| rejected | 7 |
| verified | 28 |

## 2. Theo source_type

| source_type | số |
|---|---|
| curated | 28 |
| generated_lift | 45 |
| legacy_related | 17 |

## 3. Theo use_as

| use_as | số |
|---|---|
| boost | 67 |
| filter | 1 |
| suggestion | 22 |

## 4. Relation dùng FILTER (verified, cần deterministic)

| source | target | type | confidence | note |
|---|---|---|---|---|
| `LOC_PHU_QUOC` | `SETTING_ISLAND` | implies | 1.0 | Phú Quốc là đảo |

> ⚠ Filter là lọc cứng — chỉ giữ khi quan hệ gần như tất định (vd location -> setting địa lý). Nếu evaluator báo noise cho cạnh filter, kiểm tra xem noise có phải artifact của golden set không trước khi hạ.

## 5. Top candidate theo lift (duyệt trước)

Không có candidate chờ duyệt.

## 6. Relation đã reject

| source | target | reject_reason |
|---|---|---|
| `PRICE_LUXURY` | `STYLE_LUXURY` | price tier không đồng nghĩa với cảm nhận luxury từ review; muốn khẳng định luxury phải dựa semantic_profile |
| `STYLE_LUXURY` | `PRICE_LUXURY` | style luxury (cảm nhận) không kéo theo price tier; tách hai chiều ý nghĩa khác nhau |
| `OBJ_APARTMENT` | `AMEN_BEACHFRONT` | corpus bias: apartment ven biển do mẫu, không phải đặc trưng apartment |
| `SETTING_NATURE` | `AMEN_SEA_VIEW` | corpus bias: như trên |
| `OBJ_APARTMENT` | `AMEN_SEA_VIEW` | corpus bias: như trên |
| `SETTING_NATURE` | `AMEN_BEACHFRONT` | corpus bias: nature corpus nghiêng resort biển, không phải bản chất nature |
| `SETTING_NATURE` | `AMEN_KIDS_POOL` | nature không liên quan hồ bơi trẻ em, trùng corpus |

## 7. Source/target không tồn tại trong ontology

Không có (mọi source/target hợp lệ).

## 8. Concept phổ biến làm source nhiều cạnh verified

Không có concept nào làm source > 6 cạnh verified (graph chưa phình).
