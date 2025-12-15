"""Stage 3.1: Redis Cache Tests.

These tests verify the Redis cache implementation.
Run with: doppler run -- uv run pytest tests/stage_3/test_cache.py -v

Uses Redis 7.x native asyncio (not aioredis).
"""

import pytest

pytestmark = pytest.mark.stage3


@pytest.fixture
async def cache_client():
    """Create a cache client for testing."""
    from fraim_mcp.cache.redis_client import CacheClient
    
    client = CacheClient()
    await client.connect()
    yield client
    
    # Cleanup test keys
    await client.delete("test:*")
    await client.disconnect()


@pytest.mark.asyncio
async def test_cache_connection() -> None:
    """Test that cache client can connect to Redis."""
    from fraim_mcp.cache.redis_client import CacheClient
    
    client = CacheClient()
    await client.connect()
    
    # Should be connected
    is_connected = await client.ping()
    assert is_connected is True
    
    await client.disconnect()


@pytest.mark.asyncio
async def test_cache_set_get(cache_client) -> None:
    """Test basic cache set and get operations."""
    key = "test:basic:key"
    value = {"query": "test", "results": [1, 2, 3]}
    
    # Set value
    await cache_client.set(key, value)
    
    # Get value
    result = await cache_client.get(key)
    
    assert result is not None
    assert result["query"] == "test"
    assert result["results"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_cache_invalidation(cache_client) -> None:
    """Test cache invalidation (delete)."""
    key = "test:invalidation:key"
    value = "test value"
    
    # Set value
    await cache_client.set(key, value)
    
    # Verify it exists
    result = await cache_client.get(key)
    assert result == value
    
    # Invalidate
    await cache_client.delete(key)
    
    # Should be gone
    result = await cache_client.get(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_ttl_expiry(cache_client) -> None:
    """Test that cache entries expire after TTL."""
    import asyncio
    
    key = "test:ttl:key"
    value = "expiring value"
    
    # Set with 1 second TTL
    await cache_client.set(key, value, ttl=1)
    
    # Should exist immediately
    result = await cache_client.get(key)
    assert result == value
    
    # Wait for expiry
    await asyncio.sleep(1.5)
    
    # Should be expired
    result = await cache_client.get(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_key_generation(cache_client) -> None:
    """Test cache key generation for search queries."""
    from fraim_mcp.cache.redis_client import generate_cache_key
    
    key1 = generate_cache_key(
        project_id="my-project",
        corpus_version=42,
        query="how does auth work",
    )
    
    key2 = generate_cache_key(
        project_id="my-project",
        corpus_version=42,
        query="how does auth work",
    )
    
    key3 = generate_cache_key(
        project_id="my-project",
        corpus_version=43,  # Different version
        query="how does auth work",
    )
    
    # Same inputs = same key
    assert key1 == key2
    
    # Different version = different key
    assert key1 != key3
    
    # Key format should match spec
    assert key1.startswith("fraim:my-project:v42:search:")


@pytest.mark.asyncio
async def test_cache_handles_none_gracefully(cache_client) -> None:
    """Test that getting non-existent key returns None."""
    result = await cache_client.get("nonexistent:key:12345")
    assert result is None

