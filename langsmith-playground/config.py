"""Configuration loading for the LangSmith playground."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppSettings:
    """All runtime configuration is loaded from the environment."""

    langsmith_api_key: str
    langsmith_tracing: bool
    langsmith_endpoint: str
    llm_provider: str
    openai_api_key: str
    openai_base_url: str
    anthropic_api_key: str
    model_name: str
    temperature: float
    timeout_seconds: float
    project_name: str
    session_id: str
    session_dir: Path
    user_id: str
    environment: str
    experiment: str
    language: str


def load_settings() -> AppSettings:
    load_dotenv()

    session_id = os.getenv("PLAYGROUND_SESSION_ID", uuid4().hex[:12])
    session_dir = Path("sessions") / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    return AppSettings(
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY", ""),
        langsmith_tracing=langsmith_tracing,
        langsmith_endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai").lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=float(os.getenv("TEMPERATURE", "0.2")),
        timeout_seconds=float(os.getenv("TIMEOUT_SECONDS", "60")),
        project_name=os.getenv("LANGSMITH_PROJECT", "langsmith-playground"),
        session_id=session_id,
        session_dir=session_dir,
        user_id=os.getenv("USER_ID", "demo-user"),
        environment=os.getenv("APP_ENV", "development"),
        experiment=os.getenv("EXPERIMENT_NAME", "v1"),
        language=os.getenv("LANGUAGE", "python"),
    )
