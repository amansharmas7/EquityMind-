"""Typed application configuration."""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    api_key: str | None = None
    demo_mode: bool = True
    market_country: str = "IN"
    market_exchange: str = "NSE"
    market_currency: str = "INR"
    market_timezone: str = "Asia/Kolkata"
    database_url: str | None = None
    vector_dimensions: int = Field(default=384, ge=1, le=8192)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sec_user_agent: str = "EquityMindResearchStudio/0.1 contact@example.com"
    finbert_model: str = "ProsusAI/finbert"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
