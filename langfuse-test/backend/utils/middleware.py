"""
utils/middleware.py – FastAPI logging middleware.

Logs every HTTP request with method, path, status code, and duration.
"""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("chatbot.http")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each incoming request and its response status."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        # Process the request
        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d  (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
