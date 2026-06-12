# Sprint 2 - Step 5/6: Soft Enrichment, Discovery, Handover

> Owner: Trương Anh Long. Cập nhật: 2026-06-12.
> Mục tiêu: ghi lại luồng ABSA/review enrichment, style discovery, backfill, profile merge và output cuối để team search/demo có thể dùng lại.

---

## Ket luan ngan

Sprint 2 đã hoàn thành phần ontology ở mức demo/bàn giao kỹ thuật:

- 520 hotel có `knowledge_objects.json`.
- 502 hotel có `review_evidence` từ ABSA/review enrichment.
- 520 hotel có `hotel_profiles.json`.
- Style discovery đã sinh candidate, người duyệt đã promote style phù hợp.
- Đã backfill 3 style mới hợp lý: `STYLE_BOUTIQUE`, `STYLE_MINIMALIST`, `STYLE_VINTAGE`.
- Đã sinh `negative_style_profile` từ evidence negative sẵn có, không gọi LLM lại.
- Đã loại `STYLE_FAMILY_FRIENDLY` khỏi evidence/profile/object/ontology vì nhiễu.

Các output JSON hiện là **seed/demo artifact**. Production nên ingest sang DB/JSONL/vector index thay vì coi một file JSON lớn là storage cuối cùng.

---

## Step 5 gom nhung gi

Step 5 là phần SOFT enrichment từ review, gồm 4 lớp:

| Lớp | Script / artifact | Vai trò |
|---|---|---|
| ABSA per-review | `knowledge_engineering.enrichment.absa` | Trích `(concept, sentiment, span)` từ review |
| Novel discovery | `raw_discovery.jsonl` | Ghi phrase phong cách/vibe lạ LLM phát hiện |
| Clustering/suggest | `discovery_cluster.py`, `discovery_suggest.py` | Gom phrase lạ thành candidate concept |
| Human promotion/backfill | `promote_candidate.py`, `absa --backfill` | Đưa style duyệt vào ontology và bổ sung evidence cũ |

ABSA hiện chỉ dùng concept có trong ontology cho evidence chính. Candidate mới không tự vào object; phải qua bước duyệt/promote/backfill.

---

## Step 6 gom nhung gi

Step 6 là phần hợp nhất:

| Script | Output | Vai trò |
|---|---|---|
| `profile_builder` | `hotel_profiles.json` | Merge seed profile + review evidence thành profile theo hotel |
| `build_objects` | `knowledge_objects.json` | Ghép HARD metadata + SOFT profile thành object search/demo |

Sau mỗi lần chạy ABSA/backfill/promote concept, cần chạy lại:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
```

---

## Output hien tai

| Output | Path | Số lượng / trạng thái |
|---|---|---|
| Review evidence | `knowledge_engineering/enrichment/review_evidence/*.json` | 502 file |
| Novel phrase raw | `knowledge_engineering/enrichment/raw_discovery.jsonl` | 1696 dòng |
| Discovery clusters | `knowledge_engineering/enrichment/clusters.json` | có |
| Candidate concepts | `ontology/candidate/candidate_concepts.yaml` | có |
| Promote log | `ontology/candidate/promote_log.yaml` | có |
| Hotel profiles | `knowledge_engineering/enrichment/hotel_profiles.json` | 520 hotel |
| Knowledge objects | `knowledge_engineering/enrichment/knowledge_objects.json` | 520 object |
| Synonym index | `ontology/synonym_dictionary.yaml` | 1838 surface forms |
| Negative style profile | `negative_style_profile` trong profile/object | 139 hotel |

Coverage style sau rebuild profile:

| Style | Số hotel |
|---|---:|
| `STYLE_QUIET` | 390 |
| `STYLE_RELAXING` | 82 |
| `STYLE_LUXURY` | 66 |
| `STYLE_MODERN` | 37 |
| `STYLE_BOUTIQUE` | 9 |
| `STYLE_VINTAGE` | 1 |
| `STYLE_MINIMALIST` | 1 |

`STYLE_FAMILY_FRIENDLY` đã bị loại khỏi:

- `ontology/core/style.yaml`
- `ontology/synonym_dictionary.yaml`
- `review_evidence`
- `hotel_profiles.json`
- `knowledge_objects.json`

`query_demo.py` hiện dùng `negative_style_profile` để trừ nhẹ ranking cho query cảm nhận
(vd query "yên tĩnh" sẽ đẩy xuống hotel có nhiều evidence "ồn"), nhưng không loại cứng.

---

## Luong chay lai tu dau

### 1. Build HARD ontology/object

Chạy khi raw/clean/ontology HARD thay đổi:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.ontology_mapper
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.metadata_pipeline
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
```

Nếu chỉ sửa `surface_forms`, tối thiểu cần chạy lại:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
```

### 2. Chạy ABSA corpus

Dry-run để xem scope/cost:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --all --budget-usd 3.5 --dry-run
```

Chạy thật:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --all --budget-usd 3.5
```

Ghi chú:

- Runner đọc `data/raw/reviews`.
- Review quá ngắn bị skip.
- Evidence lưu ở `knowledge_engineering/enrichment/review_evidence`.
- `raw_discovery.jsonl` ghi các phrase style/vibe lạ để discovery.

### 3. Discovery style mới

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_cluster
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_suggest --min-hotels 2
```

Sau đó người duyệt `ontology/candidate/candidate_concepts.yaml`:

- `approved`: concept đủ sạch để promote.
- `rejected`: concept nhiễu/trùng/sai facet.
- `pending`: cần xem thêm evidence.

### 4. Promote candidate vào ontology

Dry-run:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --source concepts --dry-run
```

Apply:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --source concepts --apply
```

Sau promote, luôn rebuild synonym:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
```

### 5. Backfill style mới đã duyệt

Chỉ backfill style sạch, surface form hẹp.

Ví dụ đã chạy trong Sprint 2:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --backfill STYLE_BOUTIQUE STYLE_MINIMALIST STYLE_VINTAGE --yes --workers 6
```

Không nên backfill concept rộng/nhiễu nếu chưa QC:

- `STYLE_FAMILY_FRIENDLY`
- `STYLE_AESTHETIC`
- `STYLE_NEW`
- `STYLE_EUROPEAN_JAPANESE`

Sau backfill:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
```

### 6. Sinh negative style profile

Không cần chạy LLM lại. `profile_builder` đọc `review_evidence` hiện có và aggregate các item:

- `concept.startswith("STYLE_")`
- `sentiment == "negative"`
- tối thiểu 3 review negative/concept/hotel

Output được tách riêng:

```json
"negative_style_profile": {
  "STYLE_QUIET": {
    "negative_score": 0.51,
    "neg": 4,
    "pos": 0,
    "evidence_count": 4,
    "top_spans": ["the place isn’t very quiet"],
    "source": "absa"
  }
}
```

Chỉ cần chạy lại:

```powershell
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
```

---

## Ket qua backfill Sprint 2

Style đã backfill:

- `STYLE_BOUTIQUE`
- `STYLE_MINIMALIST`
- `STYLE_VINTAGE`

Kết quả lệnh:

```text
92 hotel trong scope
165 review được bổ sung concept mới
```

Sau rebuild profile:

```text
STYLE_BOUTIQUE: 9 hotel
STYLE_VINTAGE: 1 hotel
STYLE_MINIMALIST: 1 hotel
```

Lý do profile count nhỏ hơn review count: profile chỉ tính concept đủ evidence/threshold để trở thành style đáng tin ở cấp hotel.

---

## Quyet dinh ontology quan trong

### Giữ/promote

- `STYLE_BOUTIQUE`: giữ, nhưng surface form bó hẹp quanh `boutique`.
- `STYLE_MINIMALIST`: giữ, evidence ít nhưng nghĩa rõ.
- `STYLE_VINTAGE`: giữ, surface form cần có ngữ cảnh thiết kế/phong cách.

### Loại/chưa dùng

- `STYLE_FAMILY_FRIENDLY`: loại khỏi ontology vì dễ lẫn purpose/amenity/service/staff.
- `STYLE_AESTHETIC`: chưa dùng vì quá rộng, dễ match mọi câu khen đẹp.
- `STYLE_NEW`: chưa dùng vì "mới" là trạng thái/cơ sở vật chất, không hẳn style.
- `STYLE_EUROPEAN_JAPANESE`: chưa dùng vì gộp 2 style khác nhau và evidence chưa đủ sạch.

---

## Limitation con lai

1. **Review evidence chưa bao phủ 520/520 hotel**
   - Có 502 evidence file.
   - Một số hotel không có raw review hoặc review không đủ text dài để chạy.
   - Object vẫn tồn tại đủ 520 nhờ seed/HARD metadata.

2. **Profile chưa mang ontology version rõ ràng**
   - Object có version/provenance.
   - Nên thêm version vào `hotel_profiles.json` để biết khi nào cần reprocess.

3. **Location concept id đã vào semantic metadata**
   - `semantic_metadata.location` đã có `LOC_*` cho 520/520 hotel.
   - Query/relation có thể dùng concept id; raw `location` text/toạ độ vẫn giữ để hiển thị.

4. **Generated JSON lớn**
   - `knowledge_objects.json` và evidence đủ dùng demo.
   - Production nên chuyển JSONL hoặc ingest database.

5. **Query expansion chưa có golden-set verification**
   - Các cạnh expansion/co-occurrence cần đo bằng query thật trước khi bật mạnh.

6. **Embedding tầng 2 chưa bật**
   - Khi bật cần negation veto xuyên tầng và calibrate threshold theo facet.

---

## Done criteria Sprint 2

Sprint 2 được coi là xong khi:

- HARD object 520 hotel build được và validate pass.
- Review evidence được sinh cho corpus hiện có.
- Style discovery có luồng candidate -> approve -> promote -> backfill.
- `hotel_profiles.json` và `knowledge_objects.json` rebuild sau enrichment.
- `negative_style_profile` được expose riêng để giải thích/avoid style bị chê.
- Concept nhiễu rõ ràng như `STYLE_FAMILY_FRIENDLY` không còn trong ontology/output.
- Có handover mô tả luồng chạy lại và limitation.

Các tiêu chí trên hiện đã đạt.
