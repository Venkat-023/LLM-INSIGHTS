"""
routes/chat.py – Chat API endpoints.

Flow for POST /api/chat:
  1.  Validate token & rate limits
  2.  Load or create conversation in SQLite
  3.  Build conversation history for OpenAI
  4.  Fetch system prompt from Langfuse
  5.  Create a Langfuse trace (returns trace_id)
  6.  Call OpenAI (auto-instrumented by langfuse.openai)
  7.  Save messages and usage stats to SQLite
  8.  Update Langfuse trace with output
  9.  Return response + trace_id to frontend
 10.  Frontend uses trace_id to submit feedback later
"""
import uuid
import logging
import traceback
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Conversation, Message, UsageStat
from backend.models.chat import (
    ChatRequest, ChatResponse, TokenUsage,
    ConversationSummary, ConversationMessage,
)
from backend.services.langfuse_service import langfuse_service
from backend.services.llm_service import dispatch_llm, build_messages
from backend.services.prompt_service import get_system_prompt
from backend.services import limits_service
from backend.utils.errors import ChatbotBaseError
from backend.config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("chatbot.routes.chat")
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Main chat endpoint.

    Creates a Langfuse trace for every request and uses the
    langfuse.openai wrapper to auto-instrument the OpenAI call.
    """
    trace_id = ""  # Will be set after trace creation

    try:
        # ── Step 1: Validate limits ─────────────────────────────────────────
        limits_service.check_prompt_length(request.message)
        limits_service.check_daily_limit(request.user_id, db)
        if request.conversation_id:
            limits_service.check_conversation_tokens(request.conversation_id, db)

        # ── Step 2: Load or create conversation ────────────────────────────
        conv_id = request.conversation_id or str(uuid.uuid4())
        conversation = db.query(Conversation).filter(Conversation.id == conv_id).first()

        if not conversation:
            # New conversation – build a title from the first message
            title = request.message[:60] + ("…" if len(request.message) > 60 else "")
            conversation = Conversation(
                id=conv_id,
                user_id=request.user_id,
                session_id=request.session_id,
                title=title,
                prompt_template=request.prompt_template,
            )
            db.add(conversation)
            db.commit()

        # ── Step 3: Build conversation history ─────────────────────────────
        past_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in past_messages]

        # ── Step 4: Fetch system prompt from Langfuse ───────────────────────
        system_prompt = get_system_prompt(request.prompt_template)

        # Determine model/provider for this request
        provider  = (request.provider or "openai").lower()
        api_key   = request.api_key or None
        model_name = request.model or settings.default_model

        # ── Step 5: Create Langfuse trace ───────────────────────────────────
        trace_id = langfuse_service.create_trace(
            name="chat-request",
            user_id=request.user_id,
            session_id=request.session_id,
            conversation_id=conv_id,
            input_text=request.message,
            metadata={
                "prompt_template": request.prompt_template,
                "model": model_name,
                "provider": provider,
                "conversation_turn": len(past_messages) // 2 + 1,
            },
            tags=["chat", request.prompt_template, provider, "development"],
        )

        # ── Step 6: Call LLM (any provider, logged to Langfuse) ─────────────
        messages = build_messages(system_prompt, history, request.message)
        result = dispatch_llm(
            messages=messages,
            model=model_name,
            max_tokens=settings.max_response_tokens,
            trace_id=trace_id,
            user_id=request.user_id,
            prompt_template=request.prompt_template,
            session_id=request.session_id,
            provider=provider,
            api_key=api_key,
        )

        # ── Step 7: Persist messages and usage stats ────────────────────────
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="user",
            content=request.message,
            trace_id=trace_id,
        )
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="assistant",
            content=result["text"],
            trace_id=trace_id,
        )
        db.add(user_msg)
        db.add(assistant_msg)

        # Update conversation token count
        conversation.total_tokens = (conversation.total_tokens or 0) + result["total_tokens"]
        conversation.updated_at = datetime.utcnow()

        # Record usage stat row
        usage_stat = UsageStat(
            user_id=request.user_id,
            conversation_id=conv_id,
            trace_id=trace_id,
            model=model_name,
            prompt_template=request.prompt_template,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["total_tokens"],
            estimated_cost=result["estimated_cost"],
            latency_ms=result["latency_ms"],
            date=date.today().isoformat(),
        )
        db.add(usage_stat)

        # Increment daily request counter
        limits_service.increment_daily_count(request.user_id, db)

        db.commit()

        # ── Step 8: Update Langfuse trace with output ───────────────────────
        langfuse_service.update_trace_output(trace_id, result["text"])

        # ── Step 9: Build and return response ──────────────────────────────
        return ChatResponse(
            reply=result["text"],
            conversation_id=conv_id,
            trace_id=trace_id,
            model=model_name,
            token_usage=TokenUsage(
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                estimated_cost=result["estimated_cost"],
            ),
            latency_ms=result["latency_ms"],
            timestamp=datetime.utcnow(),
        )

    except ChatbotBaseError as exc:
        # Log to Langfuse if we have a trace
        if trace_id:
            langfuse_service.log_error(
                trace_id=trace_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                stack_trace=traceback.format_exc(),
            )

        # Record error in usage stats
        if trace_id:
            try:
                err_stat = UsageStat(
                    user_id=request.user_id,
                    conversation_id=request.conversation_id or "unknown",
                    trace_id=trace_id,
                    model=request.model or settings.default_model,
                    prompt_template=request.prompt_template,
                    is_error=True,
                    error_type=type(exc).__name__,
                    date=date.today().isoformat(),
                )
                db.add(err_stat)
                db.commit()
            except Exception:
                pass

        raise HTTPException(
            status_code=exc.http_status,
            detail={"message": exc.user_message, "error_type": type(exc).__name__},
        )

    except Exception as exc:
        logger.exception("Unhandled error in /api/chat: %s", exc)
        if trace_id:
            langfuse_service.log_error(
                trace_id=trace_id,
                error_type="UnhandledError",
                error_message=str(exc),
                stack_trace=traceback.format_exc(),
            )
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


@router.get("/conversations/{user_id}", response_model=list[ConversationSummary])
def list_conversations(user_id: str, db: Session = Depends(get_db)):
    """List all conversations for a user, most recent first."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.is_active == True)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            prompt_template=c.prompt_template,
            total_tokens=c.total_tokens or 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.get("/conversation/{conversation_id}/messages", response_model=list[ConversationMessage])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    """Load full message history for a conversation."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    return [
        ConversationMessage(
            id=m.id,
            role=m.role,
            content=m.content,
            trace_id=m.trace_id,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/conversation/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Soft-delete a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        conv.is_active = False
        db.commit()
    return {"success": True}
