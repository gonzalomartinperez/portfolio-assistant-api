"""Coalesce public revisions while one index job runs; no HTTP lifecycle coupling."""

import asyncio
from collections.abc import Callable
from typing import Protocol

from app.domain.errors import (
    BudgetExhaustedError,
    DependencyUnavailableError,
    ProviderUnavailableError,
)


class PublicSource(Protocol):
    async def latest(self) -> str:
        """Resolve only the approved published branch to an immutable revision."""
        ...


class KnowledgePublisher(Protocol):
    async def observe(self, revision: str) -> None:
        """Persist a successful freshness check independently of indexing."""
        ...

    async def publish(self, revision: str) -> bool:
        """Activate only if the observed revision still matches; false means superseded."""
        ...


async def watch(
    source: PublicSource,
    publisher: KnowledgePublisher,
    stop: asyncio.Event,
    interval: float,
    report: Callable[[str], None],
) -> None:
    job: asyncio.Task[bool] | None = None
    desired: str | None = None
    indexing: str | None = None
    published: str | None = None
    try:
        while not stop.is_set():
            try:
                revision = await source.latest()
                await publisher.observe(revision)
                desired = revision
            except DependencyUnavailableError:
                report('source_unavailable')
            if job is not None and job.done():
                try:
                    if job.result():
                        published = indexing
                        report('activated')
                    else:
                        report('superseded')
                except (
                    DependencyUnavailableError,
                    BudgetExhaustedError,
                    ProviderUnavailableError,
                ):
                    report('candidate_failed')
                job = None
            if job is None and desired is not None and desired != published:
                indexing = desired
                job = asyncio.create_task(publisher.publish(desired))
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                pass
    finally:
        if job is not None:
            # Do not abandon a transaction or close its source repo during shutdown.
            result = (await asyncio.gather(job, return_exceptions=True))[0]
            report(
                'activated'
                if result is True
                else 'superseded'
                if result is False
                else 'candidate_failed'
            )
