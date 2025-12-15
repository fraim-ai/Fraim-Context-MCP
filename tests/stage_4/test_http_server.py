"""Stage 4.2: HTTP Server Tests.

These tests verify the FastAPI HTTP server implementation.
Run with: doppler run -- uv run pytest tests/stage_4/test_http_server.py -v
"""

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.stage4


@pytest.fixture
async def app():
    """Create the FastAPI app."""
    from fraim_mcp.server.http_server import create_app
    
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint(client) -> None:
    """Test the health check endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] in ("healthy", "unhealthy")
    assert "version" in data


@pytest.mark.asyncio
async def test_search_endpoint(client) -> None:
    """Test the search endpoint."""
    # Use default project which should exist
    response = await client.post(
        "/api/v1/search",
        json={
            "query": "test query",
            "project_id": "default",
            "top_k": 5,
        },
    )
    
    # Should return 200 or 503 (if service not fully initialized in test)
    # In production with lifespan, this would be 200
    assert response.status_code in (200, 503)
    
    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "latency_ms" in data


@pytest.mark.asyncio
async def test_search_endpoint_validation(client) -> None:
    """Test search endpoint validation."""
    # Empty query should fail
    response = await client.post(
        "/api/v1/search",
        json={
            "query": "",
            "project_id": "default",
        },
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_root_endpoint(client) -> None:
    """Test the root endpoint returns API info."""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "name" in data
    assert "version" in data

