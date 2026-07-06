"""LangChain LLM wrapper used by the playground."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from config import AppSettings


@dataclass(frozen=True)
class TokenUsage:
    prompt: int = 0
    completion: int = 0
    total: int = 0


@dataclass(frozen=True)
class LLMResponse:
    content: str
    token_usage: TokenUsage
    latency_seconds: float
    raw_response: dict[str, Any]


class LLMClient:
    """Small provider switch for OpenAI-compatible and Anthropic chat models."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        if settings.langsmith_api_key:
            os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        if settings.langsmith_endpoint:
            os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
        if settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        if settings.openai_base_url:
            os.environ.setdefault("OPENAI_BASE_URL", settings.openai_base_url)
        if settings.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
        os.environ.setdefault("LANGSMITH_TRACING", "true" if settings.langsmith_tracing else "false")
        os.environ.setdefault("LANGSMITH_PROJECT", settings.project_name)

    def _build_model(self) -> BaseChatModel:
        if self.settings.llm_provider == "anthropic":
            return ChatAnthropic(
                model=self.settings.model_name,
                temperature=self.settings.temperature,
                timeout=self.settings.timeout_seconds,
            )

        return ChatOpenAI(
            model=self.settings.model_name,
            temperature=self.settings.temperature,
            timeout=self.settings.timeout_seconds,
        )

    def generate(
        self,
        *,
        prompt_messages: list[dict[str, str]],
        feature: str,
        prompt_name: str,
        metadata: dict[str, Any],
        tags: list[str],
    ) -> LLMResponse:
        if self.settings.llm_provider == "anthropic" and not self.settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing. Set it in .env to use Anthropic.")

        if self.settings.llm_provider != "anthropic" and not self.settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing. Set it in .env to use any OpenAI-compatible provider."
            )

        model = self._build_model()
        messages = self._to_messages(prompt_messages)

        started = time.perf_counter()
        response = model.invoke(messages, config={"metadata": metadata, "tags": tags})
        latency = time.perf_counter() - started

        content = response.content if isinstance(response.content, str) else str(response.content)
        token_usage = self._extract_token_usage(response)
        raw_response = self._serialize_response(response)

        return LLMResponse(
            content=content.strip(),
            token_usage=token_usage,
            latency_seconds=latency,
            raw_response={
                "feature": feature,
                "prompt_name": prompt_name,
                "prompt_messages": prompt_messages,
                "response": raw_response,
            },
        )

    def _to_messages(self, prompt_messages: list[dict[str, str]]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for message in prompt_messages:
            role = message["role"]
            content = message["content"]
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def _extract_token_usage(self, response: AIMessage) -> TokenUsage:
        usage_metadata = getattr(response, "usage_metadata", None) or {}
        response_metadata = getattr(response, "response_metadata", {}) or {}

        prompt_tokens = int(
            usage_metadata.get("input_tokens")
            or usage_metadata.get("prompt_tokens")
            or response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
            or 0
        )
        completion_tokens = int(
            usage_metadata.get("output_tokens")
            or usage_metadata.get("completion_tokens")
            or response_metadata.get("token_usage", {}).get("completion_tokens", 0)
            or 0
        )
        total_tokens = int(
            usage_metadata.get("total_tokens")
            or response_metadata.get("token_usage", {}).get("total_tokens", 0)
            or (prompt_tokens + completion_tokens)
        )

        return TokenUsage(
            prompt=prompt_tokens,
            completion=completion_tokens,
            total=total_tokens,
        )

    def _serialize_response(self, response: AIMessage) -> dict[str, Any]:
        return {
            "content": response.content,
            "additional_kwargs": dict(getattr(response, "additional_kwargs", {}) or {}),
            "response_metadata": dict(getattr(response, "response_metadata", {}) or {}),
            "usage_metadata": dict(getattr(response, "usage_metadata", {}) or {}),
        }
