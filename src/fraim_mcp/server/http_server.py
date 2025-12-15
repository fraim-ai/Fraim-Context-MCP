"""HTTP server using FastAPI.

Provides:
- /health - Health check endpoint
- /api/v1/search - Search endpoint
- / - API info

Run with: doppler run -- uv run uvicorn fraim_mcp.server.http_server:app --reload
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fraim_mcp import __version__
from fraim_mcp.cache.redis_client import CacheClient
from fraim_mcp.database.client import DatabaseClient
from fraim_mcp.database.models import SearchRequest, SearchResponse
from fraim_mcp.ingestion.embeddings import EmbeddingClient
from fraim_mcp.observability.setup import setup_observability
from fraim_mcp.retrieval.service import SearchService

# Global clients (initialized in lifespan)
_db_client: DatabaseClient | None = None
_cache_client: CacheClient | None = None
_search_service: SearchService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _db_client, _cache_client, _search_service
    
    # Setup observability
    setup_observability()
    
    # Initialize clients
    _db_client = DatabaseClient()
    await _db_client.connect()
    
    _cache_client = CacheClient()
    await _cache_client.connect()
    
    embedding_client = EmbeddingClient()
    
    _search_service = SearchService(
        db_client=_db_client,
        cache_client=_cache_client,
        embedding_client=embedding_client,
    )
    
    yield
    
    # Cleanup
    if _db_client:
        await _db_client.disconnect()
    if _cache_client:
        await _cache_client.disconnect()


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="Fraim Context MCP",
        description="Semantic search MCP server for project documentation",
        version=__version__,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app: FastAPI) -> None:
    """Register API routes."""
    
    @app.get("/")
    async def root() -> dict[str, Any]:
        """API information."""
        return {
            "name": "Fraim Context MCP",
            "version": __version__,
            "description": "Semantic search MCP server for project documentation",
        }
    
    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Health check endpoint."""
        db_healthy = False
        cache_healthy = False
        
        if _db_client:
            db_healthy = await _db_client.health_check()
        
        if _cache_client:
            cache_healthy = await _cache_client.ping()
        
        status = "healthy" if (db_healthy and cache_healthy) else "unhealthy"
        
        return {
            "status": status,
            "version": __version__,
            "database": "connected" if db_healthy else "disconnected",
            "cache": "connected" if cache_healthy else "disconnected",
        }
    
    @app.post("/api/v1/search", response_model=SearchResponse)
    async def search(request: SearchRequest) -> SearchResponse:
        """Search endpoint."""
        if _search_service is None:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            return await _search_service.search(request)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Create default app instance
app = create_app()

