"""Synthetic public-input and private-read tests; no providers or persistence."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.domain.analytics import ProductEvent
from app.presentation.analytics import ProductEventBody

ORIGIN = 'http://localhost:3000'
TOKEN = 'synthetic-analytics-ops-token-00000'


def event(**changes):
    return {
        'schema_version': 1,
        'project': 'portfolio',
        'source': 'site',
        'event_id': str(uuid4()),
        'event_name': 'page_view',
        'section': 'home',
        'locale': 'en',
        **changes,
    }


class MemoryStore:
    def __init__(self):
        self.events = []
        self.limited = False

    def record(self, value):
        if self.limited:
            return 'limited'
        self.events.append(value)
        return 'accepted'

    def snapshot(self):
        return {
            'schema_version': 1,
            'project': 'portfolio',
            'window_days': 7,
            'country': 'unknown',
            'counts': [],
        }


def client(enabled=True):
    application = create_app(
        Settings(
            _env_file=None,
            product_analytics_enabled=enabled,
            ops_read_token=TOKEN,
            ops_api_commit='a' * 40,
        )
    )
    application.state.product_analytics = MemoryStore()
    return TestClient(application), application.state.product_analytics


@pytest.mark.parametrize(
    'changes',
    [
        {'email': 'synthetic@example.invalid'},
        {'country': 'AR'},
        {'occurred_at': '2026-01-01'},
        {'properties': {}},
        {'source': 'assistant'},
        {'locale': 'fr'},
        {'section': '/about?q=secret'},
        {'project': 'pequeverso'},
        {'event_name': 'made_up'},
        {'event_id': 'not-a-uuid'},
        {'event_id': '11111111-1111-1111-8111-111111111111'},
        {'target': 'email'},
        {'event_name': 'cv_link_open', 'target': 'en', 'section': 'home'},
        {'event_name': 'contact_link_open'},
        {'event_name': 'section_open', 'target': 'rampy'},
        {'event_name': 'company_link_open', 'section': 'work', 'target': 'independent'},
    ],
)
def test_rejects_unreviewed_fields_dimensions_and_semantic_combinations(changes):
    with pytest.raises(ValidationError):
        ProductEventBody.model_validate(event(**changes))


def test_noop_by_default_and_no_database_or_cookie():
    assert not Settings(_env_file=None).product_analytics_enabled
    http, store = client(False)
    response = http.post(
        '/api/v1/analytics/events', json=event(), headers={'Origin': ORIGIN}
    )
    assert response.status_code == 404
    assert not store.events
    assert 'set-cookie' not in response.headers


def test_public_credentialless_ingestion_and_private_authentication():
    http, store = client()
    headers = {'Origin': ORIGIN}
    response = http.post('/api/v1/analytics/events', json=event(), headers=headers)
    assert response.status_code == 204
    assert len(store.events) == 1
    assert isinstance(store.events[0], ProductEvent)
    assert 'no-store' in response.headers['cache-control']
    assert 'set-cookie' not in response.headers
    for auth in ({'Cookie': 'synthetic=value'}, {'Authorization': 'Bearer synthetic'}):
        assert (
            http.post(
                '/api/v1/analytics/events', json=event(), headers={**headers, **auth}
            ).status_code
            == 400
        )
    assert (
        http.post(
            '/api/v1/analytics/events',
            json=event(),
            headers={'Origin': 'https://attacker.invalid'},
        ).status_code
        == 403
    )
    assert http.post('/api/v1/analytics/events', json=event()).status_code == 403
    assert http.get('/internal/ops/v1/product-analytics').status_code == 401
    private = http.get(
        '/internal/ops/v1/product-analytics',
        headers={'Authorization': 'Bearer ' + TOKEN},
    )
    assert private.status_code == 200
    assert private.json()['counts'] == []
    assert 'no-store' in private.headers['cache-control']
    store.limited = True
    assert (
        http.post('/api/v1/analytics/events', json=event(), headers=headers).status_code
        == 429
    )


def test_bounded_actual_chunked_body_and_safe_error_output():
    http, store = client()
    response = http.post(
        '/api/v1/analytics/events',
        content=iter([b'{"secret":"', b'x' * 2000, b'"}']),
        headers={'Origin': ORIGIN, 'Content-Type': 'application/json'},
    )
    assert response.status_code == 422
    assert not store.events
    assert 'x' * 32 not in response.text


def test_internal_schema_not_exposed_and_public_contract_exported():
    http, _ = client()
    paths = http.get('/openapi.json').json()['paths']
    assert '/api/v1/analytics/events' in paths
    assert '/internal/ops/v1/product-analytics' not in paths
