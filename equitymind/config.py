"""Typed application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_key: str | None = None
    demo_mode: bool = True
    database_url: str | None = None
    vector_dimensions: int = Field(default=1536, ge=1, le=8192)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    sec_user_agent: str = "EquityMindResearchStudio/0.1 contact@example.com"
    finbert_model: str = "ProsusAI/finbert"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
