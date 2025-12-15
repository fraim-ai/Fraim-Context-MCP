# Architecture Specification

> **Version**: 5.1.0  
> **Status**: READ-ONLY  
> **Last Updated**: December 2025

---

## System Overview

Fraim Context MCP is a semantic search server that exposes project documentation to LLMs via the Model Context Protocol (MCP). It supports two operation modes: **Fast** (direct cache/search) and **Deep** (multi-round synthesis).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER REQUEST                                   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRAIM CONTEXT MANIFEST                              │
│  ┌─────────────────────┐    ┌─────────────────────┐                         │
│  │  Retrieve from      │    │   Gather Context    │                         │
│  │      Cache          │    │                     │                         │
│  └──────────┬──────────┘    └──────────┬──────────┘                         │
└─────────────┼──────────────────────────┼────────────────────────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP CLIENT                                      │
│  Get context → Cursor decision → Cursor Takes action → Update MCP           │
│                              ↑                                               │
│                              │ Need more (max 3 rounds)                      │
│                              └───────────────────────────────────────────────│
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ Context bundle (structured)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP SERVER                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       ROUTING DECISION                                  ││
│  │                    ┌─────────┴─────────┐                                ││
│  │                    │                   │                                ││
│  │                 [FAST]              [DEEP]                              ││
│  │                    │                   │                                ││
│  │                    ▼                   ▼                                ││
│  │              Direct Cache         Synthesis                             ││
│  │                                       │                                 ││
│  └──────────────────────────────────────┼──────────────────────────────────┘│
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT SOURCES (5 Domains)                          │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│    Intent    │   Research   │  References  │   Process    │   Workspace     │
│     Cache    │    Cache     │    Cache     │    Cache     │     Cache       │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│  Canonical   │ Explorations │   API Docs   │    CI/CD     │ Rules/Commands  │
│    Docs      │              │              │              │   Workflows     │
└──────────────┴──────────────┴──────────────┴──────────────┴─────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HISTORY OF REQUESTS AND ACTIONS                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## LLM Access: Pydantic AI Gateway

All LLM access flows through **Pydantic AI Gateway** for unified management:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECRETS FLOW (Doppler → Gateway)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐  │
│  │   Doppler   │────────▶│  Application     │────────▶│  Pydantic AI    │  │
│  │   Secrets   │         │  (Fraim MCP)     │         │    Gateway      │  │
│  └─────────────┘         └──────────────────┘         └────────┬────────┘  │
│        │                                                        │           │
│        │ PYDANTIC_AI_GATEWAY_API_KEY                           │           │
│        │ (single key for all providers)                        │           │
│        │                                                        ▼           │
│        │                                              ┌─────────────────┐  │
│        │                                              │   LLM Providers │  │
│        │                                              │  ┌───────────┐  │  │
│        │                                              │  │  OpenAI   │  │  │
│        │                                              │  │ Anthropic │  │  │
│        │                                              │  │  Groq     │  │  │
│        │                                              │  │  Bedrock  │  │  │
│        │                                              │  └───────────┘  │  │
│        │                                              └─────────────────┘  │
│        │                                                                    │
│  Alternative (BYOK mode):                                                  │
│  └── OPENROUTER_API_KEY (bypass gateway, direct to OpenRouter)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gateway Benefits

| Feature | Description |
|---------|-------------|
| **Single Key** | One `PYDANTIC_AI_GATEWAY_API_KEY` for all providers |
| **Cost Tracking** | Real-time spend monitoring in Logfire |
| **Rate Limits** | Project/user/key level spending caps |
| **Failover** | Automatic retry across providers |
| **Zero Translation** | Native provider formats (no schema translation) |

### Model String Format

```python
# Via Pydantic AI Gateway (recommended)
agent = Agent('gateway/openai:gpt-4o')
agent = Agent('gateway/anthropic:claude-sonnet-4-5')

# Direct to OpenRouter (BYOK fallback)
agent = Agent('openrouter/openai/gpt-4o')
```

---

## Component Responsibilities

### 1. Fraim Context Manifest

**Purpose**: Entry point that routes requests to cache or context gathering

| Mode | Behavior |
|------|----------|
| **Fast** | Check cache → Return immediately if hit |
| **Deep** | Gather context → Synthesize → Multi-round if needed |

### 2. MCP Server Layer

**Purpose**: Expose search functionality via Model Context Protocol

| Component | File | Responsibility |
|-----------|------|----------------|
| stdio Transport | `server/mcp_server.py` | Claude Desktop, Cursor integration |
| HTTP Transport | `server/http_server.py` | Web clients, SSE streaming |

**Critical Constraint**: stdio transport is sensitive to stdout. ALL logging must go to stderr or logfire.

### 3. Context Domains (5 Caches)

The system organizes context into **5 specialized domains**:

| Domain | Cache Key | Data Source | Purpose |
|--------|-----------|-------------|---------|
| **Intent** | `intent:*` | Canonical Docs | User goals, specifications |
| **Research** | `research:*` | Explorations | Investigations, analysis |
| **References** | `refs:*` | API Docs | Technical documentation |
| **Process** | `process:*` | CI/CD | Build, deploy, test info |
| **Workspace** | `workspace:*` | Rules/Workflows | Commands, conventions |

### 4. Search Service Layer

**Purpose**: Orchestrate the search pipeline

| Component | File | Responsibility |
|-----------|------|----------------|
| Search Service | `retrieval/service.py` | Orchestrate cache → search → rerank |
| Query Transform | `retrieval/dspy_pipeline.py` | Optimize queries using DSPy |
| Hybrid Search | `database/client.py` | Vector + full-text search |
| Reranker | `retrieval/reranker.py` | FlashRank local reranking |

**Critical Constraint**: DSPy is synchronous. MUST wrap in `asyncio.to_thread()`.

### 5. Data Layer

**Purpose**: Store and retrieve documents, embeddings, and cache

| Component | File | Responsibility |
|-----------|------|----------------|
| Database Client | `database/client.py` | PostgreSQL + pgvector operations |
| Cache Client | `cache/redis_client.py` | Redis 7.x native asyncio |
| LLM Client | `llm/gateway_client.py` | Pydantic AI Gateway wrapper |

**Critical Constraint**: pgvector codec MUST be registered on every connection.

---

## Data Flow

### Search Request Flow

```
1. Client sends query
   │
2. MCP/HTTP Server receives request
   │
3. Search Service checks Redis cache
   │
   ├─► Cache HIT: Return cached result
   │
   └─► Cache MISS:
       │
       4. DSPy transforms query (in thread pool)
       │
       5. Generate embedding via LiteLLM
       │
       6. Hybrid search (vector + FTS) in PostgreSQL
       │
       7. FlashRank reranks results
       │
       8. Store in Redis cache
       │
       9. Return results
```

### Ingestion Flow (Future)

```
1. Document source detected
   │
2. LlamaIndex parses document
   │
3. Chunking based on document type
   │
4. Generate embeddings via LiteLLM
   │
5. Store chunks + embeddings in PostgreSQL
   │
6. Increment corpus version (invalidates cache)
```

---

## Database Schema

### Entity Relationship

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   projects  │──────<│  documents  │──────<│   chunks    │
│             │  1:N  │             │  1:N  │             │
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ slug        │       │ project_id  │       │ document_id │
│ name        │       │ path        │       │ content     │
│ settings    │       │ title       │       │ embedding   │
└─────────────┘       │ content_hash│       │ content_tsv │
                      │ category    │       │ chunk_index │
                      └─────────────┘       └─────────────┘
                                                   │
                                                   │ Referenced by
                                                   ▼
                                            ┌─────────────┐
                                            │search_history│
                                            │             │
                                            │ query       │
                                            │ result_ids  │
                                            │ feedback    │
                                            └─────────────┘
```

### Vector Dimension Contract

**HARD REQUIREMENT**: All embeddings MUST be 1024 dimensions.

- Embedding model: `voyage/voyage-3` via OpenRouter
- PostgreSQL column: `embedding vector(1024)`
- Startup validation: Check dimension before accepting traffic

---

## Multi-Tenancy

All queries are scoped by `project_id`:

```sql
-- Every query MUST include project_id
SELECT * FROM chunks 
WHERE project_id = $1 AND ...
```

**Why?** 
- Tenant isolation
- Index efficiency (project_id in composite indexes)
- Cache key namespacing

---

## Caching Strategy

### Cache Key Format

```
fraim:{project_id}:v{corpus_version}:search:{query_hash}
```

### Invalidation

Cache is invalidated when:
1. Corpus version changes (document added/updated/deleted)
2. TTL expires (default: 1 hour)
3. Manual clear via admin endpoint

### Why Corpus Versioning?

Simple TTL-based caching means stale results after document updates. Corpus versioning ensures:
- Immediate invalidation on content change
- No stale results ever
- Predictable cache behavior

---

## Observability

### Telemetry Stack

```
┌─────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY PIPELINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Application Code                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                           │
│  │   Logfire   │ ← Auto-instruments: FastAPI, asyncpg,     │
│  │    SDK      │   Redis, httpx                            │
│  └──────┬──────┘                                           │
│         │                                                   │
│         │ OpenTelemetry Protocol (OTLP)                    │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐     ┌─────────────┐                       │
│  │   Logfire   │     │   Grafana   │                       │
│  │   (Dev)     │     │   (Prod)    │                       │
│  └─────────────┘     └─────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Required Span Attributes

Every span MUST include:
- `project_id`: Tenant identifier
- `corpus_version`: For cache debugging
- `cache_hit`: Boolean

---

## Security Considerations

### Secrets Management

- All secrets via Doppler (never .env files)
- Secrets validated at startup (Stage 0 tests)
- No secrets in logs or error messages

### Tenant Isolation

- All queries scoped by project_id
- No cross-tenant data access
- API keys per project (future)

### MCP Security

- stdio: Inherits caller process permissions
- HTTP: Requires auth token (future)

---

## Deployment Topology

### Local Development

```
┌─────────────────────────────────────────────────────┐
│                 Local Machine                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Docker  │  │ Docker  │  │ Python  │             │
│  │Postgres │  │  Redis  │  │   App   │             │
│  └─────────┘  └─────────┘  └─────────┘             │
│       ↑            ↑            ↑                   │
│       └────────────┴────────────┘                   │
│                    │                                │
│              Doppler CLI                            │
│          (injects secrets)                          │
└─────────────────────────────────────────────────────┘
```

### Production (Railway)

```
┌─────────────────────────────────────────────────────┐
│                    Railway                           │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │Railway  │  │ Upstash │  │ Railway │             │
│  │Postgres │  │  Redis  │  │Container│             │
│  └─────────┘  └─────────┘  └─────────┘             │
│       ↑            ↑            ↑                   │
│       └────────────┴────────────┘                   │
│                    │                                │
│           Doppler Integration                       │
│         (auto-injects secrets)                      │
└─────────────────────────────────────────────────────┘
```

---

## Error Handling Strategy

### Recoverable Errors

| Error | Recovery |
|-------|----------|
| Redis connection failed | Skip cache, proceed with search |
| LLM timeout | Retry with backoff (3 attempts) |
| Reranker timeout | Return un-reranked results |

### Fatal Errors

| Error | Behavior |
|-------|----------|
| Database connection failed | Refuse to start |
| Invalid embedding dimension | Refuse to start |
| Missing required secrets | Refuse to start |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search latency (cache hit) | < 50ms | P95 |
| Search latency (cache miss) | < 500ms | P95 |
| Embedding generation | < 200ms | P95 |
| Reranking | < 100ms | P95 |

---

**This architecture is final for v5.0.0. Do not modify during development.**
