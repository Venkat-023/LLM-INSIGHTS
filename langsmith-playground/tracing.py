"""Tracing helpers.

The real LangSmith decorator is used when the SDK is installed. A fallback keeps
the app importable in environments where dependencies are not yet installed.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")

try:
    from langsmith import traceable as _traceable
except Exception:  # pragma: no cover - fallback only used without dependency
    _traceable = None


def traceable_run(*args: Any, **kwargs: Any):
    if _traceable is not None:
        return _traceable(*args, **kwargs)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*func_args: Any, **func_kwargs: Any) -> T:
            return func(*func_args, **func_kwargs)

        return wrapper

    return decorator


@contextmanager
def tracing_context(*args: Any, **kwargs: Any):
    """Compatibility helper if we want to add a scoped tracing override later."""

    yield
