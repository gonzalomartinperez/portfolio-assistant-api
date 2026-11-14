"""SSE load: an httpx streaming client reporting time to first event, gaps and failures.

Locust rows: `ttfe` (time to first event), `gap` (time between consecutive events) and
`stream` (whole stream; fails on a bad status, an error terminal or a premature close) and
`setup` (session or conversation creation; only failures are reported).
"""

import time
import uuid

import httpx
from locust import User, constant, events, task

ORIGIN = 'http://localhost:3000'
TERMINAL = {'run.completed', 'run.failed', 'run.cancelled'}


class StreamingUser(User):
    wait_time = constant(0.2)

    def on_start(self):
        self.client = httpx.Client(base_url=self.host, headers={'Origin': ORIGIN})
        self.ready = False
        self.login()

    def login(self):
        started = time.perf_counter()
        try:
            session = self.client.post(
                '/api/v1/session', json={}, headers={'X-Session-Bootstrap': '1'}
            )
            session.raise_for_status()
            self.client.headers['X-CSRF-Token'] = session.json()['csrf_token']
            self.ready = True
        except Exception as exc:  # noqa: BLE001 - every setup failure is a Locust failure
            self.report('setup', time.perf_counter() - started, exc)

    def on_stop(self):
        self.client.close()

    def report(self, name, elapsed, error=None):
        events.request.fire(
            request_type='SSE',
            name=name,
            response_time=elapsed * 1000,
            response_length=0,
            exception=error,
            context={},
        )

    @task
    def ask(self):
        if not self.ready:
            self.login()
            return
        started = last = time.perf_counter()
        try:
            created = self.client.post('/api/v1/conversations', json={})
            created.raise_for_status()
            conversation = created.json()['id']
        except Exception as exc:  # noqa: BLE001 - counted as a failure, never a crash
            self.report('setup', time.perf_counter() - started, exc)
            return
        started = last = time.perf_counter()
        seen, first, error = [], True, None
        try:
            with self.client.stream(
                'POST',
                f'/api/v1/conversations/{conversation}/messages/stream',
                json={'content': 'What is Filomena?'},
                headers={'Idempotency-Key': uuid.uuid4().hex},
                timeout=30,
            ) as response:
                if response.status_code != 200:
                    error = RuntimeError(f'status {response.status_code}')
                for line in response.iter_lines() if not error else ():
                    if not line.startswith('event:'):
                        continue
                    now = time.perf_counter()
                    self.report(
                        'ttfe' if first else 'gap', now - (started if first else last)
                    )
                    first, last = False, now
                    seen.append(line[6:].strip())
        except httpx.HTTPError as exc:
            error = exc
        if not error and (not seen or seen[-1] not in TERMINAL):
            error = RuntimeError('premature close')
        if not error and seen[-1] == 'run.failed':
            error = RuntimeError('run failed')
        self.report('stream', time.perf_counter() - started, error)
