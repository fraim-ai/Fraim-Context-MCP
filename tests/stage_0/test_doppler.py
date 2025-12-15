"""Stage 0.1: Doppler Authentication Tests.

These tests verify that the Doppler CLI is installed and configured correctly.
Run with: doppler run -- uv run pytest tests/stage_0/test_doppler.py -v
"""

import shutil
import subprocess

import pytest


@pytest.mark.stage0
def test_doppler_cli_available() -> None:
    """Test that the Doppler CLI is installed and accessible."""
    doppler_path = shutil.which("doppler")
    assert doppler_path is not None, (
        "Doppler CLI not found in PATH. "
        "Install with: brew install dopplerhq/cli/doppler"
    )


@pytest.mark.stage0
def test_doppler_authenticated() -> None:
    """Test that the user is authenticated with Doppler."""
    result = subprocess.run(
        ["doppler", "me"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Doppler authentication failed. Run 'doppler login' first.\n"
        f"Error: {result.stderr}"
    )
    # Should contain workspace/user info if authenticated (case-insensitive)
    output_lower = result.stdout.lower()
    assert "workplace" in output_lower or "name" in output_lower or "@" in result.stdout, (
        "Doppler authentication response doesn't look right. "
        "Try running 'doppler login' again."
    )


@pytest.mark.stage0
def test_doppler_project_configured() -> None:
    """Test that the Doppler project 'fraim-context' is configured."""
    result = subprocess.run(
        ["doppler", "configs"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # If not configured, doppler will exit with error
    if result.returncode != 0:
        pytest.fail(
            "Doppler project not configured. Run:\n"
            "  cd <project-root>\n"
            "  doppler setup\n"
            "  # Select: fraim-context → dev\n"
            f"Error: {result.stderr}"
        )
    # Check that we're in a valid project
    assert "dev" in result.stdout.lower() or "stg" in result.stdout.lower() or "prd" in result.stdout.lower(), (
        "Doppler configs not found. Ensure project is set up with 'doppler setup'."
    )

