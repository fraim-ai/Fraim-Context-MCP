"""FlashRank reranker for search result refinement.

FlashRank provides fast, local reranking without API calls.
Model is loaded once and reused for all reranking operations.
"""

from typing import Any

from flashrank import Ranker, RerankRequest


class Reranker:
    """FlashRank-based reranker for search results.
    
    Usage:
        reranker = Reranker()
        reranked = reranker.rerank(query, documents, top_k=5)
    """
    
    # Default model - small and fast
    DEFAULT_MODEL = "ms-marco-MiniLM-L-12-v2"
    
    def __init__(self, model_name: str | None = None):
        """Initialize the reranker.
        
        Args:
            model_name: FlashRank model name. Defaults to MiniLM.
        """
        self._model_name = model_name or self.DEFAULT_MODEL
        self._ranker: Ranker | None = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the FlashRank model."""
        self._ranker = Ranker(model_name=self._model_name)
    
    @property
    def model(self) -> Ranker | None:
        """Get the loaded model."""
        return self._ranker
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._ranker is not None
    
    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Rerank documents by relevance to query.
        
        Args:
            query: Search query
            documents: List of documents with 'id' and 'content' fields
            top_k: Number of top results to return
        
        Returns:
            Reranked documents with added 'rerank_score' field
        """
        if not documents:
            return []
        
        if self._ranker is None:
            self._load_model()
        
        # Prepare passages for FlashRank
        passages = [
            {"id": doc.get("id", str(i)), "text": doc.get("content", "")}
            for i, doc in enumerate(documents)
        ]
        
        # Create rerank request
        request = RerankRequest(
            query=query,
            passages=passages,
        )
        
        # Perform reranking
        results = self._ranker.rerank(request)
        
        # Map back to original documents with scores
        id_to_doc = {doc.get("id", str(i)): doc for i, doc in enumerate(documents)}
        
        reranked = []
        for result in results[:top_k]:
            doc_id = result.get("id") or result.get("passage", {}).get("id")
            
            if doc_id in id_to_doc:
                doc = id_to_doc[doc_id].copy()
                doc["rerank_score"] = float(result.get("score", 0.0))
                reranked.append(doc)
        
        return reranked

