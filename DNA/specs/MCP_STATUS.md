# MCP Server Status & Integration Guide

> **Version**: 5.1.0  
> **Status**: READ-ONLY  
> **Last Updated**: December 2025

---

## Official MCP Servers Available

| Service | Package | Status | Notes |
|---------|---------|--------|-------|
| **PostgreSQL** | `@modelcontextprotocol/server-postgres` | ✅ Available | Direct database queries |
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | ✅ Available | File read/write |
| **GitHub** | `@modelcontextprotocol/server-github` | ✅ Available | Repo, issues, PRs |
| **Brave Search** | `@modelcontextprotocol/server-brave-search` | ✅ Available | Web search |
| **Memory** | `@modelcontextprotocol/server-memory` | ✅ Available | Persistent knowledge |
| **Puppeteer** | `@modelcontextprotocol/server-puppeteer` | ✅ Available | Browser automation |
| **Fetch** | `@modelcontextprotocol/server-fetch` | ✅ Available | HTTP requests |

### Pydantic Ecosystem

| Service | Package | Status | Notes |
|---------|---------|--------|-------|
| **Logfire** | `pydantic-logfire-mcp` | ✅ Available | Observability queries |
| **Pydantic AI** | Native in `pydantic-ai` | ✅ Available | Agent framework |

---

## Services WITHOUT Official MCP Servers

| Service | Workaround | Implementation |
|---------|------------|----------------|
| **Doppler** | CLI wrapper | `doppler run -- <command>` |
| **Railway** | CLI wrapper | `railway run <command>` |
| **Upstash** | Redis protocol | Use `redis://` URL |
| **Supabase** | PostgreSQL + REST | Use postgres MCP + HTTP |
| **Vercel** | CLI wrapper | `vercel <command>` |

---

## MCP Protocol Version

**Required**: MCP SDK `1.24.0` (November 2025 Standard)

Key features in 1.24.0:
- Structured Tool Outputs
- Progress Notifications
- Sampling Support (human-in-the-loop)
- Improved error handling

---

## Fraim MCP Server Tools

Our server exposes these tools via MCP:

### search_docs

**Purpose**: Semantic + keyword search across project documentation

```json
{
  "name": "search_docs",
  "description": "Search project documentation using semantic + keyword search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "project_id": {"type": "string", "default": "default"},
      "top_k": {"type": "integer", "default": 5},
      "category": {"type": "string", "enum": ["intent", "research", "references", "process", "workspace"]}
    },
    "required": ["query"]
  }
}
```

### get_document

**Purpose**: Retrieve full document content by path

```json
{
  "name": "get_document",
  "description": "Retrieve full document content by path",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "project_id": {"type": "string", "default": "default"}
    },
    "required": ["path"]
  }
}
```

### list_categories

**Purpose**: List available document categories for filtering

```json
{
  "name": "list_categories",
  "description": "List available document categories for a project",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_id": {"type": "string", "default": "default"}
    }
  }
}
```

---

## Transport Configuration

### stdio Transport (Claude Desktop, Cursor)

```json
{
  "mcpServers": {
    "fraim-context": {
      "command": "doppler",
      "args": ["run", "--", "uv", "run", "python", "-m", "fraim_mcp.server.mcp_server"],
      "cwd": "/path/to/fraim-context-mcp"
    }
  }
}
```

**Critical**: stdio is sensitive to stdout pollution. All logging must go to stderr or Logfire.

### HTTP/SSE Transport (Web clients)

```bash
# Start server
doppler run -- uv run uvicorn fraim_mcp.server.http_server:app --host 0.0.0.0 --port 8000

# Client connection
GET http://localhost:8000/api/v1/search/stream?query=...
Accept: text/event-stream
```

---

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fraim-context": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "fraim-context",
        "--config", "dev",
        "--",
        "uv", "run", "python", "-m", "fraim_mcp.server.mcp_server"
      ],
      "cwd": "/Users/you/projects/fraim-context-mcp"
    }
  }
}
```

---

## Cursor Configuration

Add to `.cursor/mcp.json` in project root:

```json
{
  "servers": {
    "fraim-context": {
      "command": "doppler",
      "args": ["run", "--", "uv", "run", "python", "-m", "fraim_mcp.server.mcp_server"],
      "env": {}
    }
  }
}
```

Or use the HTTP endpoint:

```json
{
  "servers": {
    "fraim-context": {
      "url": "http://localhost:8000/mcp",
      "transport": "sse"
    }
  }
}
```

---

## MCP Resources (Read-Only Data)

Our server also exposes resources:

### project://info

Project metadata and statistics

```json
{
  "uri": "project://default/info",
  "name": "Project Info",
  "mimeType": "application/json"
}
```

### docs://categories

List of document categories with counts

```json
{
  "uri": "docs://default/categories",
  "name": "Document Categories",
  "mimeType": "application/json"
}
```

---

## Progress Notifications (Deep Research Mode)

For long-running operations, we emit progress:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "search-123",
    "progress": 50,
    "total": 100,
    "message": "Reranking results..."
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_QUERY` | Query validation failed |
| `PROJECT_NOT_FOUND` | Unknown project_id |
| `DATABASE_ERROR` | PostgreSQL connection/query failed |
| `EMBEDDING_ERROR` | Failed to generate embedding |
| `CACHE_ERROR` | Redis connection failed (non-fatal) |
| `RERANK_ERROR` | Reranker failed (falls back to un-reranked) |

---

## Testing MCP Connection

```bash
# 1. Start server in one terminal
doppler run -- uv run python -m fraim_mcp.server.mcp_server

# 2. In another terminal, send test request
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  doppler run -- uv run python -m fraim_mcp.server.mcp_server

# Expected response:
# {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
```

---

**This document is for reference only. Do not modify during development.**
