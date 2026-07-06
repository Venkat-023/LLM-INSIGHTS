"""
utils/errors.py – Custom exception hierarchy for the chatbot backend.

These are raised by services and caught in route handlers, which then
return appropriate HTTP responses AND log the error to Langfuse.
"""


class ChatbotBaseError(Exception):
    """Base class for all chatbot errors."""
    http_status: int = 500
    user_message: str = "An unexpected error occurred. Please try again."

    def __init__(self, detail: str = "", user_message: str = ""):
        self.detail = detail
        self.user_message = user_message or detail or getattr(self, "user_message", "An unexpected error occurred. Please try again.")
        super().__init__(detail)


# ── Token / Rate Limit Errors ─────────────────────────────────────────────────

class TokenLimitError(ChatbotBaseError):
    """Raised when a token limit would be exceeded."""
    http_status = 429

    def __init__(self, limit_type: str, limit_value: int, current_value: int):
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.current_value = current_value
        messages = {
            "prompt_length": (
                f"Your message is too long ({current_value} chars). "
                f"Please keep it under {limit_value} characters."
            ),
            "response_tokens": (
                f"The response token limit ({limit_value}) would be exceeded."
            ),
            "conversation_tokens": (
                f"This conversation has reached the maximum token limit ({limit_value}). "
                "Please start a new conversation."
            ),
        }
        msg = messages.get(limit_type, f"Token limit exceeded: {limit_type}")
        super().__init__(detail=msg, user_message=msg)


class DailyLimitError(ChatbotBaseError):
    """Raised when the user has exceeded their daily request quota."""
    http_status = 429

    def __init__(self, user_id: str, limit: int):
        msg = (
            f"You've reached your daily limit of {limit} requests. "
            "Please try again tomorrow."
        )
        super().__init__(detail=f"Daily limit {limit} reached for user {user_id}", user_message=msg)


# ── OpenAI Errors ─────────────────────────────────────────────────────────────

class OpenAIApiError(ChatbotBaseError):
    """Raised when OpenAI returns a non-retryable error."""
    http_status = 502
    user_message = "The AI service returned an error. Please try again."


class InvalidApiKeyError(ChatbotBaseError):
    """Raised when the OpenAI API key is invalid or expired."""
    http_status = 401
    user_message = "API key configuration error. Please contact the administrator."


class RateLimitError(ChatbotBaseError):
    """Raised when OpenAI rate limits are hit."""
    http_status = 429
    user_message = "The AI service is busy right now. Please wait a moment and try again."


class TimeoutError(ChatbotBaseError):
    """Raised when the OpenAI request times out."""
    http_status = 504
    user_message = "The AI service took too long to respond. Please try again."
