"""
config.py – Application settings using Pydantic BaseSettings.

All values are loaded from the .env file automatically.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application-wide configuration, sourced from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Langfuse ──────────────────────────────────────────────────────────────
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str

    # ── Token & Rate Limits ──────────────────────────────────────────────────
    max_prompt_length: int = 4000          # characters
    max_response_tokens: int = 1024        # tokens
    daily_request_limit: int = 100         # requests per user per day
    max_conversation_tokens: int = 8000    # total tokens per conversation

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    database_url: str = "sqlite:///./chatbot.db"
    backend_port: int = 8000
    frontend_port: int = 5173

    # ── Models ────────────────────────────────────────────────────────────────
    default_model: str = "gpt-4.1-mini"
    experiment_models: list[str] = ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"]
    mock_llm: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance (loaded once at startup)."""
    return Settings()
