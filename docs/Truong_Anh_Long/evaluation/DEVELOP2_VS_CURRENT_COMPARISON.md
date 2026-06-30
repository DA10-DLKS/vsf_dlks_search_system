# Đánh giá so sánh: `develop-2` vs. project hiện tại (`fix/retrieval-quality-v1-v17`)

> Ngày: 2026-06-18
> Phạm vi: chỉ đọc code nhánh `develop-2` (bỏ qua các file dữ liệu: `data/`, `.docker_volumes/`, `*.json/jsonl/csv/parquet/db`, ảnh).
> Mục tiêu: chỉ ra khác biệt code, đánh giá ưu/nhược điểm mỗi bên, và xét độ khả thi merge.

---

## 0. Phát hiện cốt lõi (đọc trước)

`develop-2` **không phải** là một nhánh phát triển tiếp nối project hiện tại. Cả hai cùng rẽ
ra từ commit gốc `5f6fa3b ("initial")` và đi theo hai hướng **gần như độc lập**:

```
                          ┌── (24+ commit Sprint/ontology/ABSA/LMK) ──► HEAD hiện tại
5f6fa3b "initial" ────────┤
                          └── 4 commit ──► develop-2  (e1562c6, 732e382 "Add hotel knowledge platform")
```

- `git merge-base develop-2 HEAD` = `git merge-base develop-2 main` = **`5f6fa3b`** → chia sẻ rất ít lịch sử chung.
- `develop-2` chỉ có **4 commit**; toàn bộ giá trị nằm trong 2 commit cuối thêm thư mục **`hotel-knowledge-platform/`**.

`develop-2` thực chất chứa **HAI codebase**:

| Vị trí | Trạng thái | Nội dung |
|--------|-----------|----------|
| **Root** (`api/`, `retrieval/`, `context/`, `ontology/`, `ingestion/`...) | **Skeleton rỗng** | Hầu hết chỉ có `__init__.py` + `README.md`. `api/main.py` toàn `TODO`. Đây gần như là bộ khung walking-skeleton ban đầu, **chưa implement**. |
| **`hotel-knowledge-platform/`** (196 file) | **Re-platform hoàn chỉnh** | Backend FastAPI thật + PostgreSQL + Neo4j + Elasticsearch + ONNX reranker + ContextPackage + frontend Next.js 16. **Đây là phần đáng so sánh.** |

→ Khi nói "code của develop-2", thực chất là nói tới **`hotel-knowledge-platform/`**.

---

## 1. So sánh kiến trúc

| Khía cạnh | Project hiện tại (HEAD) | `develop-2` → `hotel-knowledge-platform/` |
|-----------|------------------------|-------------------------------------------|
| **Tổ chức** | Layer theo thư mục (L1–L8: crawler/ingestion/KE/indexing/retrieval/context/api), code thật rải khắp | Một backend app gói gọn (`app/api`, `app/core`, `app/retrieval`, `app/services`, `app/data_pipeline`) + frontend riêng |
| **Lưu trữ vector** | pgvector / Qdrant | pgvector (PostgreSQL) |
| **Lexical/BM25** | BM25 nội bộ | **Elasticsearch** (index có versioning + alias + asciifolding) |
| **Graph** | **Không có Neo4j** — `fusion.py` ghi rõ *"repo không có Neo4j" → thay `graph_boost` bằng `profile_boost` (semantic_profile của KE)* | **Neo4j thật**: nested Cypher, graph constraints, graph reasoning routing, citation evidence |
| **Fusion** | RRF + profile_boost; **đang vướng bug thang lệch ~24×** (xem memory `retrieval-signal-dropped-ranking`) khiến FULL ≈ NO-SERVICE | **`calibrated_rrf_fusion`**: min-max chuẩn hóa text-signal + graph-signal về [0,1] rồi `text_weight*text + graph_weight*graph` (bounded, explainable) |
| **Reranker** | neural_rerank (cross-encoder) | LocalReranker + **ONNX BGE reranker** export sẵn |
| **Query intent** | intent_parser + implicit_intent (regex RULES) | `query_intent.py`: classify route, infer requires_graph_reasoning, parse graph constraints, parse intent |
| **API** | SearchAPI/Context được wire (commit gần đây) | SearchAPI + ContextAPI thật (routes/search.py, routes/context.py), `search_id` TTL reuse, pagination, score breakdown, OpenAPI drift test |
| **ContextPackage** | context/ builder | First-class: diverse chunk selection, char/token budget, evidence + citation IDs, missing-constraints, compression provenance |
| **Frontend** | `frontend/` (đã có trong HEAD) | **Next.js 16 + React 19 + shadcn + Tailwind 4** (stack mới hơn) |
| **Observability** | observability/ | JSON request logs, request/search IDs, readiness metadata, rate limiting, node trace |
| **Benchmark/Eval** | golden_set_v1.json, evaluation dashboard | Nhiều benchmark golden-set (v1, v4 graph_lift, v4 streamlit_architecture), ablation runner, eval report tự sinh |

---

## 2. So sánh chiều sâu Knowledge Engineering (điểm mạnh của HEAD)

Đây là nơi HEAD **vượt trội rõ rệt** so với develop-2:

| Tính năng KE | HEAD | develop-2 |
|--------------|------|-----------|
| ABSA (aspect-based sentiment) | ✅ `absa.py`, merge pos/neg, Wilson, backfill | ❌ chỉ có `enrichment/__init__.py` rỗng ở root; platform có `generate_hotel_styles.py` nhưng nông hơn |
| Style mining + recall đo bằng golden | ✅ `absa-style-recall-golden` | ❌ |
| Candidate mining / discovery (LLM + embedding cluster) | ✅ `candidate_mining.py`, `discovery_cluster.py`, `discovery_suggest.py` | ❌ |
| Relation review flow (pattern STYLE, candidates.yaml) | ✅ `relation_loader.py`, apply_relation_review | một phần qua `enrich_graph.py` (cách khác) |
| Landmark / LMK gazetteer + recall fixes | ✅ build_locations/relations/synonym/objects 4 bước, nearby_landmarks | platform có graph nhưng không có pipeline LMK chi tiết như HEAD |
| Ontology Sprint 1/2 (Core/Candidate tiers, fact_type) | ✅ thiết kế chi tiết | `ontology/travel_ontology.yaml` + synonyms + query_expansion (đơn giản hơn) |
| Golden dataset KE groundtruth | ✅ groundtruth thật từ clean data | golden_set có nhưng khác phương pháp |

---

## 3. Ưu / Nhược điểm

### 3.1 Project hiện tại (HEAD)

**Ưu điểm**
- Chiều sâu **Knowledge Engineering** vượt trội: ABSA, style, candidate mining, relation review, LMK gazetteer, ontology Sprint — đây là phần khó và tốn công nhất, khó tái tạo.
- Lịch sử phát triển dày (24+ commit), nhiều bài học đã ghi nhận trong memory.
- Golden dataset + groundtruth thật, đo recall nghiêm túc.
- Cấu trúc layer 1-1 với sơ đồ DA10, dễ truy vết trách nhiệm.

**Nhược điểm**
- **Không có Neo4j** → reasoning theo quan hệ (nearby, constraint multi-hop) bị thay bằng `profile_boost` yếu hơn.
- **Bug fusion thang lệch ~24×** chưa fix triệt để (FULL ≈ NO-SERVICE, recall ~0.52) — đúng vấn đề mà develop-2 đã giải.
- BM25 nội bộ, không tận dụng Elasticsearch (versioning/alias/analyzer).
- SearchAPI/ContextAPI mới được wire gần đây, chưa "production-grade" như develop-2 (thiếu search_id TTL, OpenAPI drift test, score breakdown chuẩn).

### 3.2 `develop-2` (`hotel-knowledge-platform/`)

**Ưu điểm**
- **Kiến trúc retrieval/runtime chín hơn**: calibrated fusion bounded, ONNX reranker, ES + pgvector + Neo4j, graph reasoning routing, candidate set bounded (100–300).
- **Đã giải đúng bài toán fusion calibration** mà HEAD đang vướng (`calibrated_rrf_fusion` min-max → weighted).
- **ContextPackage first-class** (evidence, citation IDs, token budget, provenance) — sát yêu cầu Context API cho DA09.
- SearchAPI/ContextAPI thật + observability + readiness + rate limiting.
- Frontend stack mới (Next.js 16 / React 19 / shadcn).
- `hotel-search-context-upgrade-plan.md` ghi rõ 8 task, tiến độ, target architecture (mermaid) — tài liệu thiết kế tốt.

**Nhược điểm**
- **KE/ABSA/ontology nông hơn nhiều** — thiếu toàn bộ style mining, candidate discovery, LMK pipeline, relation review của HEAD.
- Code root của develop-2 là **skeleton rỗng** → dễ gây nhầm; giá trị tập trung một thư mục.
- Phụ thuộc hạ tầng nặng hơn: **cần Neo4j + Elasticsearch** chạy thật (vận hành phức tạp hơn).
- Một số phần tự nhận "architecture complete, full-model proof pending" (BGE smoke bị chặn bởi RAM/pagefile Windows) — chưa chứng minh đầy đủ bằng full model.
- Lịch sử commit mỏng (4 commit), nhiều file `scratch_*.py` / `test.py` lẫn vào.

---

## 4. Độ khả thi merge

### 4.1 Mức độ khó: **CAO** (đây là merge hai dự án, không phải merge một feature branch)

Lý do:
1. **Merge-base = commit "initial"** → `git merge HEAD develop-2` sẽ tạo lượng conflict khổng lồ và **vô nghĩa** ở các file chung (chủ yếu là `__init__.py` rỗng vs. code thật, README khác hẳn). Diff thô: **282 file thay đổi, ~3.7k thêm / ~76k xóa** — phần lớn "xóa" chỉ vì develop-2 không có code KE của HEAD.
2. Hai bên dùng **mô hình hạ tầng khác nhau** (HEAD: không Neo4j; develop-2: bắt buộc Neo4j + ES). Không thể "trộn file".
3. Tổ chức code khác paradigm: HEAD layer-per-folder rải toàn repo; develop-2 gói trong `hotel-knowledge-platform/backend/app`.

→ **Không nên `git merge` trực tiếp.** Đó sẽ là thảm họa conflict.

### 4.2 Chiến lược khả thi (khuyến nghị): **Port có chọn lọc, không merge git**

Giữ HEAD làm **nền** (vì KE là tài sản khó tái tạo nhất), port các thành phần runtime đã chín của develop-2 vào:

| Ưu tiên | Port từ develop-2 sang HEAD | Lý do | Công sức |
|---------|------------------------------|-------|----------|
| **P0** | `calibrated_rrf_fusion` (min-max chuẩn hóa text+graph) | Fix trực tiếp bug thang lệch ~24× của HEAD | Thấp (1 file, logic thuần) |
| **P0** | Bounded candidate set + graph-reasoning routing logic | Giảm gọi graph thừa, kiểm soát latency | Thấp–Trung |
| **P1** | ContextPackage first-class (evidence/citation/token budget/provenance) | Chuẩn hóa Context API cho DA09 | Trung |
| **P1** | ONNX BGE reranker export/run | Reranker nhanh hơn, deterministic | Trung |
| **P2** | Elasticsearch BM25 (versioned index + alias + asciifolding) | Nếu muốn thay BM25 nội bộ | Cao (đổi hạ tầng) |
| **P2** | Neo4j graph reasoning | Chỉ khi quyết định đưa Neo4j vào hạ tầng | Cao (đổi hạ tầng + ETL) |
| **P3** | Frontend Next.js 16 của develop-2 | Nếu muốn nâng cấp UI | Trung (so với `frontend/` hiện có) |

**KHÔNG port ngược** KE/ABSA/ontology của HEAD sang develop-2 — quá tốn công và HEAD đã là bản tốt nhất.

### 4.3 Quy trình đề xuất

1. **Không merge nhánh.** Thay vào đó tạo nhánh tích hợp từ HEAD (vd. `feature/port-dev2-runtime`).
2. Bắt đầu từ **P0 (calibrated fusion)** — đây là quick win sửa đúng bug đã biết; viết test so recall trước/sau trên golden set hiện có.
3. Cherry-pick **logic** (copy file/đoạn), không cherry-pick commit của develop-2 (vì lịch sử lệch).
4. Quyết định hạ tầng (Neo4j/ES) ở mức **dự án** trước khi đụng P2 — đây là quyết định vận hành, không chỉ kỹ thuật.
5. Đối chiếu `intrusment/*.md` và `hotel-search-context-upgrade-plan.md` của develop-2 như **tài liệu thiết kế tham khảo** (rất chi tiết) cho phần Context/Search API.

### 4.4 Rủi ro cần lưu ý
- develop-2 chưa chứng minh full-model (BGE smoke bị chặn RAM Windows) → khi port phải tự benchmark lại trên data thật của HEAD.
- Đưa Neo4j/ES vào làm tăng độ phức tạp vận hành (Docker compose nặng hơn, ETL graph) — cân nhắc ROI so với `profile_boost` hiện tại.
- Schema chunk/metadata hai bên khác nhau (develop-2 từng có bug `hotel_id` top-level vs `metadata.hotel_id`) → phải map schema cẩn thận khi port.

---

## 5. Kết luận

- `develop-2` là một **re-platform song song độc lập**, mạnh ở **runtime retrieval/context** (calibrated fusion, Neo4j graph, ES, ONNX reranker, ContextPackage) nhưng **yếu ở Knowledge Engineering**.
- Project hiện tại (HEAD) **mạnh ở KE/ontology/ABSA** (tài sản khó tái tạo) nhưng **yếu ở runtime** (không Neo4j, bug fusion).
- **Hai bên bù trừ cho nhau gần như hoàn hảo.** Nhưng vì chia nhánh từ commit gốc, **merge git trực tiếp là không khả thi/không nên**.
- **Khuyến nghị: giữ HEAD làm nền, port có chọn lọc** các thành phần runtime của develop-2 — bắt đầu bằng `calibrated_rrf_fusion` để sửa ngay bug thang lệch ~24×, rồi ContextPackage và reranker; cân nhắc Neo4j/ES ở mức quyết định hạ tầng.
