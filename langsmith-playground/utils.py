"""Shared helpers for the terminal app."""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.panel import Panel


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "prompt"


def count_tokens_approx(text: str) -> int:
    """Simple fallback token estimate used only for local summaries."""

    return max(1, len(text.split()))


def format_token_summary(token_usage) -> str:
    return (
        f"Token usage: prompt={token_usage.prompt}, completion={token_usage.completion}, "
        f"total={token_usage.total}"
    )


def pretty_metadata(metadata: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in metadata.items())


def multiline_input(prompt: str, *, end_token: str, console: Console) -> str:
    console.print(Panel(f"{prompt}\n\nEnter multiple lines and finish with [{end_token}].", border_style="blue"))
    lines: list[str] = []
    while True:
        line = console.input("> ")
        if line.strip() == end_token:
            break
        lines.append(line)
    return "\n".join(lines).strip()
