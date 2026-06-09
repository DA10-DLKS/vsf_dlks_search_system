# Dashboard Design

## Dashboard Purpose

The dashboard is the mentor-facing demo page for the OTA AI Search Platform. It shows how a user query becomes ranked search results with traceable evidence for RAG usage.

## Layout

Desktop-first layout for laptop/projector:

1. Header with product name and RAG flow.
2. Traceability strip: Query, Top-K, Metadata, Citation, Sources, Context, LLM.
3. Metric target cards: Recall@10, MRR, NDCG, P95 latency.
4. Search panel.
5. Ranked result list.
6. Per-result traceability sections.

## Main Sections

- Demo overview header.
- RAG flow visualization.
- Metrics/demo indicators.
- Search interaction area.
- Result traceability area.
- LLM context preview area.

## Components Used

- `Dashboard.jsx`
- `SearchInterface.jsx`
- `ResultList.jsx`
- `ResultCard.jsx`
- `MetadataCard.jsx`
- `CitationList.jsx`
- `ContextPreview.jsx`
- `LoadingState.jsx`
- `ErrorState.jsx`
- `EmptyState.jsx`

## How It Demonstrates Search/RAG Flow

The dashboard makes every step visible:

```text
User Query -> Top-K Results -> Metadata -> Citation -> Source Documents -> Context Chunks -> LLM Consumption
```

The demo should make it clear that the result is not only a ranked card. It also shows why the result was selected, which source supports it, which chunk was retrieved, and what context can be consumed by an LLM.
