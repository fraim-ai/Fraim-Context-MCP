"""Redis cache client using native asyncio (Redis 7.x).

Cache key format: fraim:{project_id}:v{corpus_version}:search:{query_hash}

CRITICAL: Use redis.asyncio (not aioredis or sync redis).
"""

import hashlib
import json
from typing import Any

import redis.asyncio as redis

from fraim_mcp.config import get_settings


def generate_cache_key(
    project_id: str,
    corpus_version: int,
    query: str,
) -> str:
    """Generate a cache key for a search query.
    
    Format: fraim:{project_id}:v{corpus_version}:search:{query_hash}
    
    The corpus_version ensures cache invalidation when documents change.
    """
    # Hash the query for consistent key length
    query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
    
    return f"fraim:{project_id}:v{corpus_version}:search:{query_hash}"


class CacheClient:
    """Async Redis cache client.
    
    Uses Redis 7.x native asyncio support.
    
    Usage:
        client = CacheClient()
        await client.connect()
        await client.set("key", {"data": "value"})
        result = await client.get("key")
        await client.disconnect()
    """
    
    # Default TTL: 1 hour
    DEFAULT_TTL = 3600
    
    def __init__(self, redis_url: str | None = None):
        """Initialize the cache client.
        
        Args:
            redis_url: Redis connection URL. Defaults to config.
        """
        self._redis_url = redis_url or get_settings().redis_url
        self._client: redis.Redis | None = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is not None:
            return
        
        self._client = await redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        if self._client is None:
            return False
        
        try:
            return await self._client.ping()
        except Exception:
            return False
    
    async def get(self, key: str) -> Any | None:
        """Get a value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        if self._client is None:
            return None
        
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (default: 1 hour)
        
        Returns:
            True if successful
        """
        if self._client is None:
            return False
        
        try:
            serialized = json.dumps(value)
            await self._client.set(
                key,
                serialized,
                ex=ttl or self.DEFAULT_TTL,
            )
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache.
        
        Args:
            key: Cache key (supports patterns with *)
        
        Returns:
            True if successful
        """
        if self._client is None:
            return False
        
        try:
            if "*" in key:
                # Pattern delete
                async for k in self._client.scan_iter(match=key):
                    await self._client.delete(k)
            else:
                await self._client.delete(key)
            return True
        except Exception:
            return False
    
    async def __aenter__(self) -> "CacheClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

