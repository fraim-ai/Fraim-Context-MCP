"""Pydantic models for database entities and API contracts.

These models follow the contracts defined in specs/CONTRACTS.md.
DO NOT modify the field names or types without updating the spec.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str
    detail: str | None = None
    code: str  # e.g., "INVALID_QUERY", "PROJECT_NOT_FOUND"
    request_id: str | None = None


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    
    loc: list[str | int]
    msg: str
    type: str

