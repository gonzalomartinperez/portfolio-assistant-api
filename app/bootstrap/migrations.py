"""Compose SQL and checkpoint migration work with operator configuration."""

from functools import partial

from app.adapters.postgres.db import connect
from app.adapters.postgres.migrations import migrate
from app.bootstrap.config import settings


def main() -> None:
    config = settings()
    migrate(partial(connect, config.database_url), config.database_url)
