"""Stage 2.1: LLM Client Tests.

These tests verify the LiteLLM/Pydantic AI Gateway wrapper.
Run with: doppler run -- uv run pytest tests/stage_2/test_llm_client.py -v

LLM access is via Pydantic AI Gateway (PYDANTIC_AI_GATEWAY_API_KEY)
or OpenRouter as fallback (OPENROUTER_API_KEY).
"""

import os

import pytest

pytestmark = pytest.mark.stage2


@pytest.fixture
def llm_client():
    """Create an LLM client for testing."""
    from fraim_mcp.llm.client import LLMClient
    
    return LLMClient()


def test_litellm_configured() -> None:
    """Test that LiteLLM is properly configured with API keys."""
    from fraim_mcp.llm.client import LLMClient
    
    client = LLMClient()
    
    # Should have either Gateway or OpenRouter key
    assert client.api_key is not None, (
        "No LLM API key found. Set PYDANTIC_AI_GATEWAY_API_KEY or OPENROUTER_API_KEY"
    )


@pytest.mark.asyncio
async def test_completion_returns_text(llm_client) -> None:
    """Test that completion returns text response."""
    # Simple completion test
    response = await llm_client.complete(
        prompt="Say 'hello' and nothing else.",
        max_tokens=10,
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert "hello" in response.lower()


@pytest.mark.asyncio
async def test_completion_timeout_handling(llm_client) -> None:
    """Test that completion handles timeouts gracefully."""
    from fraim_mcp.llm.client import LLMTimeoutError
    
    # This should either complete or raise a proper timeout error
    try:
        response = await llm_client.complete(
            prompt="Count from 1 to 5.",
            max_tokens=50,
            timeout=30.0,  # Reasonable timeout
        )
        assert isinstance(response, str)
    except LLMTimeoutError:
        # This is acceptable - timeout was handled properly
        pass


@pytest.mark.asyncio
async def test_completion_with_system_prompt(llm_client) -> None:
    """Test completion with a system prompt."""
    response = await llm_client.complete(
        prompt="What are you?",
        system_prompt="You are a helpful documentation assistant. Answer briefly.",
        max_tokens=50,
    )
    
    assert isinstance(response, str)
    assert len(response) > 0


def test_client_has_model_configured(llm_client) -> None:
    """Test that client has a default model configured."""
    assert llm_client.model is not None
    assert len(llm_client.model) > 0

