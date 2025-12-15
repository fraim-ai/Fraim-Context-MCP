"""Stage 1.5: CRUD Operation Tests.

These tests verify basic Create, Read, Update, Delete operations.
Run with: doppler run -- uv run pytest tests/stage_1/test_crud.py -v
"""

from uuid import uuid4

import numpy as np
import pytest

pytestmark = pytest.mark.stage1


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
    """Create a test project and clean up after."""
    project_id = uuid4()
    slug = f"test-project-{uuid4().hex[:8]}"
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO projects (id, slug, name) 
            VALUES ($1, $2, $3)
            """,
            project_id,
            slug,
            "Test Project",
        )
    
    yield {"id": project_id, "slug": slug}
    
    # Cleanup
    async with db_client._pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


@pytest.mark.asyncio
async def test_insert_document(db_client, test_project) -> None:
    """Test inserting a document."""
    from fraim_mcp.database.client import DatabaseClient
    
    doc_id = uuid4()
    
    async with db_client._pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, path, title, content_hash, category)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            doc_id,
            test_project["id"],
            "docs/test.md",
            "Test Document",
            "abc123",
            "general",
        )
        
        # Verify it was inserted
        result = await conn.fetchval(
            "SELECT path FROM documents WHERE id = $1",
            doc_id,
        )
        assert result == "docs/test.md"


@pytest.mark.asyncio
async def test_insert_chunk_with_embedding(db_client, test_project) -> None:
    """Test inserting a chunk with a 1024-dim embedding."""
    doc_id = uuid4()
    chunk_id = uuid4()
    
    # Create test embedding (1024 dims per contract)
    embedding = np.random.rand(1024).astype(np.float32).tolist()
    
    async with db_client._pool.acquire() as conn:
        # First insert document
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, path, content_hash)
            VALUES ($1, $2, $3, $4)
            """,
            doc_id,
            test_project["id"],
            f"docs/chunk-test-{uuid4().hex[:8]}.md",
            "hash123",
        )
        
        # Then insert chunk with embedding
        await conn.execute(
            """
            INSERT INTO chunks (id, document_id, project_id, content, embedding, chunk_index)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            chunk_id,
            doc_id,
            test_project["id"],
            "This is the chunk content for testing.",
            embedding,
            0,
        )
        
        # Verify chunk was inserted
        result = await conn.fetchrow(
            "SELECT content, chunk_index FROM chunks WHERE id = $1",
            chunk_id,
        )
        assert result["content"] == "This is the chunk content for testing."
        assert result["chunk_index"] == 0


@pytest.mark.asyncio
async def test_get_document_by_path(db_client, test_project) -> None:
    """Test retrieving a document by its path."""
    doc_id = uuid4()
    path = f"docs/get-by-path-{uuid4().hex[:8]}.md"
    
    async with db_client._pool.acquire() as conn:
        # Insert document
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, path, title, content_hash)
            VALUES ($1, $2, $3, $4, $5)
            """,
            doc_id,
            test_project["id"],
            path,
            "Get By Path Test",
            "hash456",
        )
        
        # Retrieve by path
        result = await conn.fetchrow(
            """
            SELECT id, title, path 
            FROM documents 
            WHERE project_id = $1 AND path = $2
            """,
            test_project["id"],
            path,
        )
        
        assert result is not None
        assert result["id"] == doc_id
        assert result["title"] == "Get By Path Test"


@pytest.mark.asyncio
async def test_project_isolation(db_client) -> None:
    """Test that projects are properly isolated (multi-tenancy)."""
    project1_id = uuid4()
    project2_id = uuid4()
    
    async with db_client._pool.acquire() as conn:
        # Create two projects
        await conn.execute(
            "INSERT INTO projects (id, slug, name) VALUES ($1, $2, $3)",
            project1_id,
            f"project-1-{uuid4().hex[:8]}",
            "Project 1",
        )
        await conn.execute(
            "INSERT INTO projects (id, slug, name) VALUES ($1, $2, $3)",
            project2_id,
            f"project-2-{uuid4().hex[:8]}",
            "Project 2",
        )
        
        # Insert document in project 1
        doc1_id = uuid4()
        await conn.execute(
            """
            INSERT INTO documents (id, project_id, path, content_hash)
            VALUES ($1, $2, $3, $4)
            """,
            doc1_id,
            project1_id,
            "docs/isolated.md",
            "hash789",
        )
        
        # Query for documents in project 2 - should not find project 1's doc
        result = await conn.fetch(
            "SELECT id FROM documents WHERE project_id = $1",
            project2_id,
        )
        
        assert len(result) == 0, "Project isolation violated!"
        
        # Query for documents in project 1 - should find the doc
        result = await conn.fetch(
            "SELECT id FROM documents WHERE project_id = $1",
            project1_id,
        )
        assert len(result) == 1
        
        # Cleanup
        await conn.execute("DELETE FROM projects WHERE id = $1", project1_id)
        await conn.execute("DELETE FROM projects WHERE id = $1", project2_id)

