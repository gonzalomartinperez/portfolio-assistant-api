"""Explicit worker entry point; the API process never starts a scheduler implicitly."""

import asyncio
import signal
import tempfile
from pathlib import Path
from threading import Event

from app.application.knowledge_watch import watch
from app.bootstrap.config import settings
from app.bootstrap.logging import configure
from app.infrastructure.db import connect
from app.infrastructure.knowledge_watch import (
    PublicKnowledgePublisher,
    PublishedPortfolio,
    report,
)


async def run() -> None:
    configure()
    config = settings()
    stop = asyncio.Event()
    index_stop = Event()

    def stop_worker():
        index_stop.set()
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_worker)
    try:
        with (
            connect() as lock,
            tempfile.TemporaryDirectory(prefix='portfolio-watch-') as directory,
        ):
            lock.autocommit = True
            if not lock.execute(
                'SELECT pg_try_advisory_lock(472023) AS acquired'
            ).fetchone()['acquired']:
                raise RuntimeError('knowledge watcher is already running')
            repo = Path(directory)
            await watch(
                PublishedPortfolio(repo),
                PublicKnowledgePublisher(repo, index_stop),
                stop,
                config.knowledge_poll_seconds,
                report,
            )
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


if __name__ == '__main__':
    asyncio.run(run())
