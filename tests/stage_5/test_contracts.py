"""
Stage 5.2: Contract Tests

Validates that all API responses match the contracts defined in CONTRACTS.md.
"""

import pytest
from pydantic import ValidationError

from fraim_mcp.database.models import (
    ChunkResult,
    SearchRequest,
    SearchResponse,
    Document,
    Project,
    ErrorResponse,
)


class TestSearchResponseSchema:
    """Validate SearchResponse matches contract."""
    
    def test_search_response_required_fields(self):
        """SearchResponse must have all required fields."""
        from uuid import uuid4
        
        # Valid response
        response = SearchResponse(
            query="test query",
            results=[],
            project_id="test-project",
            total_found=0,
            latency_ms=10,
            cache_hit=False,
            corpus_version=1,
        )
        
        assert response.query == "test query"
        assert response.results == []
        assert response.total_found == 0
        assert response.cache_hit is False
    
    def test_search_response_with_results(self):
        """SearchResponse with actual results."""
        from uuid import uuid4
        
        chunk = ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            document_path="/docs/test.md",
            content="Test content here",
            score=0.95,
            category="docs",
            chunk_index=0,
            metadata={"source": "test"},
        )
        
        response = SearchResponse(
            query="test",
            results=[chunk],
            project_id="test-project",
            total_found=1,
            latency_ms=42,
            cache_hit=False,
            corpus_version=1,
        )
        
        assert len(response.results) == 1
        assert response.results[0].score == 0.95
        assert response.latency_ms == 42
    
    def test_search_response_serialization(self):
        """SearchResponse must serialize to JSON-compatible dict."""
        from uuid import uuid4
        
        chunk = ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            document_path="/docs/test.md",
            content="Test content",
            score=0.9,
            chunk_index=0,
        )
        
        response = SearchResponse(
            query="test",
            results=[chunk],
            project_id="test-project",
            total_found=1,
            latency_ms=10,
            cache_hit=True,
            corpus_version=1,
        )
        
        data = response.model_dump(mode="json")
        
        # All fields should be JSON serializable
        assert isinstance(data, dict)
        assert isinstance(data["results"], list)
        assert isinstance(data["results"][0], dict)
        assert "id" in data["results"][0]


class TestChunkResultSchema:
    """Validate ChunkResult matches contract."""
    
    def test_chunk_result_required_fields(self):
        """ChunkResult must have required fields."""
        from uuid import uuid4
        
        chunk = ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            document_path="/path/to/doc.md",
            content="The actual chunk content",
            score=0.85,
            chunk_index=0,
        )
        
        assert chunk.document_path == "/path/to/doc.md"
        assert chunk.content == "The actual chunk content"
        assert chunk.score == 0.85
    
    def test_chunk_result_optional_fields(self):
        """ChunkResult optional fields have correct defaults."""
        from uuid import uuid4
        
        chunk = ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            document_path="/doc.md",
            content="Content",
            score=0.5,
            chunk_index=0,
        )
        
        # Default category
        assert chunk.category == "general"
        assert isinstance(chunk.metadata, dict)
    
    def test_chunk_result_score_bounds(self):
        """Score should typically be between 0 and 1."""
        from uuid import uuid4
        
        # Valid scores
        chunk = ChunkResult(
            id=uuid4(), document_id=uuid4(), document_path="/p",
            content="x", score=0.0, chunk_index=0
        )
        assert chunk.score == 0.0
        
        chunk = ChunkResult(
            id=uuid4(), document_id=uuid4(), document_path="/p",
            content="x", score=1.0, chunk_index=0
        )
        assert chunk.score == 1.0


class TestSearchRequestSchema:
    """Validate SearchRequest matches contract."""
    
    def test_search_request_minimal(self):
        """SearchRequest with only required fields."""
        request = SearchRequest(
            query="how do I configure authentication?",
            project_id="my-project",
        )
        
        assert request.query == "how do I configure authentication?"
        assert request.project_id == "my-project"
        assert request.top_k == 5  # default
    
    def test_search_request_with_options(self):
        """SearchRequest with optional filters."""
        request = SearchRequest(
            query="API reference",
            project_id="docs-project",
            top_k=10,
            category="api",
            include_metadata=True,
        )
        
        assert request.top_k == 10
        assert request.category == "api"
        assert request.include_metadata is True
    
    def test_search_request_validation(self):
        """SearchRequest validates required fields."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test")  # Missing project_id
        
        with pytest.raises(ValidationError):
            SearchRequest(project_id="proj", query="")  # Empty query


class TestDocumentSchema:
    """Validate Document model matches contract."""
    
    def test_document_creation(self):
        """Document can be created with required fields."""
        from datetime import datetime
        from uuid import uuid4
        
        doc = Document(
            id=uuid4(),
            project_id=uuid4(),
            path="/docs/readme.md",
            content_hash="sha256-abc123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert doc.path == "/docs/readme.md"
    
    def test_document_with_metadata(self):
        """Document supports metadata field."""
        from datetime import datetime
        from uuid import uuid4
        
        doc = Document(
            id=uuid4(),
            project_id=uuid4(),
            path="/doc.md",
            content_hash="hash",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"author": "test", "version": 2},
        )
        
        assert doc.metadata["author"] == "test"
        assert doc.metadata["version"] == 2


class TestProjectSchema:
    """Validate Project model matches contract."""
    
    def test_project_creation(self):
        """Project can be created."""
        from datetime import datetime
        from uuid import uuid4
        
        project = Project(
            id=uuid4(),
            slug="my-project",
            name="My Documentation Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert project.name == "My Documentation Project"
    
    def test_project_with_settings(self):
        """Project supports settings/config."""
        from datetime import datetime
        from uuid import uuid4
        
        project = Project(
            id=uuid4(),
            slug="test-project",
            name="Test Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            settings={"default_top_k": 10, "cache_ttl": 3600},
        )
        
        assert project.settings["default_top_k"] == 10


class TestErrorResponseSchema:
    """Validate ErrorResponse matches contract."""
    
    def test_error_response_basic(self):
        """ErrorResponse with code and message."""
        error = ErrorResponse(
            error="not_found",
            code="NOT_FOUND",
        )
        
        assert error.error == "not_found"
        assert error.code == "NOT_FOUND"
    
    def test_error_response_with_details(self):
        """ErrorResponse with additional details."""
        error = ErrorResponse(
            error="validation_error",
            detail="Invalid request parameters",
            code="VALIDATION_ERROR",
        )
        
        assert error.detail == "Invalid request parameters"
    
    def test_error_response_serialization(self):
        """ErrorResponse serializes correctly for API responses."""
        error = ErrorResponse(
            error="internal_error",
            code="INTERNAL_ERROR",
            request_id="req-abc-123",
        )
        
        data = error.model_dump()
        assert isinstance(data, dict)
        assert data["error"] == "internal_error"
        assert data["request_id"] == "req-abc-123"


class TestMCPToolSchemas:
    """Validate MCP tool input/output schemas."""
    
    def test_search_docs_input_schema(self):
        """search_docs tool input matches SearchRequest."""
        # MCP tool receives these parameters
        tool_input = {
            "query": "How to authenticate?",
            "project_id": "my-docs",
            "top_k": 5,
        }
        
        # Should be parseable as SearchRequest
        request = SearchRequest(**tool_input)
        assert request.query == "How to authenticate?"
    
    def test_search_docs_output_schema(self):
        """search_docs tool output is LLM-friendly."""
        from uuid import uuid4
        
        chunk = ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            document_path="/auth/oauth.md",
            content="OAuth2 authentication flow involves...",
            score=0.92,
            chunk_index=0,
        )
        
        response = SearchResponse(
            query="authentication",
            results=[chunk],
            project_id="test-project",
            total_found=1,
            latency_ms=10,
            cache_hit=False,
            corpus_version=1,
        )
        
        # Tool returns text content that's useful for LLM
        output = response.model_dump(mode="json")
        
        # Results should have content the LLM can use
        assert "content" in output["results"][0]
        assert len(output["results"][0]["content"]) > 0
    
    def test_list_docs_output_schema(self):
        """list_docs tool returns document listing."""
        from datetime import datetime
        from uuid import uuid4
        
        docs = [
            Document(
                id=uuid4(),
                project_id=uuid4(),
                path="/docs/getting-started.md",
                content_hash="hash1",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Document(
                id=uuid4(),
                project_id=uuid4(),
                path="/docs/api-reference.md",
                content_hash="hash2",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        # Should be serializable
        output = [d.model_dump(mode="json") for d in docs]
        assert len(output) == 2
        assert output[0]["path"] == "/docs/getting-started.md"
