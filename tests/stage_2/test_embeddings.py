"""Stage 2.2: Embedding Generation Tests.

These tests verify embedding generation with the HARD CONTRACT of 1024 dimensions.
Run with: doppler run -- uv run pytest tests/stage_2/test_embeddings.py -v

HARD CONTRACT: All embeddings MUST be 1024 dimensions (voyage-3 model).
"""

import pytest

pytestmark = pytest.mark.stage2


@pytest.fixture
def embedding_client():
    """Create an embedding client for testing."""
    from fraim_mcp.ingestion.embeddings import EmbeddingClient
    
    return EmbeddingClient()


@pytest.mark.asyncio
async def test_embedding_returns_list(embedding_client) -> None:
    """Test that embedding generation returns a list of floats."""
    embedding = await embedding_client.embed("Hello, world!")
    
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embedding_dimension_is_1024(embedding_client) -> None:
    """HARD CONTRACT: Embedding dimension MUST be 1024.
    
    This is a critical test. The database schema is:
        embedding vector(1024)
    
    Any other dimension will cause schema violations.
    """
    embedding = await embedding_client.embed("Test text for embedding dimension check.")
    
    assert len(embedding) == 1024, (
        f"HARD CONTRACT VIOLATION: Expected 1024 dimensions, got {len(embedding)}. "
        "Database schema requires vector(1024). Check embedding model configuration."
    )


@pytest.mark.asyncio
async def test_batch_embedding(embedding_client) -> None:
    """Test batch embedding of multiple texts."""
    texts = [
        "First document about authentication.",
        "Second document about database design.",
        "Third document about API endpoints.",
    ]
    
    embeddings = await embedding_client.embed_batch(texts)
    
    assert len(embeddings) == 3
    for emb in embeddings:
        assert len(emb) == 1024, f"Expected 1024 dims, got {len(emb)}"


@pytest.mark.asyncio
async def test_embedding_consistency(embedding_client) -> None:
    """Test that same text produces consistent embeddings."""
    text = "Consistency test for embeddings."
    
    emb1 = await embedding_client.embed(text)
    emb2 = await embedding_client.embed(text)
    
    # Embeddings should be identical or very close
    # (some models may have slight variations)
    assert len(emb1) == len(emb2)
    
    # Check first 10 values are close
    for i in range(10):
        assert abs(emb1[i] - emb2[i]) < 0.01, (
            f"Embedding inconsistency at index {i}: {emb1[i]} vs {emb2[i]}"
        )


@pytest.mark.asyncio
async def test_embedding_adapter_for_llamaindex(embedding_client) -> None:
    """Test that embedding client can be used as LlamaIndex adapter."""
    # The client should have a sync method for LlamaIndex compatibility
    assert hasattr(embedding_client, "get_text_embedding")
    
    # Test the sync wrapper
    embedding = embedding_client.get_text_embedding("Test for LlamaIndex.")
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1024


def test_embedding_client_has_model_info(embedding_client) -> None:
    """Test that embedding client exposes model information."""
    assert embedding_client.model_name is not None
    assert embedding_client.dimension == 1024

