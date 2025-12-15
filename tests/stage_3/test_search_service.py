"""Stage 3.4: Search Service Orchestrator Tests.

These tests verify the complete search pipeline:
cache check → hybrid search → reranking → cache store

Run with: doppler run -- uv run pytest tests/stage_3/test_search_service.py -v

CRITICAL: DSPy is synchronous and MUST be wrapped in asyncio.to_thread()
"""

from uuid import uuid4

import pytest

pytestmark = pytest.mark.stage3


@pytest.fixture
async def db_client():
    """Create a database client."""
    from fraim_mcp.database.client import DatabaseClient
    
    client = DatabaseClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def cache_client():
    """Create a cache client."""
    from fraim_mcp.cache.redis_client import CacheClient
    
    client = CacheClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def embedding_client():
    """Create an embedding client."""
    from fraim_mcp.ingestion.embeddings import EmbeddingClient
    
    return EmbeddingClient()


@pytest.fixture
async def test_project_with_data(db_client, embedding_client):
    """Create a test project with sample data."""
    project_id = uuid4()
    slug = f"search-svc-{uuid4().hex[:8]}"
    doc_id = uuid4()
    
    contents = [
        "How to authenticate users with JWT tokens.",
        "Database schema design best practices.",
        "API rate limiting implementation guide.",
    ]
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO projects (id, slug, name) VALUES ($1, $2, $3)",
            project_id,
            slug,
            "Search Service Test",
        )
        
        await conn.execute(
            "INSERT INTO documents (id, project_id, path, content_hash) VALUES ($1, $2, $3, $4)",
            doc_id,
            project_id,
            "docs/test.md",
            "hash123",
        )
        
        for i, content in enumerate(contents):
            embedding = await embedding_client.embed(content)
            chunk_id = uuid4()
            
            await conn.execute(
                """
                INSERT INTO chunks (id, document_id, project_id, content, embedding, chunk_index)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                chunk_id,
                doc_id,
                project_id,
                content,
                embedding,
                i,
            )
        
        # Get corpus version
        corpus_version = await conn.fetchval(
            "SELECT corpus_version FROM projects WHERE id = $1",
            project_id,
        )
    
    yield {"id": project_id, "slug": slug, "corpus_version": corpus_version}
    
    # Cleanup
    async with db_client._pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


@pytest.fixture
async def search_service(db_client, cache_client, embedding_client):
    """Create a search service instance."""
    from fraim_mcp.retrieval.service import SearchService
    
    return SearchService(
        db_client=db_client,
        cache_client=cache_client,
        embedding_client=embedding_client,
    )


@pytest.mark.asyncio
async def test_search_returns_results(search_service, test_project_with_data) -> None:
    """Test that search service returns results."""
    from fraim_mcp.database.models import SearchRequest
    
    request = SearchRequest(
        query="How does authentication work?",
        project_id=test_project_with_data["slug"],
        top_k=3,
    )
    
    response = await search_service.search(request)
    
    assert len(response.results) > 0
    assert response.query == request.query
    assert response.project_id == request.project_id


@pytest.mark.asyncio
async def test_search_uses_cache(search_service, test_project_with_data, cache_client) -> None:
    """Test that search uses cache for repeated queries."""
    from fraim_mcp.database.models import SearchRequest
    
    request = SearchRequest(
        query="database design patterns",
        project_id=test_project_with_data["slug"],
        top_k=3,
    )
    
    # First search - should miss cache
    response1 = await search_service.search(request)
    assert response1.cache_hit is False
    
    # Second search - should hit cache
    response2 = await search_service.search(request)
    assert response2.cache_hit is True
    
    # Results should be the same
    assert len(response1.results) == len(response2.results)


@pytest.mark.asyncio
async def test_search_cache_miss_stores(search_service, test_project_with_data, cache_client) -> None:
    """Test that cache miss stores results for future use."""
    from fraim_mcp.cache.redis_client import generate_cache_key
    from fraim_mcp.database.models import SearchRequest
    
    unique_query = f"unique query {uuid4().hex[:8]}"
    
    request = SearchRequest(
        query=unique_query,
        project_id=test_project_with_data["slug"],
        top_k=3,
    )
    
    # Generate expected cache key
    cache_key = generate_cache_key(
        project_id=test_project_with_data["slug"],
        corpus_version=test_project_with_data["corpus_version"],
        query=unique_query,
    )
    
    # Initially should not be cached
    cached = await cache_client.get(cache_key)
    assert cached is None
    
    # Perform search
    await search_service.search(request)
    
    # Now should be cached
    cached = await cache_client.get(cache_key)
    assert cached is not None


@pytest.mark.asyncio
async def test_search_with_reranking(search_service, test_project_with_data) -> None:
    """Test that search applies reranking when enabled."""
    from fraim_mcp.database.models import SearchRequest
    
    request = SearchRequest(
        query="JWT token authentication",
        project_id=test_project_with_data["slug"],
        top_k=3,
        use_reranker=True,
    )
    
    response = await search_service.search(request)
    
    # Should return results
    assert len(response.results) > 0
    
    # Auth-related content should be top ranked
    top_content = response.results[0].content.lower()
    assert "jwt" in top_content or "auth" in top_content or "token" in top_content

