"""
routes/prompts.py – Prompt template and analytics endpoints.

Provides:
  • GET /api/prompts               – list available prompt templates
  • GET /api/analytics             – aggregated analytics (model/prompt performance)
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db, UsageStat
from backend.services.prompt_service import list_templates

router = APIRouter(prefix="/api", tags=["prompts", "analytics"])
logger = logging.getLogger("chatbot.routes.prompts")


@router.get("/prompts")
def get_prompts() -> list[dict]:
    """Return available prompt templates for the UI selector."""
    return list_templates()


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)) -> dict:
    """
    Compute analytics from local usage_stats table.

    Returns:
      - avg_latency_by_model    : dict[model → avg_latency_ms]
      - avg_tokens_by_model     : dict[model → avg_total_tokens]
      - cost_by_model           : dict[model → total_cost]
      - requests_by_model       : dict[model → count]
      - avg_latency_by_template : dict[template → avg_latency_ms]
      - requests_by_template    : dict[template → count]
      - error_rate_by_model     : dict[model → error_rate %]
    """
    successful = db.query(UsageStat).filter(UsageStat.is_error == False)

    # ── Per-model stats ──────────────────────────────────────────────────────
    model_rows = (
        successful.with_entities(
            UsageStat.model,
            func.count(UsageStat.id).label("requests"),
            func.avg(UsageStat.latency_ms).label("avg_latency"),
            func.avg(UsageStat.total_tokens).label("avg_tokens"),
            func.sum(UsageStat.estimated_cost).label("total_cost"),
        )
        .group_by(UsageStat.model)
        .all()
    )

    avg_latency_by_model = {}
    avg_tokens_by_model = {}
    cost_by_model = {}
    requests_by_model = {}
    for r in model_rows:
        avg_latency_by_model[r.model] = round(float(r.avg_latency or 0), 2)
        avg_tokens_by_model[r.model] = round(float(r.avg_tokens or 0), 1)
        cost_by_model[r.model] = round(float(r.total_cost or 0), 6)
        requests_by_model[r.model] = r.requests

    # ── Per-template stats ────────────────────────────────────────────────────
    tmpl_rows = (
        successful.with_entities(
            UsageStat.prompt_template,
            func.count(UsageStat.id).label("requests"),
            func.avg(UsageStat.latency_ms).label("avg_latency"),
        )
        .group_by(UsageStat.prompt_template)
        .all()
    )

    avg_latency_by_template = {}
    requests_by_template = {}
    for r in tmpl_rows:
        avg_latency_by_template[r.prompt_template] = round(float(r.avg_latency or 0), 2)
        requests_by_template[r.prompt_template] = r.requests

    # ── Error rate by model ───────────────────────────────────────────────────
    # Fetch all stats grouped by model and compute error rate in Python
    all_rows = (
        db.query(
            UsageStat.model,
            UsageStat.is_error,
            func.count(UsageStat.id).label("count"),
        )
        .group_by(UsageStat.model, UsageStat.is_error)
        .all()
    )

    model_totals: dict[str, int] = {}
    model_errors: dict[str, int] = {}
    for r in all_rows:
        model_totals[r.model] = model_totals.get(r.model, 0) + r.count
        if r.is_error:
            model_errors[r.model] = model_errors.get(r.model, 0) + r.count

    error_rate_by_model = {}
    for model, total in model_totals.items():
        if total > 0:
            errors = model_errors.get(model, 0)
            error_rate_by_model[model] = round((errors / total) * 100, 2)

    return {
        "avg_latency_by_model": avg_latency_by_model,
        "avg_tokens_by_model": avg_tokens_by_model,
        "cost_by_model": cost_by_model,
        "requests_by_model": requests_by_model,
        "avg_latency_by_template": avg_latency_by_template,
        "requests_by_template": requests_by_template,
        "error_rate_by_model": error_rate_by_model,
        # Derive "best" performers
        "fastest_model": min(avg_latency_by_model, key=avg_latency_by_model.get) if avg_latency_by_model else None,
        "cheapest_model": min(cost_by_model, key=cost_by_model.get) if cost_by_model else None,
        "most_used_template": max(requests_by_template, key=requests_by_template.get) if requests_by_template else None,
    }
