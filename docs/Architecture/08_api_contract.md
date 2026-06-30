# 08 – Dịch vụ Nền tảng / Hợp đồng API (Layer 8)

`api/` cung cấp các dịch vụ truy xuất tái sử dụng được mà DA09 sẽ gọi.

## Search API
`POST /search` – tìm kiếm ngữ nghĩa / hybrid, truy xuất tài liệu.
Trả về danh sách tài liệu ứng viên đã xếp hạng.

## Context API
`POST /context` – xây dựng ngữ cảnh + sinh trích dẫn.
Trả về **Gói ngữ cảnh sẵn sàng cho LLM** `{ context, citations, sources, metadata }`.

## Knowledge API
`GET /documents/{id}` – tra cứu tài liệu.
`GET /metadata/{id}` – tra cứu metadata.

> TODO: hoàn thiện schema request/response trong `api/schemas/`.
