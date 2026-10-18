"""Real application migrations and layered permissions on a fresh project engine."""

import os
import time
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import PoolTimeout

from app.adapters.postgres import migrations
from app.adapters.postgres.db import pool
from app.bootstrap.config import Settings
from scripts.project_postgres_fixture import ROLES, project_fixture

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires an owned local database image',
    ),
]


def rejects_startup(target, connection_info, state):
    cursor = len(target.error_states())
    with pytest.raises(psycopg.OperationalError) as rejected:
        psycopg.connect(connection_info)
    assert rejected.value.sqlstate in (None, state)
    deadline = time.monotonic() + 5
    while state not in target.error_states()[cursor:]:
        if time.monotonic() >= deadline:
            pytest.fail(
                'owned server did not report expected startup SQLSTATE: ' + state
            )
        time.sleep(0.05)


def test_project_database_bootstrap_api_migrations_and_permission_boundaries(
    monkeypatch,
):
    image = os.getenv('PROJECT_POSTGRES_IMAGE', 'portfolio-assistant-postgres:18.6')
    with project_fixture(image, authorized=True) as target:
        target.bootstrap()
        configuration = Settings(
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
            lambda: psycopg.connect(configuration.database_url, row_factory=dict_row),
            configuration.database_url,
        )
        migrations.migrate(
            lambda: psycopg.connect(configuration.database_url, row_factory=dict_row),
            configuration.database_url,
        )
        target.sql_as(
            'portfolio_api_migrator', Path('deploy/runtime-grants.sql').read_text()
        )
        target.sql_as(
            'portfolio_api_migrator',
            Path('deploy/knowledge-worker-grants.sql').read_text(),
        )
        for role, own in ROLES.items():
            other = (
                'portfolio_iam'
                if own == 'portfolio_assistant'
                else 'portfolio_assistant'
            )
            with psycopg.connect(target.connection_info(role)) as connection:
                assert (
                    connection.execute(
                        'SELECT rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user'
                    ).fetchone()
                    == (False,) * 6
                )
                assert connection.execute(
                    "SELECT has_database_privilege(current_user,%s,'CONNECT'),has_database_privilege(current_user,'postgres','CONNECT'),has_database_privilege(current_user,'template1','CONNECT')",
                    (other,),
                ).fetchone() == (False, False, False)
            rejects_startup(target, target.connection_info(role, other), '28000')
            rejects_startup(
                target,
                make_conninfo(
                    target.connection_info(role), password='synthetic-invalid-password'
                ),
                '28P01',
            )
        target.sql_as(
            'portfolio_api_migrator',
            'CREATE FUNCTION public.private_default() RETURNS integer LANGUAGE sql AS $$ SELECT 42 $$',
        )
        for query in (
            'CREATE TABLE public.forbidden(id int)',
            'CREATE TEMP TABLE forbidden(id int)',
            'ALTER TABLE sessions ADD COLUMN forbidden integer',
            'DROP TABLE sessions',
            'SELECT public.private_default()',
            'DELETE FROM chunks',
            'SET ROLE portfolio_api_migrator',
            'SET ROLE portfolio_iam_runtime',
            'SET ROLE assistant_runtime',
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                target.sql_as('portfolio_api_runtime', query)
        for query in (
            'SELECT * FROM sessions',
            'DELETE FROM public_embedding_cache',
            'SET ROLE portfolio_api_runtime',
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                target.sql_as('portfolio_api_worker', query)
        for table in (
            'sessions',
            'messages',
            'runs',
            'checkpoints',
            'checkpoint_blobs',
            'checkpoint_writes',
            'schema_migrations',
        ):
            target.sql_as(
                'portfolio_api_runtime', 'SELECT * FROM ' + table + ' LIMIT 1'
            )
        with pool(target.connection_info('portfolio_api_runtime')) as database:
            held = [database.getconn() for _ in range(8)]
            try:
                with pytest.raises(PoolTimeout):
                    database.getconn(timeout=0.05)
            finally:
                for connection in held:
                    database.putconn(connection)
            with database.connection() as connection:
                assert connection.execute('SELECT 1').fetchone() == {'?column?': 1}
