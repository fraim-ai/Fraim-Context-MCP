"""Search service orchestrator.

Coordinates the complete search pipeline:
1. Check cache
2. Generate query embedding
3. Hybrid search (vector + FTS)
4. Rerank results
5. Store in cache

CRITICAL: DSPy is synchronous - wrap in asyncio.to_thread() if used.
"""

import time
from uuid import UUID

from fraim_mcp.cache.redis_client import CacheClient, generate_cache_key
from fraim_mcp.database.client import DatabaseClient
from fraim_mcp.database.models import ChunkResult, SearchRequest, SearchResponse
from fraim_mcp.ingestion.embeddings import EmbeddingClient
from fraim_mcp.retrieval.reranker import Reranker


class SearchService:
    """Orchestrates the search pipeline.
    
    Usage:
        service = SearchService(db_client, cache_client, embedding_client)
        response = await service.search(request)
    """
    
    def __init__(
        self,
        db_client: DatabaseClient,
        cache_client: CacheClient,
        embedding_client: EmbeddingClient,
        reranker: Reranker | None = None,
    ):
        """Initialize the search service.
        
        Args:
            db_client: Database client for hybrid search
            cache_client: Redis cache client
            embedding_client: Embedding generator
            reranker: Optional reranker (created if not provided)
        """
        self._db = db_client
        self._cache = cache_client
        self._embeddings = embedding_client
        self._reranker = reranker or Reranker()
    
    async def _get_project_info(self, project_id: str) -> dict:
        """Get project info by slug or ID."""
        async with self._db._pool.acquire() as conn:
            # Try slug first, then UUID
            row = await conn.fetchrow(
                """
                SELECT id, slug, corpus_version 
                FROM projects 
                WHERE slug = $1
                """,
                project_id,
            )
            
            if row is None:
                # Try as UUID
                try:
                    uuid = UUID(project_id)
                    row = await conn.fetchrow(
                        "SELECT id, slug, corpus_version FROM projects WHERE id = $1",
                        uuid,
                    )
                except ValueError:
                    pass
            
            if row is None:
                raise ValueError(f"Project not found: {project_id}")
            
            return dict(row)
    
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a search request.
        
        Args:
            request: Search request with query, project_id, etc.
        
        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.perf_counter()
        
        # Get project info
        project_info = await self._get_project_info(request.project_id)
        project_uuid = project_info["id"]
        corpus_version = project_info["corpus_version"]
        
        # Generate cache key
        cache_key = generate_cache_key(
            project_id=request.project_id,
            corpus_version=corpus_version,
            query=request.query,
        )
        
        # Check cache
        cached = await self._cache.get(cache_key)
        if cached is not None:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return SearchResponse(
                results=[ChunkResult(**r) for r in cached["results"]],
                query=request.query,
                project_id=request.project_id,
                total_found=cached["total_found"],
                latency_ms=latency_ms,
                cache_hit=True,
                corpus_version=corpus_version,
            )
        
        # Generate query embedding
        query_embedding = await self._embeddings.embed(request.query)
        
        # Execute hybrid search
        async with self._db._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM hybrid_search($1, $2, $3, $4, $5)
                """,
                project_uuid,
                query_embedding,
                request.query,
                request.top_k * 2,  # Get more for reranking
                request.category,
            )
        
        # Convert to documents for reranking
        documents = []
        for row in rows:
            doc = {
                "id": str(row["chunk_id"]),
                "document_id": str(row["document_id"]),
                "content": row["content"],
                "score": float(row["score"]) if row["score"] else 0.0,
            }
            documents.append(doc)
        
        # Rerank if enabled
        if request.use_reranker and documents:
            documents = self._reranker.rerank(
                query=request.query,
                documents=documents,
                top_k=request.top_k,
            )
        else:
            documents = documents[:request.top_k]
        
        # Get document paths for results
        chunk_ids = [UUID(doc["id"]) for doc in documents]
        
        async with self._db._pool.acquire() as conn:
            chunk_info = await conn.fetch(
                """
                SELECT c.id, d.path, d.title, d.category
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.id = ANY($1)
                """,
                chunk_ids,
            )
        
        chunk_map = {str(row["id"]): row for row in chunk_info}
        
        # Build results
        results = []
        for doc in documents:
            chunk_data = chunk_map.get(doc["id"], {})
            
            result = ChunkResult(
                id=UUID(doc["id"]),
                document_id=UUID(doc["document_id"]),
                content=doc["content"],
                score=doc.get("rerank_score", doc.get("score", 0.0)),
                document_path=chunk_data.get("path", ""),
                document_title=chunk_data.get("title"),
                category=chunk_data.get("category", "general"),
                chunk_index=0,  # Could be added to query if needed
            )
            results.append(result)
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Store in cache
        cache_data = {
            "results": [r.model_dump(mode="json") for r in results],
            "total_found": len(rows),
        }
        await self._cache.set(cache_key, cache_data)
        
        return SearchResponse(
            results=results,
            query=request.query,
            project_id=request.project_id,
            total_found=len(rows),
            latency_ms=latency_ms,
            cache_hit=False,
            corpus_version=corpus_version,
        )

