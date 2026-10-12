"""Authenticated server-to-server operational JSON and Prometheus exposition."""

import asyncio
import hmac
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

router = APIRouter(prefix='/internal/ops/v1', include_in_schema=False)
bearer = HTTPBearer(auto_error=False)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)

    @field_validator('observed_at', 'indexed_at', 'started_at', check_fields=False)
    @classmethod
    def timestamp(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError('timezone_required')
        return value


class KnowledgeView(StrictModel):
    state: Literal['fresh', 'updating', 'stale']
    source_commit: str = Field(pattern=r'^[a-f0-9]{40}$')
    corpus_version: str = Field(pattern=r'^[a-zA-Z0-9._-]{1,128}$')
    indexed_at: str = Field(max_length=40)


class ExecutionsView(StrictModel):
    total: int = Field(ge=0, le=10**12)
    completed: int = Field(ge=0, le=10**12)
    cancelled: int = Field(ge=0, le=10**12)
    failed: int = Field(ge=0, le=10**12)
    first_token_p50_ms: float | None = Field(ge=0, le=10**12)
    first_token_p95_ms: float | None = Field(ge=0, le=10**12)

    @model_validator(mode='after')
    def consistent_counts(self):
        if self.completed + self.cancelled + self.failed > self.total:
            raise ValueError('inconsistent_counts')
        return self


class UsageView(StrictModel):
    input_tokens: int = Field(ge=0, le=10**12)
    output_tokens: int = Field(ge=0, le=10**12)
    settled_usd: float = Field(ge=0, le=10**12)
    reserved_usd: float = Field(ge=0, le=10**12)
    budget_usd: float = Field(ge=0, le=10**12)
    pricing_revision: str = Field(pattern=r'^[a-zA-Z0-9._-]{1,128}$')


class StageView(StrictModel):
    name: Literal[
        'language', 'vector_retrieval', 'graph_retrieval', 'generation', 'finalization'
    ]
    duration_ms: float = Field(ge=0, le=10**12)


class TraceView(StrictModel):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    started_at: str = Field(max_length=40)
    outcome: Literal['completed', 'cancelled', 'failed']
    duration_ms: float = Field(ge=0, le=10**12)
    stages: list[StageView] = Field(max_length=16)


class OperationalSnapshot(StrictModel):
    schema_version: Literal[1]
    observed_at: str = Field(max_length=40)
    api_commit: str = Field(pattern=r'^[a-f0-9]{40}$')
    availability: Literal['ready', 'degraded', 'unavailable']
    knowledge: KnowledgeView
    executions: ExecutionsView
    usage: UsageView
    traces: list[TraceView] = Field(max_length=100)


def authorize(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> None:
    expected = request.app.state.config.ops_read_token
    if not expected:
        raise HTTPException(503, 'operations_unconfigured')
    if not credentials or not hmac.compare_digest(
        credentials.credentials.encode(), expected.encode()
    ):
        raise HTTPException(401, 'operations_unauthorized')


async def snapshot(request: Request) -> OperationalSnapshot:
    try:
        operations = request.app.state.operations
        async with asyncio.timeout(4):
            data = await asyncio.to_thread(operations.snapshot)
            await asyncio.to_thread(request.app.state.ready)
        return OperationalSnapshot.model_validate(data)
    except Exception:  # noqa: BLE001 - Never serialize dependency/validation details through an operational endpoint.
        raise HTTPException(503, 'operations_unavailable') from None


@router.get('/status', dependencies=[Depends(authorize)])
async def status(request: Request) -> OperationalSnapshot:
    return await snapshot(request)


@router.get('/metrics', dependencies=[Depends(authorize)])
async def metrics(request: Request) -> Response:
    data = await snapshot(request)
    registry = CollectorRegistry()
    executions = Gauge(
        'assistant_executions_window',
        'Observed executions in the rolling 30-day window.',
        ['outcome'],
        registry=registry,
    )
    for outcome in ('completed', 'cancelled', 'failed'):
        executions.labels(outcome).set(getattr(data.executions, outcome))
    for name, value in (
        ('settled', data.usage.settled_usd),
        ('reserved', data.usage.reserved_usd),
        ('budget', data.usage.budget_usd),
    ):
        Gauge(
            'assistant_usage_' + name + '_usd',
            'UTC-month configured USD estimate; not provider invoice.',
            registry=registry,
        ).set(value)
    for name, value in (
        ('p50', data.executions.first_token_p50_ms),
        ('p95', data.executions.first_token_p95_ms),
    ):
        if value is not None:
            Gauge(
                'assistant_first_chunk_' + name + '_seconds',
                'Server first fragment latency over 30 days.',
                registry=registry,
            ).set(value / 1000)
    Gauge(
        'assistant_operational_observations_dropped',
        'Observations lost to bounded buffering or storage/export errors.',
        registry=registry,
    ).set(request.app.state.observer.dropped)
    return Response(
        generate_latest(registry), media_type='text/plain; version=0.0.4; charset=utf-8'
    )
