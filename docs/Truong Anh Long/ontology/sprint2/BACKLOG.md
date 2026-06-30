# KE Sprint 2 - BACKLOG / Handover checklist

> File ghi nhớ việc, để không quên. Cập nhật mỗi khi làm xong / phát sinh việc mới.
> Owner: Trương Anh Long. Cập nhật: 2026-06-12.

---

## Trạng thái chốt Sprint 2

**Sprint 2 phần ontology đã đạt mức hoàn thành để demo/bàn giao kỹ thuật.**

Đã có đủ pipeline từ ontology HARD, metadata, ABSA review evidence, discovery style, promote/backfill style,
profile builder tới `knowledge_objects.json`. Các nợ còn lại bên dưới là QC/production hardening, không chặn
việc bàn giao ontology Sprint 2.

Report chốt Step 5/6: `docs/reports/ontology/sprint2/step5_6_soft_enrichment_handover.md`.

---

## Da lam trong Sprint 2

| Bước | Sản phẩm | Trạng thái |
|---|---|---|
| 0 | Khảo sát data (`step0`) | xong |
| 1 | `source_tag_map.yaml` + audit `surface_forms` | xong |
| 1b | `implicit_intent.py` cho intent ngầm như "2 con" -> `PURPOSE_FAMILY` | xong |
| 2 | `ontology_mapper` tầng 0+1 HARD cho 520 hotel | xong |
| 3 | `metadata_pipeline` reconcile luxury/price/range metadata | xong |
| 4 | `build_objects` phần HARD, 520 object | xong |
| 4b | Gắn `LOC_*` concept_id vào `semantic_metadata.location` | xong |
| 5.0 | `llm.py` đa-provider + cache/safe/resume | xong |
| 5.1 | `absa.py` batch runner: `--all`, `--max-hotels`, `--limit`, `--budget-usd`, `--dry-run`, `--backfill` | xong |
| 5.2 | `profile_builder` seed aspect từ Agoda grades + merge review evidence | xong |
| 5.3 | ABSA per-review chạy corpus hiện tại, sinh 502 file `review_evidence` | xong |
| 5.4 | `raw_discovery.jsonl` cho novel style từ review | xong |
| 5.5 | `discovery_cluster.py` + `discovery_suggest.py` + `candidate_concepts.yaml` | xong |
| 5.6 | Human review/promote style mới qua `promote_candidate.py` | xong |
| 5.7 | Backfill style đã duyệt: `STYLE_BOUTIQUE`, `STYLE_MINIMALIST`, `STYLE_VINTAGE` | xong |
| 5.8 | Loại `STYLE_FAMILY_FRIENDLY` khỏi evidence/profile/object/ontology vì nhiễu | xong |
| 5.9 | `negative_style_profile` từ evidence negative sẵn có, không gọi LLM lại | xong |
| 6 | Rebuild `hotel_profiles.json` và `knowledge_objects.json` sau ABSA/backfill/negative profile | xong |
| - | Query demo trả thêm hotel id để tiện test | xong |
| - | Pytest regression cho normalize/synonym, mapper HARD, ABSA backfill | xong |
| - | Query expansion tự sinh từ related/co-occurrence/lift | xong |
| - | Fix dedup tỉnh trùng, suy setting từ location/source tags | xong |

---

## Artifact hiện có

| Artifact | Ý nghĩa | Trạng thái |
|---|---|---|
| `knowledge_engineering/enrichment/review_evidence/*.json` | Evidence ABSA theo từng review/hotel | 502 file |
| `knowledge_engineering/enrichment/raw_discovery.jsonl` | Novel style phrase thô từ review | 1696 dòng |
| `knowledge_engineering/enrichment/clusters.json` | Cluster phrase discovery | có |
| `ontology/candidate/candidate_concepts.yaml` | Candidate concept để người duyệt | có |
| `ontology/candidate/promote_log.yaml` | Log concept đã promote | có |
| `knowledge_engineering/enrichment/hotel_profiles.json` | Profile tổng hợp seed + ABSA | 520 hotel |
| `knowledge_engineering/enrichment/knowledge_objects.json` | Knowledge object cuối cho search/demo | 520 object |
| `ontology/synonym_dictionary.yaml` | Surface form index sinh từ ontology core | 1838 surface form |
| `negative_style_profile` trong profile/object | Negative evidence riêng cho `STYLE_*` | 139 hotel |
| `semantic_metadata.location` trong object | `LOC_*` concept_id cụ thể nhất resolve từ city/area | 520/520 hotel |

Ghi chú coverage mới nhất sau `profile_builder`:

| Concept | Số hotel có profile |
|---|---:|
| `STYLE_QUIET` | 390 |
| `STYLE_RELAXING` | 82 |
| `STYLE_LUXURY` | 66 |
| `STYLE_MODERN` | 37 |
| `STYLE_BOUTIQUE` | 9 |
| `STYLE_VINTAGE` | 1 |
| `STYLE_MINIMALIST` | 1 |

---

## Viec con lai - QC / Sprint sau

Các mục này không chặn chốt Sprint 2, nhưng nên đưa sang Sprint 3/4 hoặc technical debt.

1. **Spot-check style mới trước demo rộng**
   - Kiểm vài hotel có `STYLE_BOUTIQUE`, `STYLE_MINIMALIST`, `STYLE_VINTAGE`.
   - Đảm bảo span/evidence đúng nghĩa, không phải text marketing nhiễu.

2. **Verify query expansion trên golden set**
   - Một số cạnh expansion/co-occurrence vẫn là `unverified`.
   - Cần 20-30 query golden để đo Recall/Precision trước khi dùng mạnh trong search.

3. **Mở rộng test tự động**
   - Đã có regression test cơ bản cho normalize/synonym, mapper HARD, ABSA backfill.
   - Nên mở rộng thêm pytest cho query expansion, location hierarchy, profile aggregation và end-to-end build object.

4. **JSONL/DB production output**
   - `knowledge_objects.json` một file lớn đủ dùng demo/seed.
   - Production nên chuyển JSONL hoặc ingest DB/vector index.

5. **QC location generated**
   - Location generated cần kiểm alias/hierarchy như "Nha Trang" vs "Tp. Nha Trang".
   - Không chặn demo vì city/area hiển thị vẫn dùng được.

6. **Đơn vị giá và giá capped**
   - `price_min` hiện theo VND/đêm, nhưng cần DA09 xác nhận slot-filling/query cùng đơn vị.
   - 47 object có `price_capped: true`; query giá nên xử lý mềm với nhóm này.

7. **Embedding tầng 2**
   - Chưa bật embedding tagger.
   - Khi bật cần negation veto xuyên tầng và calibrate threshold theo facet.

---

## Phu thuoc ngoai

- **Model embedding** do team search/vector chốt -> mở khóa tầng 2 ontology mapper.
- **Giá thật/data quality** -> quyết định độ tin cậy filter giá.
- **Hạ tầng production** -> JSON hiện là seed/demo, không phải storage cuối cùng.

---

## Ghi chu van hanh

- Đổi prompt SYSTEM hoặc đổi ontology vocab sẽ làm `effective_prompt_version` đổi, có thể cần chạy lại ABSA/backfill.
- `profile_builder` vẫn dùng aspect seed từ Agoda grades làm nguồn điểm ổn định; ABSA bổ sung span/evidence/style.
- Concept style mới chỉ nên backfill sau khi surface form đã được người duyệt bó hẹp.
- Không nên backfill concept quá rộng như `STYLE_FAMILY_FRIENDLY`, `STYLE_AESTHETIC`, `STYLE_NEW` nếu chưa có QC rất kỹ.
