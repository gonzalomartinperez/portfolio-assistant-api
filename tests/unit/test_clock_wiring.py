"""The injected Clock is the value consumers stamp, not the system wall clock."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

from portfolio_assistant.adapters.providers.answer import ResponsesProvider
from portfolio_assistant.application.conversations import Conversations
from portfolio_assistant.presentation.http import sse
from tests.support import FIXED_NOW, FixedClock
from tests.support_app import FakeStore


def test_session_expiry_follows_the_injected_clock():
    clock = FixedClock()
    clock.advance(days=3)
    _, session = Conversations(FakeStore(), 7, "k" * 32, clock=clock).bootstrap("subject")
    assert session.expires_at == FIXED_NOW + timedelta(days=10)


def test_sse_timestamp_is_the_injected_clock():
    clock = FixedClock()
    clock.advance(minutes=5)
    frame = sse("run.started", uuid4(), uuid4(), 1, {"state": "running"}, clock=clock)
    data = json.loads(frame.split("data: ", 1)[1])
    assert datetime.fromisoformat(data["timestamp"]) == FIXED_NOW + timedelta(minutes=5)


def test_provider_default_today_reads_the_injected_clock():
    clock = FixedClock()
    clock.advance(days=1)
    provider = ResponsesProvider(object(), model="m", clock=clock)  # type: ignore[arg-type]
    assert provider.today() == (FIXED_NOW + timedelta(days=1)).date()
