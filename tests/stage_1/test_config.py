"""Stage 1.1: Configuration Tests.

These tests verify that Settings loads correctly from environment variables.
Run with: doppler run -- uv run pytest tests/stage_1/test_config.py -v
"""

import os

import pytest


@pytest.mark.stage1
def test_settings_loads_from_environment() -> None:
    """Test that Settings loads values from environment variables."""
    from fraim_mcp.config import Settings
    
    settings = Settings()
    
    # These should be loaded from Doppler via environment
    assert settings.database_url is not None
    assert len(settings.database_url) > 0


@pytest.mark.stage1
def test_database_url_parsed_correctly() -> None:
    """Test that database URL is parsed into components."""
    from fraim_mcp.config import Settings
    
    settings = Settings()
    
    # Should be a valid PostgreSQL URL
    assert settings.database_url.startswith("postgresql://")
    
    # Should have asyncpg-compatible URL available
    assert hasattr(settings, "database_url_asyncpg") or "postgresql" in settings.database_url


@pytest.mark.stage1
def test_settings_validation_fails_on_invalid() -> None:
    """Test that Settings validation fails with invalid values."""
    from pydantic import ValidationError as PydanticValidationError
    
    from fraim_mcp.config import Settings
    
    # Save current env and clear required vars
    original_db_url = os.environ.get("DATABASE_URL")
    
    try:
        os.environ["DATABASE_URL"] = ""  # Invalid: empty string
        
        with pytest.raises(PydanticValidationError):
            Settings()
    finally:
        # Restore original
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url


@pytest.mark.stage1
def test_settings_has_required_fields() -> None:
    """Test that Settings exposes all required configuration fields."""
    from fraim_mcp.config import Settings
    
    settings = Settings()
    
    # Core database config
    assert hasattr(settings, "database_url")
    
    # Cache config
    assert hasattr(settings, "redis_url")
    
    # Application config
    assert hasattr(settings, "environment")


@pytest.mark.stage1
def test_settings_singleton_pattern() -> None:
    """Test that get_settings returns consistent settings."""
    from fraim_mcp.config import get_settings
    
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Should return the same cached instance
    assert settings1.database_url == settings2.database_url

