# data/

| Thư mục | Nội dung | Git |
|---------|----------|-----|
| `raw/` | Đầu ra thô của crawler | bị ignore (chỉ commit `.gitkeep`) |
| `cleaned/` | Tài liệu đã làm sạch/kiểm định | bị ignore |
| `processed/` | Sản phẩm đã chunk/embed | bị ignore |
| `samples/` | Mẫu nhỏ được commit để test/demo | được commit (chỉ file nhỏ) |

**Không** commit tập dữ liệu lớn. Chỉ giữ những mẫu nhỏ, mang tính đại diện trong `samples/`.
