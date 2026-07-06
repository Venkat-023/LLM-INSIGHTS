"""
services/langfuse_service.py – Central Langfuse client wrapper.

HOW LANGFUSE WORKS:
───────────────────
1. Every chat request creates a *Trace* (top-level unit of observability).
2. Inside the trace, individual LLM calls are recorded as *Generations*
   (a type of observation) via the langfuse.openai drop-in wrapper.
3. User feedback (👍/👎/⭐) is submitted as a *Score* linked to the trace.
4. Prompt templates are versioned in Langfuse *Prompts* management.
5. Errors are attached to the current observation via langfuse_context.

All methods are synchronous to keep the integration straightforward.
"""
import logging
import traceback
from functools import lru_cache
from typing import Optional

from langfuse import Langfuse

from backend.config import get_settings

logger = logging.getLogger("chatbot.langfuse")
settings = get_settings()


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse:
    """
    Return a cached Langfuse client instance.

    Langfuse is initialised with credentials from .env.
    The client batches and flushes traces asynchronously in the background.
    """
    client = Langfuse(
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host,
    )
    logger.info("Langfuse client initialised (host=%s)", settings.langfuse_host)
    return client


class LangfuseService:
    """
    Thin wrapper around the Langfuse Python SDK.

    Key Langfuse concepts used here:
      • Trace     – top-level container for one end-user request
      • Span      – sub-unit inside a trace (e.g. a retrieval step)
      • Generation– span specifically for an LLM call
      • Score     – numeric/categorical feedback attached to a trace
      • Prompt    – versioned prompt template stored in Langfuse
    """

    def __init__(self):
        self.client = get_langfuse_client()

    # ── Traces ────────────────────────────────────────────────────────────────

    def create_trace(
        self,
        name: str,
        user_id: str,
        session_id: str,
        conversation_id: str,
        input_text: str,
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """
        Create a new Langfuse trace and return its ID.

        The trace ID is stored alongside the assistant message in SQLite so
        we can later attach feedback scores to it.
        """
        trace = self.client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            # Langfuse uses 'metadata' as a free-form dict for extra context
            metadata={
                "conversation_id": conversation_id,
                "environment": settings.environment,
                **(metadata or {}),
            },
            tags=tags or ["chat", settings.environment],
            input=input_text,
        )
        logger.debug("Created Langfuse trace id=%s user=%s", trace.id, user_id)
        return trace.id

    def update_trace_output(self, trace_id: str, output_text: str) -> None:
        """Update a trace with the final output after the LLM call completes."""
        try:
            self.client.trace(id=trace_id, output=output_text)
        except Exception as exc:
            logger.warning("Failed to update trace %s: %s", trace_id, exc)

    # ── Feedback / Scores ─────────────────────────────────────────────────────

    def submit_score(
        self,
        trace_id: str,
        label: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> None:
        """
        Attach user feedback to a trace as Langfuse Scores.

        Langfuse supports two score types:
          • "label" (categorical) – thumbs up/down
          • "rating" (numeric)    – 1-5 stars
        Each score type is submitted as a separate score object.
        """
        try:
            # Categorical score: helpful / not_helpful
            self.client.score(
                trace_id=trace_id,
                name="user-feedback",
                value=1.0 if label == "helpful" else 0.0,
                comment=comment or "",
                data_type="BOOLEAN",
            )
            logger.debug("Submitted label score for trace %s: %s", trace_id, label)

            # Numeric score: 1-5 star rating
            if rating is not None:
                self.client.score(
                    trace_id=trace_id,
                    name="star-rating",
                    value=float(rating),
                    comment=comment or "",
                    data_type="NUMERIC",
                )
                logger.debug("Submitted rating score for trace %s: %d", trace_id, rating)
        except Exception as exc:
            logger.error("Failed to submit score for trace %s: %s", trace_id, exc)
            raise

    # ── Prompt Management ─────────────────────────────────────────────────────

    def get_prompt(self, name: str, fallback: str = "") -> str:
        """
        Fetch a prompt template from Langfuse Prompt Management.

        Langfuse caches prompts locally (default TTL 60s) so repeated
        fetches don't add latency.  If the fetch fails we return the fallback.
        """
        try:
            prompt = self.client.get_prompt(name, cache_ttl_seconds=300)
            return prompt.prompt
        except Exception as exc:
            logger.warning(
                "Could not fetch prompt '%s' from Langfuse (%s). Using fallback.",
                name, exc,
            )
            return fallback

    def create_or_update_prompt(
        self, name: str, prompt_text: str, labels: list[str] | None = None
    ) -> None:
        """
        Register or update a prompt in Langfuse Prompt Management.

        Called once at app startup so all three templates exist in the cloud.
        """
        try:
            self.client.create_prompt(
                name=name,
                prompt=prompt_text,
                labels=labels or ["production"],
                config={"source": "langfuse-chatbot-app"},
            )
            logger.info("Registered Langfuse prompt: %s", name)
        except Exception as exc:
            logger.warning("Could not register prompt '%s': %s", name, exc)

    # ── Error Logging ──────────────────────────────────────────────────────────

    def log_error(
        self,
        trace_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
    ) -> None:
        """
        Record an error as an event inside an existing Langfuse trace.

        This keeps error context co-located with the LLM trace so you can
        see both the prompt and the failure in the Langfuse UI.
        """
        try:
            trace = self.client.trace(id=trace_id)
            trace.event(
                name=f"error.{error_type}",
                level="ERROR",
                metadata={
                    "error_type": error_type,
                    "error_message": error_message,
                    "stack_trace": stack_trace or "",
                },
            )
            logger.error(
                "Logged error to Langfuse trace %s: [%s] %s",
                trace_id, error_type, error_message,
            )
        except Exception as exc:
            logger.error("Failed to log error to Langfuse: %s", exc)

    # ── Analytics helpers ─────────────────────────────────────────────────────

    def flush(self) -> None:
        """Force-flush any pending Langfuse events (useful at shutdown)."""
        try:
            self.client.flush()
        except Exception as exc:
            logger.warning("Langfuse flush error: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────
langfuse_service = LangfuseService()
