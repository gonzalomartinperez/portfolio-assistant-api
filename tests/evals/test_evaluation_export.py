"""No external account/key: real SDK serialization stops at a synthetic transport."""

import json
import os
from dataclasses import asdict

import pytest
from langsmith import Client
from pydantic import ValidationError
from requests import Response
from requests.exceptions import ConnectionError

from app.adapters.observability.evaluation_export import (
    ENDPOINT,
    EvaluationSession,
    LangSmithEvaluationExporter,
)
from app.application.evaluation_export import EvaluationSummary, export_evaluation
from app.bootstrap.config import Settings
from app.bootstrap.evaluation_export import run


@pytest.fixture
def summary():
    return EvaluationSummary('a' * 40, 6, 5, 1, 12000)


def test_application_port_and_disabled_path(summary):
    class MustNotRun:
        def export(self, summary):
            raise AssertionError('disabled exporter invoked')

    assert (
        export_evaluation(summary, authorized=False, exporter=MustNotRun())
        == 'disabled'
    )
    assert export_evaluation(summary, authorized=True) == 'unavailable'


@pytest.mark.parametrize(
    'changes',
    [
        {'source_commit': 'user@example.invalid'},
        {'cases': True},
        {'cases': 0},
        {'completed': 7},
        {'failed': -1},
        {'total_ms': 3600001},
        {'total_ms': 0.5},
        {'scope': 'visitor'},
    ],
)
def test_invalid_summary_is_rejected(summary, changes):
    with pytest.raises(ValueError):
        EvaluationSummary(**(asdict(summary) | changes))


def test_real_sdk_payload_is_closed_sanitized_and_bounded(monkeypatch, summary):
    requests = []
    closed = []
    original_close = Client.close

    def record(self, method, url, **kwargs):
        requests.append((method, url, kwargs))
        response = Response()
        response.status_code = 200
        response._content = b'{}'
        return response

    def close(self):
        closed.append(True)
        original_close(self)

    def session_request(self, method, url, **kwargs):
        return record(self, method, url, **kwargs)

    monkeypatch.setattr('requests.Session.request', session_request)
    monkeypatch.setattr(Client, 'close', close)
    assert LangSmithEvaluationExporter('synthetic-credential-not-real').export(summary)
    assert len(requests) == 1 and closed
    method, url, kwargs = requests[0]
    assert (method, url) == ('POST', ENDPOINT + '/runs')
    assert kwargs['allow_redirects'] is False
    assert kwargs['timeout'] == (2.0, 5.0)
    payload = json.loads(kwargs['data'])
    assert payload['inputs'] == {} and payload['outputs'] == {}
    assert payload['extra'] == {'metadata': {**asdict(summary), 'model': 'gpt-6-luna'}}
    assert 'attachments' not in payload and 'events' not in payload
    assert payload['session_name'] == 'portfolio-synthetic-evaluations'
    assert payload['start_time'] == payload['end_time']


def test_sdk_failure_is_safe_and_not_retried(monkeypatch, summary):
    attempts = []

    def fail(self, *args, **kwargs):
        attempts.append(True)
        raise ConnectionError('sensitive backend body must not surface')

    monkeypatch.setattr('requests.Session.request', fail)
    assert (
        LangSmithEvaluationExporter('synthetic-credential-not-real').export(summary)
        is False
    )
    assert len(attempts) == 1


@pytest.mark.parametrize(
    'method,url', [('GET', ENDPOINT + '/info'), ('POST', 'https://other.invalid/runs')]
)
def test_transport_rejects_other_destinations(method, url):
    with EvaluationSession() as session, pytest.raises(ValueError):
        session.request(method, url)


def test_cli_default_has_no_client_even_with_unrelated_key(
    monkeypatch, tmp_path, summary
):
    path = tmp_path / 'summary.json'
    path.write_text(json.dumps(asdict(summary)))
    monkeypatch.setenv('LANGSMITH_API_KEY', 'unrelated-key-never-used')
    monkeypatch.setattr(
        'app.bootstrap.evaluation_export.LangSmithEvaluationExporter',
        lambda *args: pytest.fail('client created'),
    )
    assert run(path) == 'disabled'
    with pytest.raises(ValueError):
        run(path, authorize_export=True)


@pytest.mark.parametrize(
    'extra', [{'answer': 'private'}, {'inputs': {}}, {'session_id': 'x'}]
)
def test_cli_rejects_raw_report_fields(tmp_path, summary, extra):
    path = tmp_path / 'summary.json'
    path.write_text(json.dumps(asdict(summary) | extra))
    with pytest.raises(ValueError):
        run(path)


def test_cli_rejects_missing_credential_and_large_file(monkeypatch, tmp_path, summary):
    monkeypatch.delenv('EVALUATION_LANGSMITH_API_KEY', raising=False)
    path = tmp_path / 'summary.json'
    path.write_text(json.dumps(asdict(summary)))
    with pytest.raises(ValueError):
        run(path, authorize_export=True)
    path.write_bytes(b' ' * 2049)
    with pytest.raises(ValueError):
        run(path)


def test_global_automatic_tracing_remains_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, langsmith_tracing=True)


def test_redirect_is_unavailable_without_following(monkeypatch, summary):
    attempts = []

    def redirect(self, method, url, **kwargs):
        attempts.append(url)
        response = Response()
        response.status_code = 307
        response.headers['Location'] = 'https://other.invalid/runs'
        return response

    monkeypatch.setattr('requests.Session.request', redirect)
    assert (
        LangSmithEvaluationExporter('synthetic-credential-not-real').export(summary)
        is False
    )
    assert attempts == [ENDPOINT + '/runs']


def test_opt_in_uses_only_explicit_evaluation_key(monkeypatch, tmp_path, summary):
    for name in list(os.environ):
        if name.startswith(('LANGSMITH_', 'LANGCHAIN_')):
            monkeypatch.delenv(name)
    path = tmp_path / 'summary.json'
    path.write_text(json.dumps(asdict(summary)))
    monkeypatch.setenv('ENVIRONMENT', 'development')
    monkeypatch.setenv('EVALUATION_LANGSMITH_API_KEY', 'synthetic-credential-not-real')
    received = []

    class FakeExporter:
        def __init__(self, key):
            received.append(key)

        def export(self, summary):
            return True

    monkeypatch.setattr(
        'app.bootstrap.evaluation_export.LangSmithEvaluationExporter', FakeExporter
    )
    assert run(path, authorize_export=True) == 'exported'
    assert received == ['synthetic-credential-not-real']
    monkeypatch.setenv('ENVIRONMENT', 'production')
    with pytest.raises(ValueError):
        run(path, authorize_export=True)


@pytest.mark.parametrize(
    'name',
    ['LANGSMITH_USE_PYO3_CLIENT', 'LANGSMITH_RUNS_ENDPOINTS', 'LANGCHAIN_ENDPOINT'],
)
def test_false_string_does_not_authorize_other_sdk_environment_hooks(
    monkeypatch, tmp_path, summary, name
):
    path = tmp_path / 'summary.json'
    path.write_text(json.dumps(asdict(summary)))
    monkeypatch.setenv(name, 'false')
    with pytest.raises(ValueError, match='clean development'):
        run(path, authorize_export=True)


def test_deep_json_is_rejected_safely(tmp_path):
    path = tmp_path / 'summary.json'
    path.write_text('[' * 1000 + '0' + ']' * 1000)
    with pytest.raises(ValueError):
        run(path)
