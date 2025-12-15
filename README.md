# Fraim Context MCP

> Semantic search MCP server for project documentation.

**Version**: 5.1.0  
**Status**: In Development  

## Overview

Fraim Context MCP exposes project documentation to LLMs via the Model Context Protocol (MCP). It supports:

- **Fast mode**: Direct cache/search for immediate results
- **Deep mode**: Multi-round synthesis for complex queries
- **Hybrid search**: Vector similarity + full-text search with pgvector
- **Smart caching**: Redis with corpus versioning for cache invalidation

## Quick Start

```bash
# 1. Setup Doppler
doppler login
doppler setup  # Select: fraim-context → dev

# 2. Install dependencies
uv sync

# 3. Verify environment
doppler run -- uv run python scripts/verify_env.py

# 4. Run tests
doppler run -- uv run pytest tests/stage_0/ -v
```

## Development

This project uses **Test-Driven Development (TDD)**. See `DNA/DEVELOPMENT_PLAN.md` for stages.

```bash
# Run all tests
doppler run -- uv run pytest tests/ -v

# Run specific stage
doppler run -- uv run pytest tests/stage_0/ -v

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/fraim_mcp
```

## Architecture

- **LLM Access**: Pydantic AI Gateway (unified key for all providers)
- **Database**: PostgreSQL + pgvector (1024-dim embeddings)
- **Cache**: Redis 7.x (native asyncio)
- **Observability**: Logfire (OpenTelemetry)

See `DNA/specs/ARCHITECTURE.md` for full details.

## License

MIT

