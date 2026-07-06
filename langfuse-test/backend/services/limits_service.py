"""
services/limits_service.py – Token and rate limit enforcement.

Checks application-level limits before making any OpenAI API call.
All limits are configurable via .env variables.

Limits enforced:
  1. MAX_PROMPT_LENGTH       – max characters in a single user message
  2. MAX_RESPONSE_TOKENS     – max tokens requested in the response
  3. DAILY_REQUEST_LIMIT     – max requests per user per calendar day
  4. MAX_CONVERSATION_TOKENS – max total tokens in a conversation
"""
import logging
from datetime import date
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import DailyRequestCount, Conversation
from backend.utils.errors import TokenLimitError, DailyLimitError

logger = logging.getLogger("chatbot.limits")
settings = get_settings()


def check_prompt_length(message: str) -> None:
    """
    Raise TokenLimitError if the user's message exceeds MAX_PROMPT_LENGTH.
    Called before any DB or API access.
    """
    if len(message) > settings.max_prompt_length:
        raise TokenLimitError(
            limit_type="prompt_length",
            limit_value=settings.max_prompt_length,
            current_value=len(message),
        )


def check_daily_limit(user_id: str, db: Session) -> None:
    """
    Raise DailyLimitError if the user has hit their daily request quota.

    Uses a SQLite table (daily_request_counts) keyed by (user_id, date).
    """
    today = date.today().isoformat()
    record = (
        db.query(DailyRequestCount)
        .filter(DailyRequestCount.user_id == user_id, DailyRequestCount.date == today)
        .first()
    )
    if record and record.count >= settings.daily_request_limit:
        raise DailyLimitError(user_id=user_id, limit=settings.daily_request_limit)


def check_conversation_tokens(conversation_id: str, db: Session) -> None:
    """
    Raise TokenLimitError if the conversation has exceeded MAX_CONVERSATION_TOKENS.
    """
    if not conversation_id:
        return  # New conversation – no history yet

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv and conv.total_tokens >= settings.max_conversation_tokens:
        raise TokenLimitError(
            limit_type="conversation_tokens",
            limit_value=settings.max_conversation_tokens,
            current_value=conv.total_tokens,
        )


def increment_daily_count(user_id: str, db: Session) -> int:
    """
    Increment (or create) the daily request counter for a user.
    Returns the new count.
    """
    today = date.today().isoformat()
    record = (
        db.query(DailyRequestCount)
        .filter(DailyRequestCount.user_id == user_id, DailyRequestCount.date == today)
        .first()
    )
    if record:
        record.count += 1
    else:
        record = DailyRequestCount(user_id=user_id, date=today, count=1)
        db.add(record)
    db.commit()
    logger.debug("Daily count for %s on %s: %d", user_id, today, record.count)
    return record.count


def get_remaining_requests(user_id: str, db: Session) -> int:
    """Return how many requests the user has left today."""
    today = date.today().isoformat()
    record = (
        db.query(DailyRequestCount)
        .filter(DailyRequestCount.user_id == user_id, DailyRequestCount.date == today)
        .first()
    )
    used = record.count if record else 0
    return max(0, settings.daily_request_limit - used)
