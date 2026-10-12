"""Private operational contracts, redaction and stream lifecycle regressions."""

import asyncio
import base64
import json
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ai.workflow import LangGraphWorkflow
from app.application.observability import Execution, Stage, measurements
from app.application.runs import RunService
from app.bootstrap.config import Settings
from app.infrastructure.operations import OperationalObserver
from app.infrastructure.telemetry import (
    PrivateSession,
    PrivateTelemetry,
    SafeTelemetryLog,
)
from app.presentation.operations import OperationalSnapshot, router
from tests.test_workflow import GatedProvider, Retrieval, Store

TOKEN = 'fixture-only-operational-token-0000'


def example():
    return {
        'schema_version': 1,
        'observed_at': '2026-10-12T12:00:00+00:00',
        'api_commit': 'a' * 40,
        'availability': 'ready',
        'knowledge': {
            'state': 'fresh',
            'source_commit': 'b' * 40,
            'corpus_version': 'fixture-v1',
            'indexed_at': '2026-10-12T11:00:00+00:00',
        },
        'executions': {
            'total': 3,
            'completed': 1,
            'cancelled': 1,
            'failed': 1,
            'first_token_p50_ms': 100.0,
            'first_token_p95_ms': 200.0,
        },
        'usage': {
            'input_tokens': 100,
            'output_tokens': 20,
            'settled_usd': 0.01,
            'reserved_usd': 0.05,
            'budget_usd': 10.0,
            'pricing_revision': 'configured-fixture',
        },
        'traces': [
            {
                'id': 'c' * 32,
                'started_at': '2026-10-12T12:00:00+00:00',
                'outcome': 'completed',
                'duration_ms': 200.0,
                'stages': [{'name': 'generation', 'duration_ms': 150.0}],
            }
        ],
    }


def test_internal_status_auth_scope_and_safe_failure():
    app = FastAPI()
    app.include_router(router)
    app.state.config = SimpleNamespace(ops_read_token=TOKEN)
    app.state.operations = SimpleNamespace(snapshot=example)
    app.state.ready = lambda: None
    app.state.observer = SimpleNamespace(dropped=2)
    client = TestClient(app)
    assert client.get('/internal/ops/v1/status').status_code == 401
    assert (
        client.get(
            '/internal/ops/v1/status', headers={'Authorization': 'Bearer spoofed'}
        ).status_code
        == 401
    )
    headers = {'Authorization': 'Bearer ' + TOKEN}
    assert client.get('/internal/ops/v1/status', headers=headers).json() == example()
    metrics = client.get('/internal/ops/v1/metrics', headers=headers)
    assert 'assistant_executions_window{outcome="cancelled"} 1.0' in metrics.text
    assert 'assistant_operational_observations_dropped 2.0' in metrics.text
    assert TOKEN not in metrics.text
    assert '/internal/ops/v1/status' not in app.openapi()['paths']
    assert client.post('/internal/ops/v1/status', headers=headers).status_code == 405

    def failure():
        raise RuntimeError('secret-canary')

    app.state.operations = SimpleNamespace(snapshot=failure)
    response = client.get('/internal/ops/v1/status', headers=headers)
    assert response.status_code == 503
    assert 'secret-canary' not in response.text
    app.state.config.ops_read_token = None
    assert client.get('/internal/ops/v1/status', headers=headers).status_code == 503


@pytest.mark.parametrize(
    'mutation', ['unknown', 'counts', 'nan', 'date', 'stage', 'trace_limit']
)
def test_private_schema_rejects_untrusted_values(mutation):
    value = example()
    if mutation == 'unknown':
        value['prompt'] = 'secret'
    if mutation == 'counts':
        value['executions']['total'] = 0
    if mutation == 'nan':
        value['usage']['settled_usd'] = float('nan')
    if mutation == 'date':
        value['observed_at'] = '2026-10-12'
    if mutation == 'stage':
        value['traces'][0]['stages'][0]['name'] = 'system_prompt'
    if mutation == 'trace_limit':
        value['traces'] *= 101
    with pytest.raises(ValidationError):
        OperationalSnapshot.model_validate(value)


@pytest.mark.parametrize(
    'endpoint',
    [
        'https://public.example',
        'http://169.254.169.254',
        'http://collector:4318/path',
        'http://user:secret@collector:4318',
    ],
)
def test_private_export_configuration_fails_closed(endpoint):
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            ops_read_token=TOKEN,
            ops_api_commit='a' * 40,
            otel_sdk_disabled=False,
            otel_private_endpoint=endpoint,
        )


def test_observer_queue_is_bounded_and_export_failure_preserves_storage():
    async def run():
        stored = []

        def broken(execution):
            raise RuntimeError('private-canary')

        observer = OperationalObserver(
            SimpleNamespace(save=lambda e, s: stored.append(e)),
            sample_ratio=1,
            exporter=SimpleNamespace(record=broken, close=lambda: None),
        )
        value = Execution('d' * 32, datetime.now(UTC), 'completed', 10, 2, (), None)
        for _ in range(130):
            observer.record(value)
        assert observer.queue.qsize() == 128 and observer.dropped == 2
        observer.start()
        with pytest.raises(RuntimeError):
            observer.start()
        await observer.close()
        assert len(stored) == 128 and observer.dropped == 130
        observer.record(value)
        assert observer.queue.empty() and observer.dropped == 131
        await observer.close()

    asyncio.run(run())


@pytest.mark.parametrize('cause', ['completed', 'disconnect'])
def test_observed_stream_closes_in_other_task_without_context_leaks(cause):
    async def run():
        captured = []
        provider = GatedProvider()
        service = RunService(
            Store(),
            LangGraphWorkflow(Retrieval(), provider),
            fixture=False,
            observer=SimpleNamespace(record=captured.append),
        )
        stream = service.execute(uuid4(), uuid4(), 'private-question-canary', 'en')
        assert (await anext(stream)).name == 'run.started'
        assert measurements.get() is None
        assert (await anext(stream)).name == 'run.status'
        assert (await anext(stream)).name == 'message.delta'
        if cause == 'completed':
            provider.release.set()
            async for _ in stream:
                pass
        else:
            await asyncio.create_task(stream.aclose())
        await service.drain_cleanup()
        assert provider.closed.is_set()
        assert len(captured) == 1
        assert captured[0].outcome == (
            'completed' if cause == 'completed' else 'cancelled'
        )
        assert captured[0].first_token_ms is not None
        assert measurements.get() is None
        assert 'private-question-canary' not in repr(captured)

    asyncio.run(run())


def test_telemetry_environment_and_logs_do_not_leak(monkeypatch):
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_HEADERS', 'authorization=secret-canary')
    with pytest.raises(ValueError, match='unsupported_telemetry_environment'):
        PrivateTelemetry('http://127.0.0.1:4318', 'a' * 40, 1)
    record = logging.LogRecord(
        'opentelemetry', logging.ERROR, '', 0, 'secret-canary', (), None
    )
    assert 'secret-canary' not in SafeTelemetryLog().format(record)


def test_private_session_disallows_redirects(monkeypatch):
    import requests

    seen = []
    monkeypatch.setattr(
        requests.Session, 'request', lambda self, *a, **kw: seen.append(kw)
    )
    PrivateSession().request('POST', 'http://collector:4318', allow_redirects=True)
    assert seen[0]['allow_redirects'] is False


def test_actual_otlp_exports_only_allowlisted_measurements(monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from google.protobuf.json_format import MessageToDict
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
        ExportMetricsServiceRequest,
    )
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )

    for key in tuple(__import__('os').environ):
        if key.startswith('OTEL_'):
            monkeypatch.delenv(key)
    bodies = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers['Content-Length']))
            message = (
                ExportTraceServiceRequest()
                if self.path == '/v1/traces'
                else ExportMetricsServiceRequest()
            )
            message.ParseFromString(data)
            bodies.append((self.path, MessageToDict(message)))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    exporter = PrivateTelemetry(f'http://127.0.0.1:{server.server_port}', 'a' * 40, 1)
    try:
        execution = Execution(
            'd' * 32,
            datetime.now(UTC),
            'completed',
            100,
            20,
            (Stage('generation', 50, 10),),
            None,
        )
        assert exporter.record(execution)
        assert exporter.traces.force_flush(timeout_millis=1000)
        assert exporter.meters.force_flush(timeout_millis=1000)
        trace = next(value for path, value in bodies if path == '/v1/traces')
        spans = trace['resourceSpans'][0]['scopeSpans'][0]['spans']
        assert {span['name'] for span in spans} == {
            'assistant.execution',
            'assistant.generation',
        }
        assert all(
            base64.b64decode(span['traceId']).hex() == 'd' * 32 for span in spans
        )
        attrs = trace['resourceSpans'][0]['resource']['attributes']
        assert {a['key'] for a in attrs} == {'service.name', 'service.version'}
        metrics = next(value for path, value in bodies if path == '/v1/metrics')
        names = {
            m['name']
            for scope in metrics['resourceMetrics'][0]['scopeMetrics']
            for m in scope['metrics']
        }
        assert names == {
            'assistant.executions',
            'assistant.execution.duration',
            'assistant.first_chunk.duration',
        }
        encoded = json.dumps(bodies)
        for forbidden in (
            'question',
            'prompt',
            'session',
            'conversation',
            'authorization',
            'api_key',
            'private-question-canary',
        ):
            assert forbidden not in encoded
    finally:
        exporter.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_empty_optional_configuration_keeps_fixture_defaults():
    config = Settings(
        _env_file=None, ops_read_token='', ops_api_commit='', otel_private_endpoint=''
    )
    assert config.ops_read_token is None and config.ops_api_commit is None
    assert config.otel_sdk_disabled
    assert TOKEN not in repr(
        Settings(_env_file=None, ops_read_token=TOKEN, ops_api_commit='a' * 40)
    )


def test_committed_operational_example_is_valid():
    from pathlib import Path

    OperationalSnapshot.model_validate_json(
        Path('contracts/operations.example.json').read_text()
    )


def test_export_shutdown_failure_does_not_escape_or_log_payload(caplog):
    async def run():
        def close():
            raise RuntimeError('secret-canary')

        observer = OperationalObserver(
            SimpleNamespace(save=lambda *args: None),
            sample_ratio=0,
            exporter=SimpleNamespace(close=close),
        )
        observer.start()
        await observer.close()
        assert observer.dropped == 1
        assert observer.worker.done()
        assert 'secret-canary' not in caplog.text

    asyncio.run(run())


def test_framework_does_not_inherit_global_request_exporter(monkeypatch):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from app.bootstrap.container import create_app

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(trace, 'get_tracer_provider', lambda: provider)
    app = create_app(Settings(_env_file=None))
    client = TestClient(app)
    assert client.get('/health/live').status_code == 200
    assert (
        client.post(
            '/api/v1/session',
            json={'private-canary': 'secret'},
            headers={'Origin': 'https://untrusted.invalid'},
        ).status_code
        == 403
    )
    assert not exporter.get_finished_spans()
    provider.shutdown()


def test_cancelled_observer_joins_failed_write_without_resuming_worker():
    import threading

    async def run():
        started, release = threading.Event(), threading.Event()

        def save(*args):
            started.set()
            assert release.wait(timeout=1)
            raise RuntimeError('secret-canary')

        observer = OperationalObserver(SimpleNamespace(save=save), sample_ratio=0)
        observer.start()
        observer.record(
            Execution('d' * 32, datetime.now(UTC), 'completed', 10, None, (), None)
        )
        await asyncio.to_thread(started.wait, 1)
        observer.worker.cancel()
        await asyncio.sleep(0)
        release.set()
        result = await asyncio.wait_for(
            asyncio.gather(observer.worker, return_exceptions=True), 1
        )
        assert isinstance(result[0], asyncio.CancelledError)
        assert observer.dropped == 1
        await observer.close()

    asyncio.run(run())


def test_all_production_openai_clients_ignore_vendor_endpoint_override(monkeypatch):
    import ast
    from pathlib import Path

    from openai import AsyncOpenAI, OpenAI

    monkeypatch.setenv('OPENAI_BASE_URL', 'https://untrusted.invalid/v1')
    calls = []
    for file in ('app/bootstrap/container.py', 'app/infrastructure/indexing.py'):
        tree = ast.parse(Path(file).read_text())
        calls.extend(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in ('OpenAI', 'AsyncOpenAI')
        )
    assert len(calls) == 3

    async def run():
        for call in calls:
            kwargs = {
                arg.arg: ast.literal_eval(arg.value)
                for arg in call.keywords
                if arg.arg in ('base_url', 'timeout', 'max_retries')
            }
            assert kwargs.get('base_url') == 'https://api.openai.com/v1'
            assert kwargs.get('max_retries') == 0
            if call.func.id == 'AsyncOpenAI':
                async with AsyncOpenAI(
                    api_key='synthetic-fixture-only', **kwargs
                ) as client:
                    assert client.base_url.host == 'api.openai.com'
            else:
                with OpenAI(api_key='synthetic-fixture-only', **kwargs) as client:
                    assert client.base_url.host == 'api.openai.com'

    asyncio.run(run())
