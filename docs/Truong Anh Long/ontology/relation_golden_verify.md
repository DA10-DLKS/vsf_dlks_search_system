# Relation Boost — Golden Query Verify (Bước 12 roadmap)

> Sinh bởi `knowledge_engineering/governance/verify_relation_golden.py`. Read-only.
> Ngày: 2026-06-14. A/B boost ON vs OFF trên golden có groundtruth.

## Tổng kết

- Câu có groundtruth kiểm: **32**
- Recall (số kết quả) thay đổi do boost: **0** (kỳ vọng 0 — boost chỉ ranking)
- Boost đẩy groundtruth LÊN top: **2**
- Boost kéo groundtruth VÀO top (trước đó ngoài): **0**
- Boost đẩy groundtruth XUỐNG: **0**

## Chi tiết

| qid | n(off) | n(on) | rank(off) | rank(on) | nhận xét |
|---|---|---|---|---|---|
| Q1-01 | 48 | 48 | 4 | 4 | không đổi |
| Q1-02 | 8 | 8 | 3 | 3 | không đổi |
| Q1-03 | 7 | 7 | 1 | 1 | không đổi |
| Q1-04 | 1 | 1 | 1 | 1 | không đổi |
| Q1-05 | 0 | 0 | — | — | groundtruth ngoài top |
| Q1-06 | 10 | 10 | 3 | 2 | boost đẩy groundtruth lên ✅ |
| Q2-01 | 6 | 6 | 4 | 4 | không đổi |
| Q2-02 | 520 | 520 | — | — | groundtruth ngoài top |
| Q2-03 | 328 | 328 | — | — | groundtruth ngoài top |
| Q2-04 | 520 | 520 | — | — | groundtruth ngoài top |
| Q2-05 | 22 | 22 | 20 | 20 | không đổi |
| Q3-01 | 328 | 328 | — | — | groundtruth ngoài top |
| Q3-02 | 328 | 328 | — | — | groundtruth ngoài top |
| Q3-03 | 112 | 112 | 46 | 46 | không đổi |
| Q3-04 | 7 | 7 | — | — | groundtruth ngoài top |
| Q3-05 | 328 | 328 | — | — | groundtruth ngoài top |
| Q4-01 | 520 | 520 | — | — | groundtruth ngoài top |
| Q4-02 | 520 | 520 | — | — | groundtruth ngoài top |
| Q4-03 | 39 | 39 | 1 | 1 | không đổi |
| Q4-04 | 520 | 520 | — | — | groundtruth ngoài top |
| Q5-01 | 1 | 1 | — | — | groundtruth ngoài top |
| Q5-02 | 520 | 520 | — | — | groundtruth ngoài top |
| Q5-03 | 520 | 520 | — | — | groundtruth ngoài top |
| Q5-04 | 28 | 28 | 2 | 2 | không đổi |
| Q6-01 | 39 | 39 | 18 | 18 | không đổi |
| Q6-02 | 23 | 23 | 17 | 17 | không đổi |
| Q6-03 | 28 | 28 | 16 | 9 | boost đẩy groundtruth lên ✅ |
| Q7-01 | 48 | 48 | 6 | 6 | không đổi |
| Q7-02 | 0 | 0 | — | — | groundtruth ngoài top |
| Q7-03 | 48 | 48 | 15 | 15 | không đổi |
| Q7-04 | 10 | 10 | 8 | 8 | không đổi |
| Q7-05 | 3 | 3 | — | — | groundtruth ngoài top |
