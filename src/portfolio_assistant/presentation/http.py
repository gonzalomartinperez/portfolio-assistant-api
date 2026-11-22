import ipaddress
import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from portfolio_assistant.application.conversations import Conversations, digest
from portfolio_assistant.application.presentation_context import PresentationContext
from portfolio_assistant.domain.conversations import Conversation, Run, Session
from portfolio_assistant.presentation.events import events
from portfolio_assistant.presentation.models import (
    ConversationCreate,
    ConversationUpdate,
    ConversationView,
    ErrorBody,
    FeedbackCreate,
    HealthView,
    Locale,
    MessagePage,
    MessageView,
    Page,
    ReadinessView,
    RunView,
    SendMessage,
    SessionView,
    StarterPrompt,
    SuggestionsView,
)
from portfolio_assistant.presentation.progress import ProgressPhases
from portfolio_assistant.presentation.streaming import ClosingStreamingResponse, heartbeat

log = logging.getLogger("portfolio_assistant")
if TYPE_CHECKING:
    from portfolio_assistant.application.clock import Clock

router = APIRouter(
    responses={code: {"model": ErrorBody} for code in (400, 401, 403, 404, 408, 409, 422, 429, 503)}
)


def fail(code: str, status: int = 400) -> NoReturn:
    raise HTTPException(status_code=status, detail=code)


def conversations_service(request: Request) -> Conversations:
    service: Conversations = request.app.state.conversations
    return service


def current_session(request: Request) -> Session:
    return conversations_service(request).authenticate(
        request.cookies.get(request.app.state.config.cookie_name)
    )


def mutation_session(request: Request, session: Session = Depends(current_session)) -> Session:
    return conversations_service(request).authorize_mutation(
        session, request.headers.get("x-csrf-token", "")
    )


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    trusted = {
        item.strip()
        for item in request.app.state.config.trusted_proxy_ips.split(",")
        if item.strip()
    }
    if peer not in trusted:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "").split(",")
    if len(forwarded) > 5:
        return peer
    try:
        chain = [str(ipaddress.ip_address(item.strip())) for item in forwarded if item.strip()]
    except ValueError:
        return peer
    for address in reversed(chain):
        if address not in trusted:
            return address
    return peer


@router.get("/health/live", operation_id="healthLive", response_model=None)
def live() -> dict[str, str]:
    """Liveness probe kept from v1; it performs no dependency I/O. Prefer `/healthz`."""
    return {"status": "ok"}


@router.get("/health/ready", operation_id="healthReady", response_model=None)
def ready(request: Request) -> dict[str, str]:
    """Readiness probe kept from v1: database schema, active corpus and graph. Prefer `/readyz`."""
    try:
        request.app.state.ready()
        return {"status": "ok"}
    except Exception:  # noqa: BLE001 - Readiness aggregates dependencies and deliberately exposes only availability.
        fail("dependency_unavailable", 503)


def revision(request: Request) -> str:
    return getattr(request.app.state, "revision", "unknown")


@router.get("/healthz", response_model=HealthView, operation_id="healthz")
def healthz(request: Request) -> dict[str, str]:
    """Liveness: the process answers, with the deployed source revision."""
    return {"status": "ok", "version": revision(request)}


@router.get(
    "/readyz",
    response_model=ReadinessView,
    responses={503: {"model": ErrorBody}},
    operation_id="readyz",
)
def readyz(request: Request) -> dict[str, str]:
    """Readiness: dependencies answer; `schema_version` is the newest applied migration prefix."""
    try:
        schema = request.app.state.ready()
    except Exception:  # noqa: BLE001 - Readiness aggregates dependencies and deliberately exposes only availability.
        fail("dependency_unavailable", 503)
    return {"status": "ok", "version": revision(request), "schema_version": schema}


@router.post(
    "/api/v1/session",
    response_model=SessionView,
    responses={403: {"model": ErrorBody}},
    operation_id="createSession",
)
def create_session(
    request: Request,
    response: Response,
    x_session_bootstrap: Annotated[str | None, Header()] = None,
) -> SessionView:
    """Bootstrap an anonymous session. Requires `Content-Type: application/json` (send `{}`), a trusted `Origin` and `X-Session-Bootstrap: 1`; sets the HttpOnly session cookie and returns the CSRF token for later mutations."""
    if (
        x_session_bootstrap != "1"
        or request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        fail("bootstrap_denied", 403)
    raw, session = request.app.state.conversations.bootstrap(client_ip(request))
    config = request.app.state.config
    response.set_cookie(
        config.cookie_name,
        raw,
        httponly=True,
        secure=config.secure_cookies,
        samesite="lax",
        path="/",
        max_age=config.retention_days * 86400,
    )
    return SessionView(
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        retention_days=config.retention_days,
    )


@router.get("/api/v1/session", response_model=SessionView, operation_id="getSession")
def get_session(
    request: Request, session: Annotated[Session, Depends(current_session)]
) -> SessionView:
    """Restore the CSRF token and expiry of the current cookie session after a reload."""
    return SessionView(
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        retention_days=request.app.state.config.retention_days,
    )


@router.delete("/api/v1/session", status_code=204, operation_id="deleteSession")
def delete_session(
    request: Request, response: Response, session: Annotated[Session, Depends(mutation_session)]
) -> None:
    """Delete the session with its conversations, messages and runs, and clear the cookie."""
    request.app.state.conversations.delete_session(session)
    request.app.state.cleanup()
    response.delete_cookie(request.app.state.config.cookie_name, path="/")


@router.post(
    "/api/v1/conversations",
    response_model=ConversationView,
    operation_id="createConversation",
)
def create_conversation(
    request: Request,
    body: ConversationCreate,
    session: Annotated[Session, Depends(mutation_session)],
) -> Conversation:
    """Create an owned conversation (at most 100 per session)."""
    return conversations_service(request).create(session, body.title)


@router.get("/api/v1/conversations", response_model=Page, operation_id="listConversations")
def list_conversations(
    request: Request,
    limit: int = 30,
    cursor: datetime | None = None,
    session: Session = Depends(current_session),
) -> Page:
    """List owned conversations, most recently updated first. Pass `next_cursor` back, URL-encoded, as `cursor`."""
    rows = request.app.state.conversations.list_conversations(session, limit, cursor)
    return Page(
        items=[ConversationView.model_validate(asdict(row)) for row in rows[:limit]],
        next_cursor=rows[limit - 1].updated_at.isoformat() if len(rows) > limit else None,
    )


@router.patch(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationView,
    operation_id="renameConversation",
)
def rename_conversation(
    request: Request,
    conversation_id: UUID,
    body: ConversationUpdate,
    session: Annotated[Session, Depends(mutation_session)],
) -> Conversation:
    """Rename an owned conversation. Foreign conversations answer 404."""
    return conversations_service(request).rename(session, conversation_id, body.title)


@router.delete(
    "/api/v1/conversations/{conversation_id}",
    status_code=204,
    operation_id="deleteConversation",
)
def delete_conversation(
    request: Request, conversation_id: UUID, session: Annotated[Session, Depends(mutation_session)]
) -> None:
    """Delete an owned conversation with its messages and runs."""
    request.app.state.conversations.delete(session, conversation_id)
    request.app.state.cleanup()


@router.get(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=MessagePage,
    operation_id="listMessages",
)
def list_messages(
    request: Request,
    conversation_id: UUID,
    limit: int = 50,
    cursor: datetime | None = None,
    session: Session = Depends(current_session),
) -> MessagePage:
    """List messages newest first, with citations on assistant messages. Pass `next_cursor` back, URL-encoded, as `cursor`."""
    rows = request.app.state.conversations.messages(session, conversation_id, limit, cursor)
    return MessagePage(
        items=[MessageView.model_validate(asdict(row)) for row in rows[:limit]],
        next_cursor=rows[limit - 1].created_at.isoformat() if len(rows) > limit else None,
    )


def sse(
    event_type: str,
    run_id: UUID,
    conversation_id: UUID,
    sequence: int,
    payload: dict[str, object],
    *,
    clock: Clock,
) -> str:
    body = events.validate_python(
        {
            "type": event_type,
            "run_id": run_id,
            "conversation_id": conversation_id,
            "sequence": sequence,
            "timestamp": clock.now(),
            "payload": payload,
        }
    )
    return f"event: {event_type}\ndata: {body.model_dump_json()}\n\n"


async def execute_run(
    request: Request,
    run_id: UUID,
    conversation_id: UUID,
    question: str,
    locale: str,
    context: PresentationContext | None = None,
    *,
    progress: bool = False,
) -> AsyncGenerator[str]:
    sequence = 0
    phases = ProgressPhases() if progress else None
    started = time.perf_counter()
    terminal = "interrupted"
    first_delta_ms = None
    try:
        async with aclosing(
            request.app.state.runs.execute(run_id, conversation_id, question, locale, context)
        ) as stream:
            async for event in stream:
                if event.name == "message.delta" and first_delta_ms is None:
                    first_delta_ms = round((time.perf_counter() - started) * 1000, 1)
                if event.name in ("run.completed", "run.failed", "run.cancelled"):
                    terminal = event.name
                frames = (
                    phases.expand(event.name, event.payload)
                    if phases
                    else iter(((event.name, event.payload),))
                )
                for name, payload in frames:
                    yield sse(
                        name,
                        run_id,
                        conversation_id,
                        sequence,
                        payload,
                        clock=request.app.state.clock,
                    )
                    sequence += 1
    finally:
        log.info(
            json.dumps(
                {
                    "operation": "answer_stream",
                    "request_id": request.state.request_id,
                    "terminal": terminal,
                    "events": sequence,
                    "first_delta_ms": first_delta_ms,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )


@router.post(
    "/api/v1/conversations/{conversation_id}/messages/stream",
    operation_id="streamMessage",
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
def stream_message(
    request: Request,
    conversation_id: UUID,
    body: SendMessage,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=128)],
    session: Annotated[Session, Depends(mutation_session)],
    x_assistant_progress: Annotated[
        str | None,
        Header(
            description="`1` opts in to `run.progress` events (contract v1.1, ADR 020); "
            "any other value is ignored.",
        ),
    ] = None,
) -> ClosingStreamingResponse:
    """Ask a question and stream the answer as Server-Sent Events (`contracts/sse.schema.json`). Requires an `Idempotency-Key`; a repeated key returns 409 and is never replayed. Keep `X-Run-ID` to read or cancel the run. Send `X-Assistant-Progress: 1` for opt-in `run.progress` events."""
    run_id = request.app.state.conversations.prepare_run(
        session,
        conversation_id,
        body.content,
        digest(body.model_dump_json(exclude_none=True)),
        idempotency_key,
    )
    return ClosingStreamingResponse(
        heartbeat(
            execute_run(
                request,
                run_id,
                conversation_id,
                body.content,
                body.locale,
                PresentationContext(
                    theme=body.context.theme,
                    opened_path=body.context.opened_path,
                    current_path=body.context.current_path,
                    presentation=body.context.presentation,
                )
                if body.context
                else None,
                progress=(x_assistant_progress or "").strip() == "1",
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store, no-transform",
            "X-Accel-Buffering": "no",
            "X-Run-ID": str(run_id),
        },
    )


@router.get("/api/v1/runs/{run_id}", response_model=RunView, operation_id="getRun")
def get_run(
    request: Request, run_id: UUID, session: Annotated[Session, Depends(current_session)]
) -> Run:
    """Read the state of an owned run, for example after a disconnect."""
    return conversations_service(request).run(session, run_id)


@router.post("/api/v1/runs/{run_id}/cancel", response_model=RunView, operation_id="cancelRun")
def cancel_run(
    request: Request, run_id: UUID, session: Annotated[Session, Depends(mutation_session)]
) -> Run:
    """Cancel a live owned run; idempotent, and a finished run is returned unchanged."""
    return conversations_service(request).run(session, run_id, cancel=True)


@router.post(
    "/api/v1/messages/{message_id}/feedback",
    status_code=204,
    operation_id="recordFeedback",
)
def record_feedback(
    request: Request,
    message_id: UUID,
    body: FeedbackCreate,
    session: Annotated[Session, Depends(mutation_session)],
) -> None:
    """Record up or down feedback on an owned assistant message."""
    request.app.state.conversations.feedback(session, message_id, body.rating)


@router.get(
    "/api/v1/knowledge/suggestions",
    response_model=SuggestionsView,
    operation_id="getKnowledgeSuggestions",
)
def get_knowledge_suggestions(request: Request, locale: Locale = "en") -> SuggestionsView:
    """Starter questions from the active public corpus for the requested locale (up to five)."""
    version, commit, prompts = request.app.state.knowledge.starter_prompts(locale)
    return SuggestionsView(
        corpus_version=version,
        source_commit=commit,
        items=[StarterPrompt(**asdict(prompt)) for prompt in prompts],
    )
