"""Application configuration using Pydantic Settings."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Configuration
    app_name: str = "Oxytec Feasibility Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+asyncpg://oxytec:oxytec@localhost:5432/oxytec_db"
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Anthropic API
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_model_haiku: str = "claude-3-5-haiku-20241022"

    # OpenAI (for embeddings)
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt"]

    # Agent Configuration
    max_subagents: int = 10
    agent_timeout_seconds: int = 300
    max_tool_iterations: int = 5

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Redis (optional, for caching)
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 3600


# Global settings instance
settings = Settings()
