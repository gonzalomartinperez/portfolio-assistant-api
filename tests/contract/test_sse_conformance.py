"""SSE wire conformance with fakes: frame grammar, closed event set, one terminal, heartbeat."""

import asyncio
import inspect
import json
import re
from types import SimpleNamespace
from uuid import uuid4

import jsonschema
import pytest
from pydantic import ValidationError

from portfolio_assistant.presentation.http import execute_run
from portfolio_assistant.presentation.streaming import heartbeat
from tests.support import ROOT, FixedClock

pytestmark = pytest.mark.contract

SCHEMA = json.loads((ROOT / "contracts/sse.schema.json").read_text())
EVENT_NAMES = {
    SCHEMA["$defs"][option["$ref"].rsplit("/", 1)[-1]]["properties"]["type"]["const"]
    for option in SCHEMA["oneOf"]
}
TERMINAL = {"run.completed", "run.failed", "run.cancelled"}
FRAME = re.compile(r"event: (?P<event>[a-z.]+)\ndata: (?P<data>\{.*\})\n\n", re.DOTALL)
MESSAGE = {"message_id": str(uuid4()), "content": "Hello", "citations": []}
SCRIPTS = {
    "success": [
        ("run.started", {"state": "running"}),
        ("run.status", {"phase": "evidence_found", "sources": 1}),
        ("message.delta", {"text": "Hel"}),
        ("message.delta", {"text": "lo"}),
        ("message.completed", MESSAGE),
        ("run.completed", {"state": "completed"}),
    ],
    "failure": [("run.started", {"state": "running"}), ("run.failed", {"code": "x"})],
    "cancelled": [("run.started", {"state": "running"}), ("run.cancelled", {})],
}


def request_for(script):
    async def execute(*_args):
        for name, payload in script:
            yield SimpleNamespace(name=name, payload=payload)

    return SimpleNamespace(
        state=SimpleNamespace(request_id="r1"),
        app=SimpleNamespace(
            state=SimpleNamespace(runs=SimpleNamespace(execute=execute), clock=FixedClock())
        ),
    )


def collect(script, *, progress=False):
    async def run():
        stream = execute_run(request_for(script), uuid4(), uuid4(), "q", "en", progress=progress)
        return [frame async for frame in stream]

    return asyncio.run(run())


OPTED_IN_ORDER = [
    "run.started",
    "run.progress",
    "run.status",
    "run.progress",
    "run.progress",
    "message.delta",
    "message.delta",
    "message.completed",
    "run.completed",
]


def decoded(frames):
    return [json.loads(FRAME.fullmatch(frame)["data"]) for frame in frames]


V1_EVENTS = {
    "run.started",
    "run.status",
    "message.delta",
    "message.completed",
    "run.completed",
    "run.failed",
    "run.cancelled",
}
OPT_IN = {"run.progress"}


def test_event_set_is_the_closed_v1_vocabulary_plus_opt_in_progress():
    assert EVENT_NAMES == V1_EVENTS | OPT_IN


@pytest.mark.parametrize("name", SCRIPTS)
def test_frames_are_well_formed_schema_valid_and_ordered(name):
    frames = collect(SCRIPTS[name])
    validator = jsonschema.Draft202012Validator(SCHEMA)
    types = []
    for index, frame in enumerate(frames):
        match = FRAME.fullmatch(frame)
        assert match, frame
        data = json.loads(match["data"])
        assert match["event"] == data["type"] in EVENT_NAMES
        assert data["sequence"] == index
        validator.validate(data)
        types.append(data["type"])
    assert types[0] == "run.started"
    assert [t for t in types if t in TERMINAL] == [types[-1]]


@pytest.mark.parametrize("name", SCRIPTS)
def test_v1_streams_never_carry_progress(name):
    events = decoded(collect(SCRIPTS[name]))
    assert [event["type"] for event in events] == [step for step, _ in SCRIPTS[name]]
    assert {event["type"] for event in events} <= V1_EVENTS


def test_opted_in_stream_carries_ordered_schema_valid_progress():
    validator = jsonschema.Draft202012Validator(SCHEMA)
    events = decoded(collect(SCRIPTS["success"], progress=True))
    for event in events:
        validator.validate(event)
    assert [event["type"] for event in events] == OPTED_IN_ORDER
    assert [event["sequence"] for event in events] == list(range(len(events)))
    phases = [event["payload"]["phase"] for event in events if event["type"] == "run.progress"]
    assert phases == ["retrieving", "reading", "writing"]


@pytest.mark.parametrize("name", ["failure", "cancelled"])
def test_opted_in_terminal_stays_last_and_unique(name):
    types = [event["type"] for event in decoded(collect(SCRIPTS[name], progress=True))]
    assert types == ["run.started", "run.progress", SCRIPTS[name][-1][0]]


def test_writing_precedes_a_completed_message_without_deltas():
    script = [
        ("run.started", {"state": "running"}),
        ("message.completed", MESSAGE),
        ("run.completed", {"state": "completed"}),
    ]
    types = [event["type"] for event in decoded(collect(script, progress=True))]
    assert types == [
        "run.started",
        "run.progress",
        "run.progress",
        "message.completed",
        "run.completed",
    ]


def test_progress_payload_is_closed():
    from portfolio_assistant.presentation.events import events

    base = {
        "type": "run.progress",
        "run_id": str(uuid4()),
        "conversation_id": str(uuid4()),
        "sequence": 0,
        "timestamp": "2026-11-22T00:00:00Z",
    }
    for payload in ({"phase": "thinking"}, {"phase": "reading", "tool": "x"}):
        with pytest.raises(ValidationError):
            events.validate_python({**base, "payload": payload})


def test_unknown_event_name_cannot_reach_the_wire():
    with pytest.raises(ValidationError):
        collect([("run.internal", {"secret": "x"})])


def test_heartbeat_interval_is_fifteen_seconds():
    assert inspect.signature(heartbeat).parameters["interval"].default == 15


def test_silence_yields_comments_that_do_not_consume_sequence_ids():
    async def slow():
        await asyncio.sleep(0.05)
        yield "event: run.started\ndata: {}\n\n"

    async def run():
        return [frame async for frame in heartbeat(slow(), interval=0.01)]

    frames = asyncio.run(run())
    assert frames[-1].startswith("event: ")
    assert set(frames[:-1]) == {": keep-alive\n\n"}
    assert len(frames) > 1


def test_closing_the_stream_cancels_upstream_work():
    state = {"closed": False, "resumed": 0}

    async def upstream():
        try:
            yield "event: run.started\ndata: {}\n\n"
            await asyncio.sleep(60)
            state["resumed"] += 1
        finally:
            state["closed"] = True

    async def run():
        stream = heartbeat(upstream(), interval=0.01)
        assert (await anext(stream)).startswith("event: run.started")
        await stream.aclose()  # what ClosingStreamingResponse does on client disconnect

    asyncio.run(run())
    assert state == {"closed": True, "resumed": 0}


def test_sse_sample_renders_v1_and_opted_in_streams(tmp_path):
    from scripts.sse_sample import main

    out = tmp_path / "sample.json"
    assert main(["--out", str(out)]) == 0
    sample = json.loads(out.read_text())
    assert all("run.progress" not in text for text in sample["v1"].values())
    assert all("event: run.progress" in text for text in sample["opt_in"].values())


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        ("generation_failed", True),
        ("provider_unavailable", True),
        ("budget_exhausted", False),
        ("knowledge_updating", True),
        ("unlisted_internal_code", True),
    ],
)
def test_run_failed_carries_retry_advice_and_bilingual_messages(code, retryable):
    events = decoded(
        collect([("run.started", {"state": "running"}), ("run.failed", {"code": code})])
    )
    payload = events[-1]["payload"]
    jsonschema.Draft202012Validator(SCHEMA).validate(events[-1])
    assert payload["code"] == code
    assert payload["retryable"] is retryable
    assert payload["messages"]["en"]
    assert payload["messages"]["es"]
    assert payload["messages"]["en"] != payload["messages"]["es"]
