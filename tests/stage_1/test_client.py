"""Stage 1.3: Database Client Tests.

These tests verify the PostgreSQL + pgvector client implementation.
Run with: doppler run -- uv run pytest tests/stage_1/test_client.py -v

CRITICAL: pgvector codec MUST be registered on every connection.
"""

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


@pytest.mark.asyncio
async def test_connect_creates_pool() -> None:
    """Test that connect() creates a connection pool."""
    from fraim_mcp.database.client import DatabaseClient
    
    client = DatabaseClient()
    
    # Before connect, pool should be None
    assert client._pool is None
    
    await client.connect()
    
    # After connect, pool should exist
    assert client._pool is not None
    
    await client.disconnect()


@pytest.mark.asyncio
async def test_pgvector_codec_registered(db_client) -> None:
    """Test that pgvector codec is registered on connections.
    
    CRITICAL: Without codec registration, vectors return as strings.
    """
    async with db_client._pool.acquire() as conn:
        # This should work if codec is registered
        result = await conn.fetchval("SELECT '[1,2,3]'::vector")
        
        # Result should be a numpy array or list, not a string
        assert not isinstance(result, str), (
            "Vector returned as string! pgvector codec not registered."
        )


@pytest.mark.asyncio
async def test_disconnect_closes_pool(db_client) -> None:
    """Test that disconnect() closes the connection pool."""
    from fraim_mcp.database.client import DatabaseClient
    
    client = DatabaseClient()
    await client.connect()
    
    assert client._pool is not None
    
    await client.disconnect()
    
    # Pool should be closed
    assert client._pool is None or client._pool._closed


@pytest.mark.asyncio
async def test_vector_roundtrip(db_client) -> None:
    """CRITICAL: Test that vectors can be stored and retrieved correctly.
    
    This test verifies the complete vector roundtrip:
    1. Create a test vector (1024 dimensions per contract)
    2. Store it in the database
    3. Retrieve it and verify dimensions
    """
    import numpy as np
    
    # Create a test vector with 1024 dimensions (HARD CONTRACT)
    test_vector = np.random.rand(1024).astype(np.float32).tolist()
    
    async with db_client._pool.acquire() as conn:
        # Store and retrieve in one query
        result = await conn.fetchval(
            "SELECT $1::vector(1024)",
            test_vector,
        )
        
        # Result should have 1024 dimensions
        assert len(result) == 1024, f"Expected 1024 dims, got {len(result)}"
        
        # Values should be close to original
        for i in range(10):  # Check first 10
            assert abs(result[i] - test_vector[i]) < 0.0001


@pytest.mark.asyncio
async def test_health_check(db_client) -> None:
    """Test the health check method."""
    is_healthy = await db_client.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_execute_query(db_client) -> None:
    """Test executing a simple query."""
    async with db_client._pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

