#!/bin/bash
# =============================================================================
# Fraim Context MCP — Doppler Setup Script
# =============================================================================
# Run this ONCE to configure Doppler for the project.
# After setup, all commands should be run with: doppler run -- <command>
# =============================================================================

set -e

echo "🔐 Fraim Context MCP — Doppler Setup"
echo "======================================"
echo ""

# Check if Doppler CLI is installed
if ! command -v doppler &> /dev/null; then
    echo "❌ Doppler CLI not found. Installing..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install dopplerhq/cli/doppler
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -Ls https://cli.doppler.com/install.sh | sh
    else
        echo "Please install Doppler manually: https://docs.doppler.com/docs/install-cli"
        exit 1
    fi
fi

echo "✅ Doppler CLI installed: $(doppler --version)"
echo ""

# Login to Doppler
echo "📋 Step 1: Login to Doppler"
echo "   This will open a browser window..."
doppler login

echo ""
echo "📋 Step 2: Setup project configuration"
echo "   Select project: fraim-context"
echo "   Select config: dev"
doppler setup

echo ""
echo "✅ Doppler configured!"
echo ""

# Verify secrets are accessible
echo "📋 Step 3: Verifying required secrets..."

REQUIRED_SECRETS=(
    "DATABASE_URL"
    "REDIS_URL"
)

OPTIONAL_SECRETS=(
    "PYDANTIC_AI_GATEWAY_API_KEY"
    "OPENROUTER_API_KEY"
    "LOGFIRE_TOKEN"
)

echo ""
echo "Required secrets:"
for secret in "${REQUIRED_SECRETS[@]}"; do
    if doppler secrets get "$secret" --plain > /dev/null 2>&1; then
        echo "  ✅ $secret"
    else
        echo "  ❌ $secret (MISSING - add in Doppler dashboard)"
    fi
done

echo ""
echo "Optional secrets:"
for secret in "${OPTIONAL_SECRETS[@]}"; do
    if doppler secrets get "$secret" --plain > /dev/null 2>&1; then
        echo "  ✅ $secret"
    else
        echo "  ⚪ $secret (not set)"
    fi
done

echo ""
echo "======================================"
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add any missing secrets in Doppler dashboard"
echo "  2. Run: uv sync"
echo "  3. Run: doppler run -- uv run python scripts/verify_env.py"
echo "  4. Start Stage 0 tests: doppler run -- uv run pytest tests/stage_0/ -v"
echo ""
