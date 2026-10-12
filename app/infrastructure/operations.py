"""Private operational persistence and bounded asynchronous observation."""

import asyncio
import hashlib
import logging
import secrets
from dataclasses import asdict
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from app.application.observability import Execution


class PostgresOperations:
    def __init__(self, connection, config):
        self.connection = connection
        self.config = config

    def save(self, execution: Execution, sampled: bool) -> None:
        with self.connection() as conn:
            conn.execute('SET LOCAL statement_timeout=500')
            conn.execute('SET LOCAL lock_timeout=200')
            conn.execute(
                'INSERT INTO operational_executions(trace_id,started_at,outcome,duration_ms,first_token_ms,stages,error_code,sampled) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (
                    execution.trace_id,
                    execution.started_at,
                    execution.outcome,
                    execution.duration_ms,
                    execution.first_token_ms,
                    Jsonb([asdict(s) for s in execution.stages]),
                    execution.error_code,
                    sampled,
                ),
            )

    def snapshot(self) -> dict:
        with self.connection() as conn:
            conn.execute('SET LOCAL statement_timeout=2000')
            knowledge = conn.execute(
                "SELECT id,source_commit,created_at FROM knowledge_versions WHERE status='active'"
            ).fetchone()
            if not knowledge:
                raise RuntimeError('knowledge_unavailable')
            watch = conn.execute(
                'SELECT observed_commit,checked_at FROM knowledge_watch WHERE singleton'
            ).fetchone()
            age = (
                (datetime.now(UTC) - watch['checked_at']).total_seconds()
                if watch
                else None
            )
            state = (
                'stale'
                if age is None or age > self.config.knowledge_freshness_seconds
                else (
                    'fresh'
                    if watch['observed_commit'] == knowledge['source_commit']
                    else 'updating'
                )
            )
            counts = conn.execute(
                "SELECT count(*) AS total,count(*) FILTER (WHERE outcome='completed') AS completed,count(*) FILTER (WHERE outcome='cancelled') AS cancelled,count(*) FILTER (WHERE outcome='failed') AS failed,percentile_cont(0.5) WITHIN GROUP (ORDER BY first_token_ms) AS p50,percentile_cont(0.95) WITHIN GROUP (ORDER BY first_token_ms) AS p95 FROM operational_executions WHERE started_at>=now()-interval '30 days'"
            ).fetchone()
            usage = conn.execute(
                "SELECT coalesce(sum(input_tokens),0) AS input_tokens,coalesce(sum(output_tokens),0) AS output_tokens,coalesce(sum(actual_usd),0) AS settled,coalesce(sum(reserved_usd) FILTER (WHERE actual_usd IS NULL),0) AS reserved FROM spend_ledger WHERE created_at>=date_trunc('month',now(),'UTC')"
            ).fetchone()
            rows = conn.execute(
                "SELECT trace_id,started_at,outcome,duration_ms,stages FROM operational_executions WHERE sampled AND started_at>=now()-interval '7 days' ORDER BY started_at DESC LIMIT 100"
            ).fetchall()
        return {
            'schema_version': 1,
            'observed_at': datetime.now(UTC).isoformat(),
            'api_commit': self.config.ops_api_commit,
            'availability': 'ready' if state == 'fresh' else 'degraded',
            'knowledge': {
                'state': state,
                'source_commit': knowledge['source_commit'],
                'corpus_version': knowledge['id'],
                'indexed_at': knowledge['created_at'].isoformat(),
            },
            'executions': {
                'total': counts['total'],
                'completed': counts['completed'],
                'cancelled': counts['cancelled'],
                'failed': counts['failed'],
                'first_token_p50_ms': counts['p50'],
                'first_token_p95_ms': counts['p95'],
            },
            'usage': {
                'input_tokens': int(usage['input_tokens']),
                'output_tokens': int(usage['output_tokens']),
                'settled_usd': float(usage['settled']),
                'reserved_usd': float(usage['reserved']),
                'budget_usd': float(self.config.monthly_budget_usd),
                'pricing_revision': 'configured-'
                + hashlib.sha256(
                    f'{self.config.input_usd_per_million}:{self.config.output_usd_per_million}:{self.config.embedding_usd_per_million}'.encode()
                ).hexdigest()[:16],
            },
            'traces': [
                {
                    'id': r['trace_id'],
                    'started_at': r['started_at'].isoformat(),
                    'outcome': r['outcome'],
                    'duration_ms': r['duration_ms'],
                    'stages': [
                        {'name': s['name'], 'duration_ms': s['duration_ms']}
                        for s in r['stages'][:16]
                    ],
                }
                for r in rows
            ],
        }


class OperationalObserver:
    def __init__(self, store, *, sample_ratio: float, exporter=None):
        self.store = store
        self.sample_ratio = sample_ratio
        self.exporter = exporter
        self.queue: asyncio.Queue[Execution] = asyncio.Queue(maxsize=128)
        self.dropped = 0
        self.worker: asyncio.Task[None] | None = None
        self.closed = False

    def start(self) -> None:
        if self.worker is not None:
            raise RuntimeError('observer_already_started')
        self.worker = asyncio.create_task(self._consume())

    def record(self, execution: Execution) -> None:
        if self.closed:
            self.dropped += 1
            return
        try:
            self.queue.put_nowait(execution)
        except asyncio.QueueFull:
            self.dropped += 1

    async def _consume(self) -> None:
        while True:
            execution = await self.queue.get()
            try:
                sampled = secrets.randbelow(1000000) < int(self.sample_ratio * 1000000)
                if self.exporter:
                    try:
                        sampled = self.exporter.record(execution)
                    except Exception:  # noqa: BLE001 - Export is independent from durable accounting/observation.
                        self.dropped += 1
                write = asyncio.create_task(
                    asyncio.to_thread(self.store.save, execution, sampled)
                )
                try:
                    await asyncio.shield(write)
                except asyncio.CancelledError:
                    # The SQL adapter bounds the write; join it before the shared pool closes.
                    result = await asyncio.gather(write, return_exceptions=True)
                    if isinstance(result[0], BaseException):
                        self.dropped += 1
                    raise
            except Exception:  # noqa: BLE001 - Observational storage/export failures cannot interrupt generation or reveal payloads.
                self.dropped += 1
                logging.getLogger('portfolio_assistant').warning(
                    '{"operation":"observability","status":"write_failed"}'
                )
            finally:
                self.queue.task_done()

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            await asyncio.wait_for(self.queue.join(), timeout=2)
        except TimeoutError:
            self.dropped += self.queue.qsize()
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        if self.exporter:
            try:
                await asyncio.to_thread(self.exporter.close)
            except Exception:  # noqa: BLE001 - Export cleanup cannot prevent database/provider cleanup.
                self.dropped += 1
                logging.getLogger('portfolio_assistant').warning(
                    '{"operation":"observability","status":"shutdown_failed"}'
                )
