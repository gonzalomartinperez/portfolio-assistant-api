"""`X-Assistant-Progress` wiring over the real routers, middleware and run service (fakes only)."""

import pytest

from portfolio_assistant.bootstrap.config import Settings
from portfolio_assistant.bootstrap.container import create_app
from tests.resilience.test_dependency_failures import frames, session
from tests.support_app import ORIGIN, build_app, pin_env


def stream(client, header):
    conversation = client.post("/api/v1/conversations", json={}).json()
    extra = {} if header is None else {"X-Assistant-Progress": header}
    return client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/stream",
        json={"content": "What is Filomena?"},
        headers={"Idempotency-Key": "k" * 8, **extra},
    )


@pytest.mark.parametrize("header", [None, "0", "true", "yes please"])
def test_without_the_opt_in_the_stream_is_v1(monkeypatch, header):
    pin_env(monkeypatch)
    response = stream(session(build_app()), header)
    assert response.status_code == 200
    names = [name for name, _ in frames(response)]
    assert "run.progress" not in names
    assert names[0] == "run.started"
    assert names[-1] == "run.completed"


@pytest.mark.parametrize("header", ["1", " 1 "])
def test_opt_in_adds_ordered_progress(monkeypatch, header):
    pin_env(monkeypatch)
    events = frames(stream(session(build_app()), header))
    assert [event["sequence"] for _, event in events] == list(range(len(events)))
    phases = [event["payload"]["phase"] for name, event in events if name == "run.progress"]
    assert phases == ["retrieving", "reading", "writing"]
    assert events[-1][0] == "run.completed"


def test_production_cors_allows_the_opt_in_header(monkeypatch):
    pin_env(monkeypatch)
    from fastapi.testclient import TestClient

    client = TestClient(create_app(Settings(_env_file=None, allowed_origins=ORIGIN)))
    preflight = client.options(
        "/api/v1/conversations/x/messages/stream",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-assistant-progress,idempotency-key",
        },
    )
    assert preflight.status_code == 200
    assert "x-assistant-progress" in preflight.headers["access-control-allow-headers"].lower()
