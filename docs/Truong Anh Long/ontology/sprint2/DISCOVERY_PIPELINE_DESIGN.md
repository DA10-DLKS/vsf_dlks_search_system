# Thiết kế: Pipeline phát hiện STYLE/concept mới từ review (Discovery)

> Owner: Trương Anh Long (KE, DA10). Soạn 2026-06-11. Cập nhật chi tiết-để-code 2026-06-11.
> **Mục đích tài liệu:** bản thiết kế đủ chi tiết để CODE THẲNG (chữ ký hàm + schema file + ngưỡng),
> tiếp tục ở SESSION MỚI mà không mất ngữ cảnh.
> Đọc file này + [BACKLOG.md](BACKLOG.md) là nắm được phải làm gì, theo thứ tự nào, vì sao.

> **MỤC TIÊU PHIÊN NÀY (chốt với chủ dự án 2026-06-11):** XONG TOÀN BỘ CODE 3 tầng + sửa
> promote TRƯỚC. ABSA 504 hotel (~$1.15 — ĐO THẬT, xem §4) CHỈ chạy SAU KHI code xong — để lần chạy thật đầu tiên
> đã có sẵn `novel`/discovery, KHÔNG phải trả tiền lại lần hai. Đây là ràng buộc cứng về thứ tự.

---

## 0. Bối cảnh & quyết định gốc rễ (đọc trước)

**Mục tiêu sản phẩm (không phải đồ án):** đọc review khách sạn → (a) gán STYLE/ASPECT đã định nghĩa
cho từng hotel, (b) **tự phát hiện STYLE mới** chưa có trong ontology để mở rộng. Đây là sản phẩm
công ty, hướng tới production.

**Hiểu biết gốc rễ đã chốt (sau khi phân tích + demo thật 2026-06-11):**
- Việc (a) "gán style định sẵn" = ABSA — **khả thi cao, chuẩn ngành, ĐÃ XONG** (`absa.py`).
- Việc (b) "phát hiện style mới" — **khả thi NHƯNG KHÔNG bằng đếm n-gram.** Cách n-gram hiện tại
  (`candidate_mining.py`) yếu: ra mảnh vụn ("tho lo", "cu ky"), gộp đại đồng nghĩa, lẫn sentiment
  (vd "cổ điển" hóa ra phần lớn là CHÊ phòng cũ, không phải khen phong cách).
- **Cách đúng (production thật):** discovery = TRỢ LÝ ĐỀ XUẤT cho người, KHÔNG phải máy tự ghi vào
  taxonomy. Các công ty lớn (Booking/Agoda/Airbnb) KHÔNG để thuật toán tự đẻ concept vào taxonomy;
  họ dùng NLP/LLM SINH ĐỀ XUẤT, con người (taxonomist) quyết. Mắt xích "người duyệt" là PHÁN ĐOÁN
  (tên concept, gộp/tách, có đáng không), không phải bấm "approved".
- Nguyên tắc giải mâu thuẫn "không sửa tay": **máy đề xuất đầy đủ (LLM sinh concept_id + label
  vi/en + description + cảnh báo), người duyệt/sửa nhẹ rồi gật. Người KHÔNG gõ YAML từ số 0.**

**Vì sao cách cũ (n-gram) phải thay:** xem [candidate-mining-design] trong memory + lịch sử demo.
Tóm: đếm chữ không hiểu nghĩa → 3 lỗi (mảnh vụn / gộp sai / sentiment lẫn). LLM+embedding giải cả 3.

---

## 0.5 QUYẾT ĐỊNH ĐÃ CHỐT (đọc trước khi code — tránh phải hỏi lại)

| # | Quyết định | Chốt là |
|---|---|---|
| Q1 | Tầng 3 ghi đâu / promote đọc đâu | **File MỚI `ontology/candidate/candidate_concepts.yaml`** (block đầy đủ vi/en/desc). promote đọc file này khi `status: approved`, ghi THẲNG core, KHÔNG sinh sườn. `candidate_queue.yaml` giữ nguyên cho nguồn keyword/n-gram cũ. Tách bạch 2 nguồn. |
| Q2 | Thuật toán clustering Tầng 2 | **Union-find theo ngưỡng cosine** (tự viết, mặc định `--threshold 0.70`). KHÔNG dùng sklearn. Deterministic, dễ giải thích cho người duyệt. **0.70 (không phải 0.80) — đo THẬT bge-m3 2026-06-11:** nhóm đồng nghĩa VN "cổ điển/cổ kính/hoài cổ/retro" chỉ ~0.69–0.75, 0.80 sẽ tách vụn; 0.70 gom đúng mà vẫn tách "hiện đại" (0.61). |
| Q3 | Bump prompt version khi thêm `novel`? | **CÓ — bump `PROMPT_VERSION_BASE` v3→v4 ngay.** Có 17 hotel evidence cũ ở `v2-multilang` (5416 review) — bump v4 khiến chúng stale, chạy lại để đồng version + có novel (~$0.6, đã nằm trong dự toán). Cache `complete_json` băm cả system prompt nên prompt v4 (có novel) = cache miss = gọi API thật, KHÔNG ăn cache v2 thiếu novel. |

---

## 1. Kiến trúc đích (pipeline 3 tầng thay cho n-gram)

```
ABSA (ĐÃ CÓ)              gán STYLE/ASPECT định sẵn + sentiment        [chạy thường xuyên]
   │  ↘ (+1 field `novel` trong CÙNG prompt — đi kèm, ít token output thêm)
   │   TẦNG 1 DISCOVERY EXTRACTOR
   │     LLM trích "style/đặc trưng LẠ" (ngoài danh sách đã biết) + diễn giải + sentiment
   │     → ghi raw_discovery.jsonl  {hotel_id, review_id, phrase, gloss, sentiment, span, prompt_version}
   ↓
TẦNG 2 CLUSTERING (embedding bge-m3, union-find cosine)
   gom phrase lạ đồng nghĩa thành CLUSTER ("cổ điển"+"cổ kính"+"hoài cổ" → 1 cluster;
   "retro" có thể tách nếu vector xa) → giải bài toán gộp/tách bằng vector, không đoán tay
   → clusters.json  {cluster_id, members[], hotel_count, freq, sentiment_dist, examples[]}
   ↓
TẦNG 3 SUMMARIZER (LLM, 1 call/cluster)
   mỗi cluster → LLM sinh ĐỀ XUẤT concept ĐẦY ĐỦ:
     concept_id, label{vi,en}, surface_forms{vi,en}, description{vi,en}, facet,
     + CẢNH BÁO: "70% negative → có thể là than phiền, không phải style"
                 "gần STYLE_MODERN đã có → cân nhắc trùng"
   → candidate_concepts.yaml  (đề xuất đầy đủ, status: pending)
   ↓
NGƯỜI DUYỆT  xem đề xuất + cảnh báo → sửa nhẹ / gộp / bỏ → status: approved
   ↓
promote_candidate.py --apply --source concepts (SỬA) → ghi core ĐẦY ĐỦ + build synonym
   ↓
absa.py --backfill CONCEPT (ĐÃ CÓ) → gán concept mới HỒI TỐ cho hotel cũ (khoanh bằng synonym)
   ↓
profile_builder + build_objects (ĐÃ CÓ) → concept mới vào hotel_profiles + knowledge_objects
```

---

## 2. Hiện trạng từng mảnh (đã đối chiếu code 2026-06-11)

| Mảnh | Trạng thái | Việc cần làm |
|---|---|---|
| ABSA gán style định sẵn | ✅ xong, test pass | (chạy thật 504 hotel — SAU khi code xong, ~$1.15 đo thật) |
| ABSA vocab đọc từ ontology | ✅ xong (`load_vocab`, `build_system_prompt`) | — |
| `absa.py --backfill` hồi tố | ✅ xong, **đã chạy thật OK** (demo 3 hotel) | — (khoanh bằng synonym, không phụ thuộc queue) |
| resume theo prompt_version | ✅ xong (`effective_prompt_version` = base+hash(vocab)) | — |
| LLM đa-provider | ✅ `complete_json(system,user,temperature,use_cache)`; cache theo hash(system+user) | ✅ MAX_TOKENS 800→1200 (đã nâng) |
| Embedding model | ✅ `from indexing.embedding.registry import get_embedding_model`; `get_embedding_model("bge-m3")`; `offline=True`→HashEmbeddingModel | dùng qua registry, KHÔNG sửa code Khánh Duy |
| `promote_candidate.py` ghi core | ✅ **ĐÃ THÊM `--source concepts`** đọc candidate_concepts.yaml đầy đủ, validate `en!=vi`, strip metadata, ghi thẳng core | test dry-run OK (SKIP đúng ca en==vi) |
| TẦNG 1 discovery extractor | ✅ **XONG** — `absa.py` (v4 + field `novel` + raw_discovery.jsonl ghi dưới lock) | test import + novel OK |
| TẦNG 2 clustering | ✅ **XONG** — `discovery_cluster.py` (union-find cosine, numpy V@V.T, dedupe) | smoke offline OK (dedupe + gom + neg_ratio đúng) |
| TẦNG 3 summarizer | ✅ **XONG** — `discovery_suggest.py` (LLM sinh đầy đủ, validate chặn rác, merge giữ approved) | smoke mock-LLM OK |
| `candidate_mining.py` (n-gram) | ⚠️ còn đó, đã cải thiện | GIỮ làm fallback/đối chiếu, KHÔNG phải đường chính nữa |

**Sự thật code đã xác minh (đừng giả định lại):**
- `EmbeddingModel.embed(texts) -> list[EmbeddingResult]`; mỗi result có `.vector: list[float]`,
  `.dimension`. bge-m3 đã `normalize_embeddings=True` → vector đã chuẩn L2 → **cosine = dot product**.
- `HashEmbeddingModel` = **vector NGẪU NHIÊN theo hash, dim=32** → KHÔNG mang ngữ nghĩa. Smoke test
  `offline=True` chỉ kiểm pipeline chạy không vỡ; **KHÔNG verify được gộp/tách** (xem cạm bẫy).
- `complete_json` cache key = `sha256(provider|model|system|user)` → **đổi system prompt = vô hiệu
  toàn bộ cache cũ.**
- normalize: `normalize(t, fold=True)` bỏ dấu + tách từ; `strip_diacritics` riêng. dùng cho chuẩn hóa phrase.
- Concept schema (ontology/_meta.yaml): required = `[facet, fact_type, tier, label, description]`;
  prefix ID theo facet: `STYLE_/AMEN_/PURPOSE_/SETTING_/...`; style/purpose/aspect = `fact_type: soft`.

---

## 3. Thiết kế chi tiết từng bước CẦN XÂY

### 3.1 — TẦNG 1: Discovery Extractor (sửa `absa.py`)

**File:** sửa `knowledge_engineering/enrichment/absa.py`.

#### 3.1.a — Bump prompt version (Q3) — LÀM ĐẦU TIÊN
```python
PROMPT_VERSION_BASE = "v4-ontology-vocab-discovery"   # v3 -> v4: thêm field novel
```
Hệ quả: `effective_prompt_version` đổi → mọi evidence demo cũ (v3) bị coi stale → chạy lại. CHẤP NHẬN
(chỉ có demo 3 hotel, chưa có corpus thật). KHÔNG cần xóa evidence cũ tay.

#### 3.1.b — Thêm mục `novel` vào SYSTEM prompt
Trong `build_system_prompt(vocab)`, sau phần aspect/style, THÊM đoạn (giữ nguyên phần cũ):
```
Ngoài các aspect/style ĐÃ LIỆT KÊ ở trên, nếu review nhắc tới một PHONG CÁCH / ĐẶC TRƯNG NỔI BẬT
KHÁC mà danh sách trên KHÔNG có, liệt kê ở field "novel". Mỗi mục:
  {"phrase": cụm tiếng Việt CHUẨN (dịch sang VN nếu review ngoại ngữ), "gloss": diễn giải ngắn,
   "sentiment": positive|negative|neutral|mixed, "span": trích nguyên văn}.
KHÔNG bịa. KHÔNG lặp lại concept đã có ở trên. Không có gì lạ -> "novel": [].
```
Và đổi khối JSON mẫu cuối prompt thành:
```json
{"overall_sentiment":"...","items":[...],"novel":[{"phrase":"...","gloss":"...","sentiment":"...","span":"..."}]}
```

#### 3.1.c — Parse + lọc `novel` trong `analyze_review`
- `analyze_review` hiện trả `{overall_sentiment, items}`. THÊM key `novel`:
  ```python
  novel = []
  for it in out.get("novel", []) or []:
      if not isinstance(it, dict): continue
      ph = (it.get("phrase") or "").strip()
      if not ph: continue
      novel.append({"phrase": ph[:80],
                    "gloss": (it.get("gloss") or "")[:160],
                    "sentiment": it.get("sentiment", "neutral"),
                    "span": (it.get("span") or "")[:200]})
  return {"overall_sentiment": ..., "items": items, "novel": novel}
  ```
- Lọc nhẹ: bỏ phrase mà sau `normalize(ph, fold=True)` rơi vào `mapped_forms` (đã là concept rồi) —
  TÙY CHỌN, có thể để Tầng 2/3 lo. Mặc định KHÔNG lọc ở đây (giữ raw thật, lọc ở sau).

#### 3.1.d — Ghi `raw_discovery.jsonl` (AN TOÀN ĐA LUỒNG)
- **CẠM BẪY:** `analyze_hotel` chạy `ThreadPoolExecutor` 12 luồng. TUYỆT ĐỐI không `open(...,"a")`
  thô từ nhiều thread (xen dòng/hỏng). Ghi DƯỚI `lock` đã có trong vòng `as_completed`.
- Chốt cách ghi: trong khối `with lock:` của `analyze_hotel`, sau khi set `store[rid]`, nếu
  `res["novel"]` không rỗng thì append vào MỘT list buffer `discovery_rows` (trong RAM), rồi
  trong `finally` (cùng chỗ `_save_evidence`) gọi `_append_discovery(discovery_rows)` 1 lần/hotel.
  → tránh ghi file trong vùng nóng đa luồng, vẫn không mất khi lỗi giữa chừng (flush ở finally).
- Hàm mới:
  ```python
  DISCOVERY_JSONL = Path("knowledge_engineering/enrichment/raw_discovery.jsonl")
  _DISCOVERY_LOCK = threading.Lock()   # nếu sau này chạy nhiều hotel song song

  def _append_discovery(rows: list[dict]) -> None:
      """Append list dòng discovery vào jsonl (1 phát hiện/dòng). Gọi 1 lần/hotel ở finally."""
      if not rows: return
      DISCOVERY_JSONL.parent.mkdir(parents=True, exist_ok=True)
      with _DISCOVERY_LOCK, open(DISCOVERY_JSONL, "a", encoding="utf-8") as fh:
          for r in rows:
              fh.write(json.dumps(r, ensure_ascii=False) + "\n")
  ```
- Mỗi dòng: `{hotel_id, review_id, phrase, gloss, sentiment, span, prompt_version, created_at}`.
- **DEDUPE chạy lại:** nếu chạy lại (resume), review đã xử lý cùng version sẽ bị skip ở `todo` →
  KHÔNG sinh lại dòng discovery → jsonl không phình trùng. NHƯNG nếu xóa evidence rồi chạy lại,
  jsonl sẽ có trùng. → Tầng 2 PHẢI dedupe theo (review_id, phrase) khi đọc (đã tính, xem §3.2).
  Khuyến nghị: KHÔNG cần xóa jsonl giữa chừng; nếu muốn chạy sạch thì xóa cả jsonl + evidence.

#### 3.1.e — Nâng MAX_TOKENS khi có discovery
- **CẠM BẪY:** `llm.py` cap `MAX_TOKENS=800`. Thêm `novel` (phrase+gloss+span) → output dài hơn,
  review giàu thông tin dễ chạm trần → JSON cụt → `_extract_json` raise → retry vô ích → tốn tiền.
- Chốt: nâng `MAX_TOKENS = 1200` trong `llm.py`. (ABSA JSON vẫn ngắn; 1200 dư an toàn, không lảm nhảm
  vì temperature=0 + prompt chặt.) Đây là sửa NHỎ, ảnh hưởng mọi call — chấp nhận, output ABSA bình
  thường < 400 token nên không tốn thêm thực tế (chỉ trả theo token THẬT sinh ra).

**Done Tầng 1 khi:** chạy `absa.py --hotel <id> --limit N` ra evidence CÓ key `novel` + sinh
`raw_discovery.jsonl` với dòng là khái niệm có nghĩa (không phải mảnh vụn). Test offline được bằng
LLM provider rẻ hoặc ollama; KHÔNG cần bge-m3 ở tầng này.

---

### 3.2 — TẦNG 2: Clustering (embedding bge-m3, union-find cosine)

**File mới:** `knowledge_engineering/enrichment/discovery_cluster.py`

#### Đọc & gom raw
- Đọc `raw_discovery.jsonl` từng dòng. **DEDUPE** theo `(review_id, normalize(phrase,fold=True))`
  để không đếm trùng khi jsonl có dòng lặp (xem §3.1.d).
- Gom theo `phrase_norm = normalize(phrase, fold=True)` (KHÓA gom) nhưng GIỮ 1 dạng hiển thị
  có dấu đẹp nhất (phrase gốc xuất hiện nhiều nhất) để show cho người.
- Mỗi phrase_norm tích lũy: `freq` (số phát hiện), `hotels: set`, `sentiment_dist: Counter`,
  `examples: list[span]` (giữ tối đa ~5), `display: str` (dạng có dấu).
- **LỌC NGƯỠNG VÀO (giảm nhiễu trước khi embed — embed tốn):** chỉ giữ phrase có
  `freq >= MIN_FREQ` (mặc định 3) VÀ `len(hotels) >= MIN_HOTELS` (mặc định 2). Phrase xuất hiện 1
  lần ở 1 hotel = nhiễu LLM, bỏ. (Đặt qua CLI `--min-freq`, `--min-hotels`.)

#### Embed
```python
from indexing.embedding.registry import get_embedding_model
model = get_embedding_model("bge-m3", offline=args.offline)
results = model.embed([p["display"] for p in phrases])   # batch sẵn trong model
vecs = [r.vector for r in results]   # đã L2-normalize (bge-m3) -> cosine = dot
```
- **CẠM BẪY (đã xác minh):** `offline=True` dùng HashEmbeddingModel = vector ngẫu nhiên → "cổ điển"
  và "cổ kính" KHÔNG gần nhau. → `--offline` CHỈ để smoke-test code chạy không lỗi, **KHÔNG dùng
  để chốt ngưỡng / nghiệm thu cụm**. Verify gộp/tách BẮT BUỘC chạy bge-m3 thật.
- **CẠM BẪY:** bge-m3 cần `sentence-transformers` (raise RuntimeError nếu chưa cài) + tải ~2GB lần
  đầu. KIỂM `pip show sentence-transformers` trong `.venv` trước khi chạy thật. Clustering chạy
  ĐỊNH KỲ/thủ công, không realtime.

#### Cluster bằng union-find cosine (Q2)
```python
# sim(i,j) = dot(vecs[i], vecs[j])  (vector đã chuẩn L2)
# parent[] union-find; với mọi cặp i<j: nếu sim >= threshold -> union(i,j)
# threshold mặc định 0.70 (CLI --threshold; đo thật bge-m3). N vài trăm-vài nghìn -> O(N^2) chấp nhận.
```
- Triển khai O(N²) đơn giản: 2 vòng for, không cần numpy (nhưng nếu numpy có sẵn thì
  `mat = V @ V.T` nhanh hơn — TÙY, ưu tiên thuần Python để khỏi thêm dep nếu numpy chưa chắc có).
- Gộp các phrase cùng root thành 1 cluster. Cluster cộng dồn freq, hotels (union set),
  sentiment_dist (cộng Counter), examples (gộp, cắt ~8).

#### Output `clusters.json`
```json
{"version":"1.0","threshold":0.70,"model":"bge-m3","n_phrases":NN,"n_clusters":MM,
 "clusters":[
   {"cluster_id":"c001",
    "members":["cổ điển","cổ kính","hoài cổ"],     // display có dấu, sort theo freq giảm
    "label_hint":"cổ điển",                          // member freq cao nhất (gợi ý cho Tầng 3)
    "hotel_count":42, "freq":118,
    "sentiment_dist":{"positive":30,"negative":70,"neutral":18,"mixed":0},
    "neg_ratio":0.59,                                // tiện cho cảnh báo Tầng 3
    "examples":["...span...","..."]}
 ]}
```
- Sort clusters theo `hotel_count` giảm dần (cluster phổ biến lên đầu cho người duyệt).
- **Output là derived → gitignore** (tái sinh bằng script). Thêm vào `.gitignore` nếu chưa có.

**Done Tầng 2 khi:** với bge-m3 THẬT, clusters.json gom đúng cụm đồng nghĩa (cổ điển/cổ kính/hoài
cổ chung 1 cluster), mỗi cluster có sentiment_dist + neg_ratio để Tầng 3 cảnh báo.

---

### 3.3 — TẦNG 3: Summarizer → đề xuất concept đầy đủ

**File mới:** `knowledge_engineering/enrichment/discovery_suggest.py`

#### Lọc cluster đáng đề xuất
- Đọc `clusters.json`. Chỉ xử lý cluster `hotel_count >= MIN_CLUSTER_HOTELS` (mặc định 3, CLI
  `--min-hotels`). Cluster 1-2 hotel = quá hiếm, bỏ (đỡ tốn LLM call).

#### Chuẩn bị "concept đã có" để cảnh báo trùng
- Đọc core qua glob `ontology/core/*.yaml` (dùng lại logic `load_vocab` tinh thần): với mỗi concept
  lấy `concept_id, facet, label.vi/en`. Tạo chuỗi đại diện `f"{label_vi} / {label_en}"` rồi embed
  1 lần (cùng model Tầng 2). Lưu `(concept_id, vec)`.
- Embed `label_hint` của cluster, so cosine với mọi concept core → nếu max sim >= `SIM_DUP` (mặc
  định 0.75) → cảnh báo `"⚠ gần {concept_id} (sim {x:.2f}) — cân nhắc trùng/gộp"`.

#### LLM sinh đề xuất (1 call/cluster)
- SYSTEM prompt yêu cầu trả JSON ĐẦY ĐỦ SONG NGỮ:
  ```
  Bạn là taxonomist khách sạn. Cho 1 nhóm cụm từ đồng nghĩa rút từ review (kèm sentiment + ví dụ),
  đề xuất 1 concept cho ontology. Trả JSON:
  {"concept_id":"<PREFIX>_<TÊN>",   // PREFIX theo facet: STYLE_/AMEN_/SETTING_/PURPOSE_, CHỮ HOA, không dấu
   "facet":"style|amenity|setting|purpose",
   "label":{"vi":"...","en":"..."},          // en PHẢI là tiếng Anh THẬT, KHÔNG để = vi
   "surface_forms":{"vi":[...],"en":[...]},   // gồm members + mở rộng hợp lý
   "description":{"vi":"...","en":"..."},
   "rationale":"vì sao nên là concept này"}
  KHÔNG để label.en trùng label.vi. surface_forms.en có ít nhất 1 từ tiếng Anh.
  ```
- USER: serialize cluster (members, sentiment_dist, neg_ratio, examples). dùng `complete_json`.
- **Cảnh báo tự động (script GẮN, không nhờ LLM):**
  - `neg_ratio >= NEG_WARN` (mặc định 0.6) → `"⚠ chủ yếu tiêu cực ({neg}%), có thể là than phiền
    (ASPECT) không phải STYLE — người duyệt cân nhắc đổi facet hoặc bỏ"`.
  - trùng concept core (mục trên) → cảnh báo sim.
- **VALIDATE output LLM trước khi ghi** (Tầng 3 phải chặn lỗi `en=vi` tận gốc):
  - `concept_id` khớp regex `^[A-Z]+_[A-Z0-9_]+$`; nếu không → log + skip cluster đó (KHÔNG ghi rác).
  - `label.en != label.vi` (so lower/strip); nếu trùng → đánh dấu `_warnings += "label.en chưa dịch"`.
  - đủ key `label/surface_forms/description` với cả vi+en; thiếu → skip + log.

#### Output `ontology/candidate/candidate_concepts.yaml`
```yaml
# candidate/candidate_concepts.yaml — ĐỀ XUẤT concept ĐẦY ĐỦ (Tầng 3 discovery). KHÁC
# candidate_queue.yaml (sườn keyword cũ): concept ở đây đã hoàn chỉnh vi/en/desc, người chỉ
# duyệt/sửa nhẹ rồi đặt status: approved. promote_candidate.py --source concepts đọc file này.
version: "1.0"
generated_at: "2026-..."
model: "..."
concepts:
  STYLE_VINTAGE:
    facet: style
    fact_type: soft            # script điền theo default_fact_type(facet) từ _meta.yaml
    tier: core                 # khi promote sẽ vào core
    provenance: [review, discovery_llm]
    label: {vi: Cổ điển, en: Vintage}
    surface_forms: {vi: [cổ điển, cổ kính, hoài cổ], en: [vintage, retro, classic]}
    description: {vi: ..., en: ...}
    # --- metadata discovery (promote sẽ LƯỢC khi ghi core) ---
    status: pending            # pending | approved | rejected  (NGƯỜI sửa)
    discovery:
      cluster_id: c001
      hotel_count: 42
      freq: 118
      sentiment_dist: {positive: 30, negative: 70, neutral: 18}
      neg_ratio: 0.59
      warnings: ["⚠ chủ yếu tiêu cực (59%)...", "⚠ gần STYLE_MODERN (sim 0.72)..."]
      members: [cổ điển, cổ kính, hoài cổ]
      examples: ["..."]
      rationale: "..."
```
- Nếu chạy lại Tầng 3: MERGE theo concept_id — concept đã `approved`/`rejected` thì GIỮ (không ghi
  đè quyết định của người); chỉ thêm/cập nhật concept còn `pending`.

**Done Tầng 3 khi:** mỗi đề xuất có en + description THẬT (KHÔNG còn `en: <tiếng việt>`), có
cảnh báo neg_ratio + trùng-core, file load được bằng yaml.safe_load.

---

### 3.4 — Sửa `promote_candidate.py` để đọc concept ĐẦY ĐỦ (Q1)

**Cách tiếp cận:** THÊM nguồn mới, KHÔNG phá nguồn cũ. CLI `--source {queue|concepts}` (mặc định
`queue` để giữ tương thích).

- Thêm hằng: `CONCEPTS = "ontology/candidate/candidate_concepts.yaml"`.
- Khi `--source concepts`:
  - đọc `CONCEPTS`; lặp `concepts` có `status == "approved"`.
  - block ghi core = LẤY THẲNG từ file (đã đầy đủ), chỉ **STRIP metadata discovery**: bỏ key
    `status` và `discovery` trước khi ghi vào core (core không chứa metadata duyệt).
  - **KHÔNG gọi `build_concept_block`** (hàm sinh sườn) cho nhánh này — concept đã đủ.
  - VALIDATE trước khi ghi (tái dùng kiểm của Tầng 3): required `[facet, fact_type, tier, label,
    description]`; `label.en != label.vi`; có surface_forms. Thiếu → skip + báo (KHÔNG ghi rác core).
  - idempotent như cũ: concept_id đã có trong core → SKIP.
  - phần SAU GIỮ NGUYÊN: `append_concepts_to_core`, `append_promote_log`, build synonym, in lệnh
    `absa.py --backfill <ids> --yes`.
- Nhánh `--source queue` (cũ) giữ y nguyên: vẫn `build_concept_block` sinh sườn cho candidate_queue.
- **Bug path đã sửa trong phiên trước:** `load_facet_files` thêm prefix `ontology/` — KIỂM lại khi
  dùng thật với nhánh concepts (cùng dùng `facet_files` để map facet→file). Backfill khoanh hotel
  bằng SYNONYM (đã chạy thật OK) — không phụ thuộc queue/concepts.

**Done §3.4 khi:** `promote_candidate.py --source concepts --dry-run` in block core đầy đủ (en thật)
từ candidate_concepts.yaml approved; `--apply` ghi core + build synonym + in lệnh backfill.

---

## 4. Thứ tự THỰC HIỆN CODE (phiên này — TẤT CẢ trước khi chạy 504 hotel)

> Mục tiêu phiên: xong CODE. Bước "chạy ABSA 504 hotel" nằm NGOÀI phiên này, chỉ làm sau khi code xong.

1. ✅ **Tầng 1** — `absa.py` (bump v4 + novel + raw_discovery + lock), `llm.py` (MAX_TOKENS 1200). Test OK.
2. ✅ **Tầng 2** — `discovery_cluster.py` (union-find cosine, threshold 0.70). bge-m3 đã có sẵn trong
   venv (sentence-transformers 5.5.1 + BAAI/bge-m3 2.29GB cached) — verify thật OK (xem ghi chú dưới).
3. ✅ **Tầng 3** — `discovery_suggest.py`. Smoke mock-LLM OK (SKIP đúng ca en==vi/id sai).
4. ✅ **§3.4** — `promote_candidate.py --source concepts`. Test dry-run OK.
5. ✅ **.gitignore** — đã thêm `raw_discovery.jsonl`, `clusters.json`.
6. **(NGOÀI phiên) chủ dự án chạy:**
   ```powershell
   .venv\Scripts\python.exe -X utf8 -m knowledge_engineering.enrichment.absa --all --limit 20 --budget-usd 3
   ```
   (vừa gán style, vừa thu raw_discovery) → Tầng 2 → Tầng 3 → người duyệt → promote --source concepts
   → backfill → profile_builder + build_objects.

**CHI PHÍ THẬT (đo bằng `--dry-run` 2026-06-11, KHÔNG phải $13 phỏng đoán cũ):**

| Phần | Chi phí | Ghi chú |
|---|---|---|
| ABSA 504 hotel (9701 review todo, gpt-4o-mini, limit 20) | **~$1.15** | gồm ~$0.6 chạy lại 17 hotel v2→v4 |
| Tầng 2 clustering (bge-m3) | **$0** | local, model đã cached |
| Tầng 3 summarizer | **vài cent** | 1 call/cluster, ít cluster |
| Backfill hotel cũ | **vài cent** | chỉ hỏi concept mới, khoanh hotel nhắc tới |
| **Tổng full luồng** | **≈ $1.2–1.5** | |

> Phanh chi phí: `--dry-run` (chỉ dự toán), `--budget-usd N` (dừng cứng), prompt gõ `yes` trước khi
> gọi API. KHÔNG cần xóa 17 hotel evidence cũ — resume-theo-version tự đánh stale & ghi đè an toàn.

---

## 5. Ràng buộc & cạm bẫy (ĐÃ ĐỐI CHIẾU CODE — đừng quên)

- **THỨ TỰ LÀ RÀNG BUỘC CỨNG:** phải bump v4 + thêm novel TRƯỚC khi chạy 504 hotel. Vì đổi system
  prompt = vô hiệu cache `complete_json` + đổi `effective_prompt_version` = chạy lại all. Nếu chạy
  504 hotel rồi mới thêm novel → trả LẦN HAI (~$1.15 nữa). (Đây là lý do cả phiên này dồn vào code trước.)
- **MAX_TOKENS=800 → nâng 1200** trong llm.py, nếu không novel làm JSON cụt → retry vô ích → tốn tiền.
- **Ghi raw_discovery.jsonl PHẢI dưới lock** (ABSA 12 thread). Cách chốt: buffer trong RAM, flush
  1 lần/hotel ở `finally` (§3.1.d).
- **offline=True (HashEmbeddingModel) = vector ngẫu nhiên dim 32** → CHỈ smoke-test pipeline,
  KHÔNG verify gộp/tách. Nghiệm thu cụm BẮT BUỘC bge-m3 thật (cần `sentence-transformers` + ~2GB).
- **KHÔNG để LLM tự ghi ontology.** LLM chỉ đề xuất (candidate_concepts.yaml, status: pending);
  người duyệt; `promote_candidate.py` mới ghi core. Mô hình Core/Candidate.
- **Concept phải song ngữ đầy đủ.** Lỗi `en: <tiếng việt>` ở demo cũ KHÔNG chấp nhận — Tầng 3 + promote
  đều VALIDATE `label.en != label.vi` và skip (không ghi rác) nếu thiếu.
- **Sentiment-gate:** cluster chủ yếu negative (neg_ratio>=0.6) → cảnh báo, có thể KHÔNG phải style
  (vd "cổ điển" = chê cũ). Người duyệt quyết.
- **KHÔNG sửa code `indexing/embedding/`** (của Khánh Duy) — chỉ import qua registry.
- **candidate_mining.py (n-gram) GIỮ lại** làm đối chiếu/fallback, không xóa, không phải đường chính.
- **Mọi output (raw_discovery.jsonl, clusters.json) là derived → gitignore**, tái sinh bằng script.
  candidate_concepts.yaml thì COMMIT (chứa quyết định duyệt của người).

---

## 6. Trạng thái sạch khi chốt phiên 2026-06-11 (giữ nguyên — tham chiếu)

- 2 concept demo lỗi (STYLE_VINTAGE, AMEN_CABLE_CAR) ĐÃ XÓA khỏi core + synonym + candidate_queue
  + promote_log + 220 evidence backfill. Ontology về sạch trước demo.
- Code đã sửa và GIỮ: absa.py (vocab ontology + backfill + resume-version), candidate_mining.py
  (sample_comments + TF-IDF + lọc địa danh/1-từ + cache), promote_candidate.py (path fix).
- candidate_mining.py đã chạy ra candidate_queue.json (1641 candidate) — n-gram, để đối chiếu.
