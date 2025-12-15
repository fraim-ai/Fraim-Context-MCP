# Dependencies Specification

> **Version**: 5.1.0  
> **Status**: READ-ONLY  
> **Last Updated**: December 2025  
> **Audit Source**: Comprehensive Dependency Audit (Dec 2025)

---

## Pinned Versions (AUDITED)

All dependencies have been audited against PyPI as of December 15, 2025.

### Core Framework

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| pydantic | 2.13.0 | ✅ UPGRADED | Polymorphic serialization, exclude_if |
| pydantic-settings | 2.12.0 | ✅ CURRENT | No update needed |
| pydantic-ai | 1.32.0 | ✅ CURRENT | Gateway support included |

### Observability

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| logfire | 4.16.0 | ✅ CURRENT | OTel 1.39 compatible |
| opentelemetry-sdk | 1.39.1 | ✅ UPGRADED | Matches Logfire internals |
| opentelemetry-exporter-otlp | 1.39.1 | ✅ UPGRADED | Consistent telemetry |

### Web Framework

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| fastapi | 0.124.0 | ✅ UPGRADED | Schema fixes, security patches |
| uvicorn | 0.38.0 | ✅ UPGRADED | Improved graceful shutdown |
| sse-starlette | 3.0.3 | 🔴 CRITICAL | Thread-safety fix (was 2.2.1) |
| httpx | 0.28.1 | ✅ CURRENT | No update needed |

### Database

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| asyncpg | 0.31.0 | ✅ CURRENT | PostgreSQL 17/18 support |
| pgvector | 0.4.2 | ✅ CURRENT | HNSW index support |

### Cache

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| redis | 7.1.0 | 🔴 CRITICAL | Native asyncio (was 5.2.1) |

### LLM & AI

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| litellm | 1.80.10 | ✅ UPGRADED | MCP Hub, Agent Gateway, Guardrails v2 |
| dspy-ai | 3.0.4 | ✅ CURRENT | No update needed |
| flashrank | 0.2.10 | ✅ UPGRADED | Performance optimizations |

### Ingestion

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| llama-index-core | 0.14.10 | ✅ UPGRADED | Multi-modal, VectorStore refactor |
| llama-index-readers-file | 0.5.5 | ✅ UPGRADED | Core compatibility |

### MCP

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| mcp | 1.24.0 | 🔴 CRITICAL | Nov 2025 Protocol Standard (was 1.9.0) |

### Utilities

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| python-dotenv | 1.2.1 | ✅ UPGRADED | Local dev fallback only |
| click | 8.3.1 | ✅ UPGRADED | Shell completion |
| rich | 14.2.0 | ✅ UPGRADED | Performance optimizations |
| tenacity | 9.1.2 | ✅ UPGRADED | Typing fixes |

---

## Critical Upgrade Rationale

### 1. redis 5.2.1 → 7.1.0 (CRITICAL)

**Why**: Redis-py v5 predates native asyncio support. Version 7.x provides:
- Native `redis.asyncio` module (no more aioredis wrappers)
- Redis 7.2 features (Sharded Pub/Sub, refined ACLs)
- Full asyncio event loop compatibility

**Risk of staying on 5.x**: Connection pool exhaustion, subtle concurrency bugs.

### 2. sse-starlette 2.2.1 → 3.0.3 (CRITICAL)

**Why**: Version 2.x has fundamental thread-safety flaws:
- Global state management for event triggers
- Race conditions in multi-user mode
- Potential data leakage between sessions

**v3.0.3 introduces**: Context-Local Events, full multi-threading support.

### 3. mcp 1.9.0 → 1.24.0 (CRITICAL)

**Why**: The MCP spec was standardized in November 2025:
- Structured Tool Outputs
- Progress Notifications (essential for Deep Research)
- Sampling Support (human-in-the-loop)

**Risk of staying on 1.9.0**: Incompatibility with Claude Desktop, Cursor.

### 4. litellm 1.55.10 → 1.80.10 (IMPORTANT)

**Why**: Versions 1.80.x introduced:
- MCP Hub (native MCP server discovery)
- Agent Gateway (A2A communication)
- Streaming Guardrails v2

**Note**: v1.57.5+ added `uvloop` dependency (not Windows compatible).

---

## Pydantic AI Gateway Integration

This project uses **Pydantic AI Gateway** as the primary LLM access layer:

| Feature | Benefit |
|---------|---------|
| Single API Key | `PYDANTIC_AI_GATEWAY_API_KEY` for all providers |
| Cost Tracking | Real-time spend monitoring via Logfire |
| Rate Limits | Project/user/key level spending caps |
| Zero Translation | Native provider formats preserved |
| Failover | Automatic retry across providers |

### Model String Format

```python
# Gateway format (recommended)
'gateway/openai:gpt-4o'
'gateway/anthropic:claude-sonnet-4-5'
'gateway/google-vertex:gemini-2.5-flash'
'gateway/groq:openai/gpt-oss-120b'

# BYOK fallback (OpenRouter)
'openrouter/openai/gpt-4o'
```

### Required Secrets (Doppler)

```
# Primary (Gateway mode)
PYDANTIC_AI_GATEWAY_API_KEY=paig_xxxxx

# Fallback (BYOK mode)
LLM_OPENROUTER_API_KEY=sk-or-xxxxx
```

---

## Compatibility Matrix

### Python Version

| Python | Status |
|--------|--------|
| 3.11 | ❌ Not supported |
| 3.12 | ✅ Required |
| 3.13 | ⚠️ May work (untested) |

### PostgreSQL Version

| PostgreSQL | pgvector | Status |
|------------|----------|--------|
| 14 | 0.7+ | ✅ Supported |
| 15 | 0.7+ | ✅ Supported |
| 16 | 0.7+ | ✅ Recommended |
| 17 | 0.8+ | ⚠️ May work |

### Redis Version

| Redis | Status |
|-------|--------|
| 6.x | ✅ Supported |
| 7.x | ✅ Recommended |

---

## Known Compatibility Issues

### 1. DSPy + asyncio

**Issue**: DSPy is synchronous and blocks the event loop.

**Solution**: Always wrap DSPy calls in `asyncio.to_thread()`:
```python
result = await asyncio.to_thread(dspy_module.forward, query=q)
```

### 2. pgvector + asyncpg

**Issue**: Vectors return as strings without codec registration.

**Solution**: Register codec on every connection:
```python
from pgvector.asyncpg import register_vector

async def init_connection(conn):
    await register_vector(conn)

pool = await asyncpg.create_pool(dsn=url, init=init_connection)
```

### 3. LlamaIndex Embeddings

**Issue**: `Settings.embed_model` doesn't accept async functions.

**Solution**: Create a proper embedding adapter class:
```python
from llama_index.core.embeddings import BaseEmbedding

class LiteLLMEmbedding(BaseEmbedding):
    def _get_text_embedding(self, text: str) -> list[float]:
        # Synchronous implementation
        ...
```

### 4. Logfire + LiteLLM

**Issue**: `litellm.success_callback = ["logfire"]` is not a documented integration.

**Solution**: Rely on httpx instrumentation instead:
```python
import logfire
logfire.instrument_httpx()  # Captures LLM HTTP calls
```

---

## Embedding Model Contract

**HARD REQUIREMENT**: Embedding dimension must be 1024.

| Model | Dimension | Provider |
|-------|-----------|----------|
| voyage-3 | 1024 | Voyage AI (via OpenRouter) |
| voyage-3-lite | 512 | ❌ Not compatible |
| text-embedding-3-small | 1536 | ❌ Not compatible |
| text-embedding-3-large | 3072 | ❌ Not compatible |

The database schema is:
```sql
embedding vector(1024)
```

Changing models requires:
1. New migration to alter column dimension
2. Re-embedding all existing documents
3. Recreating vector indexes

---

## Update Policy

### When to Update Dependencies

1. **Security vulnerabilities**: Update immediately
2. **Bug fixes**: Update if affected
3. **New features needed**: Evaluate impact first
4. **Major versions**: Wait for ecosystem stability

### How to Update

1. Update version in `pyproject.toml`
2. Run full test suite: `doppler run -- uv run pytest tests/ -v`
3. Document change in `CHANGELOG.md`:
   ```markdown
   ### Dependencies
   - Bump package X.Y.Z → X.Y.Z+1 (reason)
   ```
4. Test in staging before production

### Version Pinning Philosophy

We pin exact versions (`==`) instead of ranges (`>=`, `~=`) because:

1. **Reproducibility**: Same code = same behavior
2. **No surprises**: Updates are intentional, not automatic
3. **Debugging**: Know exactly what's running
4. **Team sync**: Everyone has identical environments

---

## External Service Versions

### Doppler CLI

```bash
# Required version
doppler --version
# >= 3.0.0

# Install/update
brew install dopplerhq/cli/doppler
# or
curl -Ls https://cli.doppler.com/install.sh | sh
```

### uv

```bash
# Required version
uv --version
# >= 0.5.0

# Install/update
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Docker (for local development)

```bash
# Required version
docker --version
# >= 24.0

# PostgreSQL image
pgvector/pgvector:pg16

# Redis image
redis:7-alpine
```

---

## Documentation Links

| Package | Documentation |
|---------|---------------|
| Pydantic | https://docs.pydantic.dev/latest/ |
| Pydantic AI | https://ai.pydantic.dev/ |
| Logfire | https://logfire.pydantic.dev/docs/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| asyncpg | https://magicstack.github.io/asyncpg/current/ |
| pgvector | https://github.com/pgvector/pgvector-python |
| LiteLLM | https://docs.litellm.ai/ |
| DSPy | https://dspy.ai/ |
| LlamaIndex | https://docs.llamaindex.ai/ |
| MCP | https://spec.modelcontextprotocol.io/ |
| FlashRank | https://github.com/PrithivirajDamodaran/FlashRank |
| Doppler | https://docs.doppler.com/ |

---

**These versions are fixed for v5.0.0. Do not modify during development.**
