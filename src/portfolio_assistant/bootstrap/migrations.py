"""Compose SQL and checkpoint migration work with operator configuration."""

from functools import partial

from portfolio_assistant.adapters.postgres.db import connect
from portfolio_assistant.adapters.postgres.migrations import migrate
from portfolio_assistant.bootstrap.config import settings


def main() -> None:
    config = settings()
    migrate(partial(connect, config.database_url), config.database_url)
