/**
 * Frontend data shapes for the OTA AI Search demo.
 *
 * This file is documentation-first because the current repo uses plain JS.
 * It documents three layers:
 *
 * 1. Old mock compatibility shape used by frontend/search_ui.html and the
 *    original React-ready components.
 * 2. Raw Kien API schema v1 shape from VuDucKien_api_schema_proposal.md.
 * 3. Normalized frontend shapes consumed by future UI components.
 */

/**
 * OLD MOCK COMPATIBILITY
 *
 * OldSearchResponse:
 * {
 *   query: string,
 *   results: OldSearchResult[],
 *   total?: number,
 *   source?: "mock" | "api"
 * }
 *
 * OldSearchResult:
 * {
 *   id: string,
 *   title: string,
 *   snippet: string,
 *   score: number,
 *   metadata: OldMetadata,
 *   citations: OldCitation[],
 *   source_documents: OldSourceDocument[],
 *   context_chunks: OldContextChunk[]
 * }
 *
 * OldMetadata:
 * {
 *   location: string,
 *   category: string,
 *   amenities: string[],
 *   ranking_info: string,
 *   price_level?: string,
 *   best_for?: string[]
 * }
 *
 * OldCitation:
 * {
 *   id: string,
 *   source_document_id: string,
 *   chunk_id: string,
 *   label: string,
 *   url?: string,
 *   quote?: string
 * }
 *
 * OldSourceDocument:
 * {
 *   id: string,
 *   title: string,
 *   type: string,
 *   path?: string,
 *   url?: string
 * }
 *
 * OldContextChunk:
 * {
 *   id: string,
 *   source_document_id: string,
 *   text: string,
 *   rank: number
 * }
 */

/**
 * RAW KIEN API SCHEMA V1
 *
 * Search API:
 * POST /api/v1/search
 *
 * KienSearchRequest:
 * {
 *   query: string,
 *   top_k?: number,
 *   page?: number,
 *   filters?: {
 *     city?: string,
 *     star_rating?: { min?: number, max?: number },
 *     price?: { min?: number, max?: number },
 *     accommodation_type?: string[],
 *     amenities?: string[],
 *     suitable_for?: string[],
 *     review_score?: { min?: number },
 *     is_luxury?: boolean,
 *     geo?: { lat: number, lng: number, radius_km: number }
 *   },
 *   options?: {
 *     include_debug?: boolean
 *   }
 * }
 *
 * KienSearchResponse:
 * {
 *   query_id: string,
 *   query: string,
 *   total_found: number,
 *   returned: number,
 *   page: number,
 *   latency_ms: number,
 *   results: HotelCard[],
 *   parsed_intent: ParsedIntent,
 *   debug_info?: object
 * }
 *
 * HotelCard:
 * {
 *   hotel_id: number,
 *   name: string,
 *   accommodation_type: string,
 *   address: string,
 *   city: string,
 *   latitude: number,
 *   longitude: number,
 *   star_rating: number,
 *   review_score: number,
 *   review_count: number,
 *   is_luxury: boolean,
 *   price_from: number,
 *   description: string,
 *   suitable_for: string[],
 *   amenities_top: string[],
 *   thumbnail_url: string,
 *   image_count: number,
 *   ranking: {
 *     final_score: number,
 *     rank: number,
 *     relevance_score?: number
 *   },
 *   nearby_places?: {
 *     name: string,
 *     type: string,
 *     distance_km: number
 *   }[],
 *   source_url?: string
 * }
 *
 * ParsedIntent:
 * {
 *   original_query: string,
 *   normalized_query: string,
 *   hard_filters: object,
 *   keyword_expansion: string[],
 *   intent_type: "hotel_search" | "destination_info" | "comparison" | "faq" | "unclear",
 *   confidence: number,
 *   parsed_by: "llm" | "rule_based"
 * }
 *
 * Context API:
 * POST /api/v1/context
 *
 * KienContextRequest:
 * {
 *   hotel_id: number,
 *   query: string,
 *   query_id?: string,
 *   options?: {
 *     max_context_tokens?: number,
 *     include_chunks?: boolean,
 *     include_metadata?: boolean,
 *     include_token_info?: boolean
 *   }
 * }
 *
 * KienContextResponse:
 * {
 *   hotel_id: number,
 *   hotel_name: string,
 *   query_id: string,
 *   context_text: string,
 *   chunks: RetrievedChunk[],
 *   citations: KienCitation[],
 *   metadata: HotelMetadata,
 *   token_info?: TokenInfo,
 *   latency_ms: number
 * }
 *
 * RetrievedChunk:
 * {
 *   chunk_id: string,
 *   text: string,
 *   source_type: "hotel_description" | "room_info" | "amenity" | "nearby" | "activity" | string,
 *   scores: {
 *     bm25_rank?: number,
 *     vector_rank?: number,
 *     rrf_score: number,
 *     reranker_score: number
 *   },
 *   payload: {
 *     hotel_id: number,
 *     source_table: "hotels" | "rooms" | "nearby_places" | "activities" | string,
 *     source_column?: string,
 *     record_id?: number,
 *     lang?: string
 *   }
 * }
 *
 * KienCitation:
 * {
 *   citation_id: string,
 *   chunk_id: string,
 *   source_type: string,
 *   text_snippet: string,
 *   relevance_score: number,
 *   metadata: {
 *     source_table: "hotels" | "rooms" | "nearby_places" | "activities" | string,
 *     source_column?: string,
 *     record_id?: number
 *   }
 * }
 *
 * HotelMetadata:
 * {
 *   hotel_id: number,
 *   name: string,
 *   accommodation_type: string,
 *   star_rating: number,
 *   is_luxury: boolean,
 *   address: string,
 *   city: string,
 *   latitude: number,
 *   longitude: number,
 *   review_score: number,
 *   review_count: number,
 *   reviews_detail: object,
 *   description: string,
 *   amenities: string[],
 *   suitable_for: string[],
 *   policy_notes: string[],
 *   useful_info: object,
 *   price_from: number,
 *   rooms: object[],
 *   nearby_places: object[],
 *   activities: object[],
 *   images: string[],
 *   source_url?: string
 * }
 *
 * TokenInfo:
 * {
 *   context_text_tokens: number,
 *   metadata_tokens: number,
 *   total_tokens: number,
 *   model_used_for_count: string
 * }
 *
 * KienErrorResponse:
 * {
 *   error: {
 *     code: string,
 *     message: string,
 *     user_message?: string,
 *     query_id?: string,
 *     details?: object
 *   }
 * }
 */

/**
 * NORMALIZED FRONTEND SHAPES
 *
 * NormalizedSearchResponse:
 * {
 *   query_id?: string,
 *   query: string,
 *   results: NormalizedSearchResult[],
 *   total: number,
 *   total_found?: number,
 *   returned?: number,
 *   page?: number,
 *   latency_ms?: number,
 *   parsed_intent?: ParsedIntent,
 *   source: "mock" | "api" | "mock_v2" | "api_v2",
 *   raw?: object
 * }
 *
 * NormalizedSearchResult:
 * {
 *   id: string,
 *   hotel_id: number | string,
 *   title: string,
 *   snippet: string,
 *   score: number,
 *   rank: number,
 *   metadata: {
 *     location?: string,
 *     category?: string,
 *     address?: string,
 *     city?: string,
 *     accommodation_type?: string,
 *     latitude?: number,
 *     longitude?: number,
 *     star_rating?: number,
 *     review_score?: number,
 *     review_count?: number,
 *     is_luxury?: boolean,
 *     price_from?: number,
 *     amenities?: string[],
 *     amenities_top?: string[],
 *     suitable_for?: string[],
 *     best_for?: string[],
 *     nearby_places?: object[],
 *     ranking_info?: string
 *   },
 *   image: {
 *     thumbnail_url?: string,
 *     image_count?: number
 *   },
 *   source_url?: string,
 *   query_id?: string,
 *   latency_ms?: number,
 *   raw: object
 * }
 *
 * NormalizedContextPackage:
 * {
 *   result_id: string,
 *   hotel_id: number | string,
 *   query_id?: string,
 *   context_text: string,
 *   chunks: NormalizedChunk[],
 *   citations: NormalizedCitation[],
 *   metadata: object,
 *   token_info?: TokenInfo,
 *   latency_ms?: number,
 *   raw: object
 * }
 *
 * NormalizedChunk:
 * {
 *   id: string,
 *   chunk_id: string,
 *   text: string,
 *   source_type?: string,
 *   rank?: number,
 *   scores?: object,
 *   payload?: object,
 *   source_document_id?: string
 * }
 *
 * NormalizedCitation:
 * {
 *   id: string,
 *   citation_id: string,
 *   chunk_id: string,
 *   source_type?: string,
 *   text_snippet?: string,
 *   relevance_score?: number,
 *   metadata?: object,
 *   source_document_id?: string,
 *   label?: string,
 *   quote?: string,
 *   url?: string
 * }
 *
 * NormalizedApiError:
 * {
 *   code: string,
 *   message: string,
 *   user_message?: string,
 *   query_id?: string,
 *   details?: object,
 *   status?: number,
 *   endpoint?: string,
 *   raw?: unknown
 * }
 */

/**
 * Search -> Context flow for Kien schema v1:
 *
 * query
 * -> searchV2(query, { filters, top_k, page })
 * -> response.results[0].hotel_id
 * -> getContextV2({
 *      hotel_id: response.results[0].hotel_id,
 *      query: response.query,
 *      query_id: response.query_id,
 *      options: { include_chunks: true, include_metadata: true }
 *    })
 * -> render context_text, chunks, citations, metadata and token_info
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
