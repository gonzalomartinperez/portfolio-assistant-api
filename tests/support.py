"""Real adapter composition for compatibility and retrieval evaluations."""

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from neo4j import GraphDatabase

from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.bootstrap.config import settings
from app.bootstrap.maintenance import connect

ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FixedClock:
    """Deterministic Clock; `advance` moves it forward explicitly."""

    def __init__(self, current: datetime = FIXED_NOW) -> None:
        if current.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self.current = current.astimezone(UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


def retrieve(question, locale="en", *, strategy="hybrid"):
    config = settings()
    with GraphDatabase.driver(
        config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
    ) as graph:
        sources = asyncio.run(
            PublicRetrieval(KnowledgeIndex(connect, graph), strategy).search(question, locale)
        )
    rows = [{**asdict(s), "title": s.title} for s in sources]
    return rows, [sources[0].commit_sha] if sources else []
