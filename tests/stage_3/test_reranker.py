"""Stage 3.3: FlashRank Reranker Tests.

These tests verify the FlashRank reranking implementation.
Run with: doppler run -- uv run pytest tests/stage_3/test_reranker.py -v

FlashRank provides fast, local reranking without API calls.
"""

import pytest

pytestmark = pytest.mark.stage3


@pytest.fixture
def reranker():
    """Create a reranker instance."""
    from fraim_mcp.retrieval.reranker import Reranker
    
    return Reranker()


def test_reranker_loads_model(reranker) -> None:
    """Test that FlashRank model loads successfully."""
    assert reranker.model is not None
    assert reranker.is_loaded


def test_rerank_changes_order(reranker) -> None:
    """Test that reranking can change the order of results."""
    query = "How to configure database connections"
    
    # Documents in suboptimal order
    documents = [
        {"id": "1", "content": "Python list comprehension tutorial"},
        {"id": "2", "content": "Database connection pooling and configuration"},
        {"id": "3", "content": "JavaScript async/await patterns"},
        {"id": "4", "content": "PostgreSQL connection string format"},
    ]
    
    reranked = reranker.rerank(query, documents, top_k=4)
    
    # Database-related content should be ranked higher
    top_ids = [doc["id"] for doc in reranked[:2]]
    assert "2" in top_ids or "4" in top_ids


def test_rerank_respects_top_k(reranker) -> None:
    """Test that reranking respects top_k limit."""
    query = "test query"
    
    documents = [
        {"id": str(i), "content": f"Document content {i}"}
        for i in range(10)
    ]
    
    # Request only top 3
    reranked = reranker.rerank(query, documents, top_k=3)
    
    assert len(reranked) == 3


def test_rerank_adds_scores(reranker) -> None:
    """Test that reranking adds relevance scores."""
    query = "machine learning models"
    
    documents = [
        {"id": "1", "content": "Neural network training techniques"},
        {"id": "2", "content": "Recipe for chocolate cake"},
    ]
    
    reranked = reranker.rerank(query, documents, top_k=2)
    
    # Each result should have a rerank_score
    for doc in reranked:
        assert "rerank_score" in doc
        assert isinstance(doc["rerank_score"], float)
    
    # ML content should score higher than cake
    ml_doc = next(d for d in reranked if d["id"] == "1")
    cake_doc = next(d for d in reranked if d["id"] == "2")
    assert ml_doc["rerank_score"] > cake_doc["rerank_score"]


def test_rerank_handles_empty_input(reranker) -> None:
    """Test that reranker handles empty input gracefully."""
    reranked = reranker.rerank("query", [], top_k=5)
    assert reranked == []


def test_rerank_preserves_original_fields(reranker) -> None:
    """Test that reranking preserves all original document fields."""
    query = "test"
    
    documents = [
        {
            "id": "1",
            "content": "Test content",
            "document_path": "docs/test.md",
            "custom_field": "preserved",
        }
    ]
    
    reranked = reranker.rerank(query, documents, top_k=1)
    
    assert len(reranked) == 1
    assert reranked[0]["document_path"] == "docs/test.md"
    assert reranked[0]["custom_field"] == "preserved"

