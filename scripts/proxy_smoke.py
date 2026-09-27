"""Exercise committed proxy routing against real API/indexes and an optional web image."""

import json
import os
import socket
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx

from scripts.container_smoke import SLOW_APP, docker

PROXY = 'nginxinc/nginx-unprivileged:stable-alpine@sha256:4714e0b1b2577eaa1a6131d07c958b67f0eb68e6d0521e90c6e5287db8cf0bc5'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='portfolio-assistant-api:ci')
    args = parser.parse_args()
    web_image = os.environ.get('FRONTEND_IMAGE')
    api_port, web_port, edge_port = port(), port(), port()
    names = ['assistant-proxy-test-' + uuid4().hex[:10] for _ in range(3)]
    with tempfile.TemporaryDirectory(prefix='assistant-proxy-') as directory:
        root = Path(directory)
        root.chmod(0o755)
        for source in Path('deploy/nginx').glob('*.conf'):
            text = (
                source.read_text()
                .replace('api:8000', f'127.0.0.1:{api_port}')
                .replace('web:3000', f'127.0.0.1:{web_port}')
            )
            if source.name == 'local-server.conf':
                text = text.replace('listen 8080;', f'listen 127.0.0.1:{edge_port};')
            (root / source.name).write_text(text)
        (root / 'smoke_app.py').write_text(SLOW_APP.replace('sleep(2)', 'sleep(0.15)'))
        try:
            docker(
                'run',
                '-d',
                '--name',
                names[0],
                '--network',
                'host',
                '--read-only',
                '--tmpfs',
                '/tmp',
                '-v',
                f'{root}:/smoke:ro',
                '-e',
                'PYTHONPATH=/app:/smoke',
                '-e',
                'AI_PROVIDER=fixture',
                '-e',
                'ALLOW_PAID_AI=false',
                '-e',
                f'DATABASE_URL={os.getenv("DATABASE_URL", "postgresql://assistant:assistant@127.0.0.1:5433/assistant")}',
                '-e',
                f'NEO4J_URI={os.getenv("NEO4J_URI", "bolt://127.0.0.1:7688")}',
                '-e',
                f'ALLOWED_ORIGINS=http://localhost:{edge_port},https://gonzalomartinperez.com',
                args.image,
                'uvicorn',
                'smoke_app:app',
                '--host',
                '127.0.0.1',
                '--port',
                str(api_port),
                '--no-access-log',
                '--no-proxy-headers',
            )
            if web_image:
                docker(
                    'run',
                    '-d',
                    '--name',
                    names[1],
                    '--network',
                    'host',
                    '--read-only',
                    '--tmpfs',
                    '/tmp',
                    '--tmpfs',
                    '/app/.next/cache:uid=1000,gid=1000,mode=0700,size=32m',
                    '--cap-drop=ALL',
                    '--security-opt=no-new-privileges',
                    '-e',
                    f'PORT={web_port}',
                    '-e',
                    'HOSTNAME=127.0.0.1',
                    web_image,
                )
            else:
                docker(
                    'run',
                    '-d',
                    '--name',
                    names[1],
                    '--network',
                    'host',
                    args.image,
                    'python',
                    '-m',
                    'http.server',
                    str(web_port),
                    '--bind',
                    '127.0.0.1',
                    '--directory',
                    '/tmp',
                )
            mounts = []
            for source, destination in [
                ('nginx.conf', 'nginx.conf'),
                ('local-server.conf', 'assistant-server.conf'),
                ('routes.conf', 'routes.conf'),
                ('api-proxy.conf', 'api-proxy.conf'),
            ]:
                mounts += ['-v', f'{root / source}:/etc/nginx/{destination}:ro']
            docker(
                'run',
                '-d',
                '--name',
                names[2],
                '--network',
                'host',
                '--read-only',
                '--tmpfs',
                '/tmp',
                *mounts,
                PROXY,
                'nginx',
                '-g',
                'daemon off;',
            )
            with httpx.Client(
                base_url=f'http://localhost:{edge_port}', timeout=20
            ) as client:
                deadline = time.monotonic() + 40
                while True:
                    try:
                        if client.get('/health/ready').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError(
                            'proxy/API readiness timeout: '
                            + '\n'.join(docker('logs', name) for name in names)
                        )
                    time.sleep(0.2)
                assert client.get('/').status_code == 200
                assert client.get('/docs').status_code == 200
                schema = client.get('/openapi.json').json()
                assert '/api/v1/session' in schema['paths']
                assert not any('/api/api/' in path for path in schema['paths'])
                assert client.get('/api/api/v1/session').status_code == 404
                origin = f'http://localhost:{edge_port}'
                response = client.post(
                    '/api/v1/session',
                    headers={'Origin': origin, 'X-Session-Bootstrap': '1'},
                    json={},
                )
                response.raise_for_status()
                assert 'no-store' in response.headers['cache-control']
                auth = {'Origin': origin, 'X-CSRF-Token': response.json()['csrf_token']}
                cid = client.post(
                    '/api/v1/conversations', headers=auth, json={}
                ).json()['id']
                assert (
                    client.post(
                        '/api/v1/conversations', headers={'Origin': origin}, json={}
                    ).status_code
                    == 403
                )
                preflight = client.options(
                    '/api/v1/conversations',
                    headers={
                        'Origin': 'https://gonzalomartinperez.com',
                        'Access-Control-Request-Method': 'POST',
                        'Access-Control-Request-Headers': 'x-csrf-token,content-type',
                    },
                )
                assert (
                    preflight.headers['access-control-allow-origin']
                    == 'https://gonzalomartinperez.com'
                )
                denied = client.options(
                    '/api/v1/conversations',
                    headers={
                        'Origin': 'https://evil.example',
                        'Access-Control-Request-Method': 'POST',
                    },
                )
                assert 'access-control-allow-origin' not in denied.headers
                timings = []
                started = time.monotonic()
                with client.stream(
                    'POST',
                    f'/api/v1/conversations/{cid}/messages/stream',
                    headers={**auth, 'Idempotency-Key': str(uuid4())},
                    json={'content': 'What is Filomena?'},
                ) as stream:
                    stream.raise_for_status()
                    run_id = stream.headers['x-run-id']
                    for line in stream.iter_lines():
                        if line.startswith('data: '):
                            event = json.loads(line[6:])
                            if event['type'] == 'message.delta':
                                timings.append(time.monotonic() - started)
                                if len(timings) == 2:
                                    break
                assert timings[1] - timings[0] >= 0.08, 'proxy buffered provider deltas'
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    state = client.get(f'/api/v1/runs/{run_id}').json()['state']
                    if state == 'interrupted':
                        break
                    time.sleep(0.1)
                assert state == 'interrupted', state
                client.delete('/api/v1/session', headers=auth).raise_for_status()
                print(
                    json.dumps(
                        {
                            'passed': True,
                            'frontend': 'committed image'
                            if web_image
                            else 'routing fixture (not frontend acceptance)',
                            'paths_preserved': True,
                            'portfolio_cors': True,
                            'delta_gap_ms': round((timings[1] - timings[0]) * 1000, 1),
                            'disconnect_state': state,
                        },
                        indent=2,
                    )
                )
        finally:
            for name in reversed(names):
                docker('rm', '-f', name)


if __name__ == '__main__':
    main()
