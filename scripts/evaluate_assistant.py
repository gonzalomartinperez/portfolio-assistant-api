"""Owned local evaluation server; paid mode is explicit and never a CI default."""

import argparse
import json
import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import uvicorn

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app


@contextmanager
def evaluation_server(config: Settings):
    if config.environment != 'development' or urlparse(
        config.database_url
    ).hostname not in ('localhost', '127.0.0.1'):
        raise ValueError('evaluation requires an isolated local development database')
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


def evaluate(config: Settings, cases: list[dict], url: str) -> list[dict]:
    reports = []
    for index, case in enumerate(cases):
        with httpx.Client(base_url=url, timeout=130) as client:
            origin = config.origins[0]
            visitor = {
                'X-Forwarded-For': f'192.0.2.{index % 240 + 1}',
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
            finally:
                client.delete('/api/v1/session', headers=headers).raise_for_status()
    return reports


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
    if not 1 <= args.limit <= 120:
        parser.error('--limit must be between 1 and 120')
    config = configuration(args.mode, args.allow_paid)
    bank = json.loads(Path('evals/assistant.json').read_text())
    cases = [
        case
        for case in (
            bank['adversarial'] if args.split == 'adversarial' else bank['cases']
        )
        if args.split == 'all' or case['split'] == args.split
    ][: args.limit]
    with evaluation_server(config) as url:
        reports = evaluate(config, cases, url)
    args.output.write_text(
        json.dumps(
            {
                'mode': args.mode,
                'model': config.openai_model if args.mode == 'openai' else None,
                'reasoning_effort': config.openai_reasoning_effort
                if args.mode == 'openai'
                else None,
                'live_quality_verified': False,
                'samples': reports,
            },
            ensure_ascii=False,
            indent=2,
        )
        + '\n'
    )
    print(
        json.dumps(
            {
                'mode': args.mode,
                'cases': len(reports),
                'terminal_failures': sum(
                    item['terminal'] != 'run.completed' for item in reports
                ),
                'human_review_required': True,
            }
        )
    )


if __name__ == '__main__':
    main()
