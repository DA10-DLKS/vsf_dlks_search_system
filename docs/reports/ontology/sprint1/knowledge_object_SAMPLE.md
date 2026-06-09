# Mẫu bàn giao — `knowledge_object` (1 khách sạn)

> Bản nháp Sprint 2. **Chưa phải code** — đây là HÌNH DẠNG output cuối mà tầng
> chunking/embedding sẽ nhận. Gán TAY (chưa qua mapper) để team thấy contract cụ thể.
>
> - Schema chuẩn: [ontology/metadata_schema.yaml](../../../../ontology/metadata_schema.yaml) (CONTRACT v1.0)
> - Nguồn dữ liệu: [hotel_805030](../../../../data/raw/hotels/hotel_805030_vinpearl-resort-spa-nha-trang-bay.json)
> - Mọi `concept_id` đều tra được trong [ontology/core/](../../../../ontology/core/)

---

## 1. Một object hoàn chỉnh (JSON)

```jsonc
{
  // ── ĐỊNH DANH (required: id, type, title, source) ──
  "id": "acc_805030",
  "type": "resort",                              // object_type -> chữ thường (theo knowledge_object.type)
  "title": "Vinpearl Resort & Spa Nha Trang Bay",
  "source": "agoda",
  "ontology_version": "concepts_v2.0.0",

  // ── (A) CONTENT cho CHUNKING + EMBEDDING ──────────────────────────────
  //   text đã clean, cắt theo block ngữ nghĩa. Mỗi block -> 1 chunk con tiềm năng,
  //   đã gắn facet_hint để chunk con thừa hưởng concept_id (parent-child).
  "content_blocks": [
    {
      "block_id": "acc_805030#overview",
      "facet_hint": ["object_type", "setting", "style"],
      "text": "Resort 5 sao nằm trên đảo Hòn Tre, vịnh Nha Trang. Không gian yên tĩnh, thư giãn, kiến trúc hiện đại, có khu vườn xanh mát và bãi biển riêng."
    },
    {
      "block_id": "acc_805030#amenities",
      "facet_hint": ["amenity"],
      "text": "Hồ bơi ngoài trời, hồ bơi trẻ em, spa, mát-xa, xông hơi, phòng tập, sân golf tại chỗ, sân tennis, câu lạc bộ trẻ em, nhà hàng, quán bar, Wi-Fi miễn phí, đưa đón sân bay."
    },
    {
      "block_id": "acc_805030#location",
      "facet_hint": ["location", "near"],
      "text": "Tọa lạc tại Hòn Tre, cách trung tâm Nha Trang 6.5 km. Gần VinWonders Nha Trang (0.86 km), Vinpearl Land (0.8 km), sân golf Vinpearl (2.7 km), Viện Hải Dương Học (3.11 km)."
    },
    {
      "block_id": "acc_805030#dining",
      "facet_hint": ["amenity"],
      "text": "5 nhà hàng và 2 quán bar. Buffet sáng phong phú, ẩm thực Việt và quốc tế, dịch vụ phòng."
    }
  ],

  // ── (B) SEMANTIC METADATA: concept_id cho FILTER + BOOST ───────────────
  //   value LUÔN là concept_id hợp lệ. one -> 1 id ; many -> list.
  "semantic_metadata": {
    "object_type": "OBJ_RESORT",                              // one
    "location":    "LOC_NHA_TRANG",                           // one
    "setting":     ["SETTING_COASTAL", "SETTING_ISLAND"],     // many
    "amenity": [                                              // many — HARD: chỉ presence
      "AMEN_POOL", "AMEN_KIDS_POOL", "AMEN_SPA", "AMEN_GYM",
      "AMEN_GOLF", "AMEN_KIDS_CLUB", "AMEN_BEACHFRONT",
      "AMEN_RESTAURANT", "AMEN_BAR", "AMEN_WIFI", "AMEN_AIRPORT_SHUTTLE"
    ],
    "price_tier":  "PRICE_LUXURY",                            // one
    "purpose":     ["PURPOSE_FAMILY", "PURPOSE_WELLNESS"],    // many
    "style": [                                                // many — SOFT: kèm sentiment + score
      {"concept_id": "STYLE_QUIET",    "sentiment": "pos", "score": 0.78},
      {"concept_id": "STYLE_RELAXING", "sentiment": "pos", "score": 0.81},
      {"concept_id": "STYLE_MODERN",   "sentiment": "pos", "score": 0.62}
    ]
  },

  // ── (C) TAGS: provenance từng nhãn (knowledge_object.tags) ─────────────
  //   để governance/audit biết nhãn này do tầng nào gắn, tin bao nhiêu.
  "tags": [
    {"concept": "AMEN_POOL",     "confidence": 1.0,  "sources": ["source_tag", "rule"]},
    {"concept": "AMEN_GOLF",     "confidence": 0.95, "sources": ["source_tag"]},
    {"concept": "STYLE_QUIET",   "confidence": 0.78, "sources": ["rule", "review_profile"]},
    {"concept": "PURPOSE_FAMILY","confidence": 0.88, "sources": ["source_tag", "rule"]}
  ],

  // ── (D) RANGE FILTERS: attribute SỐ (filter cứng kiểu khoảng) ──────────
  "range_filters": {
    "star_rating":  5,
    "review_score": 8.8,
    "price_vnd":    2700000,        // ~$112 quy đổi; lấy từ room_metadata khi có
    "distance_to_center_km": 6.5
  },

  // ── (E) NEARBY PLACES: quan hệ near (place_id + category + distance) ───
  //   thay cho near_<landmark> boolean (anti-pattern đã loại).
  "nearby_places": [
    {"place_id": "LMK_VINWONDERS_NHA_TRANG", "name": "VinWonders Nha Trang", "category": "theme_park", "distance_km": 0.86},
    {"place_id": null, "name": "Công viên giải trí Vinpearl Land",          "category": "theme_park", "distance_km": 0.8},
    {"place_id": null, "name": "Sân golf Vinpearl",                          "category": "golf",       "distance_km": 2.7},
    {"place_id": "LMK_VIEN_HAI_DUONG_HOC", "name": "Viện Hải Dương Học",     "category": "museum",     "distance_km": 3.11}
  ],

  // ── (F) GOVERNANCE ────────────────────────────────────────────────────
  "provenance": {
    "source": "agoda",
    "source_url": "https://www.agoda.com/...hotel=805030",
    "crawled_at": "2026-06-02T10:55:23",
    "mapper_version": "ontology_mapper_v0 (gán tay - mẫu)"
  }
}
```

---

## 2. Ai dùng phần nào (đây mới là "bàn giao")

| Phần | Tầng tiêu thụ | Dùng làm gì |
|---|---|---|
| **(A) content_blocks** | chunking → embedding | Cắt parent-child, sinh vector. `facet_hint` cho chunk con thừa kế concept_id. |
| **(B) semantic_metadata** | Qdrant payload + metadata_index | Filter cứng theo concept_id; `style.score` → ranking boost. |
| **(C) tags** | governance / audit | Truy vết nhãn do tầng nào gắn + độ tin. |
| **(D) range_filters** | metadata_index | Filter khoảng: "≥4 sao", "score ≥ 8". |
| **(E) nearby_places** | metadata_index (geo) | "gần VinWonders < 2km". |
| **(F) provenance** | governance + citation_builder (L7) | Nguồn + version cho trích dẫn. |

---

## 3. Bất biến (invariants) — phần ràng buộc với team

1. Mọi value trong `semantic_metadata` + `tags.concept` = **concept_id tồn tại trong ontology** (cùng `ontology_version`).
2. Facet `one` → đúng 1 concept_id. Facet `many` → list (có thể rỗng `[]`).
3. **HARD fact** (amenity, object_type, location, setting, price_tier) → chỉ concept_id.
   **SOFT fact** (style, purpose) → object `{concept_id, sentiment, score}`.
4. **Text thô** ("hồ bơi") CHỈ nằm trong `content_blocks`. Ô filter KHÔNG được chứa text thô.
5. Quan hệ gần = `nearby_places[]`, KHÔNG dùng `near_<x>` boolean.

---

## 4. Trạng thái

- **Sprint 1 (xong):** cái KHUÔN — ontology + `metadata_schema.yaml` + facets.
- **Sprint 2 (sẽ làm):** ontology_mapper đọc raw/clean data → tự sinh object như trên cho cả corpus.
- File này = **1 mẫu gán tay** để chốt hình dạng trước khi viết mapper. SOFT facts (`style.score`)
  ở đây là ước lượng tay; số thật cần **review (ABSA)** — hiện chưa crawl, nên là placeholder.
```
