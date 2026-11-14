"""Schemathesis fuzzing of the committed OpenAPI contract against the in-process ASGI app.

Fakes replace every database-backed port, so no service is needed. The session fake rejects every
cookie, so session-protected routes are exercised through auth and validation negative paths only;
positive 2xx bodies for those routes are covered by the integration lane. The SSE 200 body of
`streamMessage` cannot be validated by the tool (the contract declares `string`); frame conformance
lives in test_sse_conformance.py. Examples default to 50 (PR); nightly runs set
SCHEMATHESIS_EXAMPLES=500.

Known gaps (tracked by name, narrow on purpose; every other check still runs):
- `recordProductEvent` enforces cross-field rules that OpenAPI cannot express, so schema-valid bodies
  can get 422; only positive-data acceptance is skipped there.
- Starlette answers an unsupported method with a partial `Allow` header on paths that declare several
  routes, so the `allow_header_conformance` check is skipped everywhere.
- Malformed JSON bodies are answered by the framework parser with `400 {"detail": ...}`, which the
  contract does not document; that single known response is accepted (see MALFORMED_BODY).
"""

import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import allow_header_conformance, positive_data_acceptance

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.domain.errors import RejectedError
from tests.support import ROOT

pytestmark = pytest.mark.contract

ORIGIN = 'http://localhost:3000'
MALFORMED_BODY = {'detail': 'There was an error parsing the body'}
EXAMPLES = int(os.environ.get('SCHEMATHESIS_EXAMPLES', '50'))


class RejectingConversations:
    """Every cookie is unknown: authentication fails closed before any store access."""

    def authenticate(self, raw):
        raise RejectedError('session_required', 401)

    def bootstrap(self, subject):
        raise RejectedError('rate_limited', 429)


class MemoryAnalytics:
    def record(self, value, country='unknown'):
        return 'accepted'


def build_app():
    app = create_app(
        Settings(_env_file=None, allowed_origins=ORIGIN, product_analytics_enabled=True)
    )

    @asynccontextmanager
    async def no_lifespan(_app):  # the real lifespan opens PostgreSQL and Neo4j
        yield

    app.router.lifespan_context = no_lifespan
    app.state.conversations = RejectingConversations()
    app.state.product_analytics = MemoryAnalytics()
    app.state.ready = lambda: 'fixture'
    app.state.cleanup = lambda: None
    app.state.knowledge = SimpleNamespace(
        starter_prompts=lambda locale: ('fixture-corpus', 'a' * 40, [])
    )
    return app


schema = schemathesis.openapi.from_dict(
    json.loads((ROOT / 'contracts/openapi.json').read_text())
)
schema.app = build_app()


@schema.parametrize()
@settings(
    max_examples=EXAMPLES,
    deadline=None,
    suppress_health_check=list(HealthCheck),
    derandomize=True,
)
def test_operations_conform_to_the_committed_contract(case):
    """No 5xx, schema-conformant responses, and negative inputs rejected."""
    excluded = [allow_header_conformance]
    if case.operation.path == '/api/v1/analytics/events':
        excluded.append(positive_data_acceptance)
    response = case.call(headers={'Origin': ORIGIN})
    if response.status_code == 400 and response.json() == MALFORMED_BODY:
        return
    case.validate_response(response, excluded_checks=excluded)
