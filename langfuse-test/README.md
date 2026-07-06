# 🔭 Langfuse AI Chatbot

A full-stack AI chatbot built as a **hands-on learning project** for [Langfuse](https://langfuse.com) LLM observability. Every feature demonstrates a specific Langfuse capability.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (SQLite) |
| Frontend | React 18, Vite, Recharts |
| LLM | OpenAI (gpt-4.1-mini, gpt-4.1, gpt-4o-mini) |
| Observability | Langfuse (traces, prompts, feedback, analytics) |

---

## Project Structure

```
langfuse-test/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings
│   ├── database.py              # SQLite ORM models
│   ├── models/                  # Pydantic request/response models
│   ├── routes/                  # API endpoints
│   ├── services/
│   │   ├── langfuse_service.py  # Langfuse client wrapper ← START HERE
│   │   ├── openai_service.py    # langfuse.openai auto-instrumentation
│   │   ├── prompt_service.py    # Langfuse prompt management
│   │   └── limits_service.py   # Token & rate limits
│   └── utils/
├── frontend/
│   └── src/
│       ├── pages/               # Chat, Dashboard, Experiment, Analytics
│       └── components/          # MessageBubble, FeedbackPanel, etc.
└── requirements.txt
```

---

## Installation

### 1. Clone & set up Python environment

```bash
cd "langfuse test"

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your keys
```

Required variables:

| Variable | Description |
|---|---|
| `LANGFUSE_SECRET_KEY` | From Langfuse → Settings → API Keys |
| `LANGFUSE_PUBLIC_KEY` | From Langfuse → Settings → API Keys |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` (or self-hosted URL) |
| `OPENAI_API_KEY` | From https://platform.openai.com/api-keys |

Optional limits:

| Variable | Default | Description |
|---|---|---|
| `MAX_PROMPT_LENGTH` | 4000 | Max characters per user message |
| `MAX_RESPONSE_TOKENS` | 1024 | Max tokens in response |
| `DAILY_REQUEST_LIMIT` | 100 | Max requests per user per day |
| `MAX_CONVERSATION_TOKENS` | 8000 | Max total tokens per conversation |

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running Locally

Start both servers in separate terminals:

**Terminal 1 – Backend:**
```bash
# From the project root (langfuse test/)
venv\Scripts\activate
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 – Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**

API docs: **http://localhost:8000/api/docs**

---

## Langfuse Setup

1. Sign up at https://cloud.langfuse.com (free tier available)
2. Create a new project
3. Go to **Settings → API Keys** and copy:
   - `Secret Key` → `LANGFUSE_SECRET_KEY` in `.env`
   - `Public Key` → `LANGFUSE_PUBLIC_KEY` in `.env`
4. Start the backend – prompt templates are auto-registered on startup
5. Send a chat message – a trace appears in your Langfuse dashboard within seconds

---

## How Langfuse Integration Works

### 🔍 Traces

Every chat request creates a **Langfuse Trace** (see `backend/services/langfuse_service.py`):

```python
trace_id = langfuse_service.create_trace(
    name="chat-request",
    user_id=user_id,
    session_id=session_id,
    conversation_id=conv_id,
    tags=["chat", "development"],
)
```

Each trace captures:
- User ID, Session ID, Conversation ID
- Environment (development/production)
- Tags for filtering
- Input (user message) and Output (AI response)

### 🤖 Auto-instrumentation

The `backend/services/openai_service.py` uses `langfuse.openai` instead of `openai`:

```python
# This one import enables automatic LLM observability
from langfuse.openai import OpenAI

client = OpenAI(api_key=...)

# This call is AUTOMATICALLY recorded in Langfuse:
# - model, messages, response text
# - prompt_tokens, completion_tokens, total_tokens
# - latency, estimated cost
response = client.chat.completions.create(model="gpt-4.1-mini", ...)
```

### 👍 Feedback

After each response, users can rate with 👍/👎/⭐/💬. The `trace_id` from the response links the feedback to the exact LLM call:

```python
langfuse.score(
    trace_id=trace_id,
    name="user-feedback",
    value=1.0,  # helpful
    data_type="BOOLEAN",
)
```

### 📝 Prompt Management

Three templates are registered in Langfuse at startup:
- `friendly-assistant` – warm and conversational
- `technical-assistant` – precise with code examples
- `short-answer-assistant` – max 2-3 sentences

```python
langfuse.create_prompt(name="friendly-assistant", prompt="...", labels=["production"])
prompt = langfuse.get_prompt("friendly-assistant")  # fetched with 5-min cache
```

You can edit prompts in the Langfuse UI and the app picks up the new version automatically (within 5 minutes).

### ⚠️ Error Tracking

All OpenAI errors are caught, classified, and logged to Langfuse:

```python
trace.event(
    name="error.RateLimitError",
    level="ERROR",
    metadata={"stack_trace": "..."},
)
```

Error types tracked:
- `AuthenticationError` → Invalid API key
- `RateLimitError` → OpenAI quota exceeded
- `APITimeoutError` → Request timeout
- `APIError` → Generic OpenAI error

### 🪙 Token Limits

Application-level limits are enforced BEFORE calling OpenAI:

| Limit | Variable | Description |
|---|---|---|
| Prompt length | `MAX_PROMPT_LENGTH` | Chars in user message |
| Daily requests | `DAILY_REQUEST_LIMIT` | Requests per user per day |
| Conversation tokens | `MAX_CONVERSATION_TOKENS` | Total tokens in one conversation |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a chat message |
| `POST` | `/api/feedback` | Submit 👍/👎/⭐ feedback |
| `GET` | `/api/prompts` | List prompt templates |
| `GET` | `/api/dashboard/stats` | Token usage stats |
| `GET` | `/api/dashboard/per-user` | Per-user breakdown |
| `GET` | `/api/dashboard/daily-usage` | Daily usage history |
| `GET` | `/api/dashboard/limits/{user_id}` | Remaining requests today |
| `POST` | `/api/experiment` | Compare multiple models |
| `GET` | `/api/analytics` | Model/template analytics |
| `GET` | `/api/conversations/{user_id}` | List conversations |
| `GET` | `/api/conversation/{id}/messages` | Load conversation |

Full Swagger docs: http://localhost:8000/api/docs

---

## Docker (Optional)

```bash
docker compose up --build
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

---

## What You'll Learn

After running this project you'll understand:

1. **Langfuse Traces** – how to create traces with user/session context
2. **Auto-instrumentation** – the `langfuse.openai` drop-in wrapper
3. **Prompt Management** – versioned prompts with environment labels
4. **Feedback Scores** – attaching user ratings to specific traces
5. **Error Tracking** – logging errors co-located with LLM traces
6. **Analytics** – querying your own data to compare models and prompts

---

*Built as a learning reference for Langfuse observability.*
