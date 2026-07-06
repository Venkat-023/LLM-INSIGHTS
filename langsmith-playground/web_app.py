"""Backend API for the LangSmith Playground web UI."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import AppSettings, load_settings
from llm import LLMClient, LLMResponse
from prompts import get_prompt
from tracing import traceable_run

settings = load_settings()
llm = LLMClient(settings=settings)
app = FastAPI(title="LangSmith Playground", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class LabRequest(BaseModel):
    topic: str = Field(default="LangSmith observability", min_length=1)


class CompareRequest(BaseModel):
    question: str = Field(default="How should I monitor token usage?", min_length=1)


def base_metadata(feature: str, prompt_name: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "user_id": settings.user_id,
        "session_id": settings.session_id,
        "feature": feature,
        "environment": settings.environment,
        "experiment": settings.experiment,
        "language": settings.language,
        "ui": "web",
    }
    if prompt_name:
        metadata["prompt_name"] = prompt_name
    return metadata


def base_tags(*extra: str) -> list[str]:
    return ["demo", "playground", "langsmith", "web", *extra]


def response_payload(response: LLMResponse) -> dict[str, Any]:
    return {
        "content": response.content,
        "latency_seconds": response.latency_seconds,
        "tokens": {
            "prompt": response.token_usage.prompt,
            "completion": response.token_usage.completion,
            "total": response.token_usage.total,
        },
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "session_id": settings.session_id,
        "project": settings.project_name,
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "langsmith_tracing": settings.langsmith_tracing,
        "langsmith_dashboard": "https://smith.langchain.com",
        "ready": bool(settings.anthropic_api_key if settings.llm_provider == "anthropic" else settings.openai_api_key),
    }


@app.post("/api/chat")
@traceable_run(name="Web Chat", run_type="chain", tags=["web", "chat", "observability"])
def chat(request: ChatRequest) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": "You are a concise assistant helping test LangSmith tracing and token usage.",
        },
        {"role": "user", "content": request.message},
    ]
    response = llm.generate(
        prompt_messages=messages,
        feature="web-chat",
        prompt_name="web chat",
        metadata=base_metadata("web-chat", "web chat"),
        tags=base_tags("chat", "tokens"),
    )
    return {"trace_name": "Web Chat", **response_payload(response)}


@app.post("/api/observability-lab")
@traceable_run(
    name="Web Observability Lab",
    run_type="chain",
    tags=["web", "observability", "tokens", "latency", "analytics"],
)
def observability_lab(request: LabRequest) -> dict[str, Any]:
    started = time.perf_counter()
    scenarios = build_observability_scenarios(request.topic)
    results = []

    for scenario_name, messages in scenarios:
        estimated_tokens = estimate_tokens(messages)
        response = run_observability_scenario(scenario_name, messages, estimated_tokens)
        results.append(
            {
                "scenario": scenario_name,
                "estimated_input_tokens": estimated_tokens,
                **response_payload(response),
            }
        )

    totals = {
        "prompt": sum(item["tokens"]["prompt"] for item in results),
        "completion": sum(item["tokens"]["completion"] for item in results),
        "total": sum(item["tokens"]["total"] for item in results),
        "latency_seconds": time.perf_counter() - started,
    }
    return {
        "trace_name": "Web Observability Lab",
        "topic": request.topic,
        "results": results,
        "totals": totals,
    }


@traceable_run(name="Build Web Observability Scenarios", run_type="chain")
def build_observability_scenarios(topic: str) -> list[tuple[str, list[dict[str, str]]]]:
    system = "You are helping test LLM observability. Use a clear, structured answer."
    return [
        (
            "short-input",
            [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Explain {topic} in one sentence."},
            ],
        ),
        (
            "medium-input",
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Explain {topic}. Include a definition, two useful metrics, "
                        "and one practical dashboard workflow."
                    ),
                },
            ],
        ),
        (
            "long-input",
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Create a practical guide to {topic}. Cover traces, runs, token usage, "
                        "latency, metadata, tags, errors, analytics, and what to compare after each run."
                    ),
                },
            ],
        ),
    ]


@traceable_run(name="Web Observability Scenario", run_type="llm")
def run_observability_scenario(
    scenario_name: str,
    messages: list[dict[str, str]],
    estimated_tokens: int,
) -> LLMResponse:
    metadata = base_metadata("web-observability", scenario_name)
    metadata.update(
        {
            "scenario": scenario_name,
            "estimated_input_tokens": estimated_tokens,
            "observability_focus": "token_usage_latency_metadata_tags",
        }
    )
    return llm.generate(
        prompt_messages=messages,
        feature="web-observability",
        prompt_name=scenario_name,
        metadata=metadata,
        tags=base_tags("observability", "tokens", "latency", scenario_name),
    )


@app.post("/api/compare-prompts")
@traceable_run(name="Web Compare Prompts", run_type="chain", tags=["web", "comparison", "prompts"])
def compare_prompts(request: CompareRequest) -> dict[str, Any]:
    prompt_keys = ["helpful_assistant", "senior_python_engineer", "eli5_teacher", "pirate"]
    results = []
    for key in prompt_keys:
        spec = get_prompt(key)
        response = llm.generate(
            prompt_messages=[
                {"role": "system", "content": spec.system_prompt},
                {"role": "user", "content": request.question},
            ],
            feature="web-comparison",
            prompt_name=spec.name,
            metadata=base_metadata("web-comparison", spec.name),
            tags=base_tags("comparison", "prompts", key),
        )
        results.append({"prompt": spec.name, "description": spec.description, **response_payload(response)})

    return {
        "trace_name": "Web Compare Prompts",
        "question": request.question,
        "results": results,
    }


@app.post("/api/simulate-error")
@traceable_run(name="Web Simulate Error", run_type="tool", tags=["web", "error", "failure-demo"])
def simulate_error() -> dict[str, Any]:
    try:
        failing_tool()
    except ValueError as exc:
        return {
            "trace_name": "Web Simulate Error",
            "handled": True,
            "error": str(exc),
            "message": "The backend caught the error, while LangSmith records the failed child run.",
        }
    raise HTTPException(status_code=500, detail="Unexpected error state")


@traceable_run(name="Web Failing Tool", run_type="tool")
def failing_tool() -> None:
    raise ValueError("Artificial failure for LangSmith web dashboard demo")


def estimate_tokens(messages: list[dict[str, str]]) -> int:
    text = "\n".join(message["content"] for message in messages)
    return max(1, len(text.split()))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)
