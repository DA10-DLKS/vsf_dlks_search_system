# 05 – Kỹ thuật tri thức & Lập chỉ mục (Layer 3-4)

## Layer 3 – `knowledge_engineering/`

| Module | Thư mục | Mô tả |
|---|---|---|
| **chunking/** | `knowledge_engineering/chunking/` | Chia chunk theo ngữ nghĩa (strategies.py, preprocess.py) |
| **metadata_extraction/** | `knowledge_engineering/metadata_extraction/` | Trích xuất metadata từ hotel data |
| **entity_extraction/** | `knowledge_engineering/entity_extraction/` | Trích xuất thực thể (amenities, concepts) |
| **enrichment/** | `knowledge_engineering/enrichment/` | Phân loại taxonomy, làm giàu thuộc tính, knowledge objects |
| **governance/** | `knowledge_engineering/governance/` | Data lineage, versioning, audit |
| **common/** | `knowledge_engineering/common/` | Shared utilities (ke_labels, hotel_data) |

## Layer 3 – `ontology/`

| File | Mô tả |
|---|---|
| `ontology.yaml` | Core ontology definitions |
| `synonym_dictionary.yaml` | Từ điển từ đồng nghĩa |
| `query_expansion.yaml` | Quy tắc mở rộng truy vấn |
| `facets.yaml` | Facet definitions |
| `source_tag_map.yaml` | Map source tags → KE concepts |
| `candidate/` | Candidate hotel concepts |
| `core/` | Core domain concepts |
| `relations/` | Entity relations |

## Layer 4 – `indexing/`

| Module | Thư mục | Backend | Mô tả |
|---|---|---|---|
| **embedding/** | `indexing/embedding/` | bge-m3 | Sinh embedding vectors |
| **vector_index/** | `indexing/vector_index/` | Qdrant | Vector similarity search |
| **bm25_index/** | `indexing/bm25_index/` | OpenSearch | Full-text BM25 search |
| **metadata_index/** | `indexing/metadata_index/` | PostgreSQL | Metadata filtering |

## Đầu ra
Các chỉ mục tri thức có thể tìm kiếm được:
- **Qdrant**: vector embeddings (bge-m3 model, 1024 dimensions)
- **OpenSearch**: BM25 inverted index (hotel chunks)
- **PostgreSQL**: structured metadata (hotels, rooms, nearby_places, activities)
