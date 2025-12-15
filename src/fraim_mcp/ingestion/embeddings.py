"""Embedding generation client.

HARD CONTRACT: All embeddings MUST be 1024 dimensions.
The database schema is: embedding vector(1024)

Uses LiteLLM for embedding generation via OpenRouter.
Model: voyage/voyage-3 (1024 dims) or text-embedding-3-small with dimension override.
"""

import asyncio
from typing import Any

import litellm
from litellm import aembedding

from fraim_mcp.config import get_settings


class EmbeddingClient:
    """Async embedding client with 1024-dimension guarantee.
    
    HARD CONTRACT: dimension MUST be 1024.
    
    Usage:
        client = EmbeddingClient()
        embedding = await client.embed("Hello, world!")
        assert len(embedding) == 1024
    """
    
    # HARD CONTRACT: 1024 dimensions
    DIMENSION = 1024
    
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the embedding client.
        
        Args:
            model: Embedding model. Defaults to text-embedding-3-small with dims=1024.
            api_key: API key. Defaults to OpenAI API key from config.
        """
        settings = get_settings()
        
        # OpenAI API for embeddings (text-embedding-3-small supports dimension param)
        self._api_key = api_key or settings.open_ai_api or settings.openrouter_api_key
        
        # Use OpenAI's text-embedding-3-small which supports dimension parameter
        # This gives us exactly 1024 dims as required
        self._model = model or "text-embedding-3-small"
        self._dimension = self.DIMENSION
        
        # Configure LiteLLM
        litellm.drop_params = True
    
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension (HARD CONTRACT: 1024)."""
        return self._dimension
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            List of 1024 floats
        
        Raises:
            ValueError: If embedding dimension is not 1024
        """
        response = await aembedding(
            model=self._model,
            input=[text],
            api_key=self._api_key,
            dimensions=self._dimension,  # Request exactly 1024 dims
        )
        
        embedding = response.data[0]["embedding"]
        
        # Validate dimension (HARD CONTRACT)
        if len(embedding) != self._dimension:
            raise ValueError(
                f"HARD CONTRACT VIOLATION: Expected {self._dimension} dims, "
                f"got {len(embedding)}. Check embedding model."
            )
        
        return embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embeddings, each with 1024 floats
        """
        if not texts:
            return []
        
        response = await aembedding(
            model=self._model,
            input=texts,
            api_key=self._api_key,
            dimensions=self._dimension,
        )
        
        embeddings = [item["embedding"] for item in response.data]
        
        # Validate all dimensions
        for i, emb in enumerate(embeddings):
            if len(emb) != self._dimension:
                raise ValueError(
                    f"HARD CONTRACT VIOLATION at index {i}: "
                    f"Expected {self._dimension} dims, got {len(emb)}"
                )
        
        return embeddings
    
    def get_text_embedding(self, text: str) -> list[float]:
        """Sync wrapper for LlamaIndex compatibility.
        
        LlamaIndex's BaseEmbedding expects synchronous methods.
        This runs the async embed in a new event loop if needed.
        """
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, use asyncio.to_thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.embed(text))
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.embed(text))
    
    def get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Sync batch wrapper for LlamaIndex compatibility."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.embed_batch(texts))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.embed_batch(texts))

