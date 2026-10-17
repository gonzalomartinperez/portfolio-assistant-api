"""Fresh, owned project database fixtures; never accept an external database URL."""

import os
import re
import secrets
import subprocess
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from scripts.evaluation_isolation import EvaluationContainer

SOURCE = 'https://github.com/gonzalomartinperez/portfolio-assistant-api'
LABEL = 'io.gmperez.portfolio-project-fixture'
ROLES = {
    'portfolio_api_migrator': 'portfolio_assistant',
    'portfolio_api_runtime': 'portfolio_assistant',
    'portfolio_api_worker': 'portfolio_assistant',
    'portfolio_iam_migrator': 'portfolio_iam',
    'portfolio_iam_runtime': 'portfolio_iam',
}


class FixtureCommandError(ValueError):
    """A bounded Docker/psql fixture command failed without exposing its output."""


def docker(
    *args: str, data: bytes | None = None, timeout: int = 60, combined: bool = False
) -> bytes:
    try:
        result = subprocess.run(
            ['docker', *args],
            input=data,
            capture_output=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr if combined else result.stdout
    except OSError, subprocess.SubprocessError:
        raise FixtureCommandError(
            'owned project fixture Docker operation failed'
        ) from None


def validate_container(
    container: EvaluationContainer, identity: str, fixture: str
) -> int:
    labels = container.config.labels or {}
    if (
        not re.fullmatch(r'[a-f0-9]{64}', identity)
        or container.identity != identity
        or labels.get(LABEL) != fixture
        or labels.get('org.opencontainers.image.source') != SOURCE
        or not container.state.running
        or not container.config.image.startswith('portfolio-assistant-postgres:')
    ):
        raise ValueError('project fixture container identity is not verified')
    ports = container.network.ports.get('5432/tcp') or []
    if (
        len(ports) != 1
        or ports[0].host_ip != '127.0.0.1'
        or not ports[0].host_port.isdecimal()
        or not 1024 <= int(ports[0].host_port) <= 65535
    ):
        raise ValueError(
            'project fixture requires one private loopback PostgreSQL port'
        )
    return int(ports[0].host_port)


def remove_owned(kind: str, name: str, fixture: str) -> None:
    listing = ('--all',) if kind == 'container' else ()
    column = '{{.Names}}' if kind == 'container' else '{{.Name}}'
    names = (
        docker(kind, 'ls', *listing, '--filter', 'name=' + name, '--format', column)
        .decode()
        .splitlines()
    )
    if name not in names:
        return
    field = '.Labels' if kind != 'container' else '.Config.Labels'
    labels = TypeAdapter(dict[str, str]).validate_json(
        docker(kind, 'inspect', '--format', '{{json ' + field + '}}', name)
    )
    if labels.get(LABEL) != fixture:
        raise ValueError('refusing to remove an unverified fixture resource')
    if (
        kind == 'container'
        and docker(kind, 'inspect', '--format', '{{.State.Running}}', name).strip()
        == b'true'
    ):
        docker('stop', '--time', '30', name)
    docker(kind, 'rm', name)


class ProjectPostgres:
    def __init__(self, identity: str, fixture: str, passwords: dict[str, str]):
        self.identity = identity
        self.fixture = fixture
        self._passwords = passwords

    def port(self) -> int:
        metadata = EvaluationContainer.model_validate_json(
            docker('container', 'inspect', '--format', '{{json .}}', self.identity)
        )
        return validate_container(metadata, self.identity, self.fixture)

    def connection_info(self, role: str, database: str | None = None) -> str:
        if role not in ROLES:
            raise ValueError('unsupported project fixture identity')
        return make_conninfo(
            host='127.0.0.1',
            port=self.port(),
            user=role,
            password=self._passwords[role],
            dbname=database or ROLES[role],
            connect_timeout=3,
            options='-c statement_timeout=5000 -c lock_timeout=3000',
        )

    def connection_uri(self, role: str) -> str:
        if role not in ROLES:
            raise ValueError('unsupported project fixture identity')
        return (
            'postgresql://'
            + quote(role, safe='')
            + ':'
            + quote(self._passwords[role], safe='')
            + '@127.0.0.1:'
            + str(self.port())
            + '/'
            + ROLES[role]
        )

    def owner_sql(self, query: str) -> bytes:
        self.port()
        # The provisioning secret stays in the owned container environment, not argv.
        return docker(
            'exec',
            '-i',
            self.identity,
            'sh',
            '-c',
            'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -X --no-password '
            '-U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -At',
            data=query.encode(),
        )

    def bootstrap(self) -> None:
        self.owner_sql(
            '\\i /usr/local/share/portfolio-postgres/project-postgres-bootstrap.psql\n'
        )

    def provision_fixture_passwords(self) -> None:
        for role, password in self._passwords.items():
            self.owner_sql(
                sql.SQL('ALTER ROLE {} PASSWORD {}')
                .format(sql.Identifier(role), sql.Literal(password))
                .as_string()
            )

    def sql_as(self, role: str, query: str) -> None:
        with psycopg.connect(self.connection_info(role)) as connection:
            connection.execute(query)

    def restart(self) -> None:
        self.port()
        docker('restart', '--time', '30', self.identity)
        deadline = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(
                    self.connection_info('portfolio_api_runtime')
                ) as connection:
                    connection.execute('SELECT 1')
                return
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise ValueError(
                        'owned project database did not recover after restart'
                    ) from None
                time.sleep(0.1)

    def dump(self, database: str) -> bytes:
        if database not in set(ROLES.values()):
            raise ValueError('only owned application databases may be backed up')
        self.port()
        return docker(
            'exec',
            self.identity,
            'sh',
            '-c',
            'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump --format=custom '
            '--no-privileges -U "$POSTGRES_USER" -d "$1"',
            'fixture-dump',
            database,
        )

    def restore(self, database: str, archive: bytes) -> None:
        owners = {
            'portfolio_assistant': 'portfolio_api_migrator',
            'portfolio_iam': 'portfolio_iam_migrator',
        }
        if database not in owners or not archive.startswith(b'PGDMP'):
            raise ValueError('only owned application custom archives may be restored')
        self.owner_sql(
            sql.SQL('DROP DATABASE {} WITH (FORCE)')
            .format(sql.Identifier(database))
            .as_string()
        )
        self.owner_sql(
            sql.SQL('CREATE DATABASE {} OWNER {}')
            .format(sql.Identifier(database), sql.Identifier(owners[database]))
            .as_string()
        )
        self.bootstrap()
        docker(
            'exec',
            '-i',
            self.identity,
            'sh',
            '-c',
            'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore --exit-on-error '
            '--clean --if-exists -U "$POSTGRES_USER" -d "$1"',
            'fixture-restore',
            database,
            data=archive,
        )

    def error_states(self) -> list[str]:
        self.port()
        # libpq can omit startup SQLSTATE; only codes leave this owned log boundary.
        raw = docker('logs', self.identity, combined=True)
        return [
            value.decode('ascii')
            for value in re.findall(rb'(?:FATAL|ERROR):\s+([0-9A-Z]{5}):', raw)
        ]

    def snapshot(self) -> dict[str, object]:
        return {
            'fixture_id': self.fixture,
            'container_id': self.identity,
            'loopback_port': self.port(),
            'databases': sorted(set(ROLES.values())),
        }


@contextmanager
def project_fixture(image: str, *, authorized: bool = False):
    if not authorized:
        raise ValueError('explicit owned-fixture authorization is required')
    if (
        os.environ.get('AI_PROVIDER', 'fixture') != 'fixture'
        or os.environ.get('EMBEDDINGS_PROVIDER', 'fixture') != 'fixture'
        or os.environ.get('ALLOW_PAID_AI', 'false') != 'false'
    ):
        raise ValueError(
            'project database verification requires fixture-only configuration'
        )
    if any(name.startswith('OPENAI_') for name in os.environ):
        raise ValueError(
            'project fixture requires an environment without provider credentials or overrides'
        )
    if not re.fullmatch(r'portfolio-assistant-postgres:[a-zA-Z0-9_.-]+', image):
        raise ValueError('use a local application-owned PostgreSQL fixture image')
    labels = TypeAdapter(dict[str, str]).validate_json(
        docker('image', 'inspect', '--format', '{{json .Config.Labels}}', image)
    )
    if labels.get('org.opencontainers.image.source') != SOURCE:
        raise ValueError('PostgreSQL fixture image provenance is not verified')
    fixture = uuid4().hex
    name = 'portfolio-project-pg-' + fixture[:12]
    passwords = {role: secrets.token_urlsafe(32) for role in ROLES}
    with ExitStack() as cleanup:
        directory = Path(
            cleanup.enter_context(tempfile.TemporaryDirectory(prefix=name))
        )
        environment = directory / 'bootstrap.env'
        environment.write_text(
            'POSTGRES_USER=portfolio_bootstrap\nPOSTGRES_DB=postgres\n'
            'POSTGRES_PASSWORD=' + secrets.token_urlsafe(32) + '\n'
        )
        environment.chmod(0o600)
        for kind in ('network', 'volume'):
            # A private bridge permits the host's loopback test clients; production has no host port.
            cleanup.callback(remove_owned, kind, name, fixture)
            docker(kind, 'create', '--label', LABEL + '=' + fixture, name)
        cleanup.callback(remove_owned, 'container', name, fixture)
        identity = (
            docker(
                'create',
                '--name',
                name,
                '--network',
                name,
                '--label',
                LABEL + '=' + fixture,
                '--user',
                '999:999',
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
                '/tmp:rw,nosuid,nodev,size=16m',
                '--tmpfs',
                '/var/run/postgresql:rw,nosuid,nodev,uid=999,gid=999,mode=3775,size=8m',
                '--mount',
                'type=volume,src=' + name + ',dst=/var/lib/postgresql',
                '--publish',
                '127.0.0.1::5432',
                '--log-driver',
                'local',
                '--log-opt',
                'max-size=10m',
                '--log-opt',
                'max-file=3',
                image,
                'postgres',
                '-c',
                'shared_buffers=128MB',
                '-c',
                'work_mem=4MB',
                '-c',
                'max_connections=50',
                '-c',
                'log_error_verbosity=verbose',
                '-c',
                'hba_file=/usr/local/share/portfolio-postgres/project-pg_hba.conf',
            )
            .decode()
            .strip()
        )
        docker('start', identity)
        target = ProjectPostgres(identity, fixture, passwords)
        target.port()
        for _ in range(60):
            try:
                if target.owner_sql('SELECT 1').strip() == b'1':
                    break
            except FixtureCommandError:
                pass
            time.sleep(0.5)
        else:
            raise ValueError('owned PostgreSQL fixture did not become ready')
        target.bootstrap()
        target.provision_fixture_passwords()
        yield target
