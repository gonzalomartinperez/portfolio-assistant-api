"""Exercise both applications and independent recovery on owned fixture databases.

The caller supplies an explicit backoffice source checkout. No production URLs,
provider calls, inherited application environment or external OAuth are accepted.
"""

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.infrastructure import migrations
from scripts.project_postgres_fixture import project_fixture


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
        with (
            patch.object(migrations, 'settings', lambda: config),
            patch.object(
                migrations,
                'connect',
                lambda: psycopg.connect(config.database_url, row_factory=dict_row),
            ),
        ):
            migrations.main()
            migrations.main()
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
