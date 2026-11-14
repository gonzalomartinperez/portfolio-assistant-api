"""SSE wire conformance with fakes: frame grammar, closed event set, one terminal, heartbeat."""

import asyncio
import inspect
import json
import re
from types import SimpleNamespace
from uuid import uuid4

import jsonschema
import pytest

from app.presentation.http import execute_run
from app.presentation.streaming import heartbeat
from tests.support import ROOT

pytestmark = pytest.mark.contract

SCHEMA = json.loads((ROOT / 'contracts/sse.schema.json').read_text())
EVENT_NAMES = {
    SCHEMA['$defs'][option['$ref'].rsplit('/', 1)[-1]]['properties']['type']['const']
    for option in SCHEMA['oneOf']
}
TERMINAL = {'run.completed', 'run.failed', 'run.cancelled'}
FRAME = re.compile(r'event: (?P<event>[a-z.]+)\ndata: (?P<data>\{.*\})\n\n', re.DOTALL)
MESSAGE = {'message_id': str(uuid4()), 'content': 'Hello', 'citations': []}
SCRIPTS = {
    'success': [
        ('run.started', {'state': 'running'}),
        ('run.status', {'phase': 'evidence_found', 'sources': 1}),
        ('message.delta', {'text': 'Hel'}),
        ('message.delta', {'text': 'lo'}),
        ('message.completed', MESSAGE),
        ('run.completed', {'state': 'completed'}),
    ],
    'failure': [('run.started', {'state': 'running'}), ('run.failed', {'code': 'x'})],
    'cancelled': [('run.started', {'state': 'running'}), ('run.cancelled', {})],
}


def request_for(script):
    async def execute(*_args):
        for name, payload in script:
            yield SimpleNamespace(name=name, payload=payload)

    return SimpleNamespace(
        state=SimpleNamespace(request_id='r1'),
        app=SimpleNamespace(
            state=SimpleNamespace(runs=SimpleNamespace(execute=execute))
        ),
    )


def collect(script):
    async def run():
        stream = execute_run(request_for(script), uuid4(), uuid4(), 'q', 'en')
        return [frame async for frame in stream]

    return asyncio.run(run())


def test_event_set_is_the_closed_v1_vocabulary():
    assert EVENT_NAMES == {
        'run.started',
        'run.status',
        'message.delta',
        'message.completed',
        'run.completed',
        'run.failed',
        'run.cancelled',
    }


@pytest.mark.parametrize('name', SCRIPTS)
def test_frames_are_well_formed_schema_valid_and_ordered(name):
    frames = collect(SCRIPTS[name])
    validator = jsonschema.Draft202012Validator(SCHEMA)
    types = []
    for index, frame in enumerate(frames):
        match = FRAME.fullmatch(frame)
        assert match, frame
        data = json.loads(match['data'])
        assert match['event'] == data['type'] in EVENT_NAMES
        assert data['sequence'] == index
        validator.validate(data)
        types.append(data['type'])
    assert types[0] == 'run.started'
    assert [t for t in types if t in TERMINAL] == [types[-1]]


def test_unknown_event_name_cannot_reach_the_wire():
    with pytest.raises(Exception):  # noqa: B017 - pydantic rejects the unlisted event
        collect([('run.internal', {'secret': 'x'})])


def test_heartbeat_interval_is_fifteen_seconds():
    assert inspect.signature(heartbeat).parameters['interval'].default == 15


def test_silence_yields_comments_that_do_not_consume_sequence_ids():
    async def slow():
        await asyncio.sleep(0.05)
        yield 'event: run.started\ndata: {}\n\n'

    async def run():
        return [frame async for frame in heartbeat(slow(), interval=0.01)]

    frames = asyncio.run(run())
    assert frames[-1].startswith('event: ')
    assert set(frames[:-1]) == {': keep-alive\n\n'} and len(frames) > 1


def test_closing_the_stream_cancels_upstream_work():
    state = {'closed': False, 'resumed': 0}

    async def upstream():
        try:
            yield 'event: run.started\ndata: {}\n\n'
            await asyncio.sleep(60)
            state['resumed'] += 1
        finally:
            state['closed'] = True

    async def run():
        stream = heartbeat(upstream(), interval=0.01)
        assert (await anext(stream)).startswith('event: run.started')
        await stream.aclose()  # what ClosingStreamingResponse does on client disconnect

    asyncio.run(run())
    assert state == {'closed': True, 'resumed': 0}
