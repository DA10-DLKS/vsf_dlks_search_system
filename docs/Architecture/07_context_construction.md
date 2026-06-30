# 07 – Xây dựng Ngữ cảnh (Layer 7)

Đây là layer đặc trưng nhất của DA10 — biến các tài liệu đã xếp hạng thành **gói ngữ cảnh sẵn sàng cho LLM**.

## Cấu trúc thư mục

```
context/
├── context_package.py    Node 7C-8: ContextPackage contract + build_prompt
├── answer_generator.py   Node 9: LLM answer generation
├── selection/            Chunk selection (stub)
├── aggregation/          Chunk aggregation (stub)
├── compression/          Token compression (stub)
├── ordering/             Context ordering (stub)
├── citation_builder/     Citation building (stub)
└── token_budget/         Token budget management (stub)
```

## Modules hiện tại

### `context_package.py` (Node 7C → 8)

Định nghĩa `ContextPackage` — gói ngữ cảnh chuẩn:

```python
@dataclass
class ContextChunk:
    chunk_id: str
    hotel_id: Any
    hotel_name: str | None
    text: str
    score: float
    citation_index: int
    source_type: str | None = None
    metadata: dict[str, Any]

@dataclass
class ContextPackage:
    query: str
    chunks: list[ContextChunk]
    metadata: dict[str, Any]
```

**Functions:**
- `build_context_package(query, ranked_hotels)` → ContextPackage
- `build_context_string(pkg, max_chunks=5)` → formatted context string
- `build_prompt(pkg, max_chunks=5)` → RAG prompt

### `answer_generator.py` (Node 9)

Sinh câu trả lời bằng LLM từ ContextPackage (optional, có thể tắt).

## Đầu ra

```json
{
  "result_id": "hotel_12345",
  "llm_context": "Câu trả lời từ LLM...",
  "citations": [
    {
      "id": "cit_12345",
      "source_document_id": "doc_12345",
      "label": "Hotel Name",
      "url": "...",
      "quote": "..."
    }
  ],
  "source_documents": [...],
  "context_chunks": [...],
  "evidence": {
    "positives": [...],
    "negatives": [...]
  }
}
```
