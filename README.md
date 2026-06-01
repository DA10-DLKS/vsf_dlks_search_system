# VSF DLKS – Nền tảng Tri thức & Truy xuất DA10

> **Phạm vi: chỉ DA10.** Dự án này xây dựng **Lớp Tri thức & Truy xuất** (Knowledge & Retrieval Layer)
> có nhiệm vụ thu nạp dữ liệu du lịch, làm giàu & lập chỉ mục, rồi cung cấp các dịch vụ truy xuất
> tái sử dụng được (**Search / Context / Knowledge API**) cho DA09 và các hệ thống AI khác sử dụng.
>
> DA10 là lớp **duy nhất** được phép truy cập kho tri thức (knowledge repositories).
> DA10 **không** xây dựng giao diện tìm kiếm, hiểu ý định, hội thoại, gợi ý,
> hay xếp hạng cho người dùng cuối — những phần đó thuộc về DA09.

## Kiến trúc (ánh xạ 1-1 với sơ đồ DA10)

| Layer | Thư mục | Trách nhiệm |
|-------|---------|-------------|
| L1 Nguồn tri thức | `data/`, `crawler/` | Crawl dữ liệu du lịch thật từ web (khách sạn/resort/villa/điểm tham quan...) |
| L2 Thu nạp & Xử lý dữ liệu | `ingestion/` | Connector, kiểm định, làm sạch, khử trùng lặp |
| L3 Kỹ thuật tri thức | `knowledge_engineering/`, `ontology/` | Chunking, trích xuất metadata/thực thể, làm giàu, quản trị |
| L4 Embedding & Lập chỉ mục | `indexing/` | Embedding + chỉ mục vector / BM25 / metadata |
| L6 Hạ tầng Truy xuất | `retrieval/` | Xử lý truy vấn, tìm kiếm lexical/vector/hybrid, lọc, re-ranking |
| L7 Xây dựng Ngữ cảnh | `context/` | Chọn lọc, gộp, nén, sắp xếp, trích dẫn, ngân sách token |
| L8 Dịch vụ Nền tảng | `api/` | Search API, Context API, Knowledge API |
| Xuyên suốt | `observability/`, `evaluation/` | Log, tracing, metrics, quản trị, đánh giá truy xuất & RAG |

> Lưu ý về cách đánh số layer: chúng ta giữ nhãn L6/L7/L8 của sơ đồ để dễ truy vết.
> Repo này không có thư mục L5 riêng — phần hiểu truy vấn/ý định (DA09 L4)
> nằm ngoài phạm vi một cách có chủ đích.

## Luồng giá trị cốt lõi (bộ khung "biết đi" – walking skeleton)

```
crawl → làm sạch → chunk → embed → lập chỉ mục → truy xuất hybrid → rerank → dựng ngữ cảnh + trích dẫn → Context API
```

Hãy làm cho luồng đầu-cuối này chạy được trước (dù còn đơn giản), rồi mới tối ưu từng khâu.

## Đầu ra: Gói ngữ cảnh sẵn sàng cho LLM

Context API trả về:

```json
{ "context": "...", "citations": [...], "sources": [...], "metadata": {...} }
```

## Bắt đầu

```bash
cp .env.example .env        # điền các giá trị bí mật
pip install -r requirements.txt
docker compose up -d        # Qdrant + OpenSearch
```

Xem [`docs/`](docs/) để biết tài liệu thiết kế đầy đủ.
