# Relation Audit (Bước 1 roadmap)

> Sinh tự động bởi `knowledge_engineering/governance/audit_relations.py`. Read-only.
> Ngày: 2026-06-14.

## 0. Baseline (chụp để MVP 2 so sánh)

| Chỉ số | Giá trị |
|---|---|
| Tổng concept ontology (gồm location) | 874 |
| Cạnh legacy `related/broader/narrower` | 39 |
| Concept khóa trong `query_expansion.yaml` | 32 |
| Tổng cạnh expansion (`expands_to`) | 57 |
| └ từ `ontology_relation` | 39 |
| └ từ `cooccurrence` | 18 |
| Relation `near` (relations_near.generated) | 1834 |
| Location có SETTING suy ra (location_setting.generated) | 11 |

## 1. Legacy edges theo cặp facet

| Cặp facet (source -> target) | số cạnh |
|---|---|
| `amenity -> amenity` | 6 |
| `purpose -> amenity` | 6 |
| `amenity -> purpose` | 5 |
| `amenity -> setting` | 3 |
| `amenity -> object_type` | 2 |
| `price_tier -> price_tier` | 2 |
| `purpose -> style` | 2 |
| `style -> style` | 2 |
| `style -> setting` | 2 |
| `style -> purpose` | 2 |
| `style -> amenity` | 2 |
| `object_type -> amenity` | 1 |
| `setting -> amenity` | 1 |
| `setting -> style` | 1 |
| `setting -> setting` | 1 |
| `style -> price_tier` | 1 |

## 2. Cạnh nguy hiểm cần soát tay

| source | target | key | flags |
|---|---|---|---|
| `SETTING_ISLAND` | `SETTING_COASTAL` | related | same_facet_unclear |
| `STYLE_QUIET` | `STYLE_RELAXING` | related | same_facet_unclear |
| `STYLE_RELAXING` | `STYLE_QUIET` | related | same_facet_unclear |

## 3. Toàn bộ legacy edges + đề xuất type/use_as

| source | target | facet→facet | key | trong expansion? | suggest type | suggest use_as |
|---|---|---|---|---|---|---|
| `AMEN_BABYSITTING` | `PURPOSE_FAMILY` | amenity→purpose | related | ✅ | `evidence_for` | `boost` |
| `AMEN_BEACHFRONT` | `SETTING_COASTAL` | amenity→setting | broader | ✅ | `broader` | `boost` |
| `AMEN_HIKING` | `SETTING_MOUNTAIN` | amenity→setting | related | ✅ | `cooccurs_with` | `suggestion` |
| `AMEN_INFINITY_POOL` | `AMEN_POOL` | amenity→amenity | broader | ✅ | `broader` | `boost` |
| `AMEN_KIDS_CLUB` | `PURPOSE_FAMILY` | amenity→purpose | related | ✅ | `evidence_for` | `boost` |
| `AMEN_KIDS_POOL` | `AMEN_POOL` | amenity→amenity | broader | ✅ | `broader` | `boost` |
| `AMEN_KIDS_POOL` | `PURPOSE_FAMILY` | amenity→purpose | related | ✅ | `evidence_for` | `boost` |
| `AMEN_KITCHEN` | `OBJ_APARTMENT` | amenity→object_type | related | ✅ | `cooccurs_with` | `suggestion` |
| `AMEN_MEETING_ROOM` | `PURPOSE_BUSINESS` | amenity→purpose | related | ✅ | `evidence_for` | `boost` |
| `AMEN_POOL` | `AMEN_INFINITY_POOL` | amenity→amenity | narrower | ✅ | `narrower` | `boost` |
| `AMEN_POOL` | `AMEN_KIDS_POOL` | amenity→amenity | narrower | ✅ | `narrower` | `boost` |
| `AMEN_POOL` | `AMEN_PRIVATE_POOL` | amenity→amenity | narrower | ✅ | `narrower` | `boost` |
| `AMEN_PRIVATE_POOL` | `AMEN_POOL` | amenity→amenity | broader | ✅ | `broader` | `boost` |
| `AMEN_PRIVATE_POOL` | `OBJ_VILLA` | amenity→object_type | related | ✅ | `cooccurs_with` | `suggestion` |
| `AMEN_SPA` | `PURPOSE_WELLNESS` | amenity→purpose | related | ✅ | `evidence_for` | `boost` |
| `AMEN_WATERSPORT` | `SETTING_COASTAL` | amenity→setting | related | ✅ | `cooccurs_with` | `suggestion` |
| `OBJ_VILLA` | `AMEN_PRIVATE_POOL` | object_type→amenity | related | ✅ | `cooccurs_with` | `suggestion` |
| `PRICE_LUXURY` | `PRICE_UPSCALE` | price_tier→price_tier | broader | ✅ | `broader` | `boost` |
| `PRICE_UPSCALE` | `PRICE_LUXURY` | price_tier→price_tier | narrower | ✅ | `narrower` | `boost` |
| `PURPOSE_BUSINESS` | `AMEN_WIFI` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_FAMILY` | `AMEN_KIDS_CLUB` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_FAMILY` | `AMEN_KIDS_POOL` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `AMEN_PRIVATE_POOL` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `AMEN_SEA_VIEW` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `STYLE_ROMANTIC` | purpose→style | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_WELLNESS` | `AMEN_SPA` | purpose→amenity | related | ✅ | `evidence_for` | `boost` |
| `PURPOSE_WELLNESS` | `STYLE_QUIET` | purpose→style | related | ✅ | `evidence_for` | `boost` |
| `SETTING_COASTAL` | `AMEN_BEACHFRONT` | setting→amenity | narrower | ✅ | `narrower` | `boost` |
| `SETTING_ISLAND` | `SETTING_COASTAL` | setting→setting | related | ✅ | `similar_to` | `suggestion` |
| `SETTING_NATURE` | `STYLE_QUIET` | setting→style | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_ECO` | `SETTING_NATURE` | style→setting | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_LUXURY` | `AMEN_PRIVATE_POOL` | style→amenity | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_LUXURY` | `AMEN_SPA` | style→amenity | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_LUXURY` | `PRICE_LUXURY` | style→price_tier | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_QUIET` | `SETTING_NATURE` | style→setting | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_QUIET` | `STYLE_RELAXING` | style→style | related | ✅ | `similar_to` | `suggestion` |
| `STYLE_RELAXING` | `PURPOSE_WELLNESS` | style→purpose | related | ✅ | `cooccurs_with` | `suggestion` |
| `STYLE_RELAXING` | `STYLE_QUIET` | style→style | related | ✅ | `similar_to` | `suggestion` |
| `STYLE_ROMANTIC` | `PURPOSE_ROMANTIC` | style→purpose | related | ✅ | `cooccurs_with` | `suggestion` |

## 4. Cạnh trong query_expansion KHÔNG từ legacy (cooccurrence-sinh)

> Đây là cạnh data-driven `build_expansion.py` tự sinh. Khi migrate sang relation graph,
> các cạnh này nên thành `source_type: generated_lift`, vào `candidates.yaml`, KHÔNG verified ngay.

| source | target |
|---|---|
| `OBJ_APARTMENT` | `AMEN_KITCHEN` |
| `OBJ_APARTMENT` | `AMEN_SEA_VIEW` |
| `OBJ_HOMESTAY` | `AMEN_KITCHEN` |
| `OBJ_RESORT` | `AMEN_BEACHFRONT` |
| `OBJ_RESORT` | `AMEN_GOLF` |
| `OBJ_RESORT` | `AMEN_SEA_VIEW` |
| `OBJ_RESORT` | `AMEN_WATERSPORT` |
| `OBJ_RESORT` | `SETTING_NATURE` |
| `SETTING_MOUNTAIN` | `AMEN_BIKE` |
| `SETTING_NATURE` | `AMEN_BIKE` |
| `SETTING_NATURE` | `AMEN_GARDEN` |
| `SETTING_NATURE` | `AMEN_KIDS_POOL` |
| `SETTING_NATURE` | `AMEN_SEA_VIEW` |
| `SETTING_RIVERSIDE` | `AMEN_BAR` |
| `SETTING_RIVERSIDE` | `AMEN_CAFE` |
| `SETTING_RIVERSIDE` | `AMEN_GYM` |
| `SETTING_RIVERSIDE` | `AMEN_MEETING_ROOM` |
| `SETTING_RIVERSIDE` | `AMEN_SPA` |

## 5. Location relation bị bỏ khỏi query_expansion

`build_expansion.py` skip mọi file `*generated*` ở nguồn 1, nên:

- `location_setting.generated.yaml`: 11 location có SETTING suy ra,
  KHÔNG vào `query_expansion.yaml`. Đây là ứng viên relation `LOC_* implies SETTING_*`
  (`source_type: generated_location`, `use_as: filter` sau khi QC).
- `relations_near.generated.yaml`: 1834 cạnh `near` hotel→landmark, là quan hệ object-level
  (không phải concept→concept), giữ riêng cho ranking theo km — KHÔNG đưa vào expansion concept.

## 6. Khuyến nghị migrate đầu tiên (vào curated.yaml)

Ưu tiên cạnh có `suggest type` deterministic và facet rõ:

| source | target | suggest type | suggest use_as |
|---|---|---|---|
| `AMEN_BABYSITTING` | `PURPOSE_FAMILY` | `evidence_for` | `boost` |
| `AMEN_BEACHFRONT` | `SETTING_COASTAL` | `broader` | `boost` |
| `AMEN_INFINITY_POOL` | `AMEN_POOL` | `broader` | `boost` |
| `AMEN_KIDS_CLUB` | `PURPOSE_FAMILY` | `evidence_for` | `boost` |
| `AMEN_KIDS_POOL` | `PURPOSE_FAMILY` | `evidence_for` | `boost` |
| `AMEN_KIDS_POOL` | `AMEN_POOL` | `broader` | `boost` |
| `AMEN_MEETING_ROOM` | `PURPOSE_BUSINESS` | `evidence_for` | `boost` |
| `AMEN_POOL` | `AMEN_INFINITY_POOL` | `narrower` | `boost` |
| `AMEN_POOL` | `AMEN_KIDS_POOL` | `narrower` | `boost` |
| `AMEN_POOL` | `AMEN_PRIVATE_POOL` | `narrower` | `boost` |
| `AMEN_PRIVATE_POOL` | `AMEN_POOL` | `broader` | `boost` |
| `AMEN_SPA` | `PURPOSE_WELLNESS` | `evidence_for` | `boost` |
| `PRICE_LUXURY` | `PRICE_UPSCALE` | `broader` | `boost` |
| `PRICE_UPSCALE` | `PRICE_LUXURY` | `narrower` | `boost` |
| `PURPOSE_BUSINESS` | `AMEN_WIFI` | `evidence_for` | `boost` |
| `PURPOSE_FAMILY` | `AMEN_KIDS_CLUB` | `evidence_for` | `boost` |
| `PURPOSE_FAMILY` | `AMEN_KIDS_POOL` | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `AMEN_SEA_VIEW` | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `STYLE_ROMANTIC` | `evidence_for` | `boost` |
| `PURPOSE_ROMANTIC` | `AMEN_PRIVATE_POOL` | `evidence_for` | `boost` |
| `PURPOSE_WELLNESS` | `AMEN_SPA` | `evidence_for` | `boost` |
| `PURPOSE_WELLNESS` | `STYLE_QUIET` | `evidence_for` | `boost` |
| `SETTING_COASTAL` | `AMEN_BEACHFRONT` | `narrower` | `boost` |

_Tổng cạnh đề xuất migrate đợt đầu: 23._
