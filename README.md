# LLM Insights

This repository contains two beginner-friendly LLM observability projects:

- `langsmith-playground` - FastAPI + simple frontend for testing LangSmith traces, token usage, latency, metadata, tags, prompt comparison, and error traces.
- `langfuse-test` - FastAPI + React app for testing Langfuse traces, prompt management, feedback, analytics, token usage, and error tracking.

## Quick Start

Clone the repo, then run one of these commands from the repository root.

### LangSmith

```powershell
.\start-langsmith.ps1
```

Open:

```text
http://127.0.0.1:8010
```

Dashboard:

```text
https://smith.langchain.com
```

### Langfuse

```powershell
.\start-langfuse.ps1
```

Open:

```text
http://127.0.0.1:5173
```

Dashboard:

```text
https://cloud.langfuse.com
```

### Start Both

```powershell
.\start-all.ps1
```

## Environment Setup

Each project has its own `.env.example`.

Before real LLM calls work, create and fill these files:

- `langsmith-playground\.env`
- `langfuse-test\.env`

The startup scripts copy `.env.example` to `.env` automatically if the file does not exist, then remind you to add real API keys.

## What To Check

In the LangSmith project, use the frontend buttons:

- `Run Token Lab`
- `Run Chat Trace`
- `Compare Prompts`
- `Simulate Error Trace`

Then filter LangSmith traces by tags like `observability`, `tokens`, `latency`, `comparison`, and `error`.

In the Langfuse project, use the chat, dashboard, experiment, and analytics pages. Then inspect traces, generations, scores, prompts, costs, latency, and token usage along with prompt comparision and prompt evaluation in Langfuse.
