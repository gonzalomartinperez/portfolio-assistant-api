"""Approved Git source and database-backed synchronization worker."""

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from threading import Event

import psycopg
from neo4j.exceptions import Neo4jError
from openai import APIError

from app.domain.errors import DependencyUnavailableError
from app.infrastructure.db import connect
from app.infrastructure.indexing import git, sync

REMOTE = 'https://github.com/gonzalomartinperez/portfolio.git'


class PublishedPortfolio:
    def __init__(self, repo: Path):
        self.repo = repo
        git(repo, 'init', '-q', '--bare')
        git(repo, 'remote', 'add', 'origin', REMOTE)

    async def latest(self) -> str:
        def read():
            git(
                self.repo,
                '-c',
                'http.followRedirects=false',
                '-c',
                'protocol.allow=never',
                '-c',
                'protocol.https.allow=always',
                'fetch',
                '-q',
                '--depth=1',
                'origin',
                'main',
            )
            revision = git(self.repo, 'rev-parse', 'FETCH_HEAD').decode().strip()
            if not re.fullmatch(r'[0-9a-f]{40}', revision):
                raise ValueError('invalid source revision')
            return revision

        try:
            return await asyncio.to_thread(read)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise DependencyUnavailableError('source_unavailable') from error


class PublicKnowledgePublisher:
    def __init__(self, repo: Path, stop: Event | None = None):
        self.repo = repo
        self.stop = stop

    async def observe(self, revision: str) -> None:
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('invalid source revision')

        def save():
            with connect() as conn:
                conn.execute(
                    'INSERT INTO knowledge_watch(singleton,observed_commit,checked_at) VALUES (true,%s,now()) '
                    'ON CONFLICT(singleton) DO UPDATE SET observed_commit=excluded.observed_commit,checked_at=now()',
                    (revision,),
                )

        try:
            await asyncio.to_thread(save)
        except psycopg.Error as error:
            raise DependencyUnavailableError('storage_unavailable') from error

    async def publish(self, revision: str) -> bool:
        try:
            result = await asyncio.to_thread(
                sync, self.repo, revision, watched=True, stop=self.stop
            )
        except (
            OSError,
            subprocess.SubprocessError,
            ValueError,
            RuntimeError,
            psycopg.Error,
            Neo4jError,
            APIError,
        ) as error:
            raise DependencyUnavailableError('candidate_failed') from error
        return not result.get('superseded', False)


def report(status: str) -> None:
    logging.getLogger('portfolio_assistant').info(
        json.dumps({'operation': 'knowledge_watch', 'status': status})
    )
