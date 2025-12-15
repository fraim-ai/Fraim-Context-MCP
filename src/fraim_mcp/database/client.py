"""PostgreSQL + pgvector database client.

CRITICAL: pgvector codec MUST be registered on every connection.
Without it, vectors return as strings instead of numpy arrays.
"""

import asyncpg
from pgvector.asyncpg import register_vector

from fraim_mcp.config import get_settings


class DatabaseClient:
    """Async PostgreSQL client with pgvector support.
    
    Usage:
        client = DatabaseClient()
        await client.connect()
        # ... use client
        await client.disconnect()
    
    Or as async context manager:
        async with DatabaseClient() as client:
            # ... use client
    """
    
    def __init__(self, database_url: str | None = None):
        """Initialize the database client.
        
        Args:
            database_url: PostgreSQL connection URL. If not provided,
                          loads from settings (Doppler environment).
        """
        self._database_url = database_url or get_settings().database_url_asyncpg
        self._pool: asyncpg.Pool | None = None
    
    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        """Initialize each connection with pgvector codec.
        
        CRITICAL: This must be called on EVERY connection in the pool.
        Without it, vectors return as strings.
        """
        await register_vector(conn)
    
    async def connect(self) -> None:
        """Create the connection pool with pgvector codec registration."""
        if self._pool is not None:
            return  # Already connected
        
        self._pool = await asyncpg.create_pool(
            dsn=self._database_url,
            min_size=2,
            max_size=10,
            init=self._init_connection,  # CRITICAL: Register codec on every connection
        )
    
    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    async def health_check(self) -> bool:
        """Check if the database is healthy and reachable."""
        if self._pool is None:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False
    
    async def __aenter__(self) -> "DatabaseClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

