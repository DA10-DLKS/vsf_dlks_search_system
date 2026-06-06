# Báo cáo Sprint 1 — Đỗ Minh Hiếu

> Thời gian: 06/2026
> Vai trò: Data Quality Engineer (Layer 2 — Data Pipeline)

## Mục tiêu Sprint 1

Xây dựng pipeline thu nạp dữ liệu cơ bản: **Clean → Dedup → Validate → Export** trên tập dữ liệu nhỏ (~20 hotels).

## Công việc đã làm

### 1. Cleaning Pipeline

| Module | File | Mô tả |
|---|---|---|
| Text Normalizer | `ingestion/cleaning/text_normalizer.py` | Unicode NFC, emoji removal, whitespace collapse, normalize punctuation |
| HTML Stripper | `ingestion/cleaning/html_stripper.py` | BeautifulSoup strip HTML + extract image_urls, links |
| Amenity Normalizer | `ingestion/cleaning/amenity_normalizer.py` | 6-step pipeline: strip bracket → clean → canonical prefix → fuzzy merge (0.80) → filter basic (41 items) → filter generic |
| Translator | `ingestion/cleaning/translator.py` | `deep-translator` Google engine, auto-detect VI, cache, chỉ dịch review |
| Clean Orchestrator | `scripts/clean_pipeline.py` | Apply tất cả module cleaning lên hotel JSON, ghi ra `data/cleaned/` |

### 2. Deduplication

| Module | File | Mô tả |
|---|---|---|
| MinHash LSH | `ingestion/deduplication/minhash.py` | `datasketch` — 128 permutations, Jaccard ≥ 0.85, 5-gram character |
| Dedup Pipeline | `scripts/dedup_pipeline.py` | Đọc cleaned → LSH query → exact verify → ghi đè + `data/dedup_groups.json` |

### 3. Validation

| Module | File | Mô tả |
|---|---|---|
| Schema Validator | `ingestion/validation/schema_validator.py` | Kiểm tra required fields, numeric range, format, alias hotel_id ↔ id |
| Quality Checks | `ingestion/validation/quality_checks.py` | Missing Rate (< 5%) + Duplicate Rate (< 2%) |
| Validation Pipeline | `scripts/validation_pipeline.py` | Orchestrate validation, quarantine invalid docs to `data/quarantine/` |

### 4. Export (DuckDB)

| Module | File | Mô tả |
|---|---|---|
| DuckDB Export | `scripts/export_duckdb.py` | Export cleaned JSON → DuckDB (`data/da10.duckdb`) |

### 5. Công việc khác

- Xây dựng `contracts/data_schema.json` — schema chuẩn cho DA09-DA10 integration
- Viết `docs/cleaning_rules.md`, `docs/validation_rules.md`, `docs/data_quality_report.md`
- Viết `docs/04_ingestion.md` — pipeline documentation đầy đủ
- Script `scripts/build_amenity_freq.py` + `docs/amenity_frequency.tsv` — thống kê tần suất amenities

## Kết quả

| Metric | Giá trị | Target |
|---|---|---|
| Total documents | ~20 hotels | – |
| Missing rate | < 3% | < 5% ✅ |
| Duplicate rate | 0% | < 2% ✅ |
| Validation errors | 0 | 0 ✅ |
| Amenity reduction | ~167 → ~81 (giảm ~50%) | Giảm nhiễu |

## Khó khăn

- **Amenity noise**: Dữ liệu gốc có rất nhiều biến thể (VD: `"WiFi"`, `"Wi-Fi"`, `"Wifi"`, `"WiFi miễn phí"`, `"Internet WiFi"`). Giải pháp: canonical prefix mapping + fuzzy merge threshold 0.80.
- **DuckDB không phù hợp real-time**: Bị mentor yêu cầu chuyển sang PostgreSQL ở Sprint 2.
- **Agoda không trả giá phòng**: Giá load dynamic bằng JavaScript → cần mock price ở Sprint 2.

## File liên quan

| File | Vai trò |
|---|---|
| `scripts/run_ingest.py` | Entry point pipeline |
| `scripts/clean_pipeline.py` | Cleaning orchestrator |
| `scripts/dedup_pipeline.py` | Dedup orchestrator |
| `scripts/validation_pipeline.py` | Validation orchestrator |
| `scripts/export_duckdb.py` | DuckDB export |
| `contracts/data_schema.json` | JSON schema contract |
