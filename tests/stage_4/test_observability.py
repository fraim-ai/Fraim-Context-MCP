"""Stage 4.3: Observability Integration Tests.

These tests verify Logfire/OpenTelemetry integration.
Run with: doppler run -- uv run pytest tests/stage_4/test_observability.py -v
"""

import pytest

pytestmark = pytest.mark.stage4


def test_logfire_configured() -> None:
    """Test that Logfire is configured."""
    from fraim_mcp.observability.setup import setup_observability
    
    # Should not raise
    setup_observability()


def test_observability_setup_idempotent() -> None:
    """Test that observability setup can be called multiple times."""
    from fraim_mcp.observability.setup import setup_observability
    
    # Should not raise on multiple calls
    setup_observability()
    setup_observability()


def test_observability_returns_configured_status() -> None:
    """Test that setup returns configuration status."""
    from fraim_mcp.observability.setup import setup_observability
    
    result = setup_observability()
    
    assert isinstance(result, dict)
    assert "configured" in result

