# Ảnh hưởng của việc trả full `description` trong search API đến latency
Trả full `description` trong response API **có ảnh hưởng latency**, nhất là với search endpoint.

Ảnh hưởng đến từ 3 chỗ:

- **OpenSearch fetch phase**: query xong phải đọc `_source` đầy đủ từ disk/cache.
- **API serialization**: FastAPI phải convert nhiều text dài thành JSON.
- **Network/client read time**: benchmark client đo end-to-end, nên payload càng lớn thì P50/P95 càng tăng.

Nếu `size=10` và mỗi khách sạn có description dài vài KB, response có thể phình rất nhanh. Với benchmark latency, payload lớn thường làm **P95/P99 xấu hơn** dù OpenSearch query phase không chậm.

Nếu vẫn muốn giữ `description`, có mấy cách tối ưu thực tế:

1. **Trả snippet thay vì full description**
   - API response giữ field `description`, nhưng chỉ lấy 200-500 ký tự đầu.
   - Full description lấy qua endpoint detail riêng, ví dụ `GET /hotels/{id}`.

2. **Thêm query param**
   ```text
   GET /search?q=...&include_description=false
   GET /search?q=...&include_description=true
   ```
   Mặc định `false` để search nhanh, chỉ bật khi UI thật sự cần.

3. **Dùng OpenSearch highlight**
   - Trả đoạn description có match query thay vì full text.
   - Hữu ích cho search UI:
   ```json
   "highlight": {
     "fields": {
       "description": {
         "fragment_size": 180,
         "number_of_fragments": 2
       }
     }
   }
   ```

4. **Tách field `description_short` khi index**
   - Lưu sẵn mô tả ngắn trong index.
   - Search vẫn dùng `description` để score, nhưng response chỉ trả `description_short`.

5. **Dùng `_source` filtering**
   - Search phase vẫn query trên `description`.
   - Fetch phase không trả full `description`:
   ```json
   "_source": ["id", "name", "city", "review_score", "description_short"]
   ```

Khuyến nghị production: **không trả full description trong search results**. Search API nên trả summary/snippet, còn full description để detail/context endpoint xử lý sau. Đây là pattern tốt hơn cho RAG nữa: retrieval lấy candidate nhanh, context builder mới quyết định lấy đoạn nào cần đưa vào context.