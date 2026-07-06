"""
routes/experiment.py – Model comparison experiment endpoint.

Runs the same prompt through multiple OpenAI models in sequence,
creating a separate Langfuse trace for each model call.
Results are returned together for side-by-side comparison in the UI.
"""
import logging
import traceback
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db, UsageStat
from backend.models.experiment import ExperimentRequest, ExperimentResponse, ModelResult
from backend.services.langfuse_service import langfuse_service
from backend.services.llm_service import dispatch_llm, build_messages
from backend.services.prompt_service import get_system_prompt
from backend.config import get_settings

router = APIRouter(prefix="/api", tags=["experiment"])
logger = logging.getLogger("chatbot.routes.experiment")
settings = get_settings()


@router.post("/experiment", response_model=ExperimentResponse)
def run_experiment(
    request: ExperimentRequest,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Run the same prompt through multiple models and return comparison results.

    Each model gets its own Langfuse trace tagged with "experiment" so you
    can filter and compare them in the Langfuse dashboard.
    """
    system_prompt = get_system_prompt(request.prompt_template)
    messages = build_messages(system_prompt, [], request.prompt)
    results: list[ModelResult] = []

    for model in request.models:
        trace_id = ""
        try:
            # Create a Langfuse trace for this specific model in the experiment
            trace_id = langfuse_service.create_trace(
                name=f"experiment-{model}",
                user_id=request.user_id,
                session_id="experiment-session",
                conversation_id="experiment",
                input_text=request.prompt,
                metadata={
                    "experiment": True,
                    "model": model,
                    "prompt_template": request.prompt_template,
                },
                tags=["experiment", model, settings.environment],
            )

            # Determine provider and key for this model
            provider = "openai"
            api_key = request.openai_key
            if model.startswith("claude-"):
                provider = "anthropic"
                api_key = request.anthropic_key
            elif model.startswith("gemini-"):
                provider = "gemini"
                api_key = request.gemini_key

            result = dispatch_llm(
                messages=messages,
                model=model,
                max_tokens=400,
                trace_id=trace_id,
                user_id=request.user_id,
                prompt_template=request.prompt_template,
                session_id="experiment-session",
                provider=provider,
                api_key=api_key,
            )

            langfuse_service.update_trace_output(trace_id, result["text"])

            # Record in SQLite
            db.add(UsageStat(
                user_id=request.user_id,
                conversation_id="experiment",
                trace_id=trace_id,
                model=model,
                prompt_template=request.prompt_template,
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                estimated_cost=result["estimated_cost"],
                latency_ms=result["latency_ms"],
                date=date.today().isoformat(),
            ))
            db.commit()

            results.append(ModelResult(
                model=model,
                response=result["text"],
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                estimated_cost=result["estimated_cost"],
                latency_ms=result["latency_ms"],
                trace_id=trace_id,
            ))

        except Exception as exc:
            logger.error("Experiment failed for model %s: %s", model, exc)
            if trace_id:
                langfuse_service.log_error(
                    trace_id=trace_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    stack_trace=traceback.format_exc(),
                )
            results.append(ModelResult(
                model=model,
                response="",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
                latency_ms=0.0,
                trace_id=trace_id or "error",
                error=str(exc),
            ))

    return ExperimentResponse(results=results, prompt=request.prompt)
