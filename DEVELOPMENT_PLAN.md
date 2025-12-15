# FRAIM CONTEXT MCP — Development Plan

> **Approach**: Test-Driven Development (TDD)  
> **Philosophy**: Write tests first, implement to pass  
> **Rule**: Do NOT skip stages. Each builds on the previous.

---

## Progress Tracker

| Stage | Name | Status | Tests | Implementation |
|-------|------|--------|-------|----------------|
| 0 | Environment Setup | ✅ Complete | `tests/stage_0/` | Scripts only |
| 1 | Database Layer | ✅ Complete | `tests/stage_1/` | `src/fraim_mcp/database/` |
| 2 | LLM & Embeddings | ✅ Complete | `tests/stage_2/` | `src/fraim_mcp/llm/` |
| 3 | Retrieval Pipeline | ✅ Complete | `tests/stage_3/` | `src/fraim_mcp/retrieval/` |
| 4 | MCP Server | ✅ Complete | `tests/stage_4/` | `src/fraim_mcp/server/` |
| 5 | Integration | 🔄 In Progress | `tests/stage_5/` | Full system |

**Legend**: ⬜ Not Started | 🔄 In Progress | ✅ Complete | ❌ Blocked

---

## Stage 0: Environment Setup

> **Goal**: Verify all external dependencies are accessible and correctly configured.  
> **Tests**: `tests/stage_0/`  
> **No implementation code** — only validation scripts.

### Prerequisites
- [x] Doppler CLI installed (`doppler --version`)
- [x] uv installed (`uv --version`)
- [x] Docker available (for local PostgreSQL)

### Tasks

#### 0.1 Doppler Authentication
- [x] **Test**: `tests/stage_0/test_doppler.py::test_doppler_cli_available`
- [x] **Test**: `tests/stage_0/test_doppler.py::test_doppler_authenticated`
- [x] **Test**: `tests/stage_0/test_doppler.py::test_doppler_project_configured`

```bash
# Run Stage 0.1 tests
doppler run -- uv run pytest tests/stage_0/test_doppler.py -v
```

#### 0.2 Required Secrets Present
- [x] **Test**: `tests/stage_0/test_secrets.py::test_database_url_present`
- [x] **Test**: `tests/stage_0/test_secrets.py::test_database_url_valid_format`
- [x] **Test**: `tests/stage_0/test_secrets.py::test_redis_url_present`
- [x] **Test**: `tests/stage_0/test_secrets.py::test_redis_url_valid_format`
- [x] **Test**: `tests/stage_0/test_secrets.py::test_pydantic_ai_gateway_key_present`
- [x] **Test**: `tests/stage_0/test_secrets.py::test_logfire_token_present`

```bash
# Run Stage 0.2 tests
doppler run -- uv run pytest tests/stage_0/test_secrets.py -v
```

#### 0.3 External Service Connectivity
- [x] **Test**: `tests/stage_0/test_connectivity.py::test_postgresql_connection`
- [x] **Test**: `tests/stage_0/test_connectivity.py::test_postgresql_pgvector_extension`
- [x] **Test**: `tests/stage_0/test_connectivity.py::test_redis_connection`
- [x] **Test**: `tests/stage_0/test_connectivity.py::test_llm_api_reachable`
- [x] **Test**: `tests/stage_0/test_connectivity.py::test_logfire_api_reachable`

```bash
# Run Stage 0.3 tests
doppler run -- uv run pytest tests/stage_0/test_connectivity.py -v
```

### Stage 0 Gate
```bash
# ALL Stage 0 tests must pass before proceeding
doppler run -- uv run pytest tests/stage_0/ -v

# Expected: All tests pass ✅
# If any fail: Fix environment before continuing
```

**Stage 0 Complete**: [x] ✅ All 14 tests pass

---

## Stage 1: Database Layer

> **Goal**: Implement PostgreSQL + pgvector client with proper codec registration.  
> **Tests**: `tests/stage_1/`  
> **Implementation**: `src/fraim_mcp/database/`

### Tasks

#### 1.1 Configuration
- [ ] **Test**: `tests/stage_1/test_config.py::test_settings_loads_from_environment`
- [ ] **Test**: `tests/stage_1/test_config.py::test_database_url_parsed_correctly`
- [ ] **Test**: `tests/stage_1/test_config.py::test_settings_validation_fails_on_invalid`
- [ ] **Implement**: `src/fraim_mcp/config.py`

#### 1.2 Pydantic Models
- [ ] **Test**: `tests/stage_1/test_models.py::test_chunk_result_model`
- [ ] **Test**: `tests/stage_1/test_models.py::test_document_model`
- [ ] **Test**: `tests/stage_1/test_models.py::test_search_response_model`
- [ ] **Implement**: `src/fraim_mcp/database/models.py`

#### 1.3 Database Client
- [ ] **Test**: `tests/stage_1/test_client.py::test_connect_creates_pool`
- [ ] **Test**: `tests/stage_1/test_client.py::test_pgvector_codec_registered`
- [ ] **Test**: `tests/stage_1/test_client.py::test_disconnect_closes_pool`
- [ ] **Test**: `tests/stage_1/test_client.py::test_vector_roundtrip` (CRITICAL)
- [ ] **Implement**: `src/fraim_mcp/database/client.py`

#### 1.4 Schema Migration
- [ ] **Test**: `tests/stage_1/test_schema.py::test_tables_exist`
- [ ] **Test**: `tests/stage_1/test_schema.py::test_indexes_exist`
- [ ] **Test**: `tests/stage_1/test_schema.py::test_vector_column_correct_dimension`
- [ ] **Run**: `scripts/init_db.sql`

#### 1.5 Basic CRUD Operations
- [ ] **Test**: `tests/stage_1/test_crud.py::test_insert_document`
- [ ] **Test**: `tests/stage_1/test_crud.py::test_insert_chunk_with_embedding`
- [ ] **Test**: `tests/stage_1/test_crud.py::test_get_document_by_path`
- [ ] **Test**: `tests/stage_1/test_crud.py::test_project_isolation`

### Stage 1 Gate
```bash
doppler run -- uv run pytest tests/stage_1/ -v
```

**Stage 1 Complete**: [x] ✅ All 28 tests pass

---

## Stage 2: LLM & Embeddings

> **Goal**: Implement LiteLLM wrapper and embedding generation with dimension validation.  
> **Tests**: `tests/stage_2/`  
> **Implementation**: `src/fraim_mcp/llm/`, `src/fraim_mcp/ingestion/embeddings.py`

### Tasks

#### 2.1 LiteLLM Client
- [ ] **Test**: `tests/stage_2/test_llm_client.py::test_litellm_configured`
- [ ] **Test**: `tests/stage_2/test_llm_client.py::test_completion_returns_text`
- [ ] **Test**: `tests/stage_2/test_llm_client.py::test_completion_timeout_handling`
- [ ] **Implement**: `src/fraim_mcp/llm/client.py`

#### 2.2 Embedding Generation
- [ ] **Test**: `tests/stage_2/test_embeddings.py::test_embedding_returns_list`
- [ ] **Test**: `tests/stage_2/test_embeddings.py::test_embedding_dimension_is_1024` (HARD CONTRACT)
- [ ] **Test**: `tests/stage_2/test_embeddings.py::test_batch_embedding`
- [ ] **Test**: `tests/stage_2/test_embeddings.py::test_embedding_adapter_for_llamaindex`
- [ ] **Implement**: `src/fraim_mcp/ingestion/embeddings.py`

#### 2.3 Embedding Storage Roundtrip
- [ ] **Test**: `tests/stage_2/test_embedding_storage.py::test_store_embedding_in_pgvector`
- [ ] **Test**: `tests/stage_2/test_embedding_storage.py::test_retrieve_embedding_as_list`
- [ ] **Test**: `tests/stage_2/test_embedding_storage.py::test_vector_similarity_search`

### Stage 2 Gate
```bash
doppler run -- uv run pytest tests/stage_2/ -v
```

**Stage 2 Complete**: [x] ✅ All 14 tests pass

---

## Stage 3: Retrieval Pipeline

> **Goal**: Implement hybrid search (vector + FTS), reranking, and caching.  
> **Tests**: `tests/stage_3/`  
> **Implementation**: `src/fraim_mcp/retrieval/`, `src/fraim_mcp/cache/`

### Tasks

#### 3.1 Redis Cache
- [ ] **Test**: `tests/stage_3/test_cache.py::test_cache_connection`
- [ ] **Test**: `tests/stage_3/test_cache.py::test_cache_set_get`
- [ ] **Test**: `tests/stage_3/test_cache.py::test_cache_invalidation`
- [ ] **Test**: `tests/stage_3/test_cache.py::test_cache_ttl_expiry`
- [ ] **Implement**: `src/fraim_mcp/cache/redis_client.py`

#### 3.2 Hybrid Search
- [ ] **Test**: `tests/stage_3/test_hybrid_search.py::test_vector_search_returns_results`
- [ ] **Test**: `tests/stage_3/test_hybrid_search.py::test_fts_search_returns_results`
- [ ] **Test**: `tests/stage_3/test_hybrid_search.py::test_hybrid_combines_scores`
- [ ] **Test**: `tests/stage_3/test_hybrid_search.py::test_category_filter_works`
- [ ] **Implement**: Add `hybrid_search` to `src/fraim_mcp/database/client.py`

#### 3.3 FlashRank Reranker
- [ ] **Test**: `tests/stage_3/test_reranker.py::test_reranker_loads_model`
- [ ] **Test**: `tests/stage_3/test_reranker.py::test_rerank_changes_order`
- [ ] **Test**: `tests/stage_3/test_reranker.py::test_rerank_respects_top_k`
- [ ] **Test**: `tests/stage_3/test_reranker.py::test_rerank_timeout_fallback`
- [ ] **Implement**: `src/fraim_mcp/retrieval/reranker.py`

#### 3.4 Search Service Orchestrator
- [ ] **Test**: `tests/stage_3/test_search_service.py::test_search_returns_results`
- [ ] **Test**: `tests/stage_3/test_search_service.py::test_search_uses_cache`
- [ ] **Test**: `tests/stage_3/test_search_service.py::test_search_cache_miss_stores`
- [ ] **Test**: `tests/stage_3/test_search_service.py::test_dspy_runs_in_thread` (CRITICAL)
- [ ] **Implement**: `src/fraim_mcp/retrieval/service.py`

### Stage 3 Gate
```bash
doppler run -- uv run pytest tests/stage_3/ -v
```

**Stage 3 Complete**: [x] ✅ All 20 tests pass

---

## Stage 4: MCP Server

> **Goal**: Implement MCP server with tools and resources.  
> **Tests**: `tests/stage_4/`  
> **Implementation**: `src/fraim_mcp/server/`

### Tasks

#### 4.1 MCP stdio Server
- [ ] **Test**: `tests/stage_4/test_mcp_server.py::test_server_initializes`
- [ ] **Test**: `tests/stage_4/test_mcp_server.py::test_list_tools_returns_tools`
- [ ] **Test**: `tests/stage_4/test_mcp_server.py::test_search_docs_tool_works`
- [ ] **Test**: `tests/stage_4/test_mcp_server.py::test_stdout_not_polluted`
- [ ] **Implement**: `src/fraim_mcp/server/mcp_server.py`

#### 4.2 HTTP Server
- [ ] **Test**: `tests/stage_4/test_http_server.py::test_health_endpoint`
- [ ] **Test**: `tests/stage_4/test_http_server.py::test_search_endpoint`
- [ ] **Test**: `tests/stage_4/test_http_server.py::test_sse_streaming`
- [ ] **Implement**: `src/fraim_mcp/server/http_server.py`

#### 4.3 Observability Integration
- [ ] **Test**: `tests/stage_4/test_observability.py::test_logfire_configured`
- [ ] **Test**: `tests/stage_4/test_observability.py::test_spans_created`
- [ ] **Test**: `tests/stage_4/test_observability.py::test_attributes_present`
- [ ] **Implement**: `src/fraim_mcp/observability/setup.py`

### Stage 4 Gate
```bash
doppler run -- uv run pytest tests/stage_4/ -v
```

**Stage 4 Complete**: [x] ✅ All 7 tests pass

---

## Stage 5: Integration

> **Goal**: Full system integration tests and documentation.  
> **Tests**: `tests/stage_5/`  
> **Implementation**: Final polish

### Tasks

#### 5.1 End-to-End Tests
- [ ] **Test**: `tests/stage_5/test_e2e.py::test_ingest_then_search`
- [ ] **Test**: `tests/stage_5/test_e2e.py::test_mcp_tool_call_flow`
- [ ] **Test**: `tests/stage_5/test_e2e.py::test_cache_invalidation_on_ingest`

#### 5.2 Contract Tests
- [ ] **Test**: `tests/stage_5/test_contracts.py::test_search_response_schema`
- [ ] **Test**: `tests/stage_5/test_contracts.py::test_mcp_tool_schemas`
- [ ] **Test**: `tests/stage_5/test_contracts.py::test_error_response_schema`

#### 5.3 Chaos Tests
- [ ] **Test**: `tests/stage_5/test_chaos.py::test_redis_down_fallback`
- [ ] **Test**: `tests/stage_5/test_chaos.py::test_llm_timeout_handling`
- [ ] **Test**: `tests/stage_5/test_chaos.py::test_database_reconnection`

#### 5.4 Documentation
- [ ] README.md complete
- [ ] API documentation generated
- [ ] Claude Desktop config documented

### Stage 5 Gate
```bash
doppler run -- uv run pytest tests/stage_5/ -v
```

**Stage 5 Complete**: [ ] (check when all tests pass)

---

## 🏁 Final Checklist

When all stages are complete:

- [ ] All tests pass: `doppler run -- uv run pytest tests/ -v`
- [ ] Type check passes: `uv run mypy src/fraim_mcp`
- [ ] Lint passes: `uv run ruff check src/ tests/`
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`

---

## Command Reference

```bash
# Run all tests for a stage
doppler run -- uv run pytest tests/stage_N/ -v

# Run single test file
doppler run -- uv run pytest tests/stage_N/test_file.py -v

# Run single test
doppler run -- uv run pytest tests/stage_N/test_file.py::test_name -v

# Run with coverage
doppler run -- uv run pytest tests/ --cov=fraim_mcp --cov-report=html

# Type check
uv run mypy src/fraim_mcp

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/
```

---

**Remember**: Write tests FIRST, then implement. This is TDD.
