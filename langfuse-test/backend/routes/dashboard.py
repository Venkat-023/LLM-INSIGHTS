"""
routes/dashboard.py – Token usage dashboard endpoints.

Returns aggregated statistics from the local SQLite usage_stats table.
Data is written to SQLite on every successful chat request, so this
endpoint works purely from local data (no Langfuse API call needed here).
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db, UsageStat, DailyRequestCount

router = APIRouter(prefix="/api", tags=["dashboard"])
logger = logging.getLogger("chatbot.routes.dashboard")


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)) -> dict:
    """
    Aggregate token usage statistics for the dashboard.

    Returns:
      - total_requests, total_prompt_tokens, total_completion_tokens
      - total_tokens, estimated_cost, avg_latency_ms
      - error_count, error_rate
    """
    # Only count successful requests
    successful = db.query(UsageStat).filter(UsageStat.is_error == False)
    errors = db.query(UsageStat).filter(UsageStat.is_error == True)

    totals = successful.with_entities(
        func.count(UsageStat.id).label("total_requests"),
        func.coalesce(func.sum(UsageStat.prompt_tokens), 0).label("total_prompt_tokens"),
        func.coalesce(func.sum(UsageStat.completion_tokens), 0).label("total_completion_tokens"),
        func.coalesce(func.sum(UsageStat.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(UsageStat.estimated_cost), 0.0).label("estimated_cost"),
        func.coalesce(func.avg(UsageStat.latency_ms), 0.0).label("avg_latency_ms"),
    ).one()

    error_count = errors.count()
    total_all = (totals.total_requests or 0) + error_count
    error_rate = (error_count / total_all * 100) if total_all > 0 else 0.0

    return {
        "total_requests": totals.total_requests or 0,
        "total_prompt_tokens": int(totals.total_prompt_tokens or 0),
        "total_completion_tokens": int(totals.total_completion_tokens or 0),
        "total_tokens": int(totals.total_tokens or 0),
        "estimated_cost": round(float(totals.estimated_cost or 0), 6),
        "avg_latency_ms": round(float(totals.avg_latency_ms or 0), 2),
        "error_count": error_count,
        "error_rate": round(error_rate, 2),
    }


@router.get("/dashboard/per-user")
def get_per_user_stats(db: Session = Depends(get_db)) -> list[dict]:
    """Breakdown of request counts and token usage per user_id."""
    rows = (
        db.query(
            UsageStat.user_id,
            func.count(UsageStat.id).label("requests"),
            func.coalesce(func.sum(UsageStat.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageStat.estimated_cost), 0.0).label("cost"),
        )
        .filter(UsageStat.is_error == False)
        .group_by(UsageStat.user_id)
        .order_by(func.count(UsageStat.id).desc())
        .all()
    )
    return [
        {
            "user_id": r.user_id,
            "requests": r.requests,
            "total_tokens": int(r.total_tokens or 0),
            "cost": round(float(r.cost or 0), 6),
        }
        for r in rows
    ]


@router.get("/dashboard/daily-usage")
def get_daily_usage(db: Session = Depends(get_db)) -> list[dict]:
    """Daily request count and token usage for the past 30 days."""
    rows = (
        db.query(
            UsageStat.date,
            func.count(UsageStat.id).label("requests"),
            func.coalesce(func.sum(UsageStat.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageStat.estimated_cost), 0.0).label("cost"),
        )
        .filter(UsageStat.is_error == False)
        .group_by(UsageStat.date)
        .order_by(UsageStat.date.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "date": r.date,
            "requests": r.requests,
            "tokens": int(r.tokens or 0),
            "cost": round(float(r.cost or 0), 6),
        }
        for r in rows
    ]


@router.get("/dashboard/limits/{user_id}")
def get_user_limits(user_id: str, db: Session = Depends(get_db)) -> dict:
    """Return the user's current daily request usage vs. limit."""
    from backend.services.limits_service import get_remaining_requests
    from backend.config import get_settings
    settings = get_settings()
    remaining = get_remaining_requests(user_id, db)
    return {
        "user_id": user_id,
        "daily_limit": settings.daily_request_limit,
        "remaining": remaining,
        "used": settings.daily_request_limit - remaining,
    }


@router.get("/trace/{trace_id}")
def get_trace(trace_id: str) -> dict:
    """
    Fetch a Langfuse trace by ID from the Langfuse REST API.
    This powers the in-app Trace Inspector so users can see exactly
    what Langfuse recorded – model, tokens, latency, cost, scores, and observations.
    """
    import httpx
    from backend.config import get_settings
    settings = get_settings()

    url = f"{settings.langfuse_host}/api/public/traces/{trace_id}"
    try:
        with httpx.Client(timeout=10) as http:
            resp = http.get(url, auth=(settings.langfuse_public_key, settings.langfuse_secret_key))
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Langfuse returned {resp.status_code}", "detail": resp.text[:300]}
    except Exception as exc:
        return {"error": "Failed to fetch trace", "detail": str(exc)}

