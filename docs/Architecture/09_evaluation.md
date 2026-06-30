# 09 – Đánh giá

## Chất lượng truy xuất (`evaluation/retrieval_metrics/`)
Recall@K, Precision@K, MRR, NDCG, Hit Rate.

## Đánh giá RAG (`evaluation/rag_eval/`)
RAGAS, Faithfulness (độ trung thực), Context Precision, Context Recall.

## Tài nguyên
- `test_queries/` – bộ truy vấn được tuyển chọn
- `relevance_labels/` – nhãn mức độ liên quan chuẩn (ground-truth)
- `reports/` – báo cáo đánh giá được sinh ra (bị gitignore)

Chạy: `python scripts/run_eval.py`
