import hashlib
from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver

from app.bootstrap.config import settings
from app.infrastructure.db import connect


def validate_history(migrations: list[Path], applied: dict[str, str]) -> None:
    names = [path.name for path in migrations]
    if names != sorted(set(names)) or len({name[:3] for name in names}) != len(names):
        raise RuntimeError('migration order or version collision')
    if any(name not in names for name in applied):
        raise RuntimeError('applied migration is missing from checkout')
    if set(names[: len(applied)]) != set(applied):
        raise RuntimeError('applied migrations are not an ordered prefix')
    for path in migrations:
        if (
            path.name in applied
            and hashlib.sha256(path.read_bytes()).hexdigest() != applied[path.name]
        ):
            raise RuntimeError(f'migration checksum changed: {path.name}')


def main():
    migrations = sorted(
        (Path(__file__).parents[2] / 'migrations').glob('[0-9][0-9][0-9]_*.sql')
    )
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(472021)')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())'
        )
        applied = {
            row['version']: row['sha256']
            for row in conn.execute('SELECT version,sha256 FROM schema_migrations')
        }
        validate_history(migrations, applied)
        for path in migrations:
            script = path.read_text()
            checksum = hashlib.sha256(script.encode()).hexdigest()
            if path.name in applied:
                if applied[path.name] != checksum:
                    raise RuntimeError(f'migration checksum changed: {path.name}')
                continue
            conn.execute(script)
            conn.execute(
                'INSERT INTO schema_migrations(version,sha256) VALUES (%s,%s)',
                (path.name, checksum),
            )
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        checkpointer.setup()


if __name__ == '__main__':
    main()


def check_schema(connection) -> None:
    """Refuse readiness when this checkout's full migration history is not installed."""
    paths = sorted(
        (Path(__file__).parents[2] / 'migrations').glob('[0-9][0-9][0-9]_*.sql')
    )
    with connection() as conn:
        applied = {
            row['version']: row['sha256']
            for row in conn.execute('SELECT version,sha256 FROM schema_migrations')
        }
    validate_history(paths, applied)
    if len(applied) != len(paths):
        raise RuntimeError('pending migrations')
