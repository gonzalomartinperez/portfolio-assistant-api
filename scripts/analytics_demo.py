"""Serve disposable analytics over local TLS; never a production deployment stack."""

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from threading import Timer
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
import uvicorn
from psycopg.rows import dict_row

from app.adapters.postgres import migrations
from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from scripts.project_postgres_fixture import project_fixture


def site_origin(value: str) -> str:
    try:
        url = urlsplit(value)
        if (
            url.scheme != 'https'
            or url.hostname not in ('127.0.0.1', 'localhost')
            or not url.port
            or not 1024 <= url.port <= 65535
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(
            'demo site requires an explicit loopback HTTPS origin'
        ) from None
    return value


def require_port(port: int) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError('demo port must be unprivileged')
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    except OSError:
        raise ValueError(
            'demo port is occupied; no existing process will be stopped'
        ) from None


def private_environment(path: Path, values: dict[str, str]) -> None:
    if any(not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) for key in values) or any(
        '\n' in value or '\r' in value for value in values.values()
    ):
        raise ValueError('invalid demo environment value')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(''.join(key + '=' + value + '\n' for key, value in values.items()))


@contextmanager
def cleanup_signals() -> Iterator[None]:
    # Uvicorn replays SIGTERM after its own shutdown, before outer fixtures unwind.
    previous = signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-fixture', action='store_true')
    parser.add_argument('--postgres-image', required=True)
    parser.add_argument(
        '--site-origin', type=site_origin, default='https://127.0.0.1:3381'
    )
    parser.add_argument('--api-port', type=int, default=8317)
    parser.add_argument('--web-port', type=int, default=3317)
    parser.add_argument('--minutes', type=int, default=45)
    arguments = parser.parse_args()
    if not arguments.authorize_fixture or not 1 <= arguments.minutes <= 60:
        parser.error(
            'explicit fixture authorization and a 1–60 minute lifetime are required'
        )
    if arguments.api_port == arguments.web_port or int(
        urlsplit(arguments.site_origin).port or 0
    ) in (arguments.api_port, arguments.web_port):
        parser.error('site, API and backoffice must have distinct ports')
    require_port(arguments.api_port)
    require_port(arguments.web_port)
    openssl = shutil.which('openssl')
    if not openssl:
        parser.error('local OpenSSL is required for the disposable certificate')
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    directory = root / 'artifacts' / ('analytics-demo-' + uuid4().hex[:12])
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    with cleanup_signals(), ExitStack() as cleanup:
        private_paths = [
            directory / name
            for name in (
                'tls.key',
                'backoffice.env',
                'iam-migration.env',
                'sessions.json',
            )
        ]
        for path in private_paths:
            cleanup.callback(path.unlink, missing_ok=True)
        certificate, key = directory / 'tls.crt', private_paths[0]
        subprocess.run(
            [
                openssl,
                'req',
                '-x509',
                '-newkey',
                'rsa:2048',
                '-nodes',
                '-days',
                '1',
                '-keyout',
                str(key),
                '-out',
                str(certificate),
                '-subj',
                '/CN=portfolio.fixture.invalid',
                '-addext',
                'subjectAltName=IP:127.0.0.1,DNS:localhost',
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        key.chmod(0o600)
        target = cleanup.enter_context(
            project_fixture(arguments.postgres_image, authorized=True)
        )
        config = Settings(
            _env_file=None,
            database_url=target.connection_info('portfolio_api_migrator'),
            ai_provider='fixture',
            embeddings_provider='fixture',
            allow_paid_ai=False,
            neo4j_uri='bolt://127.0.0.1:1',
        )
        migrations.migrate(
            lambda: psycopg.connect(config.database_url, row_factory=dict_row),
            config.database_url,
        )
        target.sql_as(
            'portfolio_api_migrator', (root / 'deploy/runtime-grants.sql').read_text()
        )
        token = secrets.token_urlsafe(32)
        api = Settings(
            _env_file=None,
            database_url=target.connection_info('portfolio_api_runtime'),
            ai_provider='fixture',
            embeddings_provider='fixture',
            allow_paid_ai=False,
            neo4j_uri='bolt://127.0.0.1:1',
            allowed_origins=arguments.site_origin,
            secure_cookies=True,
            ops_read_token=token,
            ops_api_commit=revision,
            product_analytics_enabled=True,
            product_analytics_country_enabled=False,
        )
        api_origin = f'https://127.0.0.1:{arguments.api_port}'
        web_origin = f'http://127.0.0.1:{arguments.web_port}'
        environment = {
            'NODE_ENV': 'production',
            'NEXT_TELEMETRY_DISABLED': '1',
            'HOSTNAME': '127.0.0.1',
            'PORT': str(arguments.web_port),
            'BACKOFFICE_ORIGIN': web_origin,
            'BACKOFFICE_DATABASE_URL': target.connection_uri('portfolio_iam_runtime'),
            'BETTER_AUTH_SECRET': secrets.token_urlsafe(32),
            'BACKOFFICE_OWNER_EMAIL': 'owner@example.test',
            'GOOGLE_CLIENT_ID': 'fixture',
            'GOOGLE_CLIENT_SECRET': 'fixture',
            'GITHUB_CLIENT_ID': 'fixture',
            'GITHUB_CLIENT_SECRET': 'fixture',
            'OPERATIONS_API_ORIGIN': api_origin,
            'OPERATIONS_READ_TOKEN': token,
            'OPERATIONS_SOURCE_MODE': 'fixture',
            'PRODUCT_ANALYTICS_ENABLED': 'true',
            'FEEDBACK_OVERVIEW_ENABLED': 'false',
            'NODE_EXTRA_CA_CERTS': str(certificate),
            'PROJECT_FIXTURE_CONTAINER': target.identity,
            'PROJECT_FIXTURE_ID': target.fixture,
            'BACKOFFICE_FIXTURE_SESSION_FILE': str(directory / 'sessions.json'),
        }
        private_environment(directory / 'backoffice.env', environment)
        private_environment(
            directory / 'iam-migration.env',
            {
                **environment,
                'BACKOFFICE_DATABASE_URL': target.connection_uri(
                    'portfolio_iam_migrator'
                ),
            },
        )
        dirty = bool(
            subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        receipt = {
            'fixture': True,
            'api_commit': revision,
            'api_worktree_dirty': dirty,
            'api_origin': api_origin,
            'site_origin': arguments.site_origin,
            'backoffice_origin': web_origin,
            'purpose': 'analytics_http_and_disposable_iam',
            'country': 'unknown',
            'assistant_readiness': 'not_verified_no_neo4j',
            'paid_calls': 0,
        }
        (directory / 'demo.json').write_text(json.dumps(receipt, indent=2) + '\n')
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(api),
                host='127.0.0.1',
                port=arguments.api_port,
                ssl_certfile=str(certificate),
                ssl_keyfile=str(key),
                access_log=False,
                timeout_graceful_shutdown=15,
                proxy_headers=False,
            )
        )
        timer = Timer(
            arguments.minutes * 60, lambda: setattr(server, 'should_exit', True)
        )
        timer.daemon = True
        timer.start()
        cleanup.callback(timer.cancel)
        print(
            json.dumps(
                {
                    'fixture_directory': str(directory),
                    'scope': 'analytics_only_not_assistant_readiness',
                }
            ),
            flush=True,
        )
        server.run()


if __name__ == '__main__':
    main()
