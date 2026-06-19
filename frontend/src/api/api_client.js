import mockResponses from "../../mock_api_responses.json";
import mockResponsesV2 from "../../mock_api_responses_v2.json";
import { config } from "../config/config";
import { emptyMetadata } from "../types/searchTypes";

const SEARCH_V2_ENDPOINT = "/api/v1/search";
const CONTEXT_V2_ENDPOINT = "/api/v1/context";

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeMetadata(metadata = {}) {
  return {
    ...emptyMetadata,
    ...metadata,
    amenities: normalizeArray(metadata.amenities),
    best_for: normalizeArray(metadata.best_for)
  };
}

function normalizeOldResult(result = {}) {
  return {
    id: String(result.id || ""),
    title: result.title || "Untitled result",
    snippet: result.snippet || "No snippet available",
    score: normalizeNumber(result.score),
    metadata: normalizeMetadata(result.metadata),
    citations: normalizeArray(result.citations),
    source_documents: normalizeArray(result.source_documents),
    context_chunks: normalizeArray(result.context_chunks)
  };
}

function normalizeContextChunk(chunk = {}, index = 0) {
  return {
    id: String(chunk.chunk_id || chunk.id || `chunk-${index + 1}`),
    chunk_id: String(chunk.chunk_id || chunk.id || `chunk-${index + 1}`),
    text: chunk.text || "",
    source_type: chunk.source_type || "",
    rank: normalizeNumber(chunk.rank, index + 1),
    scores: chunk.scores || {},
    payload: chunk.payload || {},
    source_document_id:
      chunk.source_document_id ||
      chunk.payload?.source_table ||
      chunk.payload?.source_column ||
      ""
  };
}

function normalizeCitation(citation = {}, index = 0) {
  return {
    id: String(citation.citation_id || citation.id || `citation-${index + 1}`),
    citation_id: String(citation.citation_id || citation.id || `citation-${index + 1}`),
    chunk_id: citation.chunk_id || "",
    source_type: citation.source_type || citation.label || "",
    text_snippet: citation.text_snippet || citation.quote || "",
    relevance_score: normalizeNumber(citation.relevance_score, 0),
    metadata: citation.metadata || {},
    source_document_id: citation.source_document_id || citation.metadata?.source_table || "",
    label: citation.label || citation.source_type || citation.citation_id || citation.id || "",
    quote: citation.quote || citation.text_snippet || "",
    url: citation.url
  };
}

export function normalizeSearchResult(rawResult = {}, queryMeta = {}) {
  const hotelId = rawResult.hotel_id ?? rawResult.id ?? "";
  const ranking = rawResult.ranking || {};
  const city = rawResult.city || "";
  const address = rawResult.address || "";
  const compactMetadata = {
    location: city || address || "Unknown location",
    category: rawResult.accommodation_type || "Unknown category",
    accommodation_type: rawResult.accommodation_type || "",
    address,
    city,
    latitude: rawResult.latitude,
    longitude: rawResult.longitude,
    star_rating: rawResult.star_rating,
    review_score: rawResult.review_score,
    review_count: rawResult.review_count,
    is_luxury: rawResult.is_luxury,
    price_from: rawResult.price_from,
    amenities: normalizeArray(rawResult.amenities_top || rawResult.amenities),
    amenities_top: normalizeArray(rawResult.amenities_top),
    suitable_for: normalizeArray(rawResult.suitable_for),
    best_for: normalizeArray(rawResult.suitable_for),
    nearby_places: normalizeArray(rawResult.nearby_places),
    ranking_info: ranking.rank
      ? `Rank #${ranking.rank} by final_score ${normalizeNumber(ranking.final_score).toFixed(2)}`
      : "No ranking information available"
  };

  return {
    id: String(hotelId),
    hotel_id: hotelId,
    title: rawResult.name || rawResult.title || "Untitled hotel",
    snippet: rawResult.description || rawResult.snippet || "No description available",
    score: normalizeNumber(ranking.final_score ?? rawResult.score),
    rank: normalizeNumber(ranking.rank, 0),
    metadata: compactMetadata,
    image: {
      thumbnail_url: rawResult.thumbnail_url || "",
      image_count: normalizeNumber(rawResult.image_count, 0)
    },
    source_url: rawResult.source_url || "",
    query_id: queryMeta.query_id || "",
    latency_ms: queryMeta.latency_ms,
    raw: rawResult
  };
}

export function normalizeSearchResponse(response = {}, source = "api") {
  const isKienSchema = Boolean(response.query_id || response.total_found !== undefined);

  if (!isKienSchema) {
    const results = normalizeArray(response.results).map(normalizeOldResult);
    return {
      query: response.query || "",
      results,
      total: normalizeNumber(response.total ?? results.length),
      source
    };
  }

  const queryMeta = {
    query_id: response.query_id || "",
    latency_ms: response.latency_ms
  };
  const results = normalizeArray(response.results).map((result) =>
    normalizeSearchResult(result, queryMeta)
  );

  return {
    query_id: response.query_id || "",
    query: response.query || "",
    results,
    total: normalizeNumber(response.total_found ?? results.length),
    total_found: normalizeNumber(response.total_found ?? results.length),
    returned: normalizeNumber(response.returned ?? results.length),
    page: normalizeNumber(response.page, 0),
    latency_ms: response.latency_ms,
    parsed_intent: response.parsed_intent || null,
    debug_info: response.debug_info,
    source,
    raw: response
  };
}

export function normalizeContextResponse(response = {}) {
  const isKienSchema = Boolean(
    response.hotel_id !== undefined ||
      response.context_text !== undefined ||
      response.chunks !== undefined ||
      response.token_info !== undefined
  );

  if (!isKienSchema) {
    return {
      result_id: String(response.result_id || ""),
      llm_context: response.llm_context || "",
      citations: normalizeArray(response.citations),
      source_documents: normalizeArray(response.source_documents),
      context_chunks: normalizeArray(response.context_chunks)
    };
  }

  const hotelId = response.hotel_id ?? response.result_id ?? "";

  return {
    result_id: String(hotelId),
    hotel_id: hotelId,
    query_id: response.query_id || "",
    context_text: response.context_text || "",
    chunks: normalizeArray(response.chunks).map(normalizeContextChunk),
    citations: normalizeArray(response.citations).map(normalizeCitation),
    metadata: response.metadata || {},
    token_info: response.token_info || null,
    latency_ms: response.latency_ms,
    raw: response
  };
}

export function normalizeApiError(error, endpoint = "") {
  const apiError = error?.error || error;

  return {
    code: apiError?.code || error?.code || "UNKNOWN_ERROR",
    message: apiError?.message || error?.message || "Unexpected API error",
    user_message: apiError?.user_message || error?.user_message || "",
    query_id: apiError?.query_id || error?.query_id || "",
    details: apiError?.details || error?.details || {},
    status: error?.status,
    endpoint,
    raw: error
  };
}

function findMockQuery(query) {
  const normalizedQuery = query.trim().toLowerCase();
  return mockResponses.search_api.queries.find(
    (item) => item.query.trim().toLowerCase() === normalizedQuery
  );
}

function findMockV2SearchResponse(query) {
  const normalizedQuery = query.trim().toLowerCase();
  return mockResponsesV2.search_api.responses.find(
    (item) => item.query.trim().toLowerCase() === normalizedQuery
  );
}

function buildSearchV2Request(query, options = {}) {
  return {
    query,
    top_k: options.top_k,
    page: options.page,
    filters: options.filters,
    options: {
      include_debug: options.include_debug
    }
  };
}

function buildContextV2Request({ hotel_id, query, query_id, options = {} }) {
  return {
    hotel_id,
    query,
    query_id,
    options
  };
}

async function parseJsonResponse(response, endpoint) {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw normalizeApiError({ ...data, status: response.status }, endpoint);
  }

  return data;
}

export async function search(query, filters = {}) {
  if (config.USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    const mockMatch = findMockQuery(query);
    return normalizeSearchResponse(
      mockMatch || { query, results: [], total: 0, filters },
      "mock"
    );
  }

  const endpoint = `${config.API_BASE_URL}${config.SEARCH_ENDPOINT}`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, filters })
    });

    const data = await parseJsonResponse(response, endpoint);
    return normalizeSearchResponse(data, "api");
  } catch (error) {
    throw normalizeApiError(error, endpoint);
  }
}

export async function getContext(resultId) {
  if (config.USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const context = mockResponses.context_api.contexts_by_result_id[resultId] || {
      result_id: resultId,
      llm_context: "",
      citations: [],
      source_documents: [],
      context_chunks: []
    };
    return normalizeContextResponse(context);
  }

  const endpoint = `${config.API_BASE_URL}${config.CONTEXT_ENDPOINT}`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result_id: resultId })
    });

    const data = await parseJsonResponse(response, endpoint);
    return normalizeContextResponse(data);
  } catch (error) {
    throw normalizeApiError(error, endpoint);
  }
}

export async function searchV2(query, options = {}) {
  if (config.USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    const mockMatch = findMockV2SearchResponse(query);
    return normalizeSearchResponse(
      mockMatch || {
        query_id: "q-demo-no-results-000",
        query,
        total_found: 0,
        returned: 0,
        page: options.page || 0,
        latency_ms: 0,
        parsed_intent: {
          original_query: query,
          normalized_query: query.trim().toLowerCase(),
          hard_filters: {},
          keyword_expansion: [],
          intent_type: "hotel_search",
          confidence: 0,
          parsed_by: "rule_based"
        },
        results: []
      },
      "mock_v2"
    );
  }

  const endpoint = `${config.API_BASE_URL}${SEARCH_V2_ENDPOINT}`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildSearchV2Request(query, options))
    });

    const data = await parseJsonResponse(response, endpoint);
    return normalizeSearchResponse(data, "api_v2");
  } catch (error) {
    throw normalizeApiError(error, endpoint);
  }
}

export async function getContextV2({ hotel_id, query, query_id, options = {} }) {
  if (config.USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const key =
      options.include_chunks === false
        ? `${hotel_id}_no_chunks`
        : String(hotel_id);
    const context = mockResponsesV2.context_api.responses_by_hotel_id[key];

    if (!context) {
      throw normalizeApiError(mockResponsesV2.errors.HOTEL_NOT_FOUND, CONTEXT_V2_ENDPOINT);
    }

    return normalizeContextResponse(context);
  }

  const endpoint = `${config.API_BASE_URL}${CONTEXT_V2_ENDPOINT}`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildContextV2Request({ hotel_id, query, query_id, options }))
    });

    const data = await parseJsonResponse(response, endpoint);
    return normalizeContextResponse(data);
  } catch (error) {
    throw normalizeApiError(error, endpoint);
  }
}
