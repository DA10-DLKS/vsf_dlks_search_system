# Hướng dẫn End-to-End: từ con số 0 đến ontology + search

> Dành cho người **chưa biết gì** về dự án. Giả định: bạn chưa có khách sạn nào, chưa có review nào.
> Tài liệu chỉ rõ chạy script nào, theo thứ tự nào, ra file gì, để cuối cùng có ontology tự sinh từ data
> và search thử được.
>
> Mọi lệnh chạy từ thư mục gốc `vsf_dlks_search_system/`. Windows dùng `.venv\Scripts\python.exe`,
> macOS/Linux dùng `.venv/bin/python`. Thêm `-X utf8` để in tiếng Việt không lỗi.

---

## 0. Bức tranh tổng — 4 chặng

```
CHẶNG 1  CRAWL    : lấy data khách sạn + review từ web   -> data/raw/
CHẶNG 2  CLEAN    : làm sạch HTML/text                    -> data/cleaned/
CHẶNG 3  ENRICH   : gắn nhãn concept + profile cảm nhận   -> knowledge_objects.json
CHẶNG 4  ONTOLOGY : tự sinh quan hệ/expansion từ data     -> query_expansion.yaml + search
```

Mỗi chặng ăn output của chặng trước. **Không nhảy cóc.** Nếu thiếu data ở chặng trước, chặng sau ra rỗng.

---

## CHẶNG 1 — CRAWL (lấy data về)

Mục tiêu: có file JSON cho mỗi khách sạn + file review cho từng khách sạn, trong `data/raw/`.

### 1.1. Crawl thông tin khách sạn
Entry point là `crawler.main` (KHÔNG phải `scripts/run_crawl.py` — file đó chưa làm xong).

```bash
# Cách A — crawl 1 khách sạn từ link Agoda:
.venv/Scripts/python.exe -m crawler.main "https://www.agoda.com/.../hotel.html?hotel=65153&..."

# Cách B — crawl hàng loạt theo từ khóa:
.venv/Scripts/python.exe -m crawler.main "Vinpearl"
.venv/Scripts/python.exe -m crawler.main "Muong Thanh" --limit 5
```
→ Ghi ra `data/raw/hotels/hotel_<id>_<slug>.json`.

### 1.2. Kiểm tra crawl thiếu sót, recrawl cái thiếu
Crawl quy mô lớn luôn có % lỗi ngẫu nhiên. Thay vì crawl lại cả lượt, chỉ recrawl cái thiếu:

```bash
.venv/Scripts/python.exe -m crawler.validate    # quét data/raw/hotels/, ghi recrawl_queue.json
.venv/Scripts/python.exe -m crawler.main --recrawl   # crawl lại đúng những cái thiếu
```

### 1.3. Crawl REVIEW chi tiết cho từng khách sạn
Bước 1.1 chỉ lấy ~10 review mẫu. Để có ontology giàu (đặc biệt style/aspect từ cảm nhận), cần nhiều review:

```bash
# tất cả khách sạn đã crawl (bỏ qua cái đã có review):
.venv/Scripts/python.exe scripts/run_crawl_reviews.py --all

# 1 khách sạn theo id:
.venv/Scripts/python.exe scripts/run_crawl_reviews.py --id 1973
```
→ Ghi ra `data/raw/reviews/hotel_<id>_reviews.json` (mặc định ~250 review/khách sạn).

**Kết thúc Chặng 1:** `data/raw/hotels/*.json` + `data/raw/reviews/*.json`.

---

## CHẶNG 2 — CLEAN (làm sạch)

Mục tiêu: bỏ HTML, chuẩn hóa text, đưa data thô về dạng sạch cho enrichment đọc.

```bash
.venv/Scripts/python.exe scripts/clean_pipeline.py
```
→ Đọc `data/raw/*.json` (cả hotels lẫn reviews) → ghi `data/cleaned/hotel_*.json`.

> (Tùy dự án có thể có thêm bước lọc hotel nước ngoài / dedup — xem `scripts/remove_foreign_hotels.py`,
> `scripts/dedup_pipeline.py` nếu cần. Với corpus VN chuẩn thì `clean_pipeline` là đủ để đi tiếp.)

**Kết thúc Chặng 2:** `data/cleaned/hotel_*.json` — đây là nguồn cho mọi thứ phía sau.

---

## CHẶNG 3 — ENRICHMENT (biến data sạch thành knowledge_object)

Đây là chặng "gắn nhãn": mỗi khách sạn được gắn các **concept** (tiện ích, loại hình, mục đích...)
và **profile cảm nhận** (điểm style/aspect từ review).

> ⚠ **THỨ TỰ RẤT QUAN TRỌNG** — các script ăn output của nhau. Chạy ĐÚNG dãy 7 lệnh dưới, từ trên
> xuống. (Đây là dãy rebuild đầy đủ đã dùng thực tế.)

```bash
# 1. location ontology (LOC_* phân cấp country>province>city>area) — sinh từ data, không gõ tay
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_locations

# 2. synonym (surface form -> concept_id), gồm cả LOC_* vừa sinh
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index

# 3. tag HARD: gắn concept có/không cho mỗi hotel (dùng synonym ở bước 2)
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.ontology_mapper

# 4. metadata: map location/giá/sao/điểm -> schema KE, suy price_tier
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.metadata_pipeline

# 5. setting theo location (biển/núi/đảo) — suy từ % hotel trong location
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_location_setting

# 6. profile SOFT: điểm cảm nhận từng hotel trên ASPECT_*/STYLE_* (từ review)
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder

# 7. GHÉP TẤT CẢ -> knowledge_objects.json (chạy CUỐI vì ăn output của 1-6)
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects
```

Output các bước:
| Bước | Script | Ghi ra |
|---|---|---|
| 1 | build_locations | `ontology/core/location.generated.yaml` (LOC_*) |
| 2 | build_synonym_index | `ontology/synonym_dictionary.yaml` |
| 3 | ontology_mapper | `hotel_tags.json` (concept có/không) |
| 4 | metadata_pipeline | `hotel_metadata.json` (location/giá/sao/price_tier) |
| 5 | build_location_setting | `ontology/core/location_setting.generated.yaml` |
| 6 | profile_builder | `hotel_profiles.json` (ASPECT_*/STYLE_* score) |
| 7 | build_objects | **`knowledge_objects.json`** ⭐ (trung tâm) |

**Kết thúc Chặng 3:** `knowledge_objects.json` — mỗi hotel có `semantic_metadata` (nhãn) +
`semantic_profile` (cảm nhận). Đây là nguồn của ontology relation (Chặng 4).

> **Vì sao thứ tự này:** synonym (2) cần location (1); tagger (3) cần synonym (2); build_objects (7)
> cần cả tag + metadata + setting + profile. Quên 1 bước -> hotel mất nhãn tương ứng ở knowledge_object.

---

## CHẶNG 3B — DISCOVERY STYLE mới qua ABSA (tùy chọn, cần LLM)

> Chặng này để **phát hiện STYLE/khái niệm MỚI** mà ontology chưa có, từ review thật bằng LLM. Bỏ qua
> nếu chỉ dùng concept sẵn có. ⚠ Tốn RPD/tiền (gọi LLM) — tính batch trước.

Ý tưởng: review nói "cổ kính, hoài cổ" mà ontology chưa có `STYLE_VINTAGE` → ABSA phát hiện cụm lạ →
embedding gom cụm → LLM đề xuất concept đầy đủ → **người duyệt** → ghi vào core → backfill cho hotel cũ.

> **`raw_discovery.jsonl` ở đâu ra?** Nó KHÔNG cần lệnh riêng — là **sản phẩm phụ của ABSA chính**.
> Khi bạn chạy `absa --all`/`--hotel` để phân tích review (Tầng 1), mỗi review LLM vừa trích
> aspect/sentiment **vừa** thu cụm phong cách/vibe LẠ (ngoài vocab) vào field `novel`, ghi tích lũy ra
> `knowledge_engineering/enrichment/raw_discovery.jsonl`. Nên muốn có discovery thì trước đó phải đã
> chạy ABSA trên review. Nếu file này đã có sẵn (từ lần chạy ABSA trước) thì vào thẳng bước 1 dưới.

```bash
# 0. (nếu chưa có raw_discovery.jsonl) chạy ABSA trên review để sinh field novel:
#    .venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --all   # ⚠ tốn LLM

# 1. (Tầng 2) gom cụm phrase đồng nghĩa bằng embedding bge-m3 (đọc raw_discovery.jsonl)
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_cluster

# 2. (Tầng 3) LLM đề xuất concept ĐẦY ĐỦ song ngữ -> candidate_concepts.yaml (status: pending)
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_suggest

# 3. NGƯỜI duyệt: mở ontology/candidate/candidate_concepts.yaml, sửa status pending -> approved | rejected

# 4. xem trước block concept sẽ ghi (KHÔNG ghi):
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --source concepts --dry-run

# 5. ghi thật vào ontology/core/*.yaml + tự build lại synonym:
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.promote_candidate --source concepts --apply

# 6. BACKFILL: gán concept mới cho HOTEL CŨ (hồi tố) — chạy ABSA backfill cho từng concept vừa thêm
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --backfill STYLE_XXX --yes

# 7-8. build lại profile + objects để concept mới vào knowledge_object:
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.profile_builder
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.build_objects

# 9. test thử:
.venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.query_demo "khách sạn yên tĩnh thư giãn ở Phú Quốc"
```

> Pattern duyệt giống hệt relation (Chặng 4) và STYLE: **sửa `status` trong YAML rồi chạy script apply**,
> không sửa code. Thay `STYLE_XXX` ở bước 6 bằng concept_id thật vừa approve.

---

## CHẶNG 4 — ONTOLOGY (tự sinh quan hệ + expansion từ data)

Giờ mới tới phần relation graph. Chặng này biến `knowledge_objects.json` thành quan hệ giữa các concept
(`related`), rồi thành `query_expansion.yaml` mà tầng search dùng.

### 4.1. Sinh synonym (nếu mới đổi ontology/location)
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
```
→ Từ `ontology/core/*.yaml` sinh `ontology/synonym_dictionary.yaml` (surface form -> concept).
Cần khi vừa thêm concept/location mới — nếu quên, query sẽ không nhận ra từ mới.

### 4.2. (Tùy chọn) Audit hiện trạng quan hệ + chụp baseline
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.audit_relations
```
→ `docs/reports/ontology/relation_audit.md`. Read-only, để biết đang có gì.

### 4.3. Máy đào quan hệ ứng viên từ data
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_relation_candidates
```
→ Đọc `knowledge_objects.json` (mặc định `--source=both`: gộp `semantic_metadata` + `semantic_profile`).
→ Ghi candidate vào `ontology/relations/candidates.yaml` với `status: pending`.
- Mỗi cạnh có `provenance` (metadata|profile|metadata+profile) cho biết tín hiệu đến từ đâu.
- LMK/LOC bị loại (quan hệ vị trí, không phải quan hệ khái niệm).

### 4.4. NGƯỜI duyệt candidate ⭐ (việc tay duy nhất)
Mở `ontology/relations/candidates.yaml`. Mỗi cạnh đang `status: pending`. Sửa NGAY tại chỗ:
```yaml
- source: OBJ_RESORT
  target: AMEN_WATERSPORT
  lift: 3.11
  status: pending      # ← đổi thành: approved (đồng ý) | rejected (từ chối)
  reject_reason: "..." # ← chỉ thêm dòng này khi rejected (bắt buộc)
```
Mẹo duyệt: cạnh `provenance: metadata+profile` (hai nguồn đồng thuận) đáng approve trước; `lift` cao =
quan hệ càng đặc trưng. Cạnh nào chưa chắc thì để `pending`, duyệt sau.

### 4.5. Áp quyết định duyệt
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.apply_relation_review
```
→ `approved` chuyển sang `ontology/relations/curated.yaml` (dùng được); `rejected` sang `rejected.yaml`;
`pending` giữ lại. **Không sửa code, chỉ sửa YAML ở 4.4.**

### 4.6. Compile ra artifact cho tầng search
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.build_expansion
```
→ Đọc relation đã duyệt (verified) → ghi **`ontology/query_expansion.yaml`** (file tầng search đọc).
**Bắt buộc** — nếu không chạy, quyết định duyệt chưa tới search.

### 4.7. Kiểm tra chất lượng (read-only)
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.relation_quality            # sức khỏe graph
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.evaluate_query_expansion --report  # hit/noise
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.governance.verify_relation_golden      # A/B boost
```

### 4.8. Test thử bằng câu hỏi thật
```bash
.venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.query_demo "resort cho gia đình ở Nha Trang"
```
→ In concept hiểu được, expansion boost (kèm trace từng cạnh), và danh sách khách sạn khớp.

---

## Bảng tra nhanh — chạy gì theo tình huống

| Tình huống | Chạy lại từ |
|---|---|
| **Lần đầu, từ con số 0** | Chặng 1 → 2 → 3 (dãy 7 lệnh) → 4 |
| **Thêm khách sạn mới** | 1.1 (crawl hotel) → 1.3 (review) → 2 (clean) → **toàn bộ Chặng 3 (7 lệnh)** → Chặng 4 (4.3→4.6) |
| **Chỉ thêm review cho hotel đã có** | 1.3 → 2 → Chặng 3 bước 6 (profile) → bước 7 (build_objects) → Chặng 4 (4.3→4.6) |
| **Phát hiện STYLE mới từ review** | Chặng 3B (discovery → duyệt → promote → backfill → profile → build_objects) |
| **Chỉ sửa/thêm relation bằng tay** | sửa `curated.yaml` → 4.6 (build_expansion) |
| **Duyệt candidate relation đang chờ** | 4.4 (sửa YAML) → 4.5 (apply) → 4.6 (build_expansion) |
| **Vừa thêm concept/location vào ontology** | Chặng 3 bước 2 (synonym) → bước 3 (tag lại) → ... → bước 7 → Chặng 4 |

---

## Sơ đồ luồng dữ liệu (1 hình)

```
[web] ──crawler.main / run_crawl_reviews──> data/raw/  ──clean_pipeline──> data/cleaned/
                                                                              │
  CHẶNG 3 (thứ tự bắt buộc, build_objects chạy cuối):                         │
   1 build_locations ─┐                                                       │
   2 build_synonym ───┤ (synonym cần location)                                │
   3 ontology_mapper ─┤──> hotel_tags.json        (tag cần synonym)           │
   4 metadata_pipeline ──> hotel_metadata.json                                │
   5 build_location_setting ──> location_setting.generated.yaml               │
   6 profile_builder ──> hotel_profiles.json      (cảm nhận từ review)        │
   7 build_objects  ◄── gộp 3+4+5+6 ──────────────────────────────────────────┘
                                         ▼
                              knowledge_objects.json  ◄── nguồn của relation graph
                                         │ build_relation_candidates (--source=both)
                                         ▼
                              candidates.yaml (pending)
                                         │  [NGƯỜI duyệt: pending->approved/rejected]
                                         │  apply_relation_review
                                         ▼
                      curated.yaml / rejected.yaml
                                         │ build_expansion
                                         ▼
                              query_expansion.yaml  ──> [tầng search]

  CHẶNG 3B (discovery STYLE mới, tùy chọn, cần LLM):
   absa --all (phân tích review) ─> field `novel` ─> raw_discovery.jsonl
     ─> discovery_cluster ─> clusters.json
     ─> discovery_suggest ─> candidate_concepts.yaml (pending)
     ─> [NGƯỜI duyệt] ─> promote_candidate --apply ─> ontology/core/*.yaml
     ─> absa --backfill ─> profile_builder ─> build_objects (concept mới vào knowledge_object)
```

---

## Ghi chú quan trọng

- **`query_expansion.yaml` là file SINH RA — không sửa tay để duyệt.** Muốn đổi quan hệ thì sửa
  `curated.yaml`/`candidates.yaml` rồi chạy lại `build_expansion`. Sửa tay sẽ bị ghi đè.
- **Việc tay của con người chỉ ở 2 chỗ, đều là sửa `status` trong YAML rồi chạy script apply:**
  (a) duyệt relation — `candidates.yaml` (Chặng 4); (b) duyệt concept STYLE mới —
  `candidate_concepts.yaml` (Chặng 3B). Cùng một pattern: `pending` → `approved`/`rejected` → chạy apply.
  Mọi bước khác chỉ là gõ lệnh.
- **Ontology "tự sinh từ data"** nghĩa là: máy đọc data rồi *đề xuất* (quan hệ / concept mới); con
  người *duyệt* (vì lift/support/cụm embedding là tương quan, không phải ngữ nghĩa — máy không tự
  biết cái nào hợp lý). Máy lọc phần rõ ràng, người quyết phần cần phán xét.
- Chi tiết thiết kế relation graph: `docs/reports/ontology/relation_graph_roadmap.md` và
  `ontology/relations/README.md`.
