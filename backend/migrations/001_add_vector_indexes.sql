-- Migration: Add HNSW vector indexes for product and technology embeddings
-- Date: 2025-10-21
-- Purpose: Dramatically improve performance for semantic similarity searches

-- Prerequisites:
-- 1. pgvector extension must be installed
-- 2. Embedding tables must exist with Vector(1536) columns

-- Add HNSW index for product embeddings
-- HNSW (Hierarchical Navigable Small World) is an approximate nearest neighbor algorithm
-- that provides excellent query performance for high-dimensional vectors
-- Using cosine distance operator for similarity searches
CREATE INDEX IF NOT EXISTS product_embeddings_embedding_idx
ON product_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Add HNSW index for technology embeddings
CREATE INDEX IF NOT EXISTS technology_embeddings_embedding_idx
ON technology_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Create composite index for frequently queried combinations
CREATE INDEX IF NOT EXISTS idx_tech_embeddings_type_tech_id
ON technology_embeddings (chunk_type, technology_id);

-- Performance notes:
-- - HNSW indexes trade off some accuracy for massive speed improvements
-- - Build time can be significant for large datasets (minutes for 100k vectors)
-- - Query time is typically 10-100x faster than sequential scan
-- - Memory usage is higher than B-tree indexes
-- - For production, consider tuning m and ef_construction parameters

-- To check index usage:
-- EXPLAIN ANALYZE SELECT * FROM product_embeddings
-- ORDER BY embedding <=> '[0.1,0.2,...]'::vector LIMIT 5;

-- To monitor index size:
-- SELECT pg_size_pretty(pg_total_relation_size('product_embeddings_embedding_idx'));
