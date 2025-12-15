"""Stage 0.3: External Service Connectivity Tests.

These tests verify that we can actually connect to external services.
Run with: doppler run -- uv run pytest tests/stage_0/test_connectivity.py -v

IMPORTANT: These tests require network access and running services.
"""

import os

import pytest

# Mark all tests in this module as stage0
pytestmark = pytest.mark.stage0


@pytest.fixture
def database_url() -> str:
    """Get DATABASE_URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture
def redis_url() -> str:
    """Get REDIS_URL from environment."""
    url = os.environ.get("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set")
    return url


@pytest.mark.asyncio
async def test_postgresql_connection(database_url: str) -> None:
    """Test that we can connect to PostgreSQL."""
    import asyncpg
    import socket
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Verify connection works
        result = await conn.fetchval("SELECT 1")
        assert result == 1, "PostgreSQL SELECT 1 failed"
        
        await conn.close()
    except (socket.gaierror, OSError) as e:
        # DNS resolution failure or no route - often IPv6-only hosts or local network issues
        error_msg = str(e).lower()
        if "nodename" in error_msg or "no route" in error_msg or "errno 65" in error_msg:
            pytest.skip(
                f"Network connectivity issue (IPv6-only host or no route): {e}\n"
                "If using Supabase, get the Session Pooler URL from your dashboard."
            )
        raise
    except Exception as e:
        pytest.fail(
            f"Failed to connect to PostgreSQL: {e}\n"
            "Ensure the database is running and DATABASE_URL is correct."
        )


@pytest.mark.asyncio
async def test_postgresql_pgvector_extension(database_url: str) -> None:
    """Test that pgvector extension is installed."""
    import asyncpg
    import socket
    
    try:
        conn = await asyncpg.connect(database_url)
    except (socket.gaierror, OSError) as e:
        error_msg = str(e).lower()
        if "nodename" in error_msg or "no route" in error_msg or "errno 65" in error_msg:
            pytest.skip(
                f"Network connectivity issue (IPv6-only host or no route): {e}\n"
                "If using Supabase, get the Session Pooler URL from your dashboard."
            )
        raise
    
    try:
        # Check if pgvector extension exists
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        
        if not result:
            # Try to create it
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            except Exception as e:
                pytest.fail(
                    f"pgvector extension not installed and cannot be created: {e}\n"
                    "Install pgvector: https://github.com/pgvector/pgvector"
                )
        
        # Verify it works
        await conn.execute("SELECT '[1,2,3]'::vector")
        
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_redis_connection(redis_url: str) -> None:
    """Test that we can connect to Redis."""
    import redis.asyncio as redis_async
    
    try:
        client = await redis_async.from_url(redis_url)
        
        # Verify connection works
        pong = await client.ping()
        assert pong is True, "Redis PING failed"
        
        await client.aclose()
    except Exception as e:
        pytest.fail(
            f"Failed to connect to Redis: {e}\n"
            "Ensure Redis is running and REDIS_URL is correct."
        )


@pytest.mark.asyncio
async def test_llm_api_reachable() -> None:
    """Test that the LLM API is reachable."""
    import httpx
    
    # Check for Gateway key first, then OpenRouter
    gateway_key = os.environ.get("PYDANTIC_AI_GATEWAY_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    if gateway_key:
        # Test Pydantic AI Gateway - use the ai.pydantic.dev endpoint
        url = "https://ai.pydantic.dev/"
        headers = {"Authorization": f"Bearer {gateway_key}"}
    elif openrouter_key:
        # Test OpenRouter
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {openrouter_key}"}
    else:
        pytest.skip("No LLM API key configured")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            # Any response means the API is reachable
            # 200, 301, 302, 401, 403 all indicate the service is up
            assert response.status_code in (200, 301, 302, 401, 403, 404), (
                f"LLM API returned unexpected status: {response.status_code}"
            )
    except httpx.TimeoutException:
        pytest.fail("LLM API request timed out. Check network connectivity.")
    except httpx.ConnectError as e:
        # Network resolution issues - skip if DNS fails
        if "nodename nor servname" in str(e):
            pytest.skip(f"DNS resolution failed - possible network/VPN issue: {e}")
        pytest.fail(f"Failed to reach LLM API: {e}")
    except Exception as e:
        pytest.fail(f"Failed to reach LLM API: {e}")


@pytest.mark.asyncio
async def test_logfire_api_reachable() -> None:
    """Test that Logfire API is reachable (if configured)."""
    import httpx
    
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    
    if not logfire_token:
        pytest.skip("LOGFIRE_TOKEN not set, skipping Logfire connectivity test")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            # Just check if the Logfire endpoint is reachable
            response = await client.get(
                "https://logfire.pydantic.dev/",
                timeout=10.0,
            )
            assert response.status_code in (200, 301, 302, 401, 403), (
                f"Logfire returned unexpected status: {response.status_code}"
            )
    except Exception as e:
        pytest.fail(f"Failed to reach Logfire: {e}")

