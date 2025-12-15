"""Stage 2.3: Embedding Storage Roundtrip Tests.

These tests verify the complete embedding lifecycle:
generate → store → retrieve → search

Run with: doppler run -- uv run pytest tests/stage_2/test_embedding_storage.py -v
"""

from uuid import uuid4

import numpy as np
import pytest

pytestmark = pytest.mark.stage2


@pytest.fixture
async def db_client():
    """Create a database client for testing."""
    from fraim_mcp.database.client import DatabaseClient
    
    client = DatabaseClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def test_project(db_client):
    """Create a test project for embedding tests."""
    project_id = uuid4()
    slug = f"embed-test-{uuid4().hex[:8]}"
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO projects (id, slug, name) VALUES ($1, $2, $3)",
            project_id,
            slug,
            "Embedding Test Project",
        )
    
    yield {"id": project_id, "slug": slug}
    
    # Cleanup
    async with db_client._pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


@pytest.fixture
async def embedding_client():
    """Create an embedding client."""
    from fraim_mcp.ingestion.embeddings import EmbeddingClient
    
    return EmbeddingClient()


@pytest.mark.asyncio
async def test_store_embedding_in_pgvector(db_client, test_project, embedding_client) -> None:
    """Test storing a generated embedding in pgvector."""
    # Generate embedding
    text = "This is test content about authentication and security."
    embedding = await embedding_client.embed(text)
    
    # Store in database
    doc_id = uuid4()
    chunk_id = uuid4()
    
    async with db_client._pool.acquire() as conn:
        # Create document first
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, path, content_hash)
            VALUES ($1, $2, $3, $4)
            """,
            doc_id,
            test_project["id"],
            f"docs/embed-test-{uuid4().hex[:8]}.md",
            "hash123",
        )
        
        # Store chunk with embedding
        await conn.execute(
            """
            INSERT INTO chunks (id, document_id, project_id, content, embedding, chunk_index)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            chunk_id,
            doc_id,
            test_project["id"],
            text,
            embedding,
            0,
        )
        
        # Verify storage
        stored = await conn.fetchval(
            "SELECT embedding FROM chunks WHERE id = $1",
            chunk_id,
        )
        
        assert stored is not None
        assert len(stored) == 1024


@pytest.mark.asyncio
async def test_retrieve_embedding_as_list(db_client, test_project, embedding_client) -> None:
    """Test that retrieved embeddings are proper lists (not strings)."""
    text = "Database retrieval test content."
    embedding = await embedding_client.embed(text)
    
    doc_id = uuid4()
    chunk_id = uuid4()
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO documents (id, project_id, path, content_hash) VALUES ($1, $2, $3, $4)",
            doc_id,
            test_project["id"],
            f"docs/retrieve-test-{uuid4().hex[:8]}.md",
            "hash456",
        )
        
        await conn.execute(
            """
            INSERT INTO chunks (id, document_id, project_id, content, embedding, chunk_index)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            chunk_id,
            doc_id,
            test_project["id"],
            text,
            embedding,
            0,
        )
        
        # Retrieve and verify type
        result = await conn.fetchval(
            "SELECT embedding FROM chunks WHERE id = $1",
            chunk_id,
        )
        
        # Should NOT be a string (common pgvector issue without codec)
        assert not isinstance(result, str), (
            "Embedding returned as string! pgvector codec not registered."
        )
        
        # Should be indexable with numeric values (float or numpy.float32)
        assert len(result) == 1024
        # pgvector may return numpy.float32, which is fine
        assert isinstance(float(result[0]), float)


@pytest.mark.asyncio
async def test_vector_similarity_search(db_client, test_project, embedding_client) -> None:
    """Test vector similarity search returns relevant results."""
    # Insert multiple chunks with different content
    contents = [
        "Python programming language tutorial and examples.",
        "Database design patterns and PostgreSQL optimization.",
        "Authentication with JWT tokens and OAuth2 flows.",
    ]
    
    doc_id = uuid4()
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO documents (id, project_id, path, content_hash) VALUES ($1, $2, $3, $4)",
            doc_id,
            test_project["id"],
            f"docs/search-test-{uuid4().hex[:8]}.md",
            "hash789",
        )
        
        # Insert chunks with embeddings
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
                test_project["id"],
                content,
                embedding,
                i,
            )
        
        # Search for database-related content
        query_embedding = await embedding_client.embed("How to optimize PostgreSQL queries?")
        
        results = await conn.fetch(
            """
            SELECT content, 1 - (embedding <=> $1) as similarity
            FROM chunks
            WHERE project_id = $2
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding,
            test_project["id"],
        )
        
        assert len(results) == 3
        
        # Most similar should be the database content
        assert "database" in results[0]["content"].lower() or "postgresql" in results[0]["content"].lower(), (
            f"Expected database content first, got: {results[0]['content']}"
        )
        
        # Similarity scores should be between 0 and 1
        for row in results:
            assert 0 <= row["similarity"] <= 1

