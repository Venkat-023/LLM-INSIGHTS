"""
services/llm_service.py – Unified LLM caller for OpenAI, Anthropic, and Gemini.

All three providers are called via their REST APIs or SDKs, and every call
is manually logged to Langfuse using the low-level client so traces appear
regardless of which provider is used.
"""
import time
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

import httpx
from openai import OpenAI as _OpenAIClient

from backend.config import get_settings
from backend.utils.cost_calculator import calculate_cost
from backend.utils.errors import OpenAIApiError, RateLimitError, InvalidApiKeyError
from backend.services.langfuse_service import get_langfuse_client

logger = logging.getLogger("chatbot.llm")
settings = get_settings()


# ── Cost tables for providers not in cost_calculator ──────────────────────────
ANTHROPIC_COSTS = {
    "claude-opus-4-5":      {"input": 15.0,  "output": 75.0},
    "claude-sonnet-4-5":    {"input": 3.0,   "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022":  {"input": 0.80, "output": 4.0},
    "claude-3-haiku-20240307":    {"input": 0.25, "output": 1.25},
}

GEMINI_COSTS = {
    "gemini-1.5-pro":       {"input": 1.25,  "output": 5.0},
    "gemini-1.5-flash":     {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash":     {"input": 0.10,  "output": 0.40},
    "gemini-2.5-flash-preview-05-20": {"input": 0.075, "output": 0.30},
}


def _compute_cost_per_million(model: str, input_tokens: int, output_tokens: int, table: dict) -> float:
    prices = table.get(model)
    if not prices:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


def _log_generation(
    trace_id: str,
    name: str,
    model: str,
    messages: list,
    output: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    start_time: datetime,
    end_time: datetime,
    metadata: dict,
) -> None:
    """Manually log a generation observation to Langfuse."""
    try:
        client = get_langfuse_client()
        client.generation(
            trace_id=trace_id,
            name=name,
            model=model,
            input=messages,
            output=output,
            usage={
                "input": prompt_tokens,
                "output": completion_tokens,
                "total": total_tokens,
                "unit": "TOKENS",
            },
            start_time=start_time,
            end_time=end_time,
            metadata=metadata,
        )
        client.flush()
        logger.debug("Logged generation to Langfuse trace %s", trace_id)
    except Exception as exc:
        logger.warning("Failed to log generation to Langfuse: %s", exc)


# ── OpenAI ────────────────────────────────────────────────────────────────────

def call_openai(
    messages: list[dict],
    model: str,
    max_tokens: int,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
    api_key: Optional[str] = None,
) -> dict:
    """Call OpenAI and log the generation to Langfuse."""
    key = api_key or settings.openai_api_key
    client = _OpenAIClient(api_key=key)

    start_dt = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
    except Exception as exc:
        msg = str(exc)
        if "insufficient_quota" in msg or "quota" in msg.lower():
            raise RateLimitError(
                detail="Your OpenAI API key has exceeded its quota. "
                       "Please top up your account at https://platform.openai.com/account/billing "
                       "or enter a different key in Settings."
            ) from exc
        if "Incorrect API key" in msg or "authentication" in msg.lower():
            raise InvalidApiKeyError(detail="Invalid OpenAI API key. Check your key and try again.") from exc
        raise OpenAIApiError(detail=msg) from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    end_dt = datetime.now(timezone.utc)

    text = response.choices[0].message.content or ""
    usage = response.usage
    cost = calculate_cost(model=model, prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens)

    _log_generation(
        trace_id=trace_id,
        name=f"openai-{prompt_template}",
        model=model,
        messages=messages,
        output=text,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost=cost,
        start_time=start_dt,
        end_time=end_dt,
        metadata={"provider": "openai", "prompt_template": prompt_template, "user_id": user_id},
    )

    return {
        "text": text,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
    }


# ── Anthropic ─────────────────────────────────────────────────────────────────

def call_anthropic(
    messages: list[dict],
    model: str,
    max_tokens: int,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
    api_key: str,
) -> dict:
    """Call Anthropic Claude via REST API and log to Langfuse."""
    # Separate system message from chat messages
    system_text = ""
    chat_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            chat_msgs.append(m)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict = {
        "model": model,
        "messages": chat_msgs,
        "max_tokens": max_tokens,
    }
    if system_text:
        payload["system"] = system_text

    start_dt = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    try:
        with httpx.Client(timeout=60) as http:
            resp = http.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise OpenAIApiError(detail="Anthropic request timed out.") from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    end_dt = datetime.now(timezone.utc)

    if resp.status_code == 401:
        raise InvalidApiKeyError(detail="Invalid Anthropic API key.")
    if resp.status_code == 429:
        raise RateLimitError(detail="Anthropic rate limit or quota exceeded.")
    if resp.status_code != 200:
        raise OpenAIApiError(detail=f"Anthropic error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    text = data["content"][0]["text"]
    usage = data.get("usage", {})
    prompt_tokens = usage.get("input_tokens", 0)
    completion_tokens = usage.get("output_tokens", 0)
    total_tokens = prompt_tokens + completion_tokens
    cost = _compute_cost_per_million(model, prompt_tokens, completion_tokens, ANTHROPIC_COSTS)

    _log_generation(
        trace_id=trace_id,
        name=f"anthropic-{prompt_template}",
        model=model,
        messages=messages,
        output=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        start_time=start_dt,
        end_time=end_dt,
        metadata={"provider": "anthropic", "prompt_template": prompt_template, "user_id": user_id},
    )

    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
    }


# ── Gemini ────────────────────────────────────────────────────────────────────

def _to_gemini_contents(messages: list[dict]) -> list[dict]:
    """Convert OpenAI-style messages to Gemini contents format."""
    contents = []
    for m in messages:
        if m["role"] == "system":
            # Prepend system as a user turn prefixed with [SYSTEM]
            contents.append({"role": "user", "parts": [{"text": f"[SYSTEM INSTRUCTION]\n{m['content']}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})
    return contents


def call_gemini(
    messages: list[dict],
    model: str,
    max_tokens: int,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
    api_key: str,
) -> dict:
    """Call Google Gemini via REST API and log to Langfuse."""
    contents = _to_gemini_contents(messages)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        },
    }

    start_dt = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    try:
        with httpx.Client(timeout=60) as http:
            resp = http.post(url, json=payload)
    except httpx.TimeoutException as exc:
        raise OpenAIApiError(detail="Gemini request timed out.") from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    end_dt = datetime.now(timezone.utc)

    if resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
        raise InvalidApiKeyError(detail="Invalid Gemini API key.")
    if resp.status_code == 429:
        raise RateLimitError(detail="Gemini rate limit or quota exceeded.")
    if resp.status_code != 200:
        raise OpenAIApiError(detail=f"Gemini error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise OpenAIApiError(detail=f"Unexpected Gemini response: {str(data)[:200]}")

    usage = data.get("usageMetadata", {})
    prompt_tokens = usage.get("promptTokenCount", 0)
    completion_tokens = usage.get("candidatesTokenCount", 0)
    total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
    cost = _compute_cost_per_million(model, prompt_tokens, completion_tokens, GEMINI_COSTS)

    _log_generation(
        trace_id=trace_id,
        name=f"gemini-{prompt_template}",
        model=model,
        messages=messages,
        output=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        start_time=start_dt,
        end_time=end_dt,
        metadata={"provider": "gemini", "prompt_template": prompt_template, "user_id": user_id},
    )

    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
    }


# ── Mock ──────────────────────────────────────────────────────────────────────

def _mock_text(prompt_template: str, user_message: str) -> str:
    u = user_message.lower()
    if "reverse" in u and "string" in u:
        if prompt_template == "technical-assistant":
            return "```python\ndef reverse_string(s: str) -> str:\n    return s[::-1]\n```\nThis runs in O(n) and handles Unicode correctly."
        return "Use slicing: `my_string[::-1]`"
    if any(k in u for k in ("langfuse", "trace", "observab")):
        return (
            "Langfuse creates a **Trace** for every request. Inside each trace it records:\n"
            "- **Generations** – the actual LLM call (model, tokens, cost, latency)\n"
            "- **Spans** – other operations like DB queries\n"
            "- **Scores** – your 👍/👎 feedback\n\n"
            "Every message you send right now creates a real trace in your Langfuse dashboard!"
        )
    return (
        f"*(Mock mode – set your API key in ⚙️ Settings to use a real LLM)*\n\n"
        f"You asked: \"{user_message}\"\n\n"
        "I'm responding in simulation mode. All interactions are still traced in Langfuse "
        "with realistic token counts and latency metrics."
    )


def call_mock(
    messages: list[dict],
    model: str,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
) -> dict:
    start_dt = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    time.sleep(0.3)

    user_msg = messages[-1]["content"] if messages else ""
    text = _mock_text(prompt_template, user_msg)
    prompt_tokens = len(str(messages)) // 4
    completion_tokens = len(text) // 4
    total_tokens = prompt_tokens + completion_tokens
    cost = calculate_cost(model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    latency_ms = (time.perf_counter() - t0) * 1000
    end_dt = datetime.now(timezone.utc)

    _log_generation(
        trace_id=trace_id,
        name=f"mock-{prompt_template}",
        model=model,
        messages=messages,
        output=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        start_time=start_dt,
        end_time=end_dt,
        metadata={"provider": "mock", "prompt_template": prompt_template, "user_id": user_id, "mock": True},
    )

    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
    }


# ── Free LLM (Pollinations AI) ────────────────────────────────────────────────

def call_free(
    messages: list[dict],
    model: str,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
) -> dict:
    """Call Pollinations AI free text generation API and log to Langfuse."""
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": messages,
        "model": model,  # e.g. "openai", "llama", "mistral", "qwen"
        "jsonMode": False
    }

    start_dt = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    try:
        with httpx.Client(timeout=60) as http:
            resp = http.post(url, json=payload)
    except httpx.TimeoutException as exc:
        raise OpenAIApiError(detail="Free LLM service timed out.") from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    end_dt = datetime.now(timezone.utc)

    if resp.status_code != 200:
        raise OpenAIApiError(detail=f"Free LLM service returned error {resp.status_code}: {resp.text[:200]}")

    text = resp.text
    
    # Estimate token usage
    prompt_tokens = len(str(messages)) // 4
    completion_tokens = len(text) // 4
    total_tokens = prompt_tokens + completion_tokens
    cost = 0.0  # 100% Free!

    _log_generation(
        trace_id=trace_id,
        name=f"free-{prompt_template}",
        model=model,
        messages=messages,
        output=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        start_time=start_dt,
        end_time=end_dt,
        metadata={"provider": "free_llm", "prompt_template": prompt_template, "user_id": user_id},
    )

    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch_llm(
    messages: list[dict],
    model: str,
    max_tokens: int,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Route the request to the appropriate LLM provider based on `provider`.

    Priority:
      1. If provider + api_key are given → use that provider
      2. If provider is "free" → use free keyless LLM (Pollinations AI)
      3. If settings.mock_llm is True → use mock
      4. Default → try OpenAI with .env key
    """
    p = (provider or "").lower().strip()

    if p == "free":
        return call_free(messages, model, trace_id, user_id, prompt_template, session_id)

    if p == "anthropic" and api_key:
        return call_anthropic(messages, model, max_tokens, trace_id, user_id, prompt_template, session_id, api_key)

    if p == "gemini" and api_key:
        return call_gemini(messages, model, max_tokens, trace_id, user_id, prompt_template, session_id, api_key)

    if p == "mock" or (not api_key and settings.mock_llm):
        return call_mock(messages, model, trace_id, user_id, prompt_template, session_id)

    # Default: OpenAI
    return call_openai(messages, model, max_tokens, trace_id, user_id, prompt_template, session_id, api_key=api_key)


def build_messages(system_prompt: str, conversation_history: list[dict], user_message: str) -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt}]
    msgs.extend(conversation_history)
    msgs.append({"role": "user", "content": user_message})
    return msgs
