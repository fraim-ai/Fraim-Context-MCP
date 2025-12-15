# FRAIM CONTEXT MCP — Project Manifest

> **Version**: 5.1.0  
> **Created**: December 2025  
> **Status**: Zero-to-One Build  
> **LLM Access**: Pydantic AI Gateway  

---

## 🗺️ Quick Navigation

| Need To... | Go To |
|------------|-------|
| **Start building** | [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) |
| **Understand constraints** | [.cursorrules](./.cursorrules) → copy to project root |
| **Read specifications** | [specs/](./specs/) (READ-ONLY) |
| **Setup environment** | [scripts/](./scripts/) |
| **Test the UI** | [ui/app.py](./ui/app.py) |

---

## 📁 Target Project Structure

After setup, your project should look like:

```
fraim-context-mcp/
│
├── .cursorrules             ← Copy from DNA/.cursorrules
├── pyproject.toml           ← Copy from DNA/pyproject.toml
├── CHANGELOG.md             ← Create as you progress
│
├── DNA/                     ← THIS FOLDER (project DNA)
│   ├── README.md            ← Bundle instructions
│   ├── MANIFEST.md          ← YOU ARE HERE
│   ├── DEVELOPMENT_PLAN.md  ← TDD stages & progress
│   ├── .cursorrules         ← AI constraints (source)
│   ├── pyproject.toml       ← Dependencies (source)
│   │
│   ├── specs/               ← 🔒 READ-ONLY specifications
│   │   ├── README.md        ← How to use specs
│   │   ├── ARCHITECTURE.md  ← System design
│   │   ├── CONTRACTS.md     ← API/DB contracts
│   │   ├── DEPENDENCIES.md  ← Dependency matrix
│   │   └── MCP_STATUS.md    ← MCP server availability
│   │
│   ├── scripts/             ← Setup utilities
│   │   ├── setup_doppler.sh
│   │   ├── verify_env.py
│   │   └── init_db.sql
│   │
│   └── ui/
│       └── app.py           ← Streamlit test interface
│
├── src/fraim_mcp/           ← Implementation code (CREATE)
│   ├── __init__.py
│   ├── config.py
│   ├── database/
│   ├── retrieval/
│   ├── ingestion/
│   ├── llm/
│   ├── cache/
│   ├── observability/
│   └── server/
│
├── tests/                   ← Test files by stage (CREATE)
│   ├── stage_0/
│   ├── stage_1/
│   ├── stage_2/
│   ├── stage_3/
│   ├── stage_4/
│   └── stage_5/
│
└── docs/                    ← Documentation (CREATE)
```

---

## 🔒 Protected Files (READ-ONLY)

The following files are **specifications** and should **NOT be modified** during development:

```
specs/ARCHITECTURE.md     ← System design decisions
specs/CONTRACTS.md        ← API schemas, DB models
specs/DEPENDENCIES.md     ← Pinned dependency versions
specs/MCP_STATUS.md       ← MCP server availability
```

**Why?** These files define the architectural decisions. Changing them mid-build creates inconsistency. If you believe a spec is wrong, document the issue in `docs/SPEC_ISSUES.md` instead.

---

## 🧪 Development Workflow (TDD)

### Stage Gate Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD STAGE GATE PROCESS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Read stage requirements in DEVELOPMENT_PLAN.md              │
│  2. Write tests FIRST (tests/stage_N/)                          │
│  3. Implement code to pass tests                                │
│  4. Run: doppler run -- uv run pytest tests/stage_N/ -v        │
│  5. All tests pass? → Update DEVELOPMENT_PLAN.md checkbox       │
│  6. Proceed to next stage                                       │
│                                                                 │
│  ⚠️  DO NOT skip stages. Each depends on the previous.          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Current Progress

Check [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) for:
- ✅ Completed stages
- 🔄 Current stage
- ⬜ Upcoming stages

---

## 🔑 Secrets Management (Doppler → Gateway)

**NEVER create `.env` files. All secrets come from Doppler.**

```bash
# First time setup
doppler login
doppler setup  # Select: fraim-context → dev

# Run any command with secrets
doppler run -- <command>

# Example: run tests
doppler run -- uv run pytest tests/stage_0/ -v
```

### Required Secrets

| Secret | Purpose | Get From |
|--------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection | Railway, Supabase, Docker |
| `REDIS_URL` | Redis connection | Upstash, Railway, Docker |
| `PYDANTIC_AI_GATEWAY_API_KEY` | LLM access (all providers) | https://gateway.pydantic.dev |
| `OBSERVABILITY_LOGFIRE_TOKEN` | Observability (optional) | https://logfire.pydantic.dev |

### Secrets Flow

```
Doppler → PYDANTIC_AI_GATEWAY_API_KEY → Pydantic AI → LLM Providers
                                                       ├── OpenAI
                                                       ├── Anthropic
                                                       ├── Google Vertex
                                                       └── Groq/Bedrock
```

See [scripts/setup_doppler.sh](./scripts/setup_doppler.sh) for full setup.

---

## 📦 Dependencies (Audited December 2025)

All dependencies are pinned in `pyproject.toml`. Critical versions:

| Package | Version | Status |
|---------|---------|--------|
| pydantic | 2.13.0 | ✅ UPGRADED |
| pydantic-ai | 1.32.0 | ✅ Current (Gateway support) |
| logfire | 4.16.0 | ✅ Current |
| asyncpg | 0.31.0 | ✅ Current |
| redis | 7.1.0 | 🔴 CRITICAL upgrade |
| mcp | 1.24.0 | 🔴 CRITICAL upgrade |
| litellm | 1.80.10 | ✅ UPGRADED |
| fastapi | 0.124.0 | ✅ UPGRADED |
| sse-starlette | 3.0.3 | 🔴 CRITICAL upgrade |

See [specs/DEPENDENCIES.md](./specs/DEPENDENCIES.md) for full matrix and rationale.

---

## 🔗 MCP Server Status

| Service | Official MCP | Alternative |
|---------|--------------|-------------|
| PostgreSQL | ✅ `@modelcontextprotocol/server-postgres` | — |
| Filesystem | ✅ `@modelcontextprotocol/server-filesystem` | — |
| GitHub | ✅ `@modelcontextprotocol/server-github` | — |
| Logfire | ✅ `pydantic-logfire-mcp` | — |
| Pydantic AI Gateway | ✅ Native `pydantic-ai` | — |
| Doppler | ❌ None | CLI wrapper |
| Railway | ❌ None | CLI wrapper |
| Upstash | ❌ None | redis-cli |

See [specs/MCP_STATUS.md](./specs/MCP_STATUS.md) for details.

---

## 🚀 Quick Start

```bash
# 1. Clone and enter directory
cd fraim-context-mcp

# 2. Setup Doppler (first time only)
./scripts/setup_doppler.sh

# 3. Install dependencies
uv sync

# 4. Verify environment
doppler run -- uv run python scripts/verify_env.py

# 5. Start Stage 0 tests
doppler run -- uv run pytest tests/stage_0/ -v

# 6. Follow DEVELOPMENT_PLAN.md
```

---

## 📞 Help

- **Stuck on a stage?** Re-read the stage requirements in DEVELOPMENT_PLAN.md
- **Test failing?** Check the test file for hints
- **Spec seems wrong?** Document in docs/SPEC_ISSUES.md
- **Environment issue?** Run `doppler run -- uv run python scripts/verify_env.py`

---

**Last Updated**: December 2025  
**Maintained By**: Cursor AI (guided by specifications)
