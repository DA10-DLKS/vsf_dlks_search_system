# Định Nghĩa Mục Tiêu Chỉ Số Đánh Giá (Metrics & Targets)

Tài liệu này xác định các chỉ số đo lường hiệu năng và chất lượng (Metrics & Targets) cho hệ thống Retrieval & Ranking (R&R) và luồng RAG Hybrid Search của dự án AI Travel Assistant (DA10).

---

## 🎯 1. Chỉ Số Chất Lượng Truy Xuất (Retrieval Accuracy Metrics)

Độ chính xác của quá trình truy xuất thông tin ngữ cảnh là điều kiện tiên quyết để LLM đưa ra câu trả lời chính xác, tránh hiện tượng bịa đặt thông tin (hallucination). Các chỉ số này được đo lường trên bộ dữ liệu **Golden Set (50 kịch bản truy vấn)**.

| Chỉ số (Metric) | Định nghĩa (Definition) | Mục tiêu (Target) | Ý nghĩa nghiệp vụ (Business Value) |
| :--- | :--- | :--- | :--- |
| **Recall@5** | Tỷ lệ các chunk tài liệu liên quan thực tế (ground-truth) xuất hiện trong Top 5 kết quả trả về. | **$\ge 85\%$** | Đảm bảo phần lớn thông tin hữu ích nhất lọt vào được khung ngữ cảnh (Context) gửi cho LLM. |
| **Recall@10** | Tỷ lệ các chunk tài liệu liên quan thực tế xuất hiện trong Top 10 kết quả trả về. | **$\ge 95\%$** | Đảm bảo hầu hết toàn bộ thông tin quan trọng đều được tìm thấy trước khi qua phễu Re-ranking. |
| **MRR (Mean Reciprocal Rank)** | Điểm xếp hạng nghịch đảo trung bình của tài liệu đúng đầu tiên tìm được. | **$\ge 0.75$** | Đánh giá khả năng tìm thấy tài liệu đúng ở vị trí càng cao càng tốt (lý tưởng nhất là vị trí số 1 hoặc 2). |
| **NDCG@5** | Điểm số tích lũy chiết khấu chuẩn hóa đo lường độ liên quan xếp hạng ở Top 5. | **$\ge 80\%$** | Phạt nặng nếu hệ thống đưa tài liệu liên quan kém lên đầu và đẩy tài liệu liên quan cao xuống dưới. |

### **1.1 Chi Tiết Toán Học Cho Chỉ Số NDCG (NDCG Mathematical Formula)**
Để đo lường xem các tài liệu liên quan có được sắp xếp lên những vị trí đầu hay không, hệ thống sử dụng **NDCG (Normalized Discounted Cumulative Gain)** với công thức như sau:

1. **Cumulative Gain (CG_p):** Tổng giá trị độ liên quan của top $p$ tài liệu:
   $$CG_p = \sum_{i=1}^p rel_i$$
   Trong đó $rel_i$ là độ liên quan thực tế (graded relevance) của tài liệu ở vị trí $i$ (ví dụ: 1 là liên quan, 0 là không liên quan).

2. **Discounted Cumulative Gain (DCG_p):** Áp dụng logarit chiết khấu thứ hạng để phạt nếu tài liệu liên quan nằm ở vị trí thấp:
   $$DCG_p = \sum_{i=1}^p \frac{rel_i}{\log_2(i + 1)}$$

3. **Ideal Discounted Cumulative Gain (IDCG_p):** Điểm DCG của danh sách kết quả lý tưởng (sau khi sắp xếp giảm dần tất cả các tài liệu theo mức độ liên quan thực tế):
   $$IDCG_p = \sum_{i=1}^{|REL_p|} \frac{rel_{ideal\_i}}{\log_2(i + 1)}$$

4. **Normalized Discounted Cumulative Gain (NDCG_p):** Tỷ lệ chuẩn hóa nằm trong khoảng `[0.0, 1.0]`:
   $$NDCG_p = \frac{DCG_p}{IDCG_p}$$

---

## ⚡ 2. Chỉ Số Hiệu Năng Hệ Thống (System Performance & SLOs)

Mục tiêu tối ưu hóa trải nghiệm người dùng cuối, đảm bảo phản hồi trực quan và nhanh chóng. SLO đo lường ở môi trường local chạy Docker ổn định.

### **2.1 Mục tiêu Latency (End-to-End)**
- **p50 Latency (Thời gian phản hồi trung vị):** **< 300ms** (khi Ollama Parser đã cache model).
- **p95 Latency (Thời gian phản hồi phân vị 95):** **< 500ms** (trong điều kiện tải tối đa).

### **2.2 Phân rã độ trễ mục tiêu từng giai đoạn (Latency Budget Breakdown)**

```text
[Tổng Latency Budget: 500ms]
  ├── Giai đoạn 1: Intent Parsing (Ollama qwen2.5:7b)  ───> < 300ms
  ├── Giai đoạn 2: Pre-filtering (Postgres + Neo4j) ───> < 30ms
  ├── Giai đoạn 3: Parallel Search (ES + pgvector)   ───> < 100ms
  ├── Giai đoạn 4: Fusion & Re-ranking               ───> < 50ms
  └── Trích xuất & Ghép Prompt                       ───> < 20ms
```

---

## 💬 3. Chỉ Số Chất Lượng Phản Hồi LLM (Generation Quality Metrics)

Đo lường chất lượng câu trả lời cuối cùng được sinh ra từ LLM dựa trên Prompt Context đã được biên soạn.

| Chỉ số (Metric) | Phương pháp đo lường (Method) | Mục tiêu (Target) | Mô tả (Description) |
| :--- | :--- | :--- | :--- |
| **Faithfulness (Độ trung thực)** | Đánh giá LLM-as-a-judge hoặc kiểm tra chéo thủ công trên Golden Set. | **100%** | Câu trả lời KHÔNG được chứa bất kỳ chi tiết nào nằm ngoài Context được cung cấp (Không Hallucination). |
| **Answer Relevance (Độ liên quan)** | So sánh câu trả lời của LLM với câu hỏi của người dùng. | **$\ge 90\%$** | Câu trả lời phải đi trực tiếp vào câu hỏi, không lan man hoặc trả lời lạc đề. |
| **Citation Accuracy (Trích dẫn đúng)** | Kiểm tra xem các thẻ trích dẫn nguồn (ví dụ: `[1]`, `[2]`) có khớp đúng thông tin hay không. | **100%** | Tuyệt đối không trích dẫn sai số thứ tự nguồn hoặc tự bịa ra ký hiệu nguồn trích dẫn. |

---

## 🛠️ 4. Phương Pháp Đo Lường Bằng Golden Set (Evaluation Methodology)

Để chạy tự động và tính toán các chỉ số chất lượng R&R nêu trên, nhóm phát triển sử dụng công cụ đánh giá `run_eval.py` dựa trên tập **Golden Set (100 kịch bản truy vấn mẫu)**.

### **Quy trình các bước đo lường:**

1. **Chuẩn bị Golden Set:**
   * Tập kịch bản kiểm thử được lưu trữ dưới dạng danh sách câu hỏi tiếng Việt kèm theo danh sách các `hotel_id` và các `chunk_id` liên quan thực tế (ground-truth).
   * Ví dụ:
     ```yaml
     - query: "khách sạn yên tĩnh gần biển ở nha trang dưới 2 triệu"
       ground_truth_hotels: [65153]
       ground_truth_chunks: ["text_chunks_102", "text_chunks_103"]
     ```

2. **Khởi chạy Pipeline tìm kiếm:**
   * Với mỗi truy vấn trong Golden Set, hệ thống chạy qua toàn bộ pipeline 5 giai đoạn: Intent Parsing -> Pre-filtering -> Parallel Retrieval -> RRF Fusion -> Re-ranking.
   * Thu thập danh sách kết quả cuối cùng gồm 10 phần tử đầu tiên (Top 10 chunks).

3. **Tính toán chỉ số trên từng truy vấn:**
   * **Recall@k:** Kiểm tra xem tập `ground_truth_chunks` có giao với tập kết quả trả về Top $k$ hay không.
     $$Recall@k = \frac{|\text{Results}@k \cap \text{GroundTruth}|}{|\text{GroundTruth}|}$$
   * **MRR:** Tìm vị trí đầu tiên $i$ trong kết quả trả về trùng với một chunk trong `ground_truth_chunks`. Điểm số là $1/i$. Nếu không tìm thấy, điểm số là $0$.
   * **NDCG@5:** Gán nhãn độ liên quan nhị phân ($rel_i = 1$ nếu chunk thứ $i$ thuộc `ground_truth_chunks`, ngược lại $rel_i = 0$). Sử dụng công thức NDCG ở mục 1.1 để tính toán.

4. **Tổng hợp kết quả (Aggregate Metrics):**
   * Lấy trung bình cộng (Mean) của các điểm số NDCG@5, Recall@5, Recall@10, và MRR trên toàn bộ 100 câu truy vấn để ra báo cáo chất lượng cuối cùng.

### **Câu lệnh khởi chạy đánh giá trên terminal:**
```bash
python hotel-knowledge-platform/backend/run_eval.py --dataset intrusment/golden_dataset_ota.md --output metrics_report.json
```
