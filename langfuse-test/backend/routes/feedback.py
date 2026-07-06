"""
routes/feedback.py – User feedback endpoints.

HOW FEEDBACK WORKS IN LANGFUSE:
────────────────────────────────
1. After each AI response the frontend receives a `trace_id`.
2. The user clicks 👍/👎, optionally rates 1-5 stars and adds a comment.
3. The frontend POSTs to /api/feedback with the trace_id and feedback data.
4. This endpoint calls `langfuse.score()` which attaches the feedback
   to the trace as a "Score" object.
5. In the Langfuse UI you can filter traces by score, see which prompts
   receive the best ratings, and export feedback for fine-tuning.
"""
import logging

from fastapi import APIRouter, HTTPException
from backend.models.feedback import FeedbackRequest, FeedbackResponse
from backend.services.langfuse_service import langfuse_service

router = APIRouter(prefix="/api", tags=["feedback"])
logger = logging.getLogger("chatbot.routes.feedback")


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Attach user feedback to a Langfuse trace.

    The `trace_id` comes from the ChatResponse and uniquely identifies
    the LLM call that produced the response being rated.
    """
    try:
        langfuse_service.submit_score(
            trace_id=request.trace_id,
            label=request.label.value,
            rating=request.rating,
            comment=request.comment,
        )
        logger.info(
            "Feedback submitted: trace=%s label=%s rating=%s",
            request.trace_id, request.label.value, request.rating,
        )
        return FeedbackResponse(success=True, message="Feedback recorded. Thank you!")

    except Exception as exc:
        logger.error("Failed to submit feedback: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to record feedback")
