"""Vector retrieval package backed by Supabase/Postgres pgvector."""

from retrieval.vector_search.service import PgVectorSearchService, create_pgvector_search_service

__all__ = ["PgVectorSearchService", "create_pgvector_search_service"]
