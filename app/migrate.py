from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver

from .config import settings
from .db import connect


def main():
    with connect() as conn:
        conn.execute(Path(__file__).with_name('schema.sql').read_text())
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        checkpointer.setup()


if __name__ == '__main__':
    main()
