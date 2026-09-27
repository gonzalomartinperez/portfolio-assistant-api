import hashlib
from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver

from app.bootstrap.config import settings
from app.infrastructure.db import connect


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
