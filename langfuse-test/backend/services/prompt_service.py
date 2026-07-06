"""
services/prompt_service.py – Prompt template management via Langfuse.

HOW PROMPT VERSIONING WORKS:
─────────────────────────────
1. At app startup, `register_prompts()` is called which creates (or updates)
   the three prompt templates in Langfuse Prompt Management.
2. Every chat request calls `get_system_prompt(name)` which fetches the
   'production'-labelled version from Langfuse (with 5-minute local cache).
3. If Langfuse is unavailable, a local fallback is used so the app stays up.
4. Prompt versions are tracked in Langfuse, letting you see which prompt
   version was used for each LLM call in the dashboard.
"""
import logging
from functools import lru_cache

from backend.services.langfuse_service import langfuse_service

logger = logging.getLogger("chatbot.prompts")

# ── Local fallback prompt templates ──────────────────────────────────────────
# These are used if Langfuse is unreachable and serve as the initial values
# that are pushed to Langfuse on startup.

PROMPT_TEMPLATES: dict[str, dict] = {
    "friendly-assistant": {
        "name": "Friendly Assistant",
        "description": "Warm, conversational, encouraging. Great for general questions.",
        "system": (
            "You are a warm, friendly, and encouraging AI assistant. "
            "You speak conversationally, use simple language, and always aim to make "
            "the user feel comfortable asking any question. "
            "You celebrate curiosity and end responses with a helpful follow-up question "
            "when appropriate. Keep your answers clear and approachable."
        ),
    },
    "technical-assistant": {
        "name": "Technical Assistant",
        "description": "Precise, code-aware, structured. Best for coding and technical topics.",
        "system": (
            "You are a highly precise technical AI assistant with deep expertise in "
            "software engineering, computer science, and related fields. "
            "Your responses are structured, accurate, and include code examples where relevant. "
            "You prefer bullet points and headers for clarity. "
            "Always mention edge cases, potential pitfalls, and best practices. "
            "When providing code, include comments explaining the logic."
        ),
    },
    "short-answer-assistant": {
        "name": "Short Answer Assistant",
        "description": "Concise, direct. Answers in 1-3 sentences maximum.",
        "system": (
            "You are a concise AI assistant. Your answers must be brief and direct — "
            "no more than 2-3 sentences unless a longer answer is absolutely necessary. "
            "Avoid preamble, filler words, and unnecessary repetition. "
            "Get straight to the point."
        ),
    },
}


def register_prompts() -> None:
    """
    Register all three prompt templates in Langfuse at app startup.

    This ensures the prompts exist in Langfuse Prompt Management with the
    'production' label, ready to be fetched by get_system_prompt().
    """
    for key, template in PROMPT_TEMPLATES.items():
        langfuse_service.create_or_update_prompt(
            name=key,
            prompt_text=template["system"],
            labels=["production"],
        )
    logger.info("Registered %d prompt templates in Langfuse", len(PROMPT_TEMPLATES))


def get_system_prompt(template_name: str) -> str:
    """
    Fetch a system prompt from Langfuse (with local fallback).

    Langfuse caches the response for 5 minutes, so this call is fast
    after the first request.

    Args:
        template_name: One of the PROMPT_TEMPLATES keys

    Returns:
        The system prompt string to pass as the 'system' message to OpenAI
    """
    fallback = PROMPT_TEMPLATES.get(
        template_name,
        PROMPT_TEMPLATES["friendly-assistant"],
    )["system"]

    # Try to get the live version from Langfuse (may be edited in the cloud UI)
    prompt = langfuse_service.get_prompt(name=template_name, fallback=fallback)
    return prompt


def list_templates() -> list[dict]:
    """Return metadata for all available prompt templates."""
    return [
        {
            "id": key,
            "name": tmpl["name"],
            "description": tmpl["description"],
        }
        for key, tmpl in PROMPT_TEMPLATES.items()
    ]
