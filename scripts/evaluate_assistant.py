"""Owned local evaluation server; paid mode is explicit and never a CI default."""

import argparse
import json
import os
import signal
import socket
import stat
import tempfile
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from scripts.evaluation_isolation import validate_targets

MAX_REPORT_BYTES = 64 * 1024 * 1024


class EvaluationProgress:
    """Own a new private report and atomically retain bounded local progress."""

    def __init__(self, path: Path, metadata: dict):
        self.path = path
        self.state = {
            **metadata,
            'status': 'running',
            'active_case_id': None,
            'samples': [],
        }
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as reserved:
            self.identity = os.fstat(reserved.fileno())
        self.write(self.state)

    def write(self, state: dict) -> None:
        data = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode()
        # Keep enough space to mark even a full running snapshot interrupted.
        marker_space = max(0, len('interrupted') - len(state['status']))
        if len(data) + marker_space > MAX_REPORT_BYTES:
            raise ValueError('evaluation report exceeds the private report size limit')
        descriptor, temporary = tempfile.mkstemp(
            prefix='.evaluation-', dir=self.path.parent
        )
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
                identity = os.fstat(output.fileno())
            current = self.path.lstat()
            if (
                (current.st_dev, current.st_ino)
                != (self.identity.st_dev, self.identity.st_ino)
                or not stat.S_ISREG(current.st_mode)
                or stat.S_IMODE(current.st_mode) != 0o600
                or current.st_uid != os.getuid()
            ):
                raise ValueError('evaluation report ownership changed')
            os.replace(temporary, self.path)
            self.identity = identity
            self.state = state
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def start_case(self, case_id: str) -> None:
        self.write({**self.state, 'active_case_id': case_id})

    def record(self, sample: dict) -> None:
        self.write({**self.state, 'samples': [*self.state['samples'], sample]})

    def finish(self, status: str) -> None:
        self.write(
            {
                **self.state,
                'status': status,
                'active_case_id': None
                if status == 'complete'
                else self.state['active_case_id'],
            }
        )


@contextmanager
def interruption_signals():
    """Let SIGTERM unwind report persistence and the owned evaluation server."""
    previous = signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@contextmanager
def evaluation_server(config: Settings):
    validate_targets(config)
    server = uvicorn.Server(
        uvicorn.Config(create_app(config), log_level='error', access_log=False)
    )
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        thread = threading.Thread(
            target=server.run, kwargs={'sockets': [listener]}, daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('evaluation server failed to start')
                time.sleep(0.01)
            yield f'http://127.0.0.1:{listener.getsockname()[1]}'
        finally:
            server.should_exit = True
            thread.join(timeout=20)
            if thread.is_alive():
                raise RuntimeError('evaluation server did not stop')


def configuration(mode: str, allow_paid: bool) -> Settings:
    if mode == 'openai' and not allow_paid:
        raise ValueError(
            'paid evaluation requires explicit --allow-paid and owner authorization'
        )
    if mode == 'fixture':
        config = Settings(
            _env_file=None,
            ai_provider='fixture',
            embeddings_provider='fixture',
            allow_paid_ai=False,
            openai_api_key=None,
        )
    else:
        config = Settings(_env_file=None)
        if (
            not config.allow_paid_ai
            or config.ai_provider != 'openai'
            or config.embeddings_provider != 'openai'
        ):
            raise ValueError(
                'paid evaluation requires explicit OpenAI generation and embeddings configuration'
            )
    # Synthetic loopback-only visitors exercise normal per-subject limits; no production rate override.
    return config.model_copy(update={'trusted_proxy_ips': '127.0.0.1'})


def evaluate(
    config: Settings,
    cases: list[dict],
    url: str,
    progress: EvaluationProgress | None = None,
) -> list[dict]:
    reports = []
    for index, case in enumerate(cases):
        if progress is not None:
            progress.start_case(case['id'])
        with httpx.Client(base_url=url, timeout=130) as client:
            origin = config.origins[0]
            visitor = {
                'X-Forwarded-For': f'198.18.{index // 250}.{index % 250 + 1}',
                'Origin': origin,
            }
            response = client.post(
                '/api/v1/session',
                headers={**visitor, 'X-Session-Bootstrap': '1'},
                json={},
            )
            response.raise_for_status()
            headers = {**visitor, 'X-CSRF-Token': response.json()['csrf_token']}
            try:
                created = client.post('/api/v1/conversations', headers=headers, json={})
                created.raise_for_status()
                started = time.perf_counter()
                first = None
                completed = None
                terminal = None
                failure = None
                with client.stream(
                    'POST',
                    f'/api/v1/conversations/{created.json()["id"]}/messages/stream',
                    headers={**headers, 'Idempotency-Key': str(uuid4())},
                    json={'content': case['question'], 'locale': case['locale']},
                ) as stream:
                    stream.raise_for_status()
                    for line in stream.iter_lines():
                        if not line.startswith('data: '):
                            continue
                        event = json.loads(line[6:])
                        if event['type'] == 'message.delta' and first is None:
                            first = round((time.perf_counter() - started) * 1000, 2)
                        if event['type'] == 'message.completed':
                            completed = event['payload']
                        if event['type'] in (
                            'run.completed',
                            'run.failed',
                            'run.cancelled',
                        ):
                            terminal = event['type']
                            failure = event['payload'].get('code')
                reports.append(
                    {
                        'id': case['id'],
                        'locale_hint': case['locale'],
                        'family_id': case.get('family_id'),
                        'variation': case.get('variation'),
                        'topic': case.get('topic'),
                        'split': case['split'],
                        'first_delta_ms': first,
                        'total_ms': round((time.perf_counter() - started) * 1000, 2),
                        'terminal': terminal,
                        'failure_code': failure,
                        'answer': completed['content'] if completed else None,
                        'citations': completed['citations'] if completed else [],
                        'human_scores': None,
                    }
                )
                if progress is not None:
                    progress.record(reports[-1])
            finally:
                client.delete('/api/v1/session', headers=headers).raise_for_status()
    return reports


def select_cases(bank: dict, split: str, limit: int) -> list[dict]:
    pool = bank['adversarial'] if split == 'adversarial' else bank['cases']
    queues = defaultdict(deque)
    topics = []
    for case in pool:
        if split != 'all' and case['split'] != split:
            continue
        topic = case.get('topic', 'adversarial')
        if topic not in topics:
            topics.append(topic)
        queues[topic, case['locale']].append(case)
    first = [
        (topic, 'en' if index % 2 == 0 else 'es') for index, topic in enumerate(topics)
    ]
    order = first + [
        (topic, 'es' if locale == 'en' else 'en') for topic, locale in first
    ]
    selected = []
    while len(selected) < limit:
        batch = [queues[key].popleft() for key in order if queues[key]]
        if not batch:
            break
        selected.extend(batch[: limit - len(selected)])
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('fixture', 'openai'), default='fixture')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument(
        '--split',
        choices=('development', 'holdout', 'adversarial', 'all'),
        default='development',
    )
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bank = json.loads(Path('evals/assistant.json').read_text())
    maximum = max(len(bank['cases']), len(bank['adversarial']))
    if not 1 <= args.limit <= maximum:
        parser.error(f'--limit must be between 1 and {maximum}')
    config = configuration(args.mode, args.allow_paid)
    cases = select_cases(bank, args.split, args.limit)
    progress = EvaluationProgress(
        args.output,
        {
            'mode': args.mode,
            'corpus_version': None,
            'source_commit': None,
            'model': config.openai_model if args.mode == 'openai' else None,
            'reasoning_effort': config.openai_reasoning_effort
            if args.mode == 'openai'
            else None,
            'live_quality_verified': False,
        },
    )
    with interruption_signals():
        try:
            with evaluation_server(config) as url:
                catalog = httpx.get(url + '/api/v1/knowledge/suggestions', timeout=10)
                catalog.raise_for_status()
                revision = catalog.json()
                progress.write(
                    {
                        **progress.state,
                        'corpus_version': revision['corpus_version'],
                        'source_commit': revision['source_commit'],
                    }
                )
                reports = evaluate(config, cases, url, progress)
            progress.finish('complete')
        except BaseException as error:  # Retain cancellation; never retry generation.
            try:
                progress.finish('interrupted')
            except OSError, ValueError, TypeError:
                # A storage failure leaves the last atomic snapshot intact.
                error.add_note(
                    'Could not persist interruption marker; inspect the last private snapshot.'
                )
            raise
    failures = sum(item['terminal'] != 'run.completed' for item in reports)
    print(
        json.dumps(
            {
                'mode': args.mode,
                'cases': len(reports),
                'terminal_failures': failures,
                'human_review_required': True,
            }
        )
    )
    if failures:
        raise SystemExit(
            'evaluation contains failed or incomplete runs; inspect the report'
        )


if __name__ == '__main__':
    main()
