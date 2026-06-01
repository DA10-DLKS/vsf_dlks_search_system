# 02 – Kiến trúc

Repo này ánh xạ 1-1 với sơ đồ các layer của DA10.

```
L1 Nguồn dữ liệu      data/ , crawler/
L2 Thu nạp dữ liệu    ingestion/
L3 Kỹ thuật tri thức  knowledge_engineering/ , ontology/
L4 Lập chỉ mục        indexing/
L6 Truy xuất          retrieval/
L7 Xây dựng ngữ cảnh  context/
L8 Dịch vụ nền tảng   api/
Xuyên suốt            observability/ , evaluation/
```

## Luồng dữ liệu

```
crawler/ ──▶ ingestion/ ──▶ knowledge_engineering/ ──▶ indexing/
                                                          │
                                                          ▼
api/ ◀── context/ ◀── retrieval/ ◀───────────── (chỉ mục vector + BM25)
```

## Hợp đồng đầu ra
`api/` trả về **Gói ngữ cảnh sẵn sàng cho LLM** (LLM-Ready Context Package):
`{ context, citations, sources, metadata }`.

> TODO: dán hình sơ đồ DA10 vào và chú thích mỗi khối ứng với thư mục nào.
