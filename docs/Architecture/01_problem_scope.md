# 01 – Bài toán & Phạm vi

## DA10 là gì
Là **Nền tảng Tri thức & Truy xuất** (Knowledge & Retrieval Platform): một lớp tái sử dụng được,
có nhiệm vụ thu nạp tri thức du lịch, làm giàu & lập chỉ mục, rồi cung cấp khả năng truy xuất
thông qua các **API Search / Context / Knowledge**.

## Ranh giới với DA09 (rất quan trọng)

| Hạng mục | Đơn vị phụ trách |
|---|---|
| Crawl, làm sạch, chunk, embed, lập chỉ mục | **DA10** |
| Truy xuất (lexical/vector/hybrid), re-ranking | **DA10** |
| Xây dựng ngữ cảnh (context), trích dẫn (citations) | **DA10** |
| API Search/Context/Knowledge | **DA10** |
| Nhận diện ý định (intent parsing) | **DA10** (Node 1 pipeline) |
| Hội thoại, gợi ý, xếp hạng cuối cho người dùng | DA09 |
| Giao diện tìm kiếm / chat / product cards | DA09 |

- DA09 **KHÔNG** truy cập trực tiếp nguồn dữ liệu — luôn gọi qua API của DA10.
- DA10 **KHÔNG** xây dựng giao diện người dùng hay tầng trí tuệ (intelligence) ngoài intent parsing.

## Ngoài phạm vi
- Frontend / giao diện tìm kiếm (DA09 có `frontend/` riêng)
- Hội thoại & quản lý session
- Gợi ý (recommendation) & xếp hạng hướng người dùng

## Trong phạm vi (repo này)
- **Pipeline Node 1→9**: intent → filter → candidate → BM25+vector → fusion → rerank → context → LLM answer
- **API endpoints**: `/search`, `/hybrid_search`, `/hotel/{id}/ask`, `/context`, `/eval/golden`
- **Observability**: Prometheus metrics, JSON logging, deep health probe
