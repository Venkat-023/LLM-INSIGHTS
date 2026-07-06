"""
main.py – FastAPI application entry point.

Startup sequence:
  1. Configure logging
  2. Create SQLite tables
  3. Register prompt templates in Langfuse
  4. Mount API routers
  5. Add CORS & logging middleware
  6. Serve frontend static files (production)
"""
import logging
import sys
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import create_tables
from backend.services.prompt_service import register_prompts
from backend.services.langfuse_service import langfuse_service
from backend.utils.middleware import LoggingMiddleware
from backend.routes import chat, feedback, dashboard, experiment, prompts

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("chatbot")

# ── Settings ──────────────────────────────────────────────────────────────────
settings = get_settings()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Langfuse AI Chatbot",
    description=(
        "A full-stack AI chatbot demonstrating Langfuse observability: "
        "traces, prompt management, user feedback, and analytics."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(dashboard.router)
app.include_router(experiment.router)
app.include_router(prompts.router)


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    """
    Runs once when the FastAPI server starts.

    1. Creates SQLite tables
    2. Registers prompt templates in Langfuse Prompt Management
    """
    logger.info("Starting Langfuse AI Chatbot (env=%s)", settings.environment)
    create_tables()
    logger.info("SQLite tables ready")
    register_prompts()
    logger.info("Langfuse prompts registered")


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Flush pending Langfuse events before the server exits."""
    langfuse_service.flush()
    logger.info("Langfuse flushed. Goodbye!")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
    )
