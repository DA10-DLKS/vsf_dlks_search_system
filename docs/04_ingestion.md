# 04 – Thu nạp & Xử lý dữ liệu (Layer 2)

`ingestion/` biến đầu ra thô của crawler thành một tập dữ liệu sạch, đã kiểm định và khử trùng lặp.

- **connectors/** – thu nạp theo lô (batch), connector API, import file
- **validation/** – kiểm định schema, kiểm tra chất lượng
- **cleaning/** – chuẩn hóa văn bản, loại bỏ HTML, sửa lỗi mã hóa
- **deduplication/** – phát hiện gần trùng lặp

Đầu ra: các tài liệu đã chuẩn hóa, sạch, sẵn sàng cho bước kỹ thuật tri thức.
