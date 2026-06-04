/**
 * Frontend data shapes for the OTA AI Search demo.
 *
 * SearchResponse:
 * {
 *   query: string,
 *   results: SearchResult[],
 *   total: number,
 *   source: "mock" | "api"
 * }
 *
 * SearchResult:
 * {
 *   id: string,
 *   title: string,
 *   snippet: string,
 *   score: number,
 *   metadata: Metadata,
 *   citations: Citation[],
 *   source_documents: SourceDocument[],
 *   context_chunks: ContextChunk[]
 * }
 *
 * Metadata:
 * {
 *   location: string,
 *   category: string,
 *   amenities: string[],
 *   ranking_info: string,
 *   price_level?: string,
 *   best_for?: string[]
 * }
 *
 * Citation:
 * {
 *   id: string,
 *   source_document_id: string,
 *   chunk_id: string,
 *   label: string,
 *   url?: string,
 *   quote?: string
 * }
 *
 * SourceDocument:
 * {
 *   id: string,
 *   title: string,
 *   type: string,
 *   path?: string,
 *   url?: string
 * }
 *
 * ContextChunk:
 * {
 *   id: string,
 *   source_document_id: string,
 *   text: string,
 *   rank: number
 * }
 *
 * ApiError:
 * {
 *   message: string,
 *   status?: number,
 *   endpoint?: string,
 *   raw?: unknown
 * }
 */

export const emptySearchResponse = {
  query: "",
  results: [],
  total: 0,
  source: "mock"
};

export const emptyMetadata = {
  location: "Unknown location",
  category: "Unknown category",
  amenities: [],
  ranking_info: "No ranking information available",
  price_level: "Unknown",
  best_for: []
};
