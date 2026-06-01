# 06 – Hạ tầng Truy xuất (Layer 6)

`retrieval/`:
- **query_processing/** – chuẩn hóa, rewrite (sửa chính tả), mở rộng từ đồng nghĩa & ontology
  (LƯU Ý: đây là khâu chuẩn bị truy vấn *phía truy xuất*, không phải hiểu ý định của DA09)
- **lexical_search/** – BM25
- **vector_search/** – tìm kiếm ngữ nghĩa / dense
- **hybrid_search/** – hợp nhất điểm số (score fusion), Reciprocal Rank Fusion (RRF)
- **filtering/** – lọc theo metadata, lọc theo nghiệp vụ
- **reranking/** – re-rank bằng cross-encoder, tăng điểm theo metadata/độ mới (freshness)

Đầu ra: danh sách tài liệu ứng viên đã xếp hạng.
