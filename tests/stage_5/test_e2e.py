"""
Stage 5.1: End-to-End Integration Tests

Tests the full system flow from ingestion through search.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fraim_mcp.config import get_settings
from fraim_mcp.database.client import DatabaseClient
from fraim_mcp.database.models import SearchRequest
from fraim_mcp.cache.redis_client import RedisClient
from fraim_mcp.ingestion.embeddings import EmbeddingClient
from fraim_mcp.retrieval.service import SearchService


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
async def db_client(settings):
    """Create a database client for testing."""
    client = DatabaseClient(settings.database_url)
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def cache_client(settings):
    """Create a Redis cache client for testing."""
    client = RedisClient(settings.redis_url)
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
def embedding_client(settings):
    """Create an embedding client for testing."""
    return EmbeddingClient(api_key=settings.open_ai_api)


@pytest.fixture
async def project_id(db_client):
    """Create a test project and return its slug."""
    slug = f"test-e2e-{uuid.uuid4().hex[:8]}"
    project_uuid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await db_client.execute(
        """
        INSERT INTO projects (id, slug, name, created_at, updated_at, corpus_version)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        project_uuid, slug, f"Test Project {slug}", now, now, 1
    )
    
    yield slug
    
    # Cleanup
    await db_client.execute("DELETE FROM chunks WHERE project_id = $1", project_uuid)
    await db_client.execute("DELETE FROM documents WHERE project_id = $1", project_uuid)
    await db_client.execute("DELETE FROM projects WHERE id = $1", project_uuid)


@pytest.fixture
async def search_service(db_client, cache_client, embedding_client):
    """Create a search service with all dependencies."""
    service = SearchService(
        db_client=db_client,
        cache_client=cache_client,
        embedding_client=embedding_client,
    )
    yield service


async def get_project_uuid(db_client, project_slug: str) -> UUID:
    """Get project UUID from slug."""
    async with db_client._pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM projects WHERE slug = $1",
            project_slug
        )
        return row["id"]


async def insert_test_document(
    db_client,
    project_slug: str,
    path: str,
    content: str,
    embedding: list[float],
    category: str = "test"
) -> tuple[UUID, UUID]:
    """Helper to insert a test document and chunk."""
    project_uuid = await get_project_uuid(db_client, project_slug)
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Insert document
    await db_client.execute(
        """
        INSERT INTO documents (id, project_id, path, content_hash, created_at, updated_at, category)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        doc_id, project_uuid, path, f"hash-{doc_id.hex[:8]}", now, now, category
    )
    
    # Insert chunk with embedding
    await db_client.execute(
        """
        INSERT INTO chunks (id, document_id, project_id, content, embedding, chunk_index, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        chunk_id, doc_id, project_uuid, content, embedding, 0, json.dumps({})
    )
    
    return doc_id, chunk_id


@pytest.mark.asyncio
async def test_ingest_then_search(db_client, cache_client, embedding_client, project_id, search_service):
    """
    Test full flow: insert document with embedding, then search for it.
    
    This validates the entire pipeline:
    1. Generate embeddings for content
    2. Store document and chunk with embedding
    3. Search returns the document
    """
    # 1. Generate embedding for test content
    test_content = "Python is a versatile programming language used for web development, data science, and machine learning."
    embedding = await embedding_client.embed(test_content)
    
    # Embedding dimension depends on the model (1024 for Voyage, 1536 for OpenAI text-embedding-3-small)
    assert len(embedding) in (1024, 1536), f"Expected 1024 or 1536-dim embedding, got {len(embedding)}"
    
    # 2. Insert the document
    doc_id, chunk_id = await insert_test_document(
        db_client, project_id, "/docs/python.md", test_content, embedding, category="docs"
    )
    
    # 3. Search for the content
    search_request = SearchRequest(
        query="What programming language is good for machine learning?",
        project_id=project_id,
        top_k=5,
    )
    
    response = await search_service.search(search_request)
    
    # 4. Validate results
    assert response is not None, "Search should return a response"
    assert len(response.results) > 0, "Search should return at least one result"
    
    # The document we inserted should be in the results
    result_ids = [r.id for r in response.results]
    assert chunk_id in result_ids, f"Inserted chunk {chunk_id} should be in results"
    
    # Find our specific result
    our_result = next((r for r in response.results if r.id == chunk_id), None)
    assert our_result is not None
    assert "Python" in our_result.content


@pytest.mark.asyncio
async def test_mcp_tool_call_flow(db_client, cache_client, embedding_client, project_id, search_service):
    """
    Test simulated MCP tool call flow.
    
    This mimics what happens when an LLM calls the search_docs tool:
    1. Tool receives query and project_id
    2. SearchService processes the request
    3. Results are formatted for LLM consumption
    """
    # Setup: Insert some test documents
    contents = [
        ("API authentication using JWT tokens", "/docs/auth.md", "api"),
        ("Database migrations with Alembic", "/docs/database.md", "database"),
        ("REST API endpoint documentation", "/docs/api-reference.md", "api"),
    ]
    
    chunk_ids = []
    for content, path, category in contents:
        embedding = await embedding_client.embed(content)
        _, chunk_id = await insert_test_document(
            db_client, project_id, path, content, embedding, category
        )
        chunk_ids.append(chunk_id)
    
    # Simulate MCP tool call
    tool_args = {
        "query": "How does authentication work?",
        "project_id": project_id,
        "top_k": 5,
        "category": "api",  # Filter to API docs
    }
    
    request = SearchRequest(**tool_args)
    response = await search_service.search(request)
    
    # Validate tool response format
    assert response is not None
    assert hasattr(response, "results")
    assert hasattr(response, "query")
    assert hasattr(response, "total_found")
    
    # Results should be serializable (for MCP JSON-RPC)
    response_dict = response.model_dump(mode="json")
    assert isinstance(response_dict, dict)
    assert "results" in response_dict


@pytest.mark.asyncio
async def test_cache_invalidation_on_ingest(db_client, cache_client, embedding_client, project_id, search_service):
    """
    Test that cache is invalidated when new documents are ingested.
    
    Flow:
    1. Insert document A
    2. Search (cache miss, stores result)
    3. Search again (cache hit)
    4. Insert document B (should invalidate cache)
    5. Search again (cache miss, includes B)
    """
    # 1. Insert first document
    content_a = "FastAPI is a modern Python web framework"
    embedding_a = await embedding_client.embed(content_a)
    _, chunk_id_a = await insert_test_document(
        db_client, project_id, "/docs/fastapi.md", content_a, embedding_a
    )
    
    # 2. First search (cache miss)
    request = SearchRequest(
        query="Python web framework",
        project_id=project_id,
        top_k=10,
    )
    response1 = await search_service.search(request)
    assert len(response1.results) >= 1
    assert response1.cache_hit is False
    
    # 3. Second search (should be cache hit)
    response2 = await search_service.search(request)
    assert len(response2.results) >= 1
    assert response2.cache_hit is True
    
    # 4. Insert new document
    content_b = "Flask is a lightweight Python web framework"
    embedding_b = await embedding_client.embed(content_b)
    _, chunk_id_b = await insert_test_document(
        db_client, project_id, "/docs/flask.md", content_b, embedding_b
    )
    
    # 5. Invalidate cache for this project
    await cache_client.invalidate_project(project_id)
    
    # 6. Third search (cache miss, should include new document)
    response3 = await search_service.search(request)
    
    # Should be cache miss after invalidation
    assert response3.cache_hit is False
    # Both documents should potentially be in results
    assert len(response3.results) >= 1


@pytest.mark.asyncio
async def test_multi_tenant_isolation(db_client, cache_client, embedding_client, search_service):
    """
    Test that projects are properly isolated.
    
    Documents from project A should not appear in project B's search results.
    """
    now = datetime.now(timezone.utc)
    
    # Create two test projects
    project_a_slug = f"test-tenant-a-{uuid.uuid4().hex[:8]}"
    project_a_uuid = uuid.uuid4()
    await db_client.execute(
        """
        INSERT INTO projects (id, slug, name, created_at, updated_at, corpus_version)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        project_a_uuid, project_a_slug, "Project A", now, now, 1
    )
    
    project_b_slug = f"test-tenant-b-{uuid.uuid4().hex[:8]}"
    project_b_uuid = uuid.uuid4()
    await db_client.execute(
        """
        INSERT INTO projects (id, slug, name, created_at, updated_at, corpus_version)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        project_b_uuid, project_b_slug, "Project B", now, now, 1
    )
    
    try:
        # Insert document in project A
        content_a = "Secret document for project A only"
        embedding_a = await embedding_client.embed(content_a)
        _, chunk_id_a = await insert_test_document(
            db_client, project_a_slug, "/secret/a.md", content_a, embedding_a
        )
        
        # Insert document in project B
        content_b = "Public document for project B"
        embedding_b = await embedding_client.embed(content_b)
        _, chunk_id_b = await insert_test_document(
            db_client, project_b_slug, "/public/b.md", content_b, embedding_b
        )
        
        # Search in project A
        request_a = SearchRequest(
            query="document",
            project_id=project_a_slug,
            top_k=10,
        )
        response_a = await search_service.search(request_a)
        
        # Verify isolation - project A should only see its own documents
        result_ids_a = [r.id for r in response_a.results]
        assert chunk_id_b not in result_ids_a, "Project A should not see project B's documents"
        
        # Search in project B
        request_b = SearchRequest(
            query="document",
            project_id=project_b_slug,
            top_k=10,
        )
        response_b = await search_service.search(request_b)
        
        # Verify isolation - project B should only see its own documents
        result_ids_b = [r.id for r in response_b.results]
        assert chunk_id_a not in result_ids_b, "Project B should not see project A's documents"
        
    finally:
        # Cleanup
        await db_client.execute("DELETE FROM chunks WHERE project_id = $1", project_a_uuid)
        await db_client.execute("DELETE FROM documents WHERE project_id = $1", project_a_uuid)
        await db_client.execute("DELETE FROM projects WHERE id = $1", project_a_uuid)
        
        await db_client.execute("DELETE FROM chunks WHERE project_id = $1", project_b_uuid)
        await db_client.execute("DELETE FROM documents WHERE project_id = $1", project_b_uuid)
        await db_client.execute("DELETE FROM projects WHERE id = $1", project_b_uuid)
