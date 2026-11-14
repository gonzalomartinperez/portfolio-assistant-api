"""In-process API composition over fakes: no PostgreSQL, Neo4j or provider is contacted."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import Evidence
from app.application.conversations import Conversations
from app.application.runs import RunService
from app.bootstrap.config import Settings
from app.domain.conversations import Conversation, Run, Session
from app.domain.errors import RejectedError
from app.presentation.analytics import router as analytics_router
from app.presentation.feedback import router as feedback_router
from app.presentation.http import router
from app.presentation.middleware import BodyLimit, install
from app.presentation.operations import router as operations_router

ORIGIN = 'http://localhost:3000'
SOURCE = Evidence(
    'stub', 'Stub', 'https://example.test', 'page', 'a' * 40, 'README.md', 1, 2, 'Stub'
)


class FakeStore:
    """Ownership-checking conversation store; `fault` raises on every storage call."""

    def __init__(self):
        self.sessions, self.owners, self.fault = {}, {}, None

    def _check(self, owner=None, key=None):
        if self.fault:
            raise self.fault
        if owner is not None and self.owners.get(key) != owner:
            raise RejectedError('not_found', 404)

    def seed(self, owner):
        """Create one conversation, run and message owned by `owner`."""
        ids = (uuid4(), uuid4(), uuid4())
        for key in ids:
            self.owners[key] = owner
        return ids

    def session(self, secret_digest):
        self._check()
        return self.sessions.get(secret_digest)

    def create_session(self, session_id, secret_digest, csrf, expires):
        self._check()
        self.sessions[secret_digest] = Session(session_id, csrf, expires)

    def rate_limit(self, subject_hash, operation, limit):
        self._check()

    def delete_session(self, session_id):
        self._check()

    def create(self, session_id, title):
        self._check()
        now = datetime.now(UTC)
        conversation = Conversation(uuid4(), title, now, now)
        self.owners[conversation.id] = session_id
        return conversation

    def list_conversations(self, session_id, limit, cursor):
        self._check()
        return []

    def rename(self, session_id, conversation_id, title):
        self._check(session_id, conversation_id)
        now = datetime.now(UTC)
        return Conversation(conversation_id, title, now, now)

    def delete(self, session_id, conversation_id):
        self._check(session_id, conversation_id)

    def messages(self, session_id, conversation_id, limit, cursor):
        self._check(session_id, conversation_id)
        return []

    def prepare_run(self, session_id, conversation_id, content, payload_hash, key):
        self._check(session_id, conversation_id)
        return uuid4()

    def run(self, session_id, run_id, cancel=False):
        self._check(session_id, run_id)
        now = datetime.now(UTC)
        return Run(
            run_id, uuid4(), 'cancelled' if cancel else 'running', None, None, now, now
        )

    def feedback(self, session_id, message_id, rating):
        self._check(session_id, message_id)


class FakeRunStore:
    """Run persistence that always succeeds unless `fault` is set."""

    def __init__(self):
        self.fault, self.failed = None, None

    async def start(self, run_id):
        if self.fault:
            raise self.fault
        return True

    async def history(self, run_id, conversation_id):
        return ()

    async def running(self, run_id):
        return True

    async def complete(self, run_id, conversation_id, answer, citations):
        return uuid4()

    async def fail(self, run_id, code):
        self.failed = code
        return True

    async def interrupt(self, run_id):
        return None


class StubRetrieval:
    def __init__(self, fault=None):
        self.fault = fault

    async def search(self, question, locale):
        if self.fault:
            raise self.fault
        return (SOURCE,)


class StubProvider:
    """Streams `chunks` deltas `delay` seconds apart; `fault` raises before the first one."""

    def __init__(self, chunks=6, delay=0.0, fault=None):
        self.chunks, self.delay, self.fault = chunks, delay, fault

    async def stream(self, question, evidence, locale, history=(), context=None):
        if self.fault:
            raise self.fault
        for index in range(self.chunks):
            yield f'part {index} [1] '
            await asyncio.sleep(self.delay)


class FakeAccounting:
    def __init__(self, fault=None):
        self.fault = fault

    async def reserve(self, run_id):
        if self.fault:
            raise self.fault

    async def settle(self, run_id, usage):
        return None


def pin_env(monkeypatch):
    """Remove every environment variable that Settings would read, so tests are hermetic."""
    import os

    for name in Settings.model_fields:
        if name.upper() in os.environ:
            monkeypatch.delenv(name.upper())


def build_app(
    *,
    provider=None,
    retrieval=None,
    accounting=None,
    store=None,
    timeout=5,
    fixture=False,
    **config,
) -> FastAPI:
    """Compose the real routers, middleware, services and workflow over fakes."""
    settings = Settings(_env_file=None, **config)
    app = FastAPI()
    app.state.config = settings
    app.state.revision = 'unknown'
    app.state.store, app.state.run_store = store or FakeStore(), FakeRunStore()
    app.state.retrieval = retrieval or StubRetrieval()
    app.state.provider = provider or StubProvider()
    app.state.accounting = accounting
    app.state.conversations = Conversations(app.state.store, 7, settings.rate_hash_key)
    workflow = LangGraphWorkflow(app.state.retrieval, app.state.provider, accounting)
    app.state.runs = RunService(
        app.state.run_store, workflow, fixture=fixture, timeout_seconds=timeout
    )
    app.state.ready = lambda: '009'
    app.state.cleanup = lambda: None
    app.state.knowledge = type(
        'Knowledge',
        (),
        {'starter_prompts': lambda self, locale: ('v1', 'a' * 40, [])},
    )()
    app.state.product_analytics = type(
        'Analytics', (), {'record': lambda self, *a: 'accepted'}
    )()
    app.add_middleware(BodyLimit)
    # Same arguments as app.bootstrap.container.create_app.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
        allow_headers=[
            'Content-Type',
            'X-CSRF-Token',
            'X-Session-Bootstrap',
            'Idempotency-Key',
        ],
        expose_headers=['X-Run-ID', 'X-Request-ID'],
    )
    install(app, settings.origins)
    for item in (router, operations_router, analytics_router, feedback_router):
        app.include_router(item)
    return app
