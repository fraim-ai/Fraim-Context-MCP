"""Stage 1.2: Pydantic Model Tests.

These tests verify that all Pydantic models validate correctly.
Run with: doppler run -- uv run pytest tests/stage_1/test_models.py -v
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.stage1
def test_chunk_result_model() -> None:
    """Test ChunkResult model validation."""
    from fraim_mcp.database.models import ChunkResult
    
    chunk = ChunkResult(
        id=uuid4(),
        document_id=uuid4(),
        content="This is test content for the chunk.",
        score=0.85,
        document_path="docs/api/auth.md",
        document_title="Authentication Guide",
        category="references",
        chunk_index=0,
        metadata={"source": "markdown"},
    )
    
    assert chunk.score == 0.85
    assert chunk.category == "references"
    assert chunk.chunk_index == 0


@pytest.mark.stage1
def test_chunk_result_score_bounds() -> None:
    """Test that ChunkResult score is bounded 0-1."""
    from pydantic import ValidationError
    
    from fraim_mcp.database.models import ChunkResult
    
    # Score > 1 should fail
    with pytest.raises(ValidationError):
        ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            content="Test",
            score=1.5,  # Invalid: > 1
            document_path="test.md",
            chunk_index=0,
        )
    
    # Score < 0 should fail
    with pytest.raises(ValidationError):
        ChunkResult(
            id=uuid4(),
            document_id=uuid4(),
            content="Test",
            score=-0.1,  # Invalid: < 0
            document_path="test.md",
            chunk_index=0,
        )


@pytest.mark.stage1
def test_document_model() -> None:
    """Test Document model validation."""
    from fraim_mcp.database.models import Document
    
    now = datetime.now(timezone.utc)
    doc = Document(
        id=uuid4(),
        project_id=uuid4(),
        path="docs/readme.md",
        title="README",
        content_hash="abc123def456",
        category="intent",
        metadata={},
        created_at=now,
        updated_at=now,
    )
    
    assert doc.path == "docs/readme.md"
    assert doc.category == "intent"


@pytest.mark.stage1
def test_search_request_model() -> None:
    """Test SearchRequest model validation."""
    from fraim_mcp.database.models import SearchRequest
    
    request = SearchRequest(
        query="How does authentication work?",
        project_id="my-project",
        top_k=5,
        category="references",
        use_reranker=True,
    )
    
    assert request.query == "How does authentication work?"
    assert request.top_k == 5


@pytest.mark.stage1
def test_search_request_validation() -> None:
    """Test SearchRequest validation rules."""
    from pydantic import ValidationError
    
    from fraim_mcp.database.models import SearchRequest
    
    # Empty query should fail
    with pytest.raises(ValidationError):
        SearchRequest(query="", project_id="test")
    
    # top_k out of bounds should fail
    with pytest.raises(ValidationError):
        SearchRequest(query="test", project_id="test", top_k=100)  # > 50


@pytest.mark.stage1
def test_search_response_model() -> None:
    """Test SearchResponse model validation."""
    from fraim_mcp.database.models import ChunkResult, SearchResponse
    
    chunk = ChunkResult(
        id=uuid4(),
        document_id=uuid4(),
        content="Test content",
        score=0.9,
        document_path="test.md",
        chunk_index=0,
    )
    
    response = SearchResponse(
        results=[chunk],
        query="test query",
        project_id="test-project",
        total_found=1,
        latency_ms=45,
        cache_hit=False,
        corpus_version=1,
    )
    
    assert len(response.results) == 1
    assert response.latency_ms == 45


@pytest.mark.stage1
def test_project_model() -> None:
    """Test Project model validation."""
    from fraim_mcp.database.models import Project
    
    now = datetime.now(timezone.utc)
    project = Project(
        id=uuid4(),
        slug="my-project",
        name="My Project",
        settings={"theme": "dark"},
        corpus_version=1,
        created_at=now,
        updated_at=now,
    )
    
    assert project.slug == "my-project"
    assert project.corpus_version == 1


@pytest.mark.stage1
def test_error_response_model() -> None:
    """Test ErrorResponse model."""
    from fraim_mcp.database.models import ErrorResponse
    
    error = ErrorResponse(
        error="Invalid query",
        detail="Query cannot be empty",
        code="INVALID_QUERY",
        request_id="req_123",
    )
    
    assert error.code == "INVALID_QUERY"

