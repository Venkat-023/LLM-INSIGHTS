# LangSmith Playground

LangSmith Playground is a beginner-friendly Python terminal app for exploring LangSmith traces, child runs, metadata, tags, token usage, latency, and failures.

The project is intentionally educational rather than production-ready. Each feature is designed to create a useful trace pattern inside the LangSmith dashboard.

## What You Get

- A Rich-powered terminal menu
- Chat, prompt comparison, summarization, and code explanation workflows
- A token and latency observability lab with short, medium, and long prompts
- Nested traced steps for easy inspection in LangSmith
- A deliberately failing path for error tracing
- Local logging and markdown export
- OpenAI-compatible model support through environment variables

## Project Layout

```text
langsmith-playground/
|-- app.py
|-- llm.py
|-- prompts.py
|-- tracing.py
|-- utils.py
|-- config.py
|-- requirements.txt
|-- .env.example
|-- README.md
`-- sessions/
```

## Installation

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your values.

## Environment Variables

```env
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=langsmith-playground

OPENAI_API_KEY=
OPENAI_BASE_URL=
MODEL_NAME=gpt-4o-mini
TEMPERATURE=0.2
TIMEOUT_SECONDS=60
```

Optional metadata defaults:

```env
USER_ID=demo-user
APP_ENV=development
EXPERIMENT_NAME=v1
LANGUAGE=python
```

## LangSmith API Key

1. Sign in to LangSmith.
2. Open Settings.
3. Go to API Keys.
4. Create a key and copy it into `LANGSMITH_API_KEY`.

## OpenAI-Compatible Providers

The app uses LangChain's `ChatOpenAI`, so it works with any provider that exposes an OpenAI-compatible API surface.

Examples:

- OpenRouter
- GitHub Models
- Together AI
- Groq
- Any compatible self-hosted endpoint

Set these variables to switch providers without changing code:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
MODEL_NAME=
```

## Run the App

```bash
python app.py
```

## Menu Overview

1. Chat - Generates a normal conversational trace with prompt, model call, metadata, and response.
2. Compare Prompts - Runs one question through four system prompts and creates one parent trace with four child runs.
3. Summarize Text - Shows preprocessing, LLM, and postprocessing as separate child runs.
4. Explain Code - Breaks code understanding into separate traced stages for explanation, complexity, and improvements.
5. Observability Lab - Runs short, medium, and long prompts so you can compare token usage and latency.
6. Simulate Error - Intentionally raises an exception so you can inspect a failed run.
7. View Session Info - Summarizes session metrics and can export chat history to Markdown.
8. Exit - Prints a local summary including token totals.

## Token Consumption Test

Run menu option `5. Observability Lab`.

It creates one parent trace with three comparable LLM runs:

- `short-input`
- `medium-input`
- `long-input`

Each run includes:

- tags: `observability`, `tokens`, `latency`
- metadata: scenario name, estimated input tokens, session ID, feature, experiment
- local terminal metrics: prompt tokens, completion tokens, total tokens, latency

In LangSmith, open the `Venkat` project and filter traces by the `observability` or `tokens` tag. Compare the token columns, latency, child runs, metadata, inputs, outputs, and error status.

## What To Inspect In LangSmith

Focus on these sections:

- Traces - See the parent/child structure for each feature.
- Runs - Inspect individual prompt and model steps.
- Metadata - Confirm session ID, feature name, user ID, experiment, and environment.
- Tags - Look for values like `chat`, `summary`, `comparison`, and `error`.
- Token Usage - Compare prompt and completion token counts between features.
- Analytics - Use the Observability Lab traces to compare token totals and latency across prompt sizes.
- Latency - Observe which operations are slowest.
- Errors - Open the intentionally failing trace from the error demo.
- Prompts - Compare the different system prompts used by the app.

## Screenshots

Add your own screenshots here after you run the app:

- `docs/screenshots/menu.png`
- `docs/screenshots/chat.png`
- `docs/screenshots/compare-prompts.png`
- `docs/screenshots/langsmith-trace.png`

## Local Files

Session artifacts are written under `sessions/<session_id>/`:

- `activity.log` - Local run log
- `conversation.md` - Optional exported conversation history

## Why This Project Is Useful

Every traced function is intentionally small so you can understand how LangSmith displays:

- parent traces
- child runs
- prompt construction
- LLM calls
- post-processing
- metadata and tags
- latency and token usage
- handled errors

That makes the app a safe sandbox for learning how to read and reason about LangSmith dashboards.
