# Query Expansion Evaluation (Bước 9 roadmap)

> Sinh bởi `knowledge_engineering/governance/evaluate_query_expansion.py --report`. Read-only.
> Ngày: 2026-06-14. Golden: 32 câu, 18 rule.

Evaluator KHÔNG tự sửa ontology. Quyết định cuối ghi vào `curated.yaml` / `candidates.yaml` / `rejected.yaml`.

## Per-edge (source -> target) đánh giá trên golden set

| source | target | relation_type | source_type | use_as | status | hits | noise | recommendation |
|---|---|---|---|---|---|---|---|---|
| `AMEN_BEACHFRONT` | `SETTING_COASTAL` | broader | curated | boost | verified | 0 | 2 | downgrade |
| `AMEN_INFINITY_POOL` | `AMEN_POOL` | broader | curated | boost | verified | 0 | 1 | downgrade |
| `AMEN_POOL` | `AMEN_INFINITY_POOL` | narrower | curated | boost | verified | 0 | 1 | downgrade |
| `AMEN_POOL` | `AMEN_KIDS_POOL` | narrower | curated | boost | verified | 0 | 1 | downgrade |
| `AMEN_POOL` | `AMEN_PRIVATE_POOL` | narrower | curated | boost | verified | 0 | 1 | downgrade |
| `AMEN_SPA` | `PURPOSE_WELLNESS` | evidence_for | curated | boost | verified | 0 | 1 | downgrade |
| `LOC_PHU_QUOC` | `SETTING_ISLAND` | implies | curated | filter | verified | 0 | 1 | reject |
| `OBJ_APARTMENT` | `AMEN_KITCHEN` | cooccurs_with | curated | boost | verified | 0 | 1 | downgrade |
| `OBJ_RESORT` | `AMEN_BEACHFRONT` | cooccurs_with | curated | boost | verified | 0 | 3 | downgrade |
| `OBJ_RESORT` | `AMEN_TENNIS` | cooccurs_with | curated | boost | verified | 0 | 3 | downgrade |
| `OBJ_RESORT` | `AMEN_WATERSPORT` | cooccurs_with | curated | boost | verified | 0 | 3 | downgrade |
| `PRICE_LUXURY` | `PRICE_UPSCALE` | broader | curated | boost | verified | 0 | 0 | needs_retrieval_test |
| `PURPOSE_FAMILY` | `AMEN_KIDS_CLUB` | evidence_for | curated | boost | verified | 2 | 0 | keep/promote |
| `PURPOSE_FAMILY` | `AMEN_KIDS_POOL` | evidence_for | curated | boost | verified | 2 | 0 | keep/promote |
| `PURPOSE_ROMANTIC` | `AMEN_PRIVATE_POOL` | evidence_for | curated | boost | verified | 1 | 0 | keep/promote |
| `PURPOSE_ROMANTIC` | `AMEN_SEA_VIEW` | evidence_for | curated | boost | verified | 1 | 0 | keep/promote |
| `PURPOSE_ROMANTIC` | `STYLE_ROMANTIC` | evidence_for | curated | boost | verified | 0 | 0 | needs_retrieval_test |
| `SETTING_COASTAL` | `AMEN_BEACHFRONT` | narrower | curated | boost | verified | 0 | 2 | downgrade |

## Phân loại câu golden

| classification | số câu |
|---|---|
| expansion_risk_if_filter | 3 |
| intent_router_needed | 19 |
| ok | 8 |
| out_of_scope_for_concept_parser | 1 |
| parser_miss | 1 |
