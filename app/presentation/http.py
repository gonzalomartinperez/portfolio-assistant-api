import ipaddress
import json
import logging
import time
from contextlib import aclosing
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from app.application.conversations import digest
from app.application.presentation_context import PresentationContext
from app.presentation.events import events
from app.presentation.models import (
    ConversationCreate,
    ConversationUpdate,
    ConversationView,
    ErrorBody,
    FeedbackCreate,
    Locale,
    MessagePage,
    Page,
    RunView,
    SendMessage,
    SessionView,
    StarterPrompt,
    SuggestionsView,
)
from app.presentation.streaming import ClosingStreamingResponse, heartbeat

log = logging.getLogger('portfolio_assistant')
router = APIRouter(
    responses={
        code: {'model': ErrorBody} for code in (400, 401, 403, 404, 409, 422, 429, 503)
    }
)


def utcnow():
    return datetime.now(UTC)


def fail(code: str, status: int = 400):
    raise HTTPException(status_code=status, detail=code)


def current_session(request: Request):
    return request.app.state.conversations.authenticate(
        request.cookies.get(request.app.state.config.cookie_name)
    )


def mutation_session(request: Request, session=Depends(current_session)):
    return request.app.state.conversations.authorize_mutation(
        session, request.headers.get('x-csrf-token', '')
    )


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else 'unknown'
    trusted = {
        item.strip()
        for item in request.app.state.config.trusted_proxy_ips.split(',')
        if item.strip()
    }
    if peer not in trusted:
        return peer
    forwarded = request.headers.get('x-forwarded-for', '').split(',')
    if len(forwarded) > 5:
        return peer
    try:
        chain = [
            str(ipaddress.ip_address(item.strip()))
            for item in forwarded
            if item.strip()
        ]
    except ValueError:
        return peer
    for address in reversed(chain):
        if address not in trusted:
            return address
    return peer


@router.get('/health/live', operation_id='healthLive')
def live():
    return {'status': 'ok'}


@router.get('/health/ready', operation_id='healthReady')
def ready(request: Request):
    try:
        request.app.state.ready()
        return {'status': 'ok'}
    except Exception:  # noqa: BLE001 - Readiness aggregates dependencies and deliberately exposes only availability.
        fail('dependency_unavailable', 503)


@router.post(
    '/api/v1/session',
    response_model=SessionView,
    responses={403: {'model': ErrorBody}},
    operation_id='createSession',
)
def create_session(
    request: Request,
    response: Response,
    x_session_bootstrap: str | None = Header(default=None),
):
    if (
        x_session_bootstrap != '1'
        or request.headers.get('content-type', '').split(';')[0] != 'application/json'
    ):
        fail('bootstrap_denied', 403)
    raw, session = request.app.state.conversations.bootstrap(client_ip(request))
    config = request.app.state.config
    response.set_cookie(
        config.cookie_name,
        raw,
        httponly=True,
        secure=config.secure_cookies,
        samesite='lax',
        path='/',
        max_age=config.retention_days * 86400,
    )
    return SessionView(
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        retention_days=config.retention_days,
    )


@router.get('/api/v1/session', response_model=SessionView, operation_id='getSession')
def get_session(request: Request, session=Depends(current_session)):
    return SessionView(
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        retention_days=request.app.state.config.retention_days,
    )


@router.delete('/api/v1/session', status_code=204, operation_id='deleteSession')
def delete_session(
    request: Request, response: Response, session=Depends(mutation_session)
):
    request.app.state.conversations.delete_session(session)
    request.app.state.cleanup()
    response.delete_cookie(request.app.state.config.cookie_name, path='/')


@router.post(
    '/api/v1/conversations',
    response_model=ConversationView,
    operation_id='createConversation',
)
def create_conversation(
    request: Request, body: ConversationCreate, session=Depends(mutation_session)
):
    return request.app.state.conversations.create(session, body.title)


@router.get(
    '/api/v1/conversations', response_model=Page, operation_id='listConversations'
)
def list_conversations(
    request: Request,
    limit: int = 30,
    cursor: datetime | None = None,
    session=Depends(current_session),
):
    rows = request.app.state.conversations.list_conversations(session, limit, cursor)
    return Page(
        items=[asdict(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].updated_at.isoformat()
        if len(rows) > limit
        else None,
    )


@router.patch(
    '/api/v1/conversations/{conversation_id}',
    response_model=ConversationView,
    operation_id='renameConversation',
)
def rename_conversation(
    request: Request,
    conversation_id: UUID,
    body: ConversationUpdate,
    session=Depends(mutation_session),
):
    return request.app.state.conversations.rename(session, conversation_id, body.title)


@router.delete(
    '/api/v1/conversations/{conversation_id}',
    status_code=204,
    operation_id='deleteConversation',
)
def delete_conversation(
    request: Request, conversation_id: UUID, session=Depends(mutation_session)
):
    request.app.state.conversations.delete(session, conversation_id)
    request.app.state.cleanup()


@router.get(
    '/api/v1/conversations/{conversation_id}/messages',
    response_model=MessagePage,
    operation_id='listMessages',
)
def list_messages(
    request: Request,
    conversation_id: UUID,
    limit: int = 50,
    cursor: datetime | None = None,
    session=Depends(current_session),
):
    rows = request.app.state.conversations.messages(
        session, conversation_id, limit, cursor
    )
    return MessagePage(
        items=[asdict(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].created_at.isoformat()
        if len(rows) > limit
        else None,
    )


def sse(
    event_type: str, run_id: UUID, conversation_id: UUID, sequence: int, payload: dict
):
    body = events.validate_python(
        {
            'type': event_type,
            'run_id': run_id,
            'conversation_id': conversation_id,
            'sequence': sequence,
            'timestamp': utcnow(),
            'payload': payload,
        }
    )
    return f'event: {event_type}\ndata: {body.model_dump_json()}\n\n'


async def execute_run(
    request: Request,
    run_id: UUID,
    conversation_id: UUID,
    question: str,
    locale: str,
    context: PresentationContext | None = None,
):
    sequence = 0
    started = time.perf_counter()
    terminal = 'interrupted'
    first_delta_ms = None
    try:
        async with aclosing(
            request.app.state.runs.execute(
                run_id, conversation_id, question, locale, context
            )
        ) as stream:
            async for event in stream:
                if event.name == 'message.delta' and first_delta_ms is None:
                    first_delta_ms = round((time.perf_counter() - started) * 1000, 1)
                if event.name in ('run.completed', 'run.failed', 'run.cancelled'):
                    terminal = event.name
                yield sse(event.name, run_id, conversation_id, sequence, event.payload)
                sequence += 1
    finally:
        log.info(
            json.dumps(
                {
                    'operation': 'answer_stream',
                    'request_id': request.state.request_id,
                    'terminal': terminal,
                    'events': sequence,
                    'first_delta_ms': first_delta_ms,
                    'duration_ms': round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )


@router.post(
    '/api/v1/conversations/{conversation_id}/messages/stream',
    operation_id='streamMessage',
    responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}}}},
)
def stream_message(
    request: Request,
    conversation_id: UUID,
    body: SendMessage,
    idempotency_key: str = Header(min_length=8, max_length=128),
    session=Depends(mutation_session),
):
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
            )
        ),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-store, no-transform',
            'X-Accel-Buffering': 'no',
            'X-Run-ID': str(run_id),
        },
    )


@router.get('/api/v1/runs/{run_id}', response_model=RunView, operation_id='getRun')
def get_run(request: Request, run_id: UUID, session=Depends(current_session)):
    return request.app.state.conversations.run(session, run_id)


@router.post(
    '/api/v1/runs/{run_id}/cancel', response_model=RunView, operation_id='cancelRun'
)
def cancel_run(request: Request, run_id: UUID, session=Depends(mutation_session)):
    return request.app.state.conversations.run(session, run_id, cancel=True)


@router.post(
    '/api/v1/messages/{message_id}/feedback',
    status_code=204,
    operation_id='recordFeedback',
)
def record_feedback(
    request: Request,
    message_id: UUID,
    body: FeedbackCreate,
    session=Depends(mutation_session),
):
    request.app.state.conversations.feedback(session, message_id, body.rating)


@router.get(
    '/api/v1/knowledge/suggestions',
    response_model=SuggestionsView,
    operation_id='getKnowledgeSuggestions',
)
def get_knowledge_suggestions(request: Request, locale: Locale = 'en'):
    version, commit, prompts = request.app.state.knowledge.starter_prompts(locale)
    return SuggestionsView(
        corpus_version=version,
        source_commit=commit,
        items=[StarterPrompt(**asdict(prompt)) for prompt in prompts],
    )
