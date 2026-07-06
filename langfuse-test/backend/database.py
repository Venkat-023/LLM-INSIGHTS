"""
database.py – SQLAlchemy async SQLite setup.

Tables:
  - conversations  : one row per conversation (user_id, session_id, etc.)
  - messages       : one row per message (linked to conversation)
  - request_counts : daily request counter per user (for rate limiting)
  - usage_stats    : one row per LLM call capturing token / cost data
"""
from sqlalchemy import (
    create_engine, Column, String, Integer, Float,
    DateTime, Text, ForeignKey, Boolean, func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Generator

from backend.config import get_settings

settings = get_settings()

# ── Engine & Session ──────────────────────────────────────────────────────────
# Using synchronous SQLite for simplicity (connect_args required for SQLite)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── ORM Models ────────────────────────────────────────────────────────────────

class Conversation(Base):
    """Represents a chat session."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)          # UUID
    user_id = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    title = Column(String, default="New Conversation")
    prompt_template = Column(String, default="friendly-assistant")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_tokens = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Message(Base):
    """Represents a single message in a conversation."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)           # UUID
    conversation_id = Column(String, ForeignKey("conversations.id"), index=True)
    role = Column(String, nullable=False)                       # "user" | "assistant"
    content = Column(Text, nullable=False)
    trace_id = Column(String, nullable=True)                    # Langfuse trace ID
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageStat(Base):
    """Records token usage and cost per LLM request."""
    __tablename__ = "usage_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    conversation_id = Column(String, index=True)
    trace_id = Column(String, nullable=True)                    # Langfuse trace ID
    model = Column(String)
    prompt_template = Column(String)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    is_error = Column(Boolean, default=False)
    error_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    date = Column(String)                                       # "YYYY-MM-DD" for easy grouping


class DailyRequestCount(Base):
    """Tracks daily request count per user for rate limiting."""
    __tablename__ = "daily_request_counts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    date = Column(String, index=True)                           # "YYYY-MM-DD"
    count = Column(Integer, default=0)


def create_tables() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
