"""
models/experiment.py – Pydantic models for the model comparison experiment page.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ExperimentRequest(BaseModel):
    """Run the same prompt through multiple models."""
    prompt: str = Field(..., description="The prompt to test")
    models: List[str] = Field(
        default=["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        description="Models to compare",
    )
    user_id: str = Field(default="anonymous")
    prompt_template: str = Field(default="friendly-assistant")
    openai_key: Optional[str] = Field(None, description="User's custom OpenAI key")
    anthropic_key: Optional[str] = Field(None, description="User's custom Anthropic key")
    gemini_key: Optional[str] = Field(None, description="User's custom Gemini key")


class ModelResult(BaseModel):
    """Results for a single model in the experiment."""
    model: str
    response: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    latency_ms: float
    trace_id: str
    error: Optional[str] = None            # Non-None if the model call failed


class ExperimentResponse(BaseModel):
    """Full experiment results – one ModelResult per model."""
    results: List[ModelResult]
    prompt: str
