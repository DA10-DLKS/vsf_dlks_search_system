-- Supabase pgvector schema for DA10 vector retrieval.
-- Run this file in Supabase SQL Editor or via psql using DATABASE_URL.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS text_chunks (
    chunk_id TEXT PRIMARY KEY,
    hotel_id INTEGER,
    source_type TEXT NOT NULL,
    section TEXT,
    strategy TEXT,
    text TEXT NOT NULL,
    raw_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_text_chunks_hotel_id
    ON text_chunks (hotel_id);

CREATE INDEX IF NOT EXISTS idx_text_chunks_source_type
    ON text_chunks (source_type);

CREATE INDEX IF NOT EXISTS idx_text_chunks_metadata
    ON text_chunks
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_text_chunks_embedding_hnsw
    ON text_chunks
    USING hnsw (embedding vector_cosine_ops);

