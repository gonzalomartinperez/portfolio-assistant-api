"""Exercise both applications and independent recovery on owned fixture databases.

The caller supplies an explicit backoffice source checkout. No production URLs,
provider calls, inherited application environment or external OAuth are accepted.
"""

import argparse
import hashlib
import json
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.adapters.postgres import migrations
from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from scripts.project_postgres_fixture import (
    LABEL,
    ProjectPostgres,
    docker,
    project_fixture,
    remove_owned,
)


class ImageConfiguration(BaseModel):
    user: str = Field(alias='User')
    labels: dict[str, str] = Field(alias='Labels')


class FixtureImage(BaseModel):
    identity: str = Field(alias='Id', pattern=r'^sha256:[a-f0-9]{64}$')
    configuration: ImageConfiguration = Field(alias='Config')


def verify_image(target: ProjectPostgres, image: str) -> dict[str, object]:
    if not re.fullmatch(r'portfolio-backoffice:[a-zA-Z0-9_.-]+', image):
        raise ValueError('expected an explicitly built local backoffice image')
    target.port()
    metadata = FixtureImage.model_validate_json(
        docker('image', 'inspect', '--format', '{{json .}}', image)
    )
    if (
        metadata.configuration.user != '65532:65532'
        or metadata.configuration.labels.get('org.opencontainers.image.source')
        != 'https://github.com/gonzalomartinperez/portfolio-backoffice'
    ):
        raise ValueError('backoffice image provenance or non-root identity is invalid')
    network = 'portfolio-project-pg-' + target.fixture[:12]
    with ExitStack() as cleanup:
        directory = Path(cleanup.enter_context(tempfile.TemporaryDirectory()))
        common = {
            'BACKOFFICE_ORIGIN': 'https://iam.fixture.invalid',
            'BETTER_AUTH_SECRET': 'disposable-fixture-auth-secret-32-characters',
            'BACKOFFICE_OWNER_EMAIL': 'owner@example.invalid',
            'GOOGLE_CLIENT_ID': 'fixture',
            'GOOGLE_CLIENT_SECRET': 'fixture',
            'GITHUB_CLIENT_ID': 'fixture',
            'GITHUB_CLIENT_SECRET': 'fixture',
        }

        def create(name: str, role: str, *command: str, publish: bool = False) -> None:
            environment = directory / (name + '.env')
            environment.touch(mode=0o600)
            uri = target.connection_uri(role).replace(
                '@127.0.0.1:' + str(target.port()), '@' + network + ':5432'
            )
            environment.write_text(
                '\n'.join(
                    key + '=' + value
                    for key, value in {**common, 'BACKOFFICE_DATABASE_URL': uri}.items()
                )
                + '\n'
            )
            cleanup.callback(remove_owned, 'container', name, target.fixture)
            publication = ('--publish', '127.0.0.1::3000') if publish else ()
            docker(
                'create',
                '--name',
                name,
                '--network',
                network,
                '--label',
                LABEL + '=' + target.fixture,
                '--env-file',
                str(environment),
                '--read-only',
                '--cap-drop',
                'ALL',
                '--security-opt',
                'no-new-privileges',
                '--memory',
                '512m',
                '--memory-swap',
                '512m',
                '--cpus',
                '0.75',
                '--pids-limit',
                '128',
                '--tmpfs',
                '/tmp:uid=65532,gid=65532,mode=0700,size=32m',
                '--tmpfs',
                '/app/.next/cache:uid=65532,gid=65532,mode=0700,size=32m',
                *publication,
                image,
                *command,
            )

        for attempt in range(2):
            name = (
                'portfolio-project-migration-'
                + target.fixture[:12]
                + '-'
                + str(attempt)
            )
            create(
                name,
                'portfolio_iam_migrator',
                'node',
                'scripts/auth-migrate.ts',
                '--project-grants',
            )
            docker('start', '--attach', name)
            if (
                docker('inspect', '--format', '{{.State.ExitCode}}', name).strip()
                != b'0'
            ):
                raise ValueError('exact backoffice image IAM migration failed')
        name = 'portfolio-project-bo-' + target.fixture[:12]
        create(name, 'portfolio_iam_runtime', publish=True)
        docker('start', name)
        port = (
            docker(
                'inspect',
                '--format',
                '{{(index (index .NetworkSettings.Ports "3000/tcp") 0).HostPort}}',
                name,
            )
            .decode()
            .strip()
        )
        if not port.isdecimal() or not 1024 <= int(port) <= 65535:
            raise ValueError('backoffice fixture port is invalid')
        deadline = time.monotonic() + 30
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while True:
            try:
                with opener.open(
                    'http://127.0.0.1:' + port + '/api/ready', timeout=3
                ) as response:
                    assert response.status == 200
                    assert json.load(response) == {'status': 'ready'}
                    cache_control = response.headers['Cache-Control']
                    assert cache_control and 'no-store' in {
                        value.strip().lower() for value in cache_control.split(',')
                    }
                break
            except OSError, urllib.error.URLError:
                if time.monotonic() >= deadline:
                    raise ValueError(
                        'restricted backoffice image did not become ready'
                    ) from None
                time.sleep(0.2)
        return {
            'image_id': metadata.identity,
            'two_migrations_and_restricted_runtime_readiness': True,
            'readiness_cache_control': cache_control,
        }


def revision(directory: Path) -> dict[str, str | bool]:
    def git(*arguments: str) -> str:
        return subprocess.run(
            ['git', '-C', str(directory), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    return {
        'commit': git('rev-parse', 'HEAD'),
        'dirty': bool(git('status', '--porcelain')),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backoffice-path', required=True, type=Path)
    parser.add_argument('--postgres-image', required=True)
    parser.add_argument('--backoffice-image')
    parser.add_argument('--authorize-fixture', action='store_true')
    parser.add_argument(
        '--output', type=Path, default=Path('artifacts/project-databases.json')
    )
    arguments = parser.parse_args()
    if not arguments.authorize_fixture:
        parser.error('explicit owned-fixture authorization is required')
    root = Path(__file__).resolve().parents[1]
    backoffice = arguments.backoffice_path.resolve(strict=True)
    if (
        json.loads((backoffice / 'package.json').read_text()).get('name')
        != 'portfolio-backoffice'
    ):
        parser.error('expected the explicit portfolio-backoffice source checkout')
    node = shutil.which('node')
    if node is None:
        parser.error('Node.js 24 must be available on PATH')
    version = subprocess.run(
        [node, '--version'], check=True, capture_output=True, text=True, timeout=10
    ).stdout
    if not version.startswith('v24.'):
        parser.error('Node.js 24 must be available on PATH')
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket() as check:
        check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        check.bind(('127.0.0.1', 3972))
    with project_fixture(
        arguments.postgres_image, authorized=arguments.authorize_fixture
    ) as target:
        config = Settings(
            _env_file=None,
            database_url=target.connection_info('portfolio_api_migrator'),
            ai_provider='fixture',
            embeddings_provider='fixture',
            allow_paid_ai=False,
            langsmith_tracing=False,
            langsmith_tracing_v2=False,
            langchain_tracing=False,
            langchain_tracing_v2=False,
            otel_sdk_disabled=True,
            ops_read_token=None,
        )
        migrations.migrate(
            lambda: psycopg.connect(config.database_url, row_factory=dict_row),
            config.database_url,
        )
        migrations.migrate(
            lambda: psycopg.connect(config.database_url, row_factory=dict_row),
            config.database_url,
        )
        target.sql_as(
            'portfolio_api_migrator', (root / 'deploy/runtime-grants.sql').read_text()
        )
        target.sql_as(
            'portfolio_api_migrator',
            (root / 'deploy/knowledge-worker-grants.sql').read_text(),
        )
        runtime_config = config.model_copy(
            update={
                'database_url': target.connection_info('portfolio_api_runtime'),
                'neo4j_uri': 'bolt://127.0.0.1:1',
            }
        )
        with TestClient(
            create_app(runtime_config), client=('127.0.0.1', 50000)
        ) as client:
            session = client.post(
                '/api/v1/session',
                headers={'Origin': 'http://localhost:3000', 'X-Session-Bootstrap': '1'},
                json={},
            )
            assert session.status_code == 200
            headers = {
                'Origin': 'http://localhost:3000',
                'X-CSRF-Token': session.json()['csrf_token'],
            }
            conversation = client.post(
                '/api/v1/conversations', headers=headers, json={}
            )
            assert conversation.status_code == 200, conversation.status_code
            identity = conversation.json()['id']
            response = client.post(
                f'/api/v1/conversations/{identity}/messages/stream',
                headers={**headers, 'Idempotency-Key': str(uuid4())},
                json={'content': 'What information can you share?'},
            )
            assert (
                response.status_code == 200 and 'event: run.completed' in response.text
            )
            assert (
                len(
                    client.get(f'/api/v1/conversations/{identity}/messages').json()[
                        'items'
                    ]
                )
                == 2
            )

        environment = {
            'PATH': str(Path(node).parent) + ':/usr/local/bin:/usr/bin:/bin',
            'NODE_ENV': 'test',
            'NEXT_TELEMETRY_DISABLED': '1',
            'BACKOFFICE_DATABASE_URL': target.connection_uri('portfolio_iam_runtime'),
            'BACKOFFICE_MIGRATION_DATABASE_URL': target.connection_uri(
                'portfolio_iam_migrator'
            ),
            'PROJECT_FIXTURE_CONTAINER': target.identity,
            'PROJECT_FIXTURE_ID': target.fixture,
        }
        result = subprocess.run(
            [node, '--test', 'tests/integration/auth.test.ts'],
            check=False,
            cwd=backoffice,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = arguments.output.parent / 'project-iam-dual-test.log'
        output.write_text(result.stdout + result.stderr)
        output.chmod(0o600)
        if result.returncode:
            raise ValueError(
                'owned restricted IAM integration failed; inspect private synthetic fixture log'
            )
        image_result = (
            verify_image(target, arguments.backoffice_image)
            if arguments.backoffice_image
            else None
        )

        def fingerprint(role, tables, database_target=target):
            from psycopg import sql

            values = {}
            with psycopg.connect(database_target.connection_info(role)) as connection:
                for table in tables:
                    rows = connection.execute(
                        sql.SQL(
                            'SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text'
                        ).format(sql.Identifier(table))
                    ).fetchall()
                    values[table] = {
                        'rows': len(rows),
                        'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                    }
            return values

        api_tables = [
            'sessions',
            'conversations',
            'messages',
            'runs',
            'spend_ledger',
            'schema_migrations',
            'checkpoints',
            'checkpoint_blobs',
            'checkpoint_writes',
            'product_event_dedupe',
            'product_event_counts',
            'product_daily_counts',
            'product_interaction_counts',
            'product_collection_status',
        ]
        iam_tables = [
            'user',
            'session',
            'account',
            'verification',
            'rateLimit',
            'backoffice_member',
            'backoffice_invitation',
            'backoffice_access_audit',
        ]
        api_before = fingerprint('portfolio_api_migrator', api_tables)
        iam_before = fingerprint('portfolio_iam_migrator', iam_tables)
        iam_dump = target.dump('portfolio_iam')
        api_dump = target.dump('portfolio_assistant')
        with psycopg.connect(
            target.connection_info('portfolio_api_runtime')
        ) as held_api:
            assert held_api.execute('SELECT 1').fetchone() == (1,)
            target.restore('portfolio_iam', iam_dump)
            assert held_api.execute('SELECT 1').fetchone() == (1,)
        assert api_before == fingerprint('portfolio_api_migrator', api_tables)
        assert iam_before == fingerprint('portfolio_iam_migrator', iam_tables)
        with psycopg.connect(
            target.connection_info('portfolio_iam_migrator')
        ) as connection:
            connection.execute(
                (backoffice / 'migrations/runtime-grants.sql').read_text()
            )
        with psycopg.connect(
            target.connection_info('portfolio_iam_runtime')
        ) as held_iam:
            assert held_iam.execute('SELECT count(*) FROM "user"').fetchone()[0] > 0
            target.restore('portfolio_assistant', api_dump)
            assert held_iam.execute('SELECT count(*) FROM "user"').fetchone()[0] > 0
        target.sql_as(
            'portfolio_api_migrator', (root / 'deploy/runtime-grants.sql').read_text()
        )
        target.sql_as(
            'portfolio_api_migrator',
            (root / 'deploy/knowledge-worker-grants.sql').read_text(),
        )
        assert api_before == fingerprint('portfolio_api_migrator', api_tables)
        assert iam_before == fingerprint('portfolio_iam_migrator', iam_tables)
        target.restart()
        assert api_before == fingerprint('portfolio_api_migrator', api_tables)
        assert iam_before == fingerprint('portfolio_iam_migrator', iam_tables)
        with project_fixture(arguments.postgres_image, authorized=True) as replacement:
            replacement.restore('portfolio_assistant', api_dump)
            replacement.restore('portfolio_iam', iam_dump)
            replacement.sql_as(
                'portfolio_api_migrator',
                (root / 'deploy/runtime-grants.sql').read_text(),
            )
            replacement.sql_as(
                'portfolio_api_migrator',
                (root / 'deploy/knowledge-worker-grants.sql').read_text(),
            )
            replacement.sql_as(
                'portfolio_iam_migrator',
                (backoffice / 'migrations/runtime-grants.sql').read_text(),
            )
            assert api_before == fingerprint(
                'portfolio_api_migrator', api_tables, replacement
            )
            assert iam_before == fingerprint(
                'portfolio_iam_migrator', iam_tables, replacement
            )
            with psycopg.connect(
                replacement.connection_info('portfolio_api_runtime')
            ) as restored_api:
                assert restored_api.execute(
                    'SELECT count(*) FROM messages'
                ).fetchone() == (2,)
            with psycopg.connect(
                replacement.connection_info('portfolio_iam_runtime')
            ) as restored_iam:
                assert (
                    restored_iam.execute('SELECT count(*) FROM "user"').fetchone()[0]
                    > 0
                )
        receipt = {
            'both_actual_migration_commands': True,
            'restricted_fake_oauth_suite': True,
            'api_unseeded_fixture_run_history_checkpoint': True,
            'independent_restores_preserve_other_database_and_live_connection': True,
            'restart_preserves_both_databases': True,
            'fresh_cluster_restore_reapplies_roles_and_exact_runtime_grants': True,
            'api_snapshot': api_before,
            'iam_snapshot': iam_before,
            'archive_bytes': {'api': len(api_dump), 'iam': len(iam_dump)},
            'backoffice_image': image_result,
            'fixture': target.snapshot(),
            'source': {'api': revision(root), 'backoffice': revision(backoffice)},
            'scope': 'local fixture model/no corpus; no production acceptance',
        }
        arguments.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(
            json.dumps(
                {
                    key: value
                    for key, value in receipt.items()
                    if key not in ('api_snapshot', 'iam_snapshot')
                }
            )
        )


if __name__ == '__main__':
    main()
