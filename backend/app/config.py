"""Application configuration using Pydantic Settings."""

import json
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated list
                return [origin.strip() for origin in v.split(',')]
        return v

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
    anthropic_model: str = "claude-sonnet-4-5"
    anthropic_model_haiku: str = "claude-4-5-haiku-20250110"

    # OpenAI (for embeddings and extraction)
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Agent-specific model configuration
    extractor_model: str = "gpt-5"
    extractor_temperature: float = 0.2
    planner_model: str = "gpt-mini"
    planner_temperature: float = 0.9
    subagent_model: str = "gpt-nano"
    subagent_temperature: float = 0.4
    risk_assessor_model: str = "gpt-5"
    risk_assessor_temperature: float = 0.4
    writer_model: str = "claude-sonnet-4-5"
    writer_temperature: float = 0.4

    # Prompt versioning configuration
    extractor_prompt_version: str = "v3.0.0"  # Updated 2025-10-24: Content-first architecture
    planner_prompt_version: str = "v1.0.0"
    subagent_prompt_version: str = "v1.0.0"
    risk_assessor_prompt_version: str = "v1.0.0"
    writer_prompt_version: str = "v1.0.0"

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"]

    # Agent Configuration
    max_subagents: int = 10
    agent_timeout_seconds: int = 300
    max_tool_iterations: int = 5

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # LangSmith Tracing (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_endpoint: Optional[str] = None  # Use https://eu.api.smith.langchain.com for EU region
    langchain_project: str = "oxytec-feasibility-platform"

    # Excel Extraction Configuration
    excel_max_preview_rows: int = 50  # For non-measurement data
    excel_statistical_threshold: float = 0.5  # >50% numeric columns → use statistical summary
    excel_max_rows_full: int = 100  # Show full data if less than this many rows
    excel_sample_rows: int = 3  # Number of first/last rows to show as samples


# Global settings instance
settings = Settings()
