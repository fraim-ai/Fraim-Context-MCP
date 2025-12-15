"""LLM client using LiteLLM with Pydantic AI Gateway or OpenRouter.

LLM access flows through Pydantic AI Gateway for unified management:
- Single API key for all providers
- Cost tracking via Logfire
- Rate limits and failover

Fallback to OpenRouter if Gateway key not available.
"""

import asyncio
from typing import Any

import litellm
from litellm import acompletion

from fraim_mcp.config import get_settings


class LLMTimeoutError(Exception):
    """Raised when LLM request times out."""
    
    pass


class LLMClient:
    """Async LLM client using LiteLLM.
    
    Usage:
        client = LLMClient()
        response = await client.complete("What is Python?")
    """
    
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the LLM client.
        
        Args:
            model: Model identifier. Defaults to config setting.
            api_key: API key. Defaults to Gateway or OpenRouter from config.
        """
        settings = get_settings()
        
        # Determine API key and model
        self._api_key = api_key
        self._model = model
        
        if self._api_key is None:
            # Use OpenRouter (proven to work) - Gateway can be added later
            if settings.openrouter_api_key:
                self._api_key = settings.openrouter_api_key
                self._model = model or "openrouter/openai/gpt-4o-mini"
                self._api_base = None  # LiteLLM handles OpenRouter natively
            elif settings.pydantic_ai_gateway_api_key:
                self._api_key = settings.pydantic_ai_gateway_api_key
                self._model = model or "openai/gpt-4o-mini"
                self._api_base = "https://ai.pydantic.dev/v1"
            else:
                self._api_base = None
        else:
            self._api_base = None
            self._model = model or "gpt-4o-mini"
        
        # Configure LiteLLM
        litellm.drop_params = True  # Ignore unsupported params
    
    @property
    def api_key(self) -> str | None:
        """Get the configured API key."""
        return self._api_key
    
    @property
    def model(self) -> str:
        """Get the configured model."""
        return self._model
    
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> str:
        """Generate a completion for the given prompt.
        
        Args:
            prompt: User prompt/message
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            timeout: Request timeout in seconds
            **kwargs: Additional LiteLLM parameters
        
        Returns:
            Generated text response
        
        Raises:
            LLMTimeoutError: If request times out
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await asyncio.wait_for(
                acompletion(
                    model=self._model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=self._api_key,
                    api_base=self._api_base,
                    **kwargs,
                ),
                timeout=timeout,
            )
            
            return response.choices[0].message.content
            
        except asyncio.TimeoutError as e:
            raise LLMTimeoutError(f"LLM request timed out after {timeout}s") from e

