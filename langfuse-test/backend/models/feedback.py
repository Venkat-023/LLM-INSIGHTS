"""
models/feedback.py – Pydantic models for user feedback endpoints.

Feedback is forwarded to Langfuse as a 'score' attached to a trace.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class FeedbackLabel(str, Enum):
    helpful = "helpful"
    not_helpful = "not_helpful"


class FeedbackRequest(BaseModel):
    """Feedback submitted by the user after an AI response."""
    trace_id: str = Field(..., description="Langfuse trace ID from the ChatResponse")
    label: FeedbackLabel = Field(..., description="Thumbs up or down")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1–5 star rating")
    comment: Optional[str] = Field(None, max_length=500, description="Optional text comment")


class FeedbackResponse(BaseModel):
    """Confirmation that feedback was received."""
    success: bool
    message: str
