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
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return the status.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
        
        Returns:
            Status string from the query execution
        """
        if self._pool is None:
            raise RuntimeError("Database client not connected. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch all rows from a query.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
        
        Returns:
            List of row records
        """
        if self._pool is None:
            raise RuntimeError("Database client not connected. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row from a query.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
        
        Returns:
            Row record or None
        """
        if self._pool is None:
            raise RuntimeError("Database client not connected. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value from a query.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
        
        Returns:
            Single value or None
        """
        if self._pool is None:
            raise RuntimeError("Database client not connected. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def __aenter__(self) -> "DatabaseClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

