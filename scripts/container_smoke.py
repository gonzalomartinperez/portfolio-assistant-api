"""Smoke one non-root image and active-stream SIGTERM using isolated fixture data."""

import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg

SLOW_APP = """import asyncio
from app.bootstrap.container import create_app
from app.infrastructure.answer import FixtureProvider
class SlowFixture(FixtureProvider):
    async def stream(self, question, evidence, locale, history=(), context=None):
        async for item in super().stream(question, evidence, locale, history, context):
            yield item
            await asyncio.sleep(2)
app = create_app(provider_override=SlowFixture())
"""


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def consume(client, cid, auth, run_ids, events, first_delta, slow, failures):
    try:
        with client.stream(
            'POST',
            f'/api/v1/conversations/{cid}/messages/stream',
            headers={**auth, 'Idempotency-Key': str(uuid4())},
            json={'content': 'What is Filomena?', 'locale': 'en'},
        ) as stream:
            stream.raise_for_status()
            run_ids.append(stream.headers['x-run-id'])
            for line in stream.iter_lines():
                if line.startswith('data: '):
                    event = json.loads(line[6:])
                    events.append(event['type'])
                    if event['type'] == 'message.delta':
                        first_delta.set()
    except httpx.RemoteProtocolError:
        if not slow:
            failures.append('unexpected interrupted response')
    except httpx.HTTPError:
        failures.append('HTTP transport failure')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='portfolio-assistant-api:fixture')
    parser.add_argument('--port', type=int, default=58080)
    args = parser.parse_args()
    database_url = os.environ.get(
        'DATABASE_URL', 'postgresql://assistant:assistant@127.0.0.1:5433/assistant'
    )
    graph_uri = os.environ.get('NEO4J_URI', 'bolt://127.0.0.1:7688')
    reports = []
    for slow in (False, True):
        name = 'assistant-smoke-' + uuid4().hex[:10]
        with tempfile.TemporaryDirectory(prefix='assistant-smoke-') as directory:
            Path(directory).chmod(0o755)
            Path(directory, 'smoke_app.py').write_text(SLOW_APP)
            command = [
                'run',
                '-d',
                '--name',
                name,
                '--network',
                'host',
                '--read-only',
                '--tmpfs',
                '/tmp',
                '--cap-drop=ALL',
                '--security-opt=no-new-privileges',
                '-e',
                f'DATABASE_URL={database_url}',
                '-e',
                f'NEO4J_URI={graph_uri}',
                '-e',
                'AI_PROVIDER=fixture',
                '-e',
                'ALLOW_PAID_AI=false',
            ]
            if slow:
                command += [
                    '-v',
                    f'{directory}:/smoke:ro',
                    '-e',
                    'PYTHONPATH=/smoke:/app',
                ]
            command += [
                args.image,
                'uvicorn',
                'smoke_app:app' if slow else 'app.main:app',
                '--host',
                '127.0.0.1',
                '--port',
                str(args.port),
                '--no-access-log',
                '--timeout-graceful-shutdown',
                '1' if slow else '15',
            ]
            docker(*command)
            try:
                with httpx.Client(
                    base_url=f'http://localhost:{args.port}', timeout=20
                ) as client:
                    deadline = time.monotonic() + 40
                    while True:
                        try:
                            ready = client.get('/health/ready')
                            if ready.status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        if time.monotonic() >= deadline:
                            raise RuntimeError('container readiness timed out')
                        time.sleep(0.2)
                    assert client.get('/health/live').status_code == 200
                    uid = docker('exec', name, 'id', '-u')
                    assert uid == '65532'
                    docker(
                        'exec',
                        name,
                        'python',
                        '-c',
                        'import shutil; assert shutil.which("git"); '
                        'assert not shutil.which("uv"); assert not shutil.which("uvx")',
                    )
                    docker(
                        'exec',
                        name,
                        '/usr/local/bin/python',
                        '-c',
                        'import importlib.util; '
                        'assert importlib.util.find_spec("pip") is None; '
                        'assert importlib.util.find_spec("ensurepip") is None',
                    )
                    response = client.post(
                        '/api/v1/session',
                        headers={
                            'Origin': 'http://localhost:3000',
                            'X-Session-Bootstrap': '1',
                        },
                        json={},
                    )
                    response.raise_for_status()
                    auth = {
                        'Origin': 'http://localhost:3000',
                        'X-CSRF-Token': response.json()['csrf_token'],
                    }
                    cid = client.post(
                        '/api/v1/conversations', headers=auth, json={}
                    ).json()['id']
                    first_delta = threading.Event()
                    events, run_ids, failures = [], [], []
                    worker = threading.Thread(
                        target=consume,
                        args=(
                            client,
                            cid,
                            auth,
                            run_ids,
                            events,
                            first_delta,
                            slow,
                            failures,
                        ),
                    )
                    worker.start()
                    assert first_delta.wait(15), 'no incremental delta received'
                    if slow:
                        docker('stop', '--time', '15', name)
                    worker.join(timeout=20)
                    assert not worker.is_alive() and not failures
                    if not slow:
                        assert events[-2:] == ['message.completed', 'run.completed']
                        client.delete(
                            '/api/v1/session', headers=auth
                        ).raise_for_status()
                        docker('stop', '--time', '20', name)
                    assert (
                        docker('inspect', '--format', '{{.State.ExitCode}}', name)
                        == '0'
                    )
                    if slow:
                        with psycopg.connect(database_url) as conn:
                            state = conn.execute(
                                'SELECT state FROM runs WHERE id=%s', (run_ids[0],)
                            ).fetchone()[0]
                            assert state == 'interrupted', state
                            # The test owns this synthetic session and its cleanup record.
                            conn.execute(
                                'INSERT INTO checkpoint_cleanup(thread_id) VALUES (%s) ON CONFLICT DO NOTHING',
                                (run_ids[0],),
                            )
                            conn.execute(
                                'DELETE FROM sessions WHERE id=(SELECT session_id FROM conversations WHERE id=%s)',
                                (cid,),
                            )
                    reports.append(
                        {
                            'mode': 'active-stream SIGTERM' if slow else 'normal SSE',
                            'uid': uid,
                            'events': len(events),
                            'passed': True,
                        }
                    )
            finally:
                docker('rm', '-f', name)
    print(json.dumps({'image': args.image, 'checks': reports}, indent=2))


if __name__ == '__main__':
    main()
