-- =============================================================================
-- Fraim Context MCP — Database Initialization
-- =============================================================================
-- Run with: doppler run -- psql $DATABASE_URL -f scripts/init_db.sql
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- TABLES
-- =============================================================================

-- Projects table (multi-tenant root)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    corpus_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    path VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    content_hash VARCHAR(64) NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(project_id, path)
);

-- Chunks table (with pgvector)
-- HARD CONTRACT: embedding dimension MUST be 1024
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search history (for analytics and feedback)
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_embedding vector(1024),
    result_ids UUID[] NOT NULL,
    feedback VARCHAR(20),
    latency_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Vector similarity index (HNSW for fast approximate search)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv ON chunks USING gin(content_tsv);

-- Composite indexes for filtered queries
CREATE INDEX IF NOT EXISTS idx_chunks_project_id ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_project_category ON documents(project_id, category);
CREATE INDEX IF NOT EXISTS idx_search_history_project ON search_history(project_id, created_at DESC);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to increment corpus version on document change
CREATE OR REPLACE FUNCTION increment_corpus_version()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects 
    SET corpus_version = corpus_version + 1,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.project_id, OLD.project_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

-- Triggers for corpus version
DROP TRIGGER IF EXISTS increment_corpus_on_document_change ON documents;
CREATE TRIGGER increment_corpus_on_document_change
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION increment_corpus_version();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Hybrid search function (vector + FTS with RRF fusion)
CREATE OR REPLACE FUNCTION hybrid_search(
    p_project_id UUID,
    p_embedding vector(1024),
    p_fts_query TEXT,
    p_limit INTEGER DEFAULT 10,
    p_category VARCHAR DEFAULT NULL,
    p_vector_weight FLOAT DEFAULT 0.7,
    p_fts_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    score FLOAT,
    vector_rank INTEGER,
    fts_rank INTEGER
) AS $$
WITH vector_search AS (
    SELECT 
        c.id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> p_embedding) as similarity,
        ROW_NUMBER() OVER (ORDER BY c.embedding <=> p_embedding) as rank
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.project_id = p_project_id
      AND (p_category IS NULL OR d.category = p_category)
    ORDER BY c.embedding <=> p_embedding
    LIMIT p_limit * 2
),
fts_search AS (
    SELECT 
        c.id,
        c.document_id,
        c.content,
        ts_rank_cd(c.content_tsv, plainto_tsquery('english', p_fts_query)) as rank_score,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.content_tsv, plainto_tsquery('english', p_fts_query)) DESC) as rank
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.project_id = p_project_id
      AND c.content_tsv @@ plainto_tsquery('english', p_fts_query)
      AND (p_category IS NULL OR d.category = p_category)
    ORDER BY rank_score DESC
    LIMIT p_limit * 2
),
combined AS (
    SELECT 
        COALESCE(v.id, f.id) as id,
        COALESCE(v.document_id, f.document_id) as document_id,
        COALESCE(v.content, f.content) as content,
        -- RRF (Reciprocal Rank Fusion) score
        (p_vector_weight * COALESCE(1.0 / (60 + v.rank), 0)) +
        (p_fts_weight * COALESCE(1.0 / (60 + f.rank), 0)) as rrf_score,
        v.rank as v_rank,
        f.rank as f_rank
    FROM vector_search v
    FULL OUTER JOIN fts_search f ON v.id = f.id
)
SELECT 
    id as chunk_id,
    document_id,
    content,
    rrf_score as score,
    v_rank::INTEGER as vector_rank,
    f_rank::INTEGER as fts_rank
FROM combined
ORDER BY rrf_score DESC
LIMIT p_limit;
$$ LANGUAGE SQL STABLE;

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Insert default project if not exists
INSERT INTO projects (slug, name, settings)
VALUES ('default', 'Default Project', '{"description": "Default project for testing"}')
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Verify setup
DO $$
DECLARE
    vector_version TEXT;
    project_count INTEGER;
BEGIN
    -- Check pgvector
    SELECT extversion INTO vector_version FROM pg_extension WHERE extname = 'vector';
    IF vector_version IS NULL THEN
        RAISE EXCEPTION 'pgvector extension not installed';
    END IF;
    
    -- Check tables
    SELECT COUNT(*) INTO project_count FROM projects;
    
    RAISE NOTICE '✅ Database initialized successfully';
    RAISE NOTICE '   pgvector version: %', vector_version;
    RAISE NOTICE '   Projects: %', project_count;
END $$;
