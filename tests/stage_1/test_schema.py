"""Stage 1.4: Schema Migration Tests.

These tests verify that the database schema is correctly set up.
Run with: doppler run -- uv run pytest tests/stage_1/test_schema.py -v
"""

import pytest

pytestmark = pytest.mark.stage1


@pytest.fixture
async def db_client():
    """Create a database client for testing."""
    from fraim_mcp.database.client import DatabaseClient
    
    client = DatabaseClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_tables_exist(db_client) -> None:
    """Test that all required tables exist."""
    required_tables = ["projects", "documents", "chunks", "search_history"]
    
    async with db_client._pool.acquire() as conn:
        for table in required_tables:
            exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
                """,
                table,
            )
            assert exists, f"Table '{table}' does not exist. Run scripts/init_db.sql"


@pytest.mark.asyncio
async def test_indexes_exist(db_client) -> None:
    """Test that required indexes exist."""
    required_indexes = [
        "idx_chunks_embedding",
        "idx_chunks_content_tsv",
        "idx_chunks_project_id",
    ]
    
    async with db_client._pool.acquire() as conn:
        for index in required_indexes:
            exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = $1
                )
                """,
                index,
            )
            assert exists, f"Index '{index}' does not exist. Run scripts/init_db.sql"


@pytest.mark.asyncio
async def test_vector_column_correct_dimension(db_client) -> None:
    """Test that the embedding column has 1024 dimensions (HARD CONTRACT)."""
    async with db_client._pool.acquire() as conn:
        # Check the column type definition
        result = await conn.fetchval(
            """
            SELECT atttypmod 
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = 'chunks' 
            AND a.attname = 'embedding'
            """
        )
        
        # pgvector stores dimension in atttypmod
        # For vector(1024), atttypmod = 1024
        assert result == 1024, (
            f"Embedding column has wrong dimension: {result}. "
            "Expected 1024 per CONTRACTS.md"
        )


@pytest.mark.asyncio
async def test_pgvector_extension_enabled(db_client) -> None:
    """Test that pgvector extension is installed."""
    async with db_client._pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        assert exists, "pgvector extension not installed"


@pytest.mark.asyncio
async def test_tsvector_column_generated(db_client) -> None:
    """Test that content_tsv is a generated column."""
    async with db_client._pool.acquire() as conn:
        result = await conn.fetchval(
            """
            SELECT attgenerated 
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = 'chunks' 
            AND a.attname = 'content_tsv'
            """
        )
        # 's' means stored generated column (may be bytes or str)
        expected = "s"
        if isinstance(result, bytes):
            result = result.decode()
        assert result == expected, "content_tsv should be a GENERATED STORED column"

