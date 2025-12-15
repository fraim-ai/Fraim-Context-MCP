# API & Database Contracts

> **Version**: 5.1.0  
> **Status**: READ-ONLY  
> **Last Updated**: December 2025

---

## Database Schema

### Tables

```sql
-- Projects table (multi-tenant root)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    corpus_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table
CREATE TABLE documents (
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
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,  -- HARD CONTRACT: 1024 dimensions
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search history (for analytics)
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_embedding vector(1024),
    result_ids UUID[] NOT NULL,
    feedback VARCHAR(20),  -- 'helpful', 'not_helpful', null
    latency_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes

```sql
-- Vector similarity index (HNSW for speed)
CREATE INDEX idx_chunks_embedding ON chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX idx_chunks_content_tsv ON chunks USING gin(content_tsv);

-- Composite indexes for filtered queries
CREATE INDEX idx_chunks_project_id ON chunks(project_id);
CREATE INDEX idx_documents_project_category ON documents(project_id, category);
CREATE INDEX idx_search_history_project ON search_history(project_id, created_at DESC);
```

---

## Pydantic Models

### Core Models

```python
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

class ChunkResult(BaseModel):
    """Single search result chunk."""
    id: UUID
    document_id: UUID
    content: str
    score: float = Field(ge=0, le=1, description="Relevance score 0-1")
    document_path: str
    document_title: str | None = None
    category: str = "general"
    chunk_index: int
    metadata: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str = Field(min_length=1, max_length=1000)
    project_id: str = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=50)
    category: str | None = None
    use_reranker: bool = True
    include_metadata: bool = False


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    results: list[ChunkResult]
    query: str
    project_id: str
    total_found: int
    latency_ms: int
    cache_hit: bool = False
    corpus_version: int


class Document(BaseModel):
    """Document metadata."""
    id: UUID
    project_id: UUID
    path: str
    title: str | None = None
    content_hash: str
    category: str = "general"
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Project(BaseModel):
    """Project (tenant) model."""
    id: UUID
    slug: str
    name: str
    settings: dict = Field(default_factory=dict)
    corpus_version: int = 1
    created_at: datetime
    updated_at: datetime
```

### Error Models

```python
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
    code: str  # e.g., "INVALID_QUERY", "PROJECT_NOT_FOUND"
    request_id: str | None = None


class ValidationError(BaseModel):
    """Validation error detail."""
    loc: list[str | int]
    msg: str
    type: str
```

---

## MCP Tool Schemas

### search_docs Tool

```json
{
  "name": "search_docs",
  "description": "Search project documentation using semantic + keyword search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query",
        "minLength": 1,
        "maxLength": 1000
      },
      "project_id": {
        "type": "string",
        "description": "Project identifier",
        "default": "default"
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results to return",
        "minimum": 1,
        "maximum": 20,
        "default": 5
      },
      "category": {
        "type": "string",
        "description": "Filter by document category",
        "enum": ["intent", "research", "references", "process", "workspace"]
      }
    },
    "required": ["query"]
  }
}
```

### get_document Tool

```json
{
  "name": "get_document",
  "description": "Retrieve full document content by path",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Document path (e.g., 'docs/api/auth.md')"
      },
      "project_id": {
        "type": "string",
        "description": "Project identifier",
        "default": "default"
      }
    },
    "required": ["path"]
  }
}
```

### list_categories Tool

```json
{
  "name": "list_categories",
  "description": "List available document categories for a project",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_id": {
        "type": "string",
        "description": "Project identifier",
        "default": "default"
      }
    }
  }
}
```

---

## HTTP API Endpoints

### Search Endpoint

```
POST /api/v1/search
Content-Type: application/json

Request:
{
  "query": "how does authentication work",
  "project_id": "my-project",
  "top_k": 5,
  "category": null,
  "use_reranker": true
}

Response (200 OK):
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "document_id": "550e8400-e29b-41d4-a716-446655440001",
      "content": "Authentication is handled via JWT tokens...",
      "score": 0.92,
      "document_path": "docs/api/authentication.md",
      "document_title": "Authentication Guide",
      "category": "references",
      "chunk_index": 0,
      "metadata": {}
    }
  ],
  "query": "how does authentication work",
  "project_id": "my-project",
  "total_found": 12,
  "latency_ms": 145,
  "cache_hit": false,
  "corpus_version": 42
}

Error Response (400/500):
{
  "error": "Invalid query",
  "detail": "Query cannot be empty",
  "code": "INVALID_QUERY",
  "request_id": "req_abc123"
}
```

### Health Endpoint

```
GET /health

Response (200 OK):
{
  "status": "healthy",
  "version": "5.1.0",
  "database": "connected",
  "cache": "connected",
  "uptime_seconds": 3600
}

Response (503 Service Unavailable):
{
  "status": "unhealthy",
  "version": "5.1.0",
  "database": "disconnected",
  "cache": "connected",
  "error": "Database connection failed"
}
```

### SSE Streaming Endpoint

```
GET /api/v1/search/stream?query=...&project_id=...

Response (text/event-stream):
event: search_started
data: {"query": "...", "project_id": "..."}

event: cache_check
data: {"hit": false, "key": "fraim:proj:v42:..."}

event: embedding
data: {"model": "voyage-3", "latency_ms": 120}

event: search_results
data: {"count": 12, "latency_ms": 35}

event: rerank
data: {"input": 12, "output": 5, "latency_ms": 25}

event: complete
data: {"results": [...], "total_latency_ms": 180}
```

---

## Cache Key Format

```
fraim:{project_id}:v{corpus_version}:search:{query_hash}
```

**Examples:**
```
fraim:my-project:v42:search:a1b2c3d4
fraim:default:v1:search:e5f6g7h8
```

**TTL:** 3600 seconds (1 hour)

**Invalidation triggers:**
1. Document added/updated/deleted → increment `corpus_version`
2. Manual cache clear via admin endpoint
3. TTL expiration

---

## Embedding Contract

| Property | Value |
|----------|-------|
| Model | `voyage/voyage-3` (via OpenRouter or Gateway) |
| Dimensions | **1024** (HARD CONTRACT) |
| Normalization | L2 normalized |
| Max tokens | 8192 |

**Validation:**
```python
def validate_embedding(embedding: list[float]) -> None:
    if len(embedding) != 1024:
        raise ValueError(f"Expected 1024 dimensions, got {len(embedding)}")
```

---

**These contracts are fixed for v5.0.0. Do not modify during development.**
