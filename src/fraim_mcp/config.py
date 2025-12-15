"""Application configuration loaded from environment variables.

All secrets come from Doppler - NEVER create .env files.
Run with: doppler run -- <command>
"""

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Required environment variables (from Doppler):
    - DATABASE_URL: PostgreSQL connection string
    - REDIS_URL: Redis connection string
    - PYDANTIC_AI_GATEWAY_API_KEY: LLM access (or OPENROUTER_API_KEY)
    """
    
    model_config = SettingsConfigDict(
        env_file=None,  # No .env files - use Doppler
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        min_length=1,
    )
    
    # Cache
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )
    
    # LLM Access (Pydantic AI Gateway or OpenRouter)
    pydantic_ai_gateway_api_key: str | None = Field(
        default=None,
        description="Pydantic AI Gateway API key",
    )
    openrouter_api_key: str | None = Field(
        default=None,
        description="OpenRouter API key (fallback)",
    )
    open_ai_api: str | None = Field(
        default=None,
        description="OpenAI API key (for embeddings)",
    )
    
    # Observability
    logfire_token: str | None = Field(
        default=None,
        description="Logfire observability token",
    )
    
    # Application
    environment: str = Field(
        default="development",
        description="Environment name (development, staging, production)",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level",
    )
    
    # Embedding model (HARD CONTRACT: 1024 dimensions)
    embedding_model: str = Field(
        default="voyage/voyage-3",
        description="Embedding model (must produce 1024 dims)",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding dimension (HARD CONTRACT: 1024)",
    )
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @property
    def database_url_asyncpg(self) -> str:
        """Get database URL in asyncpg-compatible format."""
        # asyncpg prefers postgresql:// over postgres://
        return self.database_url.replace("postgres://", "postgresql://", 1)
    
    @property
    def llm_api_key(self) -> str | None:
        """Get the LLM API key (Gateway preferred, OpenRouter fallback)."""
        return self.pydantic_ai_gateway_api_key or self.openrouter_api_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Uses lru_cache for singleton pattern - settings are loaded once
    and reused across the application.
    """
    return Settings()

