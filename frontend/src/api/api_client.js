import mockResponses from "../../mock_api_responses.json";
import { config } from "../config/config";
import { emptyMetadata } from "../types/searchTypes";

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeMetadata(metadata = {}) {
  return {
    ...emptyMetadata,
    ...metadata,
    amenities: normalizeArray(metadata.amenities),
    best_for: normalizeArray(metadata.best_for)
  };
}

function normalizeResult(result = {}) {
  return {
    id: String(result.id || ""),
    title: result.title || "Untitled result",
    snippet: result.snippet || "No snippet available",
    score: Number(result.score || 0),
    metadata: normalizeMetadata(result.metadata),
    citations: normalizeArray(result.citations),
    source_documents: normalizeArray(result.source_documents),
    context_chunks: normalizeArray(result.context_chunks)
  };
}

export function normalizeSearchResponse(response = {}, source = "api") {
  const results = normalizeArray(response.results).map(normalizeResult);
  return {
    query: response.query || "",
    results,
    total: Number(response.total ?? results.length),
    source
  };
}

export function normalizeContextResponse(response = {}) {
  return {
    result_id: String(response.result_id || ""),
    llm_context: response.llm_context || "",
    citations: normalizeArray(response.citations),
    source_documents: normalizeArray(response.source_documents),
    context_chunks: normalizeArray(response.context_chunks)
  };
}

export function normalizeApiError(error, endpoint = "") {
  return {
    message: error?.message || "Unexpected API error",
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

    if (!response.ok) {
      throw { message: `Search API failed with status ${response.status}`, status: response.status };
    }

    const data = await response.json();
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

    if (!response.ok) {
      throw { message: `Context API failed with status ${response.status}`, status: response.status };
    }

    const data = await response.json();
    return normalizeContextResponse(data);
  } catch (error) {
    throw normalizeApiError(error, endpoint);
  }
}
