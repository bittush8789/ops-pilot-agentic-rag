"""
config.py — Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated config.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-in-production"

    # ── LLM ──────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")

    # ── MySQL ─────────────────────────────────────────────────────
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="ops_workflow_db", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="ops_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")

    # ── Pinecone ──────────────────────────────────────────────────
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field(default="ops-runbooks", alias="PINECONE_INDEX_NAME")
    pinecone_environment: str = Field(default="us-east-1", alias="PINECONE_ENVIRONMENT")

    # ── LangSmith ────────────────────────────────────────────────
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="opspilot", alias="LANGCHAIN_PROJECT")

    # ── Embeddings ───────────────────────────────────────────────
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    @property
    def database_url(self) -> str:
        """Synchronous SQLAlchemy URL for MySQL."""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def async_database_url(self) -> str:
        """Async SQLAlchemy URL for MySQL."""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @field_validator("groq_api_key", "pinecone_api_key", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if v else v


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


# Convenience alias
settings = get_settings()
