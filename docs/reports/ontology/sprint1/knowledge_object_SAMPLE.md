# Mẫu bàn giao — `knowledge_object` (1 khách sạn)

> ⚠ **ĐÃ THAY THẾ MỘT PHẦN bởi code Sprint 2** — đây là bản nháp gán TAY Sprint 1 để chốt
> HÌNH DẠNG. Output THẬT do [build_objects.py](../../../../knowledge_engineering/enrichment/build_objects.py)
> sinh; khi khác file này thì **code là chuẩn**. Hai điểm đã đổi so với mẫu dưới (xem callout 🔻 tại chỗ):
> 1. Tín hiệu review (`score`) KHÔNG còn đổ vào `tags[].confidence` — `tags` chỉ mang nhãn presence
>    (HARD) với `confidence` = độ chắc tag đúng. Điểm trải nghiệm review nằm RIÊNG ở `semantic_profile`
>    với trường tên là `score` (xem mục 1 review thiết kế — semantics `confidence` ≠ `score`).
> 2. Object thật có thêm khối `semantic_profile` (SOFT, điểm review) tách khỏi `semantic_metadata`.
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
    // 🔻 ĐÃ ĐỔI: code (build_objects.py) đưa style vào đây dưới dạng LIST concept_id (không
    //   phải object), CHỈ style có score >= SOFT_STYLE_MIN_SCORE (0.6). Sentiment + score đầy đủ
    //   nằm ở (G) semantic_profile. Ở đây style chỉ để FILTER/BOOST nhanh như các many-facet khác.
    "style": ["STYLE_QUIET", "STYLE_RELAXING", "STYLE_MODERN"]  // many — chỉ style đủ mạnh
  },

  // ── (C) TAGS: provenance từng nhãn PRESENCE (knowledge_object.tags) ─────
  //   🔻 ĐÃ ĐỔI: `confidence` = ĐỘ CHẮC TAG ĐÚNG (presence từ structured/rule), KHÔNG phải
  //   điểm trải nghiệm review. Tín hiệu review (yên tĩnh tới mức nào) nằm ở (G) semantic_profile
  //   với trường `score` — KHÔNG đổ vào đây nữa (tránh ranking hiểu nhầm 0.40 = "bằng chứng yếu").
  "tags": [
    {"concept": "AMEN_POOL",     "confidence": 1.0,  "sources": ["source_tag", "rule"]},
    {"concept": "AMEN_GOLF",     "confidence": 0.95, "sources": ["source_tag"]},
    {"concept": "PURPOSE_FAMILY","confidence": 0.95, "sources": ["source_tag", "rule"]}
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
  },

  // ── (G) SEMANTIC PROFILE: điểm SOFT/trải nghiệm từ review (KHÔNG lọc cứng) ─
  //   🔻 KHỐI MỚI (Bước 5). Mỗi concept review nhắc tới -> {score, evidence_count, source}.
  //   `score` = mức độ MẠNH/YẾU của trải nghiệm (Wilson lower bound), KHÔNG phải confidence tag.
  //   STYLE: score = tỷ lệ KHEN (cặp đối nghĩa, chỉ đếm positive). ASPECT: từ Agoda grades.
  //   Tầng ranking đọc score để boost; concept dưới ngưỡng vẫn ở đây nhưng không lên (B).
  "semantic_profile": {
    "ASPECT_LOCATION":   {"score": 0.92, "evidence_count": 8123, "source": "agoda_grades"},
    "ASPECT_CLEANLINESS":{"score": 0.90, "evidence_count": 8123, "source": "agoda_grades"},
    "STYLE_RELAXING":    {"score": 0.81, "evidence_count": 42,   "source": "absa"},
    "STYLE_QUIET":       {"score": 0.78, "evidence_count": 37,   "source": "absa"},
    "STYLE_MODERN":      {"score": 0.62, "evidence_count": 19,   "source": "absa"}
  }
}
```

---

## 2. Ai dùng phần nào (đây mới là "bàn giao")

| Phần | Tầng tiêu thụ | Dùng làm gì |
|---|---|---|
| **(A) content_blocks** | chunking → embedding | Cắt parent-child, sinh vector. `facet_hint` cho chunk con thừa kế concept_id. |
| **(B) semantic_metadata** | Qdrant payload + metadata_index | Filter cứng theo concept_id (style đủ mạnh cũng để filter/boost nhanh). |
| **(C) tags** | governance / audit | Truy vết nhãn PRESENCE do tầng nào gắn + `confidence` = độ chắc tag đúng. |
| **(D) range_filters** | metadata_index | Filter khoảng: "≥4 sao", "score ≥ 8". |
| **(E) nearby_places** | metadata_index (geo) | "gần VinWonders < 2km". |
| **(F) provenance** | governance + citation_builder (L7) | Nguồn + version cho trích dẫn. |
| **(G) semantic_profile** | ranking / boost + giải thích | Điểm trải nghiệm review (`score`); ranking boost theo concept. KHÔNG lọc cứng. |

---

## 3. Bất biến (invariants) — phần ràng buộc với team

1. Mọi value trong `semantic_metadata` + `tags.concept` = **concept_id tồn tại trong ontology** (cùng `ontology_version`).
2. Facet `one` → đúng 1 concept_id. Facet `many` → list (có thể rỗng `[]`).
3. **HARD fact** (amenity, object_type, location, setting, price_tier) → chỉ concept_id trong `semantic_metadata`.
   **SOFT fact** (style/aspect, điểm review) → `semantic_profile[concept] = {score, evidence_count, source}`.
   `style` đủ mạnh (score ≥ 0.6) cũng được nhân bản vào `semantic_metadata.style` (list) cho filter/boost nhanh.
4. **`confidence` (trong tags) ≠ `score` (trong semantic_profile).** `confidence` = độ chắc NHÃN ĐÚNG
   (presence). `score` = mức độ MẠNH/YẾU của trải nghiệm review. KHÔNG trộn hai trường.
5. **Text thô** ("hồ bơi") CHỈ nằm trong `content_blocks`. Ô filter KHÔNG được chứa text thô.
6. Quan hệ gần = `nearby_places[]`, KHÔNG dùng `near_<x>` boolean.

---

## 4. Trạng thái

- **Sprint 1 (xong):** cái KHUÔN — ontology + `metadata_schema.yaml` + facets.
- **Sprint 2 (sẽ làm):** ontology_mapper đọc raw/clean data → tự sinh object như trên cho cả corpus.
- File này = **1 mẫu gán tay** để chốt hình dạng trước khi viết mapper. SOFT facts (`style.score`)
  ở đây là ước lượng tay; số thật cần **review (ABSA)** — hiện chưa crawl, nên là placeholder.
```
