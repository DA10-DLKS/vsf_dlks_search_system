# 09 – Đánh giá

## Cấu trúc thư mục

```
evaluation/
├── retrieval_metrics/      Retrieval evaluation
│   ├── eval_golden.py      Golden dataset evaluation (Recall, Precision, MRR, nDCG)
│   ├── ab_runner.py        A/B testing runner
│   └── sweep_neural.py     Neural reranker sweep
├── rag_eval/               RAG evaluation (RAGAS, Faithfulness)
├── test_queries/           Test queries for evaluation
├── relevance_labels/       Ground-truth relevance labels
└── reports/                Evaluation reports (gitignored)
```

## Retrieval Metrics

### Golden Dataset Evaluation

Metrics:
- **Recall@K**: Tỉ lệ relevant items được trả về trong top-K
- **Precision@K**: Tỉ lệ items trong top-K là relevant
- **Hit Rate**: Có ít nhất 1 relevant item trong top-K
- **MRR** (Mean Reciprocal Rank): Rank của relevant item đầu tiên
- **nDCG@K**: Normalized Discounted Cumulative Gain

**Current Results (candidate-only):**
| Metric | Value |
|---|---|
| Recall@10 | 0.5495 |
| Hit@10 | 1.00 |
| MRR | 0.9065 |

### API Endpoint

```
GET /eval/golden?k=10&limit=10&use_services=false
```

## RAG Evaluation

- RAGAS (Retrieval Augmented Generation Assessment)
- Faithfulness: Độ trung thực của câu trả lời
- Context Precision: Độ chính xác của context
- Context Recall: Độ bao phủ của context

## Chạy evaluation

```bash
# Via API
curl "http://localhost:8000/eval/golden?k=10&limit=10"

# Via script
python evaluation/retrieval_metrics/eval_golden.py
```
