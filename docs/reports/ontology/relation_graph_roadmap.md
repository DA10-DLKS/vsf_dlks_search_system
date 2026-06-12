# Ontology Relation Graph Roadmap

> Mục tiêu: nâng cấp `related`/`query_expansion` hiện tại thành relation graph có kiểu quan hệ,
> provenance, confidence, use-case rõ ràng và có luồng duyệt giống style discovery.
>
> Ngày viết: 2026-06-12.

---

## 1. Đánh giá khả thi

Mức khả thi với data/code hiện tại: **85%**.

Nếu chỉ làm MVP gồm audit, schema, loader/validator và candidate generation từ object hiện tại thì khả thi khoảng
**90%**. Nếu làm đầy đủ tới mức dùng mạnh trong production ranking/filter thì còn khoảng **75-80%**, vì cần thêm
golden query set và A/B retrieval để tránh relation tốt trên thống kê nhưng làm query nhiễu.

Lý do khả thi cao:

- Ontology đã tách facet rõ: `object_type`, `location`, `amenity`, `setting`, `purpose`, `price_tier`, `style`, `aspect`.
- `knowledge_objects.json` đã có 520 object, đủ concept hard/soft để đếm co-occurrence.
- `semantic_metadata.location` đã có `LOC_*` cho 520/520 hotel, nên location hierarchy dùng được.
- Đã có `query_expansion.yaml` tự sinh từ `related` + co-occurrence, tức là phần ý tưởng đã tồn tại.
- Đã có generated relation khác: `relations_near.generated.yaml`, `location_setting.generated.yaml`.
- Đã có workflow candidate/promote/backfill cho STYLE, có thể tái sử dụng tinh thần cho relation.
- Đã có pytest regression cơ bản cho normalize/synonym, mapper, backfill.

Những điểm rủi ro:

- `related` hiện tại chưa typed, không biết cạnh nào dùng để filter, boost, suggestion hay explanation.
- Co-occurrence từ `hotel_tags.json` chủ yếu là hard/source tags, chưa tận dụng đầy đủ `semantic_profile`.
- STYLE mới còn sparse: `STYLE_BOUTIQUE`, `STYLE_MINIMALIST`, `STYLE_VINTAGE` ít hotel, dễ sinh relation yếu.
- Một số relation thống kê có thể đúng về data nhưng sai về semantics, ví dụ `PRICE_LUXURY -> STYLE_LUXURY`.
- Chưa có golden query đủ mạnh để verify expansion/ranking.
- Query expansion hiện `status=unverified`, nên chưa nên bật như logic production mạnh.

Kết luận: **nên làm**, nhưng làm theo hướng incremental. Không nên thay toàn bộ `related` ngay.

---

## 2. Nguyên tắc thiết kế

### 2.1 Không dùng `related` mơ hồ lâu dài

`related` hiện tại chỉ nói hai concept có liên quan, nhưng không nói liên quan kiểu gì. Ví dụ:

```yaml
LOC_PHU_QUOC -> SETTING_ISLAND
AMEN_SPA -> PURPOSE_WELLNESS
STYLE_BOUTIQUE -> STYLE_VINTAGE
```

Ba cạnh trên không nên được dùng như nhau.

Thay vào đó, relation nên có:

- `type`: loại quan hệ.
- `source_type`: quan hệ sinh từ đâu.
- `confidence`: độ tin.
- `support`/`lift`: bằng chứng thống kê nếu có.
- `use_as`: dùng để làm gì trong search.
- `status`: đã duyệt chưa.

### 2.2 Tách filter và boost

Không phải relation nào cũng được dùng để lọc cứng.

Ví dụ:

- `LOC_PHU_QUOC -> SETTING_ISLAND`: có thể dùng filter/boost mạnh.
- `PURPOSE_WELLNESS -> AMEN_SPA`: nên dùng boost, không bắt buộc filter.
- `AMEN_SPA -> STYLE_RELAXING`: chỉ boost/suggestion.
- `STYLE_BOUTIQUE -> STYLE_VINTAGE`: suggestion hoặc explanation, không filter.

Rule quan trọng:

```text
cooccurs_with không được dùng filter cứng.
generated_lift mặc định chỉ candidate/boost.
filter chỉ dành cho relation verified và gần như deterministic.
```

### 2.3 Generated relation không tự động verified

Relation sinh từ data chỉ nên vào candidate.

Luồng đúng:

```text
generated relation -> candidates.yaml -> người duyệt -> curated.yaml -> query dùng
```

### 2.4 Relation phải debug được

Mỗi cạnh relation phải trả lời được:

- Vì sao có cạnh này?
- Sinh từ file nào/script nào?
- Dựa trên bao nhiêu hotel?
- Có được người duyệt chưa?
- Query layer dùng nó để filter hay boost?

---

## 3. Schema relation đề xuất

File relation mới nên có format:

```yaml
version: "1.0.0"
relations:
  - source: LOC_PHU_QUOC
    target: SETTING_ISLAND
    type: implies
    source_type: curated
    confidence: 1.0
    use_as: filter
    status: verified
    note: "Phú Quốc là đảo"
```

### 3.1 Field bắt buộc

| Field | Ý nghĩa |
|---|---|
| `source` | concept nguồn |
| `target` | concept đích |
| `type` | kiểu quan hệ |
| `source_type` | nguồn sinh relation |
| `confidence` | độ tin 0-1 |
| `use_as` | cách query/search được phép dùng |
| `status` | trạng thái duyệt |

### 3.2 Field tùy chọn

| Field | Ý nghĩa |
|---|---|
| `support` | số hotel/review có bằng chứng |
| `probability` | P(target\|source) |
| `lift` | mức target đặc trưng cho source |
| `direction` | `directed` hoặc `undirected` |
| `evidence` | mô tả bằng chứng ngắn |
| `note` | ghi chú người duyệt |
| `reject_reason` | lý do reject |
| `created_by` | script/người tạo |
| `created_at` | thời điểm tạo |

### 3.3 Enum đề xuất

`type`:

```text
implies
evidence_for
cooccurs_with
broader
narrower
located_in
near
supports_setting
supports_purpose
similar_to
conflicts_with
avoid_with
```

`source_type`:

```text
curated
legacy_related
generated_lift
generated_location
generated_near
llm_suggested
```

`use_as`:

```text
filter
boost
suggestion
explanation
avoid
```

`status`:

```text
candidate
verified
rejected
deprecated
```

---

## 4. Cấu trúc file đề xuất

Không nhét tất cả relation vào concept YAML nữa. Nên tách riêng:

```text
ontology/
  relations/
    curated.yaml
    candidates.yaml
    generated.cooccurrence.yaml
    generated.location_setting.yaml
    README.md
```

Ý nghĩa:

| File | Vai trò |
|---|---|
| `curated.yaml` | Relation đã duyệt, dùng được trong query/ranking |
| `candidates.yaml` | Relation chờ duyệt |
| `generated.cooccurrence.yaml` | Relation sinh tự động từ object/profile |
| `generated.location_setting.yaml` | Relation location -> setting sinh từ data |
| `README.md` | Contract/schema ngắn cho người sửa ontology |

Giữ backward-compatible:

- Giai đoạn đầu vẫn đọc `related` trong `ontology/core/*.yaml`.
- Loader normalize `related` cũ thành relation có `source_type: legacy_related`.
- Sau khi ổn mới migrate dần `related` sang `curated.yaml`.

---

## 5. Kế thừa luồng `query_expansion` cũ

Đây không phải một hệ thống mới từ số 0. Luồng relation graph nên được xây bằng cách **nâng cấp luồng
`query_expansion` hiện có**.

### 5.1 Luồng cũ hiện tại

Luồng đã có:

```text
related/broader/narrower trong ontology/core/*.yaml
+ co-occurrence từ knowledge_engineering/enrichment/hotel_tags.json
-> knowledge_engineering/common/build_expansion.py
-> ontology/query_expansion.yaml
-> knowledge_engineering/governance/evaluate_query_expansion.py
-> audit với docs/reports/ontology/sprint1/golden_query_concepts.md
```

Vai trò từng phần:

| Thành phần cũ | Vai trò hiện tại |
|---|---|
| `related` trong core YAML | cạnh người viết tay, chưa typed |
| `build_expansion.py` | compiler sinh `query_expansion.yaml` |
| `query_expansion.yaml` | artifact bàn giao cho query layer |
| co-occurrence từ `hotel_tags.json` | gợi ý cạnh data-driven |
| `evaluate_query_expansion.py` | audit read-only hit/noise trên golden set |
| `golden_query_concepts.md` | bộ query có `expansion_should_help` |

Điểm tốt của luồng cũ:

- Đã có script sinh tự động, không phải sửa tay `query_expansion.yaml`.
- Đã có ngưỡng thống kê `probability/support/lift`.
- Đã có golden query để kiểm expansion.
- Output đã có `status: unverified`, tức là không tự nhận đúng.

Điểm còn thiếu:

- `related` chưa có `type`, `use_as`, `confidence`, `source_type`.
- `query_expansion.yaml` là generated artifact, nếu sửa tay status sẽ bị overwrite khi chạy lại.
- Chưa có nơi lưu quyết định duyệt/reject bền vững.
- Co-occurrence đi thẳng vào expansion, chưa qua candidate review.
- Evaluation chỉ report, chưa ghi lại verified/rejected.
- Chưa phân biệt relation dùng để `filter`, `boost`, `suggestion`, `explanation`.

### 5.2 Mapping từ luồng cũ sang luồng mới

| Cũ | Giữ hay đổi | Vai trò mới |
|---|---|---|
| `related/broader/narrower` trong core YAML | giữ tạm | legacy relation input |
| `build_expansion.py` | refactor | expansion compiler đọc relation graph |
| `query_expansion.yaml` | giữ | output cuối cho query layer, backward-compatible |
| co-occurrence từ `hotel_tags.json` | giữ, nâng cấp | generated relation candidate |
| `evaluate_query_expansion.py` | mở rộng | relation/query expansion evaluator |
| `golden_query_concepts.md` | giữ | kiểm hit/noise |
| sửa tay `query_expansion.yaml` | bỏ dần | thay bằng `curated.yaml`/`rejected` |

Target mới:

```text
legacy related
+ curated relations
+ generated relation candidates
+ rejected registry
-> relation_loader.py
-> build_expansion.py
-> query_expansion.yaml typed + backward-compatible
-> evaluate_query_expansion.py
-> promote/reject relation
```

### 5.3 Vai trò mới của `query_expansion.yaml`

Không bỏ `query_expansion.yaml`. File này vẫn là artifact cho query layer. Nhưng nó nên được sinh từ relation graph.

Format backward-compatible:

```yaml
rules:
  PURPOSE_WELLNESS:
    expands_to:
      - AMEN_SPA
    evidence:
      AMEN_SPA: curated/evidence_for/use_as=boost
    status: verified
    expansions:
      - target: AMEN_SPA
        relation_type: evidence_for
        source_type: curated
        use_as: boost
        weight: 0.8
        confidence: 0.9
        status: verified
```

Trong đó:

- `expands_to` giữ để code cũ không vỡ.
- `evidence` giữ để người đọc nhanh hiểu source.
- `expansions` là schema mới cho query layer thông minh hơn.
- `status` của rule lấy từ relation verified/candidate, không sửa tay ở output.

### 5.4 Vai trò mới của `build_expansion.py`

Hiện tại `build_expansion.py` làm 2 việc cùng lúc:

```text
1. đọc ontology related
2. tự tính co-occurrence
3. ghi query_expansion.yaml
```

Sau nâng cấp nên tách:

```text
relation_loader.py
  đọc curated/candidate/legacy related/rejected

build_relation_candidates.py
  tính co-occurrence và ghi candidates/generated

build_expansion.py
  chỉ compile relation verified thành query_expansion.yaml
```

Như vậy `build_expansion.py` trở thành compiler ổn định, không phải nơi chứa toàn bộ logic duyệt.

### 5.5 Vai trò mới của `evaluate_query_expansion.py`

Hiện tại evaluator read-only là đúng. Nên giữ nguyên tinh thần đó, nhưng mở rộng report:

```text
rule source concept
target concept
relation_type
source_type
use_as
status
hit query
noise query
recommendation: keep / downgrade / reject / needs_retrieval_test
```

Evaluator vẫn không tự sửa ontology. Quyết định cuối cùng ghi vào:

```text
ontology/relations/curated.yaml
ontology/relations/candidates.yaml
ontology/relations/rejected.yaml
```

### 5.6 Quy tắc migration quan trọng

Không sửa tay `ontology/query_expansion.yaml` để duyệt.

Lý do:

```text
query_expansion.yaml là generated artifact.
Chạy build_expansion.py lần sau sẽ overwrite.
Quyết định duyệt phải nằm trong curated/rejected/candidates.
```

Luồng đúng:

```text
candidate relation -> review -> curated/rejected -> build_expansion.py -> query_expansion.yaml
```

---

## 6. Luồng triển khai từng bước

### Bước 0. Đóng băng vai trò của file generated

Mục tiêu: thống nhất file nào là source of truth, file nào là artifact.

Quy ước:

| File | Vai trò |
|---|---|
| `ontology/core/*.yaml` | source of truth concept, giữ `related` legacy tạm thời |
| `ontology/relations/curated.yaml` | source of truth relation đã duyệt |
| `ontology/relations/candidates.yaml` | source of truth relation chờ duyệt |
| `ontology/relations/rejected.yaml` | source of truth relation đã reject |
| `ontology/query_expansion.yaml` | generated artifact, không sửa tay để duyệt |

Tiêu chí hoàn thành:

```text
Document/README ghi rõ query_expansion.yaml là generated.
Không dùng manual edit query_expansion.yaml làm trạng thái duyệt.
```

### Bước 1. Audit `related` và `query_expansion` hiện tại

Mục tiêu: biết hiện có bao nhiêu relation legacy, cạnh nào chắc, cạnh nào mơ hồ, cạnh nào đang xuất hiện trong
`query_expansion.yaml`.

Input:

```text
ontology/core/*.yaml
ontology/query_expansion.yaml
ontology/relations_near.generated.yaml
ontology/core/location_setting.generated.yaml
knowledge_engineering/common/build_expansion.py
```

Output:

```text
docs/reports/ontology/relation_audit.md
```

Việc cần làm:

1. Quét mọi concept có field `related`, `broader`, `narrower`.
2. Parse `ontology/query_expansion.yaml` hiện tại.
3. Với mỗi cạnh ghi:
   - source concept
   - target concept
   - source facet
   - target facet
   - file gốc
   - target có tồn tại không
   - có xuất hiện trong `query_expansion.yaml` không
   - evidence hiện tại là `ontology_relation` hay `cooccurrence`
   - type/use_as đề xuất
4. Đánh dấu cạnh nguy hiểm:
   - target không tồn tại
   - source/target quá rộng như `OBJ_HOTEL`
   - cạnh từ price sang style
   - cạnh cùng facet nhưng không rõ nghĩa
   - cạnh generated nhưng đang có nguy cơ được dùng như filter
5. Ghi riêng các cạnh location đang bị bỏ khỏi `query_expansion.yaml` do `build_expansion.py` skip `location.generated.yaml`.

Tiêu chí hoàn thành:

```text
Có report audit.
Không còn relation target bị thiếu concept mà không biết.
Có danh sách relation nên migrate đầu tiên.
Có danh sách rule `query_expansion` nên giữ/reject/downgrade.
```

### Bước 2. Viết schema/contract cho relation

Mục tiêu: người sửa ontology biết relation phải có field gì và dùng thế nào.

Output:

```text
ontology/relations/README.md
```

Nội dung cần có:

- Relation schema.
- Enum `type`, `source_type`, `use_as`, `status`.
- Ví dụ đúng/sai.
- Rule không dùng `generated_lift` làm filter.
- Rule relation generated phải qua candidate trước.

Tiêu chí hoàn thành:

```text
README mô tả đủ schema.
Người khác nhìn vào có thể thêm relation thủ công đúng format.
```

### Bước 3. Tạo `curated.yaml` cho relation chắc nhất

Mục tiêu: đưa các relation viết tay chắc vào file mới.

Output:

```text
ontology/relations/curated.yaml
```

Nên migrate trước các cạnh chắc:

```yaml
relations:
  - source: LOC_PHU_QUOC
    target: SETTING_ISLAND
    type: implies
    source_type: curated
    confidence: 1.0
    use_as: filter
    status: verified

  - source: PURPOSE_WELLNESS
    target: AMEN_SPA
    type: evidence_for
    source_type: curated
    confidence: 0.9
    use_as: boost
    status: verified

  - source: PURPOSE_FAMILY
    target: AMEN_KIDS_CLUB
    type: evidence_for
    source_type: curated
    confidence: 0.9
    use_as: boost
    status: verified
```

Chưa nên xóa `related` cũ ngay.

Tiêu chí hoàn thành:

```text
curated.yaml có 10-30 relation verified đầu tiên.
Mọi source/target đều tồn tại trong ontology.
```

### Bước 4. Viết relation loader/validator

Mục tiêu: đọc relation từ file mới và legacy `related`, validate, trả về format thống nhất.

File đề xuất:

```text
knowledge_engineering/common/relation_loader.py
```

Input:

```text
ontology/relations/curated.yaml
ontology/relations/candidates.yaml
ontology/relations/rejected.yaml
ontology/core/*.yaml
```

Loader nên làm:

1. Load concept ids + facets từ `ontology/core/*.yaml`.
2. Load relation YAML mới.
3. Load rejected relation để generator/evaluator biết không đề xuất lại.
4. Load legacy `related/broader/narrower` từ concept YAML.
5. Normalize mọi cạnh về schema chung.
6. Validate:
   - source tồn tại
   - target tồn tại
   - enum hợp lệ
   - confidence trong 0-1
   - `use_as=filter` chỉ cho `status=verified`
7. Deduplicate cạnh.
8. Khi relation cùng source-target xuất hiện ở nhiều nguồn, ưu tiên:
   - `curated.yaml`
   - `rejected.yaml`
   - `candidates.yaml`
   - legacy `related`

Output function:

```python
load_relations(status={"verified"}, use_as=None) -> list[Relation]
```

Tiêu chí hoàn thành:

```text
Loader chạy được.
Validate fail sớm nếu relation sai.
Có pytest cho target thiếu, enum sai, duplicate, precedence curated > legacy.
```

### Bước 5. Tách co-occurrence khỏi `build_expansion.py`

Mục tiêu: biến logic co-occurrence cũ thành generator candidate riêng, không ghi thẳng vào expansion artifact.

Hiện tại:

```text
build_expansion.py đọc hotel_tags.json -> ghi cạnh cooccurrence vào query_expansion.yaml
```

Sau nâng cấp:

```text
build_relation_candidates.py đọc knowledge_objects.json/hotel_tags.json
-> ontology/relations/generated.cooccurrence.yaml
-> ontology/relations/candidates.yaml
```

Lý do:

- Candidate cần được duyệt trước khi vào expansion chính thức.
- Dùng được cả hard metadata và soft profile.
- Có nơi lưu support/probability/lift đầy đủ.
- Tránh overwrite quyết định duyệt.

Tiêu chí hoàn thành:

```text
build_expansion.py không còn tự quyết định co-occurrence mới.
Co-occurrence mới nằm trong generated/candidates.
query_expansion.yaml chỉ compile relation verified hoặc legacy được cho phép.
```

### Bước 6. Sinh candidate relation từ `knowledge_objects.json`

Mục tiêu: giảm viết tay bằng thống kê corpus.

File đề xuất:

```text
knowledge_engineering/entity_extraction/build_relation_candidates.py
```

Input:

```text
knowledge_engineering/enrichment/knowledge_objects.json
```

Cách lấy concept cho mỗi hotel:

```text
semantic_metadata.object_type
semantic_metadata.location
semantic_metadata.amenity
semantic_metadata.setting
semantic_metadata.purpose
semantic_metadata.price_tier
semantic_metadata.style
semantic_profile concept có score >= 0.6
```

Chỉ số cần tính:

```text
support(A,B) = số hotel có cả A và B
probability(A->B) = P(B|A)
lift(A,B) = P(B|A) / P(B)
```

Ngưỡng khởi điểm đề xuất:

```text
support >= 8
probability >= 0.35
lift >= 1.5
max edges per source = 5
```

Rule lọc rác:

- Bỏ `OBJ_HOTEL` làm source vì quá rộng.
- Bỏ concept xuất hiện ở quá nhiều hotel nếu lift thấp.
- Bỏ relation `PRICE_* -> STYLE_*` nếu chưa duyệt tay.
- Bỏ relation cùng facet nếu không nằm trong whitelist.
- Bỏ relation đã có trong curated.
- Bỏ relation đã rejected trước đó.

Output:

```text
ontology/relations/generated.cooccurrence.yaml
ontology/relations/candidates.yaml
```

Ví dụ output:

```yaml
relations:
  - source: OBJ_RESORT
    target: AMEN_BEACHFRONT
    type: cooccurs_with
    source_type: generated_lift
    support: 30
    probability: 0.70
    lift: 2.73
    confidence: 0.68
    use_as: boost
    status: candidate
```

Tiêu chí hoàn thành:

```text
candidates.yaml sinh được candidate có support/lift.
Không tự verified.
Không phá query_expansion hiện tại.
```

### Bước 7. Duyệt candidate relation

Mục tiêu: có human-in-the-loop như style discovery.

Luồng:

```text
candidates.yaml -> người duyệt -> promote vào curated.yaml hoặc reject
```

Cách duyệt ban đầu:

1. Mở `ontology/relations/candidates.yaml`.
2. Với mỗi relation:
   - nếu hợp lý: đổi `status: verified` hoặc dùng script promote.
   - nếu nhiễu: `status: rejected`, thêm `reject_reason`.
3. Promote relation verified vào `curated.yaml`.
4. Giữ rejected để generator không đề xuất lại.

File script đề xuất sau này:

```text
knowledge_engineering/entity_extraction/promote_relation_candidate.py
```

Tiêu chí duyệt:

- Relation có ý nghĩa semantic, không chỉ thống kê.
- Dùng `boost` nếu chưa chắc.
- Chỉ dùng `filter` nếu deterministic.
- Có support đủ lớn.
- Không làm query quá hẹp.

### Bước 8. Refactor `build_expansion.py` thành compiler

Mục tiêu: giữ `query_expansion.yaml` làm output, nhưng sinh từ relation graph typed.

Input mới:

```text
relation_loader.load_relations(status={"verified"})
```

Output vẫn là:

```text
ontology/query_expansion.yaml
```

Nhưng format nên có thêm `expansions`:

```yaml
rules:
  PURPOSE_WELLNESS:
    expands_to:
      - AMEN_SPA
    evidence:
      AMEN_SPA: curated/evidence_for/use_as=boost
    status: verified
    expansions:
      - target: AMEN_SPA
        relation_type: evidence_for
        source_type: curated
        use_as: boost
        weight: 0.8
        confidence: 0.9
        status: verified
```

Backward-compatible:

- Giữ `expands_to`.
- Giữ `evidence`.
- Thêm `expansions`.
- Header ghi rõ file generated từ relation graph.

Tiêu chí hoàn thành:

```text
Code cũ đọc expands_to vẫn chạy.
Code mới đọc expansions để biết filter/boost/suggestion.
Không cần sửa tay query_expansion.yaml.
```

### Bước 9. Mở rộng `evaluate_query_expansion.py`

Mục tiêu: tận dụng evaluator cũ, nhưng audit được relation metadata.

Hiện tại evaluator đã đọc:

```text
golden_query_concepts.md
query_expansion.yaml
```

Cần mở rộng để report:

```text
source concept
target concept
relation_type
source_type
use_as
status
hit/missing/noise
recommendation
```

Recommendation gợi ý:

| Tình huống | Recommendation |
|---|---|
| hit nhiều, không noise | keep/promote |
| hit nhưng có noise | keep as boost, not filter |
| không hit, nhiều noise | reject |
| parser không bắt source | parser_miss |
| intent cần router | intent_router_needed |

Output:

```text
docs/reports/ontology/query_expansion_evaluation.md
```

Tiêu chí hoàn thành:

```text
Evaluator vẫn read-only.
Report đủ thông tin để người duyệt update curated/rejected.
```

### Bước 10. Tạo relation quality report

Mục tiêu: relation graph không phình thành mạng nhiễu.

Output:

```text
docs/reports/ontology/relation_quality.md
```

Report nên có:

- Tổng số relation theo `status`.
- Tổng số relation theo `source_type`.
- Tổng số relation theo `use_as`.
- Top generated relation theo lift.
- Relation bị reject.
- Relation target/source không tồn tại.
- Relation dùng filter.
- Relation từ concept quá phổ biến.

Tiêu chí hoàn thành:

```text
Mỗi lần sinh candidate có report đi kèm.
Người duyệt nhìn report biết nên duyệt cái gì trước.
```

### Bước 11. Cho `query_demo` dùng relation graph ở chế độ an toàn

Mục tiêu: dùng relation mới nhưng không làm search chết.

Giai đoạn 1:

- Chỉ dùng `use_as=boost`.
- Không filter bằng generated relation.
- In explanation để debug.

Ví dụ:

```text
→ expansion boost: PURPOSE_WELLNESS -> AMEN_SPA (curated/evidence_for)
```

Giai đoạn 2:

- Cho phép `use_as=filter` với relation verified deterministic.
- Ví dụ `LOC_PHU_QUOC -> SETTING_ISLAND`.

Không nên:

- Không đưa tất cả expansion vào hard filter.
- Không dùng `cooccurs_with` để filter.
- Không dùng candidate relation trong query mặc định.

Tiêu chí hoàn thành:

```text
Query demo in được expansion explanation.
Kết quả không giảm mạnh recall trên golden query.
```

### Bước 12. Verify bằng golden query set

Mục tiêu: relation giúp search tốt hơn thật, không chỉ đẹp ontology.

Input:

```text
docs/reports/ontology/sprint1/golden_query_concepts.md
ontology/query_expansion.yaml
```

Cách đánh giá:

1. Chạy query không expansion.
2. Chạy query có expansion boost.
3. So:
   - số kết quả
   - top hotel có hợp lý không
   - relation nào làm sai intent
   - relation nào giúp recall

Metrics đơn giản:

```text
no-result reduction
top-5 relevance manual check
bad expansion count
good expansion count
```

Tiêu chí hoàn thành:

```text
20-30 query được check.
Relation gây nhiễu bị hạ use_as hoặc reject.
```

---

## 7. Lộ trình MVP đề xuất

### MVP 1: Chuẩn hóa relation, chưa đổi search

Thời lượng ước tính: 1-2 ngày làm việc.

Việc làm:

1. Audit legacy `related`.
2. Viết `ontology/relations/README.md`.
3. Tạo `ontology/relations/curated.yaml` với relation chắc.
4. Viết `relation_loader.py`.
5. Thêm pytest validator.

Kết quả:

```text
Relation graph có schema.
Không phá pipeline hiện tại.
```

### MVP 2: Sinh candidate từ object

Thời lượng ước tính: 1-2 ngày làm việc.

Việc làm:

1. Viết `build_relation_candidates.py`.
2. Đọc `knowledge_objects.json`.
3. Tính support/probability/lift.
4. Ghi `generated.cooccurrence.yaml` và `candidates.yaml`.
5. Viết `relation_quality.md`.

Kết quả:

```text
Không cần viết tay toàn bộ related.
Có danh sách relation gợi ý để duyệt.
```

### MVP 3: Query demo dùng relation ở chế độ boost

Thời lượng ước tính: 0.5-1 ngày làm việc.

Việc làm:

1. Update `query_demo` đọc relation verified.
2. Chỉ dùng `use_as=boost`.
3. In expansion explanation.
4. Test 10 query demo.

Kết quả:

```text
Ontology thông minh hơn nhưng ít rủi ro.
```

### MVP 4: Cho một số relation dùng filter

Thời lượng ước tính: sau khi có golden query.

Chỉ áp dụng cho relation:

```text
status=verified
use_as=filter
source_type=curated hoặc generated_location đã QC
type=implies/supports_setting/located_in
```

Kết quả:

```text
Search dùng relation mạnh hơn nhưng vẫn kiểm soát được.
```

---

## 8. Những cải thiện thêm so với luồng ban đầu

### 7.1 Thêm rejected registry

Nên giữ relation rejected thay vì xóa.

Lý do:

- Generator không đề xuất lại mãi.
- Có lịch sử quyết định ontology.

Format:

```yaml
relations:
  - source: PRICE_LUXURY
    target: STYLE_LUXURY
    status: rejected
    reject_reason: "price tier không đồng nghĩa với cảm nhận luxury từ review"
```

### 7.2 Tính confidence theo type

Không nên dùng cùng công thức confidence cho mọi relation.

Gợi ý:

```text
curated deterministic: 0.95-1.0
curated soft/evidence_for: 0.75-0.9
generated_lift: combine support/probability/lift
llm_suggested: <=0.5, luôn candidate
```

### 7.3 Per-facet threshold

Relation giữa `purpose -> amenity` dễ hữu ích hơn `style -> style` sparse. Vì vậy threshold nên khác nhau:

```text
purpose -> amenity: support >= 5, lift >= 1.3
object_type -> amenity: support >= 8, lift >= 1.5
location -> setting: dùng generated_location riêng
style -> amenity/style: support >= 3 nhưng status candidate, không filter
price -> style: mặc định block hoặc manual only
```

### 7.4 Relation direction rõ ràng

`AMEN_SPA -> PURPOSE_WELLNESS` và `PURPOSE_WELLNESS -> AMEN_SPA` không giống nhau.

Trong query:

- Người hỏi purpose wellness: spa là evidence tốt.
- Hotel có spa không chắc chắn là wellness hotel.

Vì vậy relation nên directed mặc định.

### 7.5 Không để relation graph thay thế profile score

Relation chỉ giúp mở rộng/gợi ý. Điểm review vẫn phải là nguồn chính cho cảm nhận.

Ví dụ:

```text
AMEN_SPA -> STYLE_RELAXING
```

Không có nghĩa hotel chắc chắn relaxing. Nó chỉ boost nhẹ nếu query hỏi relaxing. Muốn khẳng định relaxing vẫn cần `semantic_profile.STYLE_RELAXING >= 0.6`.

### 7.6 Thêm explanation trace

Query demo/search nên có trace:

```text
PURPOSE_WELLNESS -> AMEN_SPA
type=evidence_for
use_as=boost
source=curated
weight=0.8
```

Trace này cực quan trọng khi demo và debug.

---

## 9. Checklist triển khai

### Chuẩn bị

- [ ] Chốt schema relation.
- [ ] Tạo thư mục `ontology/relations/`.
- [ ] Viết `ontology/relations/README.md`.

### Audit

- [ ] Sinh `relation_audit.md`.
- [ ] Kiểm target/source thiếu.
- [ ] Phân loại relation legacy.
- [ ] So sánh legacy `related` với rule đang có trong `query_expansion.yaml`.
- [ ] Ghi riêng rule co-occurrence hiện tại nên giữ/reject/downgrade.
- [ ] Ghi riêng location-related bị thiếu do `build_expansion.py` đang skip `location.generated.yaml`.

### Curated relation

- [ ] Tạo `curated.yaml`.
- [ ] Migrate 10-30 relation chắc.
- [ ] Giữ `related` cũ để backward-compatible.

### Loader/validator

- [ ] Viết `relation_loader.py`.
- [ ] Validate enum/source/target/confidence.
- [ ] Deduplicate edge.
- [ ] Pytest validator.

### Generated candidates

- [ ] Tách logic co-occurrence ra khỏi `build_expansion.py`.
- [ ] Viết `build_relation_candidates.py`.
- [ ] Đọc `knowledge_objects.json`.
- [ ] Tính support/probability/lift.
- [ ] Ghi `generated.cooccurrence.yaml`.
- [ ] Ghi `candidates.yaml`.
- [ ] Giữ rejected registry.

### Human review

- [ ] Duyệt top 20 relation.
- [ ] Promote relation tốt vào `curated.yaml`.
- [ ] Reject relation nhiễu với lý do.

### Query integration

- [ ] Update `build_expansion.py` đọc relation loader.
- [ ] Output typed expansion song song `expands_to`.
- [ ] Giữ `query_expansion.yaml` backward-compatible cho code cũ.
- [ ] Không sửa tay `query_expansion.yaml` để duyệt.
- [ ] Query demo dùng `use_as=boost` trước.
- [ ] Chỉ bật filter cho relation verified deterministic.

### Quality

- [ ] Viết `relation_quality.md`.
- [ ] Mở rộng `evaluate_query_expansion.py` để report `relation_type/source_type/use_as/status`.
- [ ] Sinh `query_expansion_evaluation.md`.
- [ ] Chạy golden query.
- [ ] Hạ/reject relation gây nhiễu.

---

## 10. Quyết định khuyến nghị

Nên làm theo thứ tự:

```text
audit -> schema -> curated.yaml -> loader/validator -> candidate generator -> human review -> query boost -> query filter
```

Không nên làm:

```text
generated relation -> auto verified -> auto filter
```

Với code/data hiện tại, hướng này không chỉ khả thi mà còn là bước tiến tự nhiên sau Sprint 2. Nó tận dụng được
những gì đã có (`related`, co-occurrence, query expansion, location setting, near relations) nhưng đưa vào một
contract rõ ràng hơn để ontology thông minh mà vẫn kiểm soát được.
