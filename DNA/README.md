# DNA Bundle — Fraim Context MCP

> **Drop-in project DNA for Cursor AI-assisted development**

## What's This?

This folder contains the complete "DNA" for building Fraim Context MCP — a semantic search server that exposes project documentation to LLMs via the Model Context Protocol.

**The bundle includes:**
- Architecture specifications (READ-ONLY)
- Development plan with TDD stages
- Cursor rules and constraints
- Dependency manifest (audited Dec 2025)
- pyproject.toml ready to install

## Quick Setup

```bash
# 1. Copy this DNA folder to your project root
cp -r DNA /path/to/fraim-context-mcp/

# 2. Copy pyproject.toml to root (if not exists)
cp DNA/pyproject.toml /path/to/fraim-context-mcp/

# 3. Copy .cursorrules to root
cp DNA/.cursorrules /path/to/fraim-context-mcp/

# 4. Install dependencies
cd /path/to/fraim-context-mcp
uv sync
```

## File Layout

```
DNA/
├── README.md              ← You are here
├── MANIFEST.md            ← START HERE (navigation index)
├── DEVELOPMENT_PLAN.md    ← TDD stages & progress tracking
├── .cursorrules           ← AI constraints (copy to project root)
├── pyproject.toml         ← Dependencies (copy to project root)
│
├── specs/                 ← 🔒 READ-ONLY specifications
│   ├── ARCHITECTURE.md    ← System design
│   ├── CONTRACTS.md       ← API/DB schemas
│   ├── DEPENDENCIES.md    ← Dependency matrix
│   └── MCP_STATUS.md      ← MCP server availability
│
├── scripts/               ← Setup utilities
│   ├── setup_doppler.sh   ← Doppler configuration
│   ├── verify_env.py      ← Environment checker
│   └── init_db.sql        ← Database schema
│
└── ui/
    └── app.py             ← Streamlit test interface
```

## First Prompt for Cursor

After dropping this bundle into your project, send this to Cursor:

---

**FIRST PROMPT:**

```
I've added a DNA folder to this project containing the complete specification for Fraim Context MCP v5.1.

Please:
1. Read DNA/.cursorrules first (this contains your constraints)
2. Read DNA/MANIFEST.md for project navigation
3. Read DNA/DEVELOPMENT_PLAN.md for current status

Then tell me:
- What stage are we at?
- What are the next 3 tasks to complete?
- What files need to be created first?

Important: All specs in DNA/specs/ are READ-ONLY. Do not modify them.
```

---

## Secrets Setup (Doppler)

Before building, configure Doppler:

```bash
doppler login
doppler setup  # Select: fraim-context → dev

# Required secrets:
# - DATABASE_URL
# - REDIS_URL  
# - PYDANTIC_AI_GATEWAY_API_KEY (or OPENROUTER_API_KEY for BYOK)
# - LOGFIRE_TOKEN (optional)
```

## Key Constraints

| Rule | Why |
|------|-----|
| No `.env` files | All secrets via Doppler |
| TDD only | Write tests before implementation |
| specs/ is read-only | Architecture is locked |
| 1024-dim embeddings | pgvector schema contract |
| DSPy in threads | `asyncio.to_thread()` required |
| No `print()` in MCP | Corrupts JSON-RPC |

## Links

- [Pydantic AI](https://ai.pydantic.dev/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Logfire](https://logfire.pydantic.dev/docs/)
- [Doppler](https://docs.doppler.com/)

---

**Ready to build? Send the first prompt to Cursor!**
