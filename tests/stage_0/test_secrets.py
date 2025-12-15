"""Stage 0.2: Required Secrets Tests.

These tests verify that all required secrets are present in the environment.
Run with: doppler run -- uv run pytest tests/stage_0/test_secrets.py -v

IMPORTANT: These tests must be run with 'doppler run --' to inject secrets.
"""

import os
import re

import pytest


@pytest.mark.stage0
def test_database_url_present() -> None:
    """Test that DATABASE_URL is set in the environment."""
    database_url = os.environ.get("DATABASE_URL")
    assert database_url is not None, (
        "DATABASE_URL not found in environment. "
        "Ensure it's configured in Doppler (fraim-context → dev)."
    )
    assert len(database_url) > 0, "DATABASE_URL is empty."


@pytest.mark.stage0
def test_database_url_valid_format() -> None:
    """Test that DATABASE_URL has a valid PostgreSQL format."""
    database_url = os.environ.get("DATABASE_URL", "")
    
    # PostgreSQL URL pattern: postgres[ql]://user:pass@host:port/dbname
    pattern = r"^postgres(ql)?:\/\/.+:.+@.+:\d+\/.+"
    assert re.match(pattern, database_url), (
        f"DATABASE_URL format invalid. Expected: postgres://user:pass@host:port/dbname\n"
        f"Got: {database_url[:50]}..."
    )


@pytest.mark.stage0
def test_redis_url_present() -> None:
    """Test that REDIS_URL is set in the environment."""
    redis_url = os.environ.get("REDIS_URL")
    assert redis_url is not None, (
        "REDIS_URL not found in environment. "
        "Ensure it's configured in Doppler (fraim-context → dev)."
    )
    assert len(redis_url) > 0, "REDIS_URL is empty."


@pytest.mark.stage0
def test_redis_url_valid_format() -> None:
    """Test that REDIS_URL has a valid Redis format."""
    redis_url = os.environ.get("REDIS_URL", "")
    
    # Redis URL patterns: redis://... or rediss://... (TLS)
    pattern = r"^rediss?:\/\/"
    assert re.match(pattern, redis_url), (
        f"REDIS_URL format invalid. Expected: redis://... or rediss://...\n"
        f"Got: {redis_url[:50]}..."
    )


@pytest.mark.stage0
def test_pydantic_ai_gateway_key_present() -> None:
    """Test that Pydantic AI Gateway API key is set."""
    gateway_key = os.environ.get("PYDANTIC_AI_GATEWAY_API_KEY")
    
    # Also check for fallback OpenRouter key
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    assert gateway_key is not None or openrouter_key is not None, (
        "No LLM API key found. Set one of:\n"
        "  - PYDANTIC_AI_GATEWAY_API_KEY (recommended)\n"
        "  - OPENROUTER_API_KEY (fallback)\n"
        "Configure in Doppler (fraim-context → dev)."
    )


@pytest.mark.stage0
def test_logfire_token_present() -> None:
    """Test that Logfire token is set for observability."""
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    
    if logfire_token is None:
        pytest.skip(
            "LOGFIRE_TOKEN not set. Observability will be disabled. "
            "This is optional but recommended."
        )
    
    assert len(logfire_token) > 0, "LOGFIRE_TOKEN is empty."

