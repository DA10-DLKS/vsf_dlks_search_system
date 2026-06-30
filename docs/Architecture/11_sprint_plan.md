# 11 – Kế hoạch Sprint

## Nguyên tắc: dựng "bộ khung biết đi" (walking skeleton) trước
Xây dựng luồng giá trị đầu-cuối trước khi tối ưu bất kỳ khâu nào:

```
crawl → làm sạch → chunk → embed → lập chỉ mục → truy xuất hybrid → rerank → dựng ngữ cảnh → Context API
```

## Các sprint (bản nháp)
- **Sprint 1** – Crawler + thu nạp (làm sạch/khử trùng lặp) trên một tập dữ liệu nhỏ
- **Sprint 2** – Chunking + embedding + lập chỉ mục (vector + BM25)
- **Sprint 3** – Truy xuất hybrid + re-ranking cơ bản
- **Sprint 4** – Xây dựng ngữ cảnh + trích dẫn + Context API
- **Sprint 5** – Bộ đánh giá (Recall@K, NDCG, RAGAS) + observability
- **Sprint 6** – Củng cố (hardening), Docker, tài liệu

> TODO: phân công người phụ trách và mốc thời gian.
