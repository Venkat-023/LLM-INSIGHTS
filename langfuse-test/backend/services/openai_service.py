"""
services/openai_service.py – OpenAI API wrapper with Langfuse auto-instrumentation.

HOW AUTO-INSTRUMENTATION WORKS:
────────────────────────────────
Instead of importing `openai` directly, we import `langfuse.openai`.
This is a drop-in replacement that patches the OpenAI client so every
call to `chat.completions.create()` is automatically recorded in Langfuse
as a Generation observation, capturing:
  • model, input messages, output text
  • prompt_tokens, completion_tokens, total_tokens
  • latency
  • estimated cost (using Langfuse's built-in price table)

We then enrich the trace with our own metadata by calling
`langfuse_context.update_current_observation()` inside the @observe decorator.
"""
import time
import logging
import traceback
from typing import Optional, AsyncGenerator

# ── Langfuse drop-in replacement for OpenAI ───────────────────────────────────
# This single import enables automatic LLM observability.
from langfuse.openai import OpenAI
from langfuse.decorators import observe, langfuse_context

from backend.config import get_settings
from backend.utils.errors import (
    OpenAIApiError, InvalidApiKeyError, RateLimitError, TimeoutError
)
from backend.utils.cost_calculator import calculate_cost
import openai as openai_raw  # for exception types only

logger = logging.getLogger("chatbot.openai")
settings = get_settings()

# ── OpenAI client (Langfuse-instrumented) ─────────────────────────────────────
_client = OpenAI(api_key=settings.openai_api_key)


def generate_mock_response(prompt_template: str, user_message: str) -> str:
    """Generate realistic mock completions for testing when mock_llm is True."""
    user_msg_lower = user_message.lower()
    
    if "reverse" in user_msg_lower and "string" in user_msg_lower:
        if prompt_template == "technical-assistant":
            return (
                "Here is a Python function to reverse a string:\n\n"
                "```python\n"
                "def reverse_string(s: str) -> str:\n"
                "    return s[::-1]\n"
                "```\n\n"
                "### Explanation\n"
                "1. `s[::-1]` uses Python's slice syntax with a step of `-1` to traverse the string backwards.\n"
                "2. This is highly efficient, running in $O(n)$ time complexity and utilizing optimized C-level iterations.\n"
                "3. Edge cases: Handles empty strings and Unicode characters correctly."
            )
        elif prompt_template == "short-answer-assistant":
            return "You can reverse a string in Python using slicing: `reversed_str = my_string[::-1]`."
        else:
            return "Sure! To reverse a string in Python, you can use slicing. For example, `\"hello\"[::-1]` returns `\"olleh\"`. It's fast and easy!"

    if "langfuse" in user_msg_lower or "trace" in user_msg_lower or "observability" in user_msg_lower:
        if prompt_template == "technical-assistant":
            return (
                "### Langfuse Observability Tracing\n\n"
                "Langfuse traces LLM requests by wrapping calls or using decorators. Key concepts:\n"
                "1. **Traces**: The top-level execution path of a user interaction.\n"
                "2. **Observations**: Sub-steps inside a trace, which can be:\n"
                "   - *Generations*: LLM model inputs, outputs, token counts, and cost.\n"
                "   - *Spans*: Operations like DB lookups or vector search.\n"
                "   - *Events*: Discrete logs (e.g. errors, clicks).\n"
                "3. **Scores**: User-submitted feedback (👍/👎, ratings) attached to the trace ID."
            )
        elif prompt_template == "short-answer-assistant":
            return "Langfuse traces LLM applications by creating a parent 'Trace' for each user request, which contains sub-observations like 'Generations' (LLM calls) and 'Spans' (database queries)."
        else:
            return "Langfuse is an open-source LLM engineering platform! It helps you track, monitor, and optimize your LLM applications. It traces your inputs, outputs, latencies, costs, and lets users submit ratings (like 👍 or 👎) so you can measure quality over time."

    # Default responses
    if prompt_template == "technical-assistant":
        return (
            "### Simulated Technical Response\n\n"
            "I received your request: *\"" + user_message + "\"*.\n\n"
            "Here is how you can process this request in Python:\n"
            "```python\n"
            "def handle_request(msg: str):\n"
            "    # Simulated technical breakdown\n"
            "    print(f'Processing: {msg}')\n"
            "    return True\n"
            "```\n"
            "This mock response is returned because `MOCK_LLM=true` is enabled in your configuration, allowing you to test prompt versioning, trace logging, and user feedback without spending OpenAI quota."
        )
    elif prompt_template == "short-answer-assistant":
        return f"This is a short simulated response to your message: '{user_message}'. Mock mode is active."
    else:
        return (
            "Hello there! I received your message: \"" + user_message + "\". \n\n"
            "Since `MOCK_LLM=true` is active in the `.env` file, I am responding in simulation mode. "
            "Every interaction you have here is fully recorded and traced in your Langfuse dashboard! "
            "You can rate this response with the thumbs-up/down buttons below, and see the latency and cost metrics update. "
            "Is there anything else you'd like to test?"
        )


def call_openai(
    messages: list[dict],
    model: str,
    max_tokens: int,
    trace_id: str,
    user_id: str,
    prompt_template: str,
    session_id: str,
) -> dict:
    """
    Call the OpenAI Chat Completions API with Langfuse auto-instrumentation,
    or fall back to mock generation if Settings.mock_llm is True.
    """
    start_time = time.perf_counter()

    # ── Mock LLM Mode ─────────────────────────────────────────────────────────
    if settings.mock_llm:
        from datetime import datetime, timezone
        from backend.services.langfuse_service import langfuse_service
        
        start_time_dt = datetime.now(timezone.utc)
        time.sleep(0.3)  # simulate network/processing delay
        
        user_msg = messages[-1]["content"] if messages else ""
        text = generate_mock_response(prompt_template, user_msg)
        
        prompt_tokens = len(str(messages)) // 4
        completion_tokens = len(text) // 4
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = calculate_cost(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000
        end_time_dt = datetime.now(timezone.utc)
        
        try:
            langfuse_service.client.generation(
                trace_id=trace_id,
                name=f"chat-{prompt_template}",
                model=model,
                input=messages,
                output=text,
                usage={
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "total": total_tokens,
                },
                start_time=start_time_dt,
                end_time=end_time_dt,
                metadata={
                    "prompt_template": prompt_template,
                    "user_id": user_id,
                    "session_id": session_id,
                    "mock": True,
                }
            )
            logger.info("Mock LLM call successfully traced in Langfuse")
        except Exception as exc:
            logger.error("Failed to log mock generation to Langfuse: %s", exc)
            
        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "latency_ms": latency_ms,
        }

    # ── Real OpenAI API call ──────────────────────────────────────────────────
    try:
        response = _client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
            name=f"chat-{prompt_template}",
            metadata={
                "prompt_template": prompt_template,
                "user_id": user_id,
                "session_id": session_id,
                "trace_id": trace_id,
            },
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        usage = response.usage
        text = response.choices[0].message.content or ""

        estimated_cost = calculate_cost(
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        logger.info(
            "OpenAI call OK | model=%s tokens=%d latency=%.0fms cost=$%.6f",
            model, usage.total_tokens, latency_ms, estimated_cost,
        )

        return {
            "text": text,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost": estimated_cost,
            "latency_ms": latency_ms,
        }

    # ── Error handling & classification ───────────────────────────────────────
    # Each error type is re-raised as our custom exception so the route
    # handler can return the right HTTP status and log to Langfuse.

    except openai_raw.AuthenticationError as exc:
        logger.error("OpenAI authentication error: %s", exc)
        raise InvalidApiKeyError(detail=str(exc)) from exc

    except openai_raw.RateLimitError as exc:
        logger.warning("OpenAI rate limit hit: %s", exc)
        raise RateLimitError(detail=str(exc)) from exc

    except openai_raw.APITimeoutError as exc:
        logger.warning("OpenAI timeout: %s", exc)
        raise TimeoutError(detail=str(exc)) from exc

    except openai_raw.APIError as exc:
        logger.error("OpenAI API error: %s\n%s", exc, traceback.format_exc())
        raise OpenAIApiError(detail=str(exc)) from exc


def build_messages(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
) -> list[dict]:
    """
    Construct the OpenAI messages list from conversation history.

    The list starts with the system prompt, followed by alternating
    user/assistant messages from history, ending with the new user message.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    return messages
