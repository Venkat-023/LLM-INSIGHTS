"""
models/chat.py – Pydantic request/response models for chat endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""
    message: str = Field(..., description="User's message text")
    user_id: str = Field(default="anonymous", description="Client-provided user identifier")
    session_id: str = Field(..., description="Browser session identifier")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID; None to start new")
    prompt_template: str = Field(default="friendly-assistant", description="Which system prompt template to use")
    stream: bool = Field(default=False, description="Whether to stream the response")
    provider: Optional[str] = Field(None, description="The LLM provider, e.g. openai, anthropic, gemini")
    api_key: Optional[str] = Field(None, description="User's custom LLM API key")
    model: Optional[str] = Field(None, description="User's custom LLM model")


class TokenUsage(BaseModel):
    """Token counts returned with every response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float


class ChatResponse(BaseModel):
    """Response payload sent back to the frontend."""
    reply: str
    conversation_id: str
    trace_id: str                           # Langfuse trace ID – used to attach feedback
    model: str
    token_usage: TokenUsage
    latency_ms: float
    timestamp: datetime


class ConversationSummary(BaseModel):
    """Lightweight conversation listing item."""
    id: str
    title: str
    prompt_template: str
    total_tokens: int
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    """A single message returned when loading history."""
    id: str
    role: str
    content: str
    trace_id: Optional[str]
    created_at: datetime
