# Ontology Relations — Schema & Contract

> Nơi định nghĩa **relation graph** giữa các concept ontology (typed, có provenance, confidence, use-case).
> Roadmap đầy đủ: [docs/reports/ontology/relation_graph_roadmap.md](../../docs/reports/ontology/relation_graph_roadmap.md).

## File trong thư mục này (source of truth)

| File | Vai trò | Sửa tay? |
|---|---|---|
| `curated.yaml` | Relation đã duyệt, dùng được trong query/ranking | ✅ có (duyệt tay) |
| `candidates.yaml` | Relation chờ duyệt (do generator sinh) | ✅ đổi `status` để promote/reject |
| `rejected.yaml` | Relation đã reject — giữ để generator không đề xuất lại | ✅ có |
| `generated.cooccurrence.yaml` | Cạnh data-driven generator sinh thô (input cho candidates) | ❌ auto-generated |

### Luồng duyệt (giống STYLE — sửa YAML, không sửa code)

Candidate trong `candidates.yaml` có `status: pending`. Người duyệt mở file, đổi NGAY tại chỗ:

```yaml
- source: OBJ_RESORT
  target: AMEN_GAME_ROOM
  status: pending      # ← đổi thành: approved  (đồng ý)  hoặc  rejected
  reject_reason: "..." # ← chỉ thêm dòng này khi rejected (bắt buộc)
```

Rồi chạy:
```
python -m knowledge_engineering.entity_extraction.apply_relation_review
```
Script chuyển `approved` → `curated.yaml` (verified, boost-only), `rejected` → `rejected.yaml`,
giữ `pending` lại chờ vòng sau. Sau đó chạy `build_expansion.py` để đẩy ra artifact query layer.

**`provenance` của candidate** (do generator ghi) cho biết cạnh đến từ nguồn nào — dùng để ưu tiên duyệt:
- `metadata` — chỉ `semantic_metadata` (nhãn có/không) thấy.
- `profile` — chỉ `semantic_profile` (cảm nhận review, score≥0.6) thấy. Nhóm `style→*` thường ở đây.
- `metadata+profile` — **cả hai nguồn độc lập đồng thuận → đáng tin nhất, duyệt trước.**

Generator mặc định chạy `--source=both`, đọc từ `knowledge_objects.json` (gộp metadata + profile).
KHÔNG dùng `hotel_tags.json` (thiếu LMK/LOC/ASPECT/price_tier, gần như không có style). LMK/LOC bị
loại khỏi co-occurrence (là quan hệ object-level, đi đường generated_near/generated_location riêng).

**Ngoài thư mục này:**

- `ontology/query_expansion.yaml` là **generated artifact** cho query layer. **KHÔNG sửa tay để duyệt.**
  Chạy lại `build_expansion.py` sẽ overwrite. Quyết định duyệt phải nằm trong `curated.yaml`/`rejected.yaml`.
- `ontology/core/*.yaml` giữ `related/broader/narrower` **legacy** tạm thời; loader đọc chúng với
  `source_type: legacy_related`. Sẽ migrate dần sang `curated.yaml`.

## Schema một relation

```yaml
relations:
  - source: LOC_PHU_QUOC      # concept nguồn (bắt buộc, phải tồn tại trong ontology)
    target: SETTING_ISLAND    # concept đích (bắt buộc, phải tồn tại)
    type: implies             # kiểu quan hệ (bắt buộc, enum bên dưới)
    source_type: curated      # relation sinh từ đâu (bắt buộc, enum)
    confidence: 1.0           # độ tin 0-1 (bắt buộc)
    use_as: filter            # query layer được phép dùng làm gì (bắt buộc, enum)
    status: verified          # trạng thái duyệt (bắt buộc, enum)
    # --- tùy chọn ---
    support: 28               # số hotel/review có bằng chứng
    probability: 0.82         # P(target|source)
    lift: 2.5                 # mức target đặc trưng cho source
    direction: directed       # directed (mặc định) | undirected
    evidence: "Phú Quốc là đảo"
    note: "ghi chú người duyệt"
    reject_reason: "..."      # bắt buộc khi status=rejected
    created_by: "build_relation_candidates.py"
    created_at: "2026-06-14"
```

### Field bắt buộc
`source`, `target`, `type`, `source_type`, `confidence`, `use_as`, `status`.

## Enum

**`type`** — kiểu quan hệ:
```
implies          A kéo theo B gần như chắc chắn (vd location -> setting)
evidence_for     A là bằng chứng cho B (vd spa -> wellness)
cooccurs_with    A và B hay đi cùng, không khẳng định nhân quả
broader          A rộng hơn B (A là cha)
narrower         A hẹp hơn B (A là con)
located_in       quan hệ vị trí phân cấp
near             gần về địa lý (object-level, không phải concept)
supports_setting A củng cố một setting
supports_purpose A củng cố một purpose
similar_to       A và B tương tự (cùng facet)
conflicts_with   A và B mâu thuẫn
avoid_with       không nên gợi ý cùng nhau
```

**`source_type`** — nguồn sinh relation:
```
curated            người viết tay, đã duyệt
legacy_related     từ related/broader/narrower trong ontology/core (đang migrate)
generated_lift     sinh từ co-occurrence + lift trên corpus
generated_location sinh từ location_setting.generated.yaml
generated_near     sinh từ relations_near.generated.yaml
llm_suggested      LLM đề xuất (luôn vào candidate, confidence <= 0.5)
```

**`use_as`** — query layer được phép dùng làm gì:
```
filter        lọc cứng kết quả (CHỈ cho status=verified + deterministic)
boost         tăng điểm, không loại
suggestion    gợi ý cho người dùng
explanation   chỉ để giải thích/debug
avoid         hạ điểm / không gợi ý cùng
```

**`status`** — trạng thái duyệt:
```
# hàng đợi candidate (candidates.yaml — người duyệt sửa tại chỗ, giống STYLE):
pending     chờ duyệt
approved    người đã đồng ý, chờ apply (apply dịch -> verified vào curated.yaml)
rejected    đã từ chối (cần reject_reason)

# graph nội bộ (curated.yaml):
verified    đã duyệt, dùng được cho query layer
deprecated  từng dùng, nay bỏ
candidate   (cũ, đồng nghĩa pending — vẫn chấp nhận để backward-compat)
```

## Rule bắt buộc (loader/validator enforce)

1. `source` và `target` phải tồn tại trong `ontology/core/*.yaml`.
2. `confidence` trong khoảng `[0, 1]`.
3. **`use_as: filter` CHỈ cho phép khi `status: verified`.** Generated/candidate không bao giờ filter.
4. **`source_type: generated_*` KHÔNG được `status: verified` trực tiếp** — phải qua candidate → người duyệt.
5. `status: rejected` phải có `reject_reason`.
6. Khi cùng cặp `source→target` xuất hiện nhiều nơi, precedence:
   `curated > rejected > candidates > legacy_related`.

## Ví dụ ĐÚNG / SAI

✅ Đúng — deterministic, verified, filter:
```yaml
- source: LOC_PHU_QUOC
  target: SETTING_ISLAND
  type: implies
  source_type: curated
  confidence: 1.0
  use_as: filter
  status: verified
```

✅ Đúng — soft evidence, chỉ boost:
```yaml
- source: PURPOSE_WELLNESS
  target: AMEN_SPA
  type: evidence_for
  source_type: curated
  confidence: 0.9
  use_as: boost
  status: verified
```

❌ Sai — generated mà verified + filter (vi phạm rule 3 & 4):
```yaml
- source: OBJ_RESORT
  target: AMEN_BEACHFRONT
  source_type: generated_lift
  use_as: filter        # ❌ generated không được filter
  status: verified      # ❌ generated không tự verified
```

❌ Sai — price tier coi như cảm nhận style (đúng thống kê, sai semantic):
```yaml
- source: PRICE_LUXURY
  target: STYLE_LUXURY  # ❌ price tier ≠ cảm nhận luxury từ review -> để rejected.yaml
```

## Luồng làm việc

```
generator -> generated.cooccurrence.yaml -> candidates.yaml
          -> người duyệt -> curated.yaml (verified) | rejected.yaml (rejected)
          -> build_expansion.py -> query_expansion.yaml (artifact cho query layer)
```

Ngưỡng sinh candidate: xem bảng **per-facet threshold (mục 8.3)** trong roadmap — nguồn chân lý duy nhất.
