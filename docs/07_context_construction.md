# 07 – Xây dựng Ngữ cảnh (Layer 7)

Đây là layer đặc trưng nhất của DA10 — biến các tài liệu đã xếp hạng thành **gói ngữ cảnh sẵn sàng cho LLM**.

`context/`:
- **selection/** – chọn các chunk nào sẽ đưa vào
- **aggregation/** – gộp các chunk liên quan
- **compression/** – nén để vừa với ngân sách token
- **ordering/** – sắp xếp ngữ cảnh + sắp xếp bằng chứng (evidence)
- **citation_builder/** – dựng trích dẫn nguồn
- **token_budget/** – trình quản lý ngân sách token

Đầu ra:
```json
{ "context": "...", "citations": [...], "sources": [...], "metadata": {...} }
```
