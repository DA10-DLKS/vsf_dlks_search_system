# 05 – Kỹ thuật tri thức & Lập chỉ mục (Layer 3-4)

## Layer 3 – `knowledge_engineering/`
- **chunking/** – chia chunk theo ngữ nghĩa, chunk cha-con (parent-child)
- **metadata_extraction/** – trích xuất metadata
- **entity_extraction/** – trích xuất thực thể
- **enrichment/** – phân loại theo taxonomy, làm giàu thuộc tính
- **governance/** – truy vết nguồn gốc dữ liệu (data lineage), quản lý phiên bản, metadata kiểm toán

Kèm theo `ontology/`: ontology du lịch, từ điển từ đồng nghĩa, từ điển mở rộng truy vấn.

## Layer 4 – `indexing/`
- **embedding/** – sinh embedding (OpenAI / BGE) + trình quản lý phiên bản embedding
- **vector_index/** – Qdrant
- **bm25_index/** – OpenSearch
- **metadata_index/** – chỉ mục metadata

Đầu ra: các chỉ mục tri thức có thể tìm kiếm được.
