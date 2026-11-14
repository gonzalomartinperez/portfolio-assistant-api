"""Every OpenAPI operation declares its access class here; a new route fails until it does.

Limit: ownership and CSRF run through the real Conversations policy, but the store is the
in-memory FakeStore. Ownership results come from FakeStore._check, and FakeStore.session
ignores expiry (the real rule is SQL `expires_at>now()`). The same ownership and expiry cases
run against PostgresConversations in tests/integration/test_conversation_store_contract.py.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.presentation import analytics, feedback, http, operations
from tests.support import ROOT
from tests.support_app import ORIGIN, build_app, pin_env

EVIL = {'Origin': 'https://evil.example'}
# kind: public | bootstrap | event | read | object_read | write | object_write
KINDS = {
    'healthLive': 'public',
    'healthReady': 'public',
    'healthz': 'public',
    'readyz': 'public',
    'getKnowledgeSuggestions': 'public',
    'createSession': 'bootstrap',
    'recordProductEvent': 'event',
    'getSession': 'read',
    'listConversations': 'read',
    'listMessages': 'object_read',
    'getRun': 'object_read',
    'deleteSession': 'write',
    'createConversation': 'write',
    'renameConversation': 'object_write',
    'deleteConversation': 'object_write',
    'streamMessage': 'object_write',
    'cancelRun': 'object_write',
    'recordFeedback': 'object_write',
}
BODIES = {
    'createSession': {},
    'createConversation': {},
    'renameConversation': {'title': 'x'},
    'streamMessage': {'content': 'hi'},
    'recordFeedback': {'rating': 'up'},
    'recordProductEvent': {
        'schema_version': 1,
        'project': 'portfolio',
        'source': 'site',
        'event_id': '12345678-1234-4123-8123-123456789abc',
        'event_name': 'page_view',
        'section': 'home',
        'locale': 'en',
    },
}
OPERATIONS = [
    (op['operationId'], method.upper(), path)
    for path, item in json.loads((ROOT / 'contracts/openapi.json').read_text())[
        'paths'
    ].items()
    for method, op in item.items()
]


def login(app):
    client = TestClient(app)
    response = client.post(
        '/api/v1/session',
        json={},
        headers={'Origin': ORIGIN, 'X-Session-Bootstrap': '1'},
    )
    return client, response.json()['csrf_token']


@pytest.fixture(autouse=True)
def hermetic(monkeypatch):
    pin_env(monkeypatch)


@pytest.fixture(params=[False, True], ids=['live', 'fixture'])
def world(request):
    app = build_app(product_analytics_enabled=True, fixture=request.param)
    owner, owner_csrf = login(app)
    other, other_csrf = login(app)
    ids = app.state.store.seed(_owner(app, owner))
    return app, owner, owner_csrf, other, other_csrf, ids


def _owner(app, client):
    from app.application.conversations import digest

    raw = client.cookies.get(app.state.config.cookie_name)
    return app.state.store.sessions[digest(raw)].id


def call(client, op, ids, headers=None):
    operation, method, path = op
    conversation, run, message = ids
    url = path.format(conversation_id=conversation, run_id=run, message_id=message)
    extra = {'Idempotency-Key': 'k' * 8} if operation == 'streamMessage' else {}
    return client.request(
        method, url, json=BODIES.get(operation), headers={**extra, **(headers or {})}
    )


def test_every_operation_has_a_matrix_entry_and_no_entry_is_stale():
    assert {op[0] for op in OPERATIONS} == set(KINDS)


def test_every_composed_route_is_documented_or_internal():
    documented = {(m.upper(), p) for _, m, p in OPERATIONS}
    composed = {
        (method, route.path)
        for module in (http, analytics, feedback, operations)
        for route in module.router.routes
        for method in route.methods
        if method != 'HEAD'
    }
    assert composed
    for method, path in composed:
        assert (method, path) in documented or path.startswith('/internal/')


@pytest.mark.parametrize('op', OPERATIONS, ids=lambda op: op[0])
def test_security_matrix(op, world):
    app, owner, csrf, other, other_csrf, ids = world
    kind, anonymous = KINDS[op[0]], TestClient(app)
    good = {'Origin': ORIGIN}
    if kind == 'public':
        assert call(anonymous, op, ids).status_code == 200
    elif kind == 'bootstrap':
        assert (
            call(anonymous, op, ids, {**good, 'X-Session-Bootstrap': '1'}).status_code
            == 200
        )
        denied = call(anonymous, op, ids, good)
        assert (denied.status_code, denied.json()['code']) == (403, 'bootstrap_denied')
        assert call(anonymous, op, ids, EVIL).json()['code'] == 'origin_denied'
    elif kind == 'event':
        assert call(anonymous, op, ids, good).status_code == 204
        assert call(anonymous, op, ids, EVIL).json()['code'] == 'origin_denied'
        # Anonymous collection must never attach to a session.
        assert (
            call(owner, op, ids, good).json()['code']
            == 'analytics_credentials_forbidden'
        )
    elif kind in ('read', 'object_read'):
        missing = call(anonymous, op, ids)
        assert (missing.status_code, missing.json()['code']) == (
            401,
            'session_required',
        )
        assert (
            call(
                anonymous, op, ids, {'Cookie': 'assistant_session_dev=forged'}
            ).status_code
            == 401
        )
        assert call(owner, op, ids).status_code == 200
        if kind == 'object_read':
            foreign = call(other, op, ids)
            assert (foreign.status_code, foreign.json()['code']) == (404, 'not_found')
    else:
        assert (
            call(owner, op, ids, {**EVIL, 'X-CSRF-Token': csrf}).json()['code']
            == 'origin_denied'
        )
        assert call(owner, op, ids).json()['code'] == 'origin_denied'
        assert (
            call(anonymous, op, ids, {**good, 'X-CSRF-Token': csrf}).status_code == 401
        )
        for token in ({}, {'X-CSRF-Token': other_csrf}):
            denied = call(owner, op, ids, {**good, **token})
            assert (denied.status_code, denied.json()['code']) == (403, 'csrf_denied')
        if kind == 'object_write':
            foreign = call(other, op, ids, {**good, 'X-CSRF-Token': other_csrf})
            assert (foreign.status_code, foreign.json()['code']) == (404, 'not_found')
        assert call(owner, op, ids, {**good, 'X-CSRF-Token': csrf}).status_code < 300


def test_ops_routes_need_the_bearer_token_and_fail_closed_when_unconfigured(
    hermetic,
):
    token = 'a' * 40
    configured = build_app(ops_read_token=token, ops_api_commit='b' * 40)
    paths = [
        route.path
        for module in (operations, analytics, feedback)
        for route in module.router.routes
        if route.path.startswith('/internal/')
    ]
    assert paths
    for path in paths:
        client = TestClient(configured)
        assert client.get(path).json()['code'] == 'operations_unauthorized'
        bad = client.get(path, headers={'Authorization': 'Bearer ' + 'c' * 40})
        assert bad.status_code == 401
        assert (
            TestClient(build_app()).get(path).json()['code']
            == 'operations_unconfigured'
        )
