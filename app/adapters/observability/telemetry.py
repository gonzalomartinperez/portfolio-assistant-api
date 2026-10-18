"""Manual private OTLP export; only allowlisted operational scalars leave the API."""

import logging
import os
import secrets
from contextvars import ContextVar

import requests
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.application.observability import Execution

trace_override: ContextVar[int | None] = ContextVar(
    'operational_trace_id', default=None
)


class OperationalIDs(IdGenerator):
    def generate_span_id(self) -> int:
        return secrets.randbits(64) or 1

    def generate_trace_id(self) -> int:
        return trace_override.get() or secrets.randbits(128) or 1


class SafeTelemetryLog(logging.Formatter):
    def format(self, record):
        return (
            '{"operation":"telemetry_export","status":"diagnostic","level":"'
            + record.levelname.lower()
            + '"}'
        )


class PrivateSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs['allow_redirects'] = False
        return super().request(method, url, **kwargs)


class PrivateTelemetry:
    def __init__(self, endpoint: str, revision: str, sample_ratio: float):
        # Vendor environment hooks can inject headers, credentials or extensions.
        if any(
            key.startswith('OTEL_')
            and key not in ('OTEL_SDK_DISABLED', 'OTEL_PRIVATE_ENDPOINT')
            for key in os.environ
        ):
            raise ValueError('unsupported_telemetry_environment')
        resource = Resource(
            {'service.name': 'portfolio-assistant-api', 'service.version': revision}
        )
        handler = logging.StreamHandler()
        handler.setFormatter(SafeTelemetryLog())
        logger = logging.getLogger('opentelemetry')
        logger.handlers = [handler]
        logger.propagate = False
        session = PrivateSession()
        session.trust_env = False
        self.trace_session = session
        self.metric_session = PrivateSession()
        self.metric_session.trust_env = False
        self.traces = TracerProvider(
            resource=resource,
            sampler=TraceIdRatioBased(sample_ratio),
            id_generator=OperationalIDs(),
        )
        self.traces.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=endpoint.rstrip('/') + '/v1/traces',
                    headers={},
                    compression=Compression.NoCompression,
                    max_request_size=256000,
                    timeout=1,
                    session=session,
                ),
                max_queue_size=128,
                max_export_batch_size=16,
                schedule_delay_millis=1000,
                export_timeout_millis=1000,
            )
        )
        self.tracer = self.traces.get_tracer('assistant.operations')
        self.meters = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=endpoint.rstrip('/') + '/v1/metrics',
                        headers={},
                        compression=Compression.NoCompression,
                        max_request_size=256000,
                        timeout=1,
                        session=self.metric_session,
                    ),
                    export_interval_millis=15000,
                    export_timeout_millis=1000,
                )
            ],
        )
        meter = self.meters.get_meter('assistant.operations')
        self.executions = meter.create_counter(
            'assistant.executions', unit='{execution}'
        )
        self.duration = meter.create_histogram('assistant.execution.duration', unit='s')
        self.first_token = meter.create_histogram(
            'assistant.first_chunk.duration', unit='s'
        )

    def record(self, execution: Execution) -> bool:
        labels = {'outcome': execution.outcome}
        self.executions.add(1, labels)
        self.duration.record(execution.duration_ms / 1000, labels)
        if execution.first_token_ms is not None:
            self.first_token.record(execution.first_token_ms / 1000, labels)
        start = int(execution.started_at.timestamp() * 1000000000)
        end = start + int(execution.duration_ms * 1000000)
        token = trace_override.set(int(execution.trace_id, 16))
        try:
            root = self.tracer.start_span(
                'assistant.execution',
                context=Context(),
                attributes=labels,
                start_time=start,
            )
            sampled = root.is_recording()
            from opentelemetry.trace import set_span_in_context

            for stage in execution.stages:
                child_start = start + int(stage.start_offset_ms * 1000000)
                child = self.tracer.start_span(
                    'assistant.' + stage.name,
                    context=set_span_in_context(root),
                    start_time=child_start,
                )
                child.end(
                    end_time=min(end, child_start + int(stage.duration_ms * 1000000))
                )
            root.end(end_time=end)
            return sampled
        finally:
            trace_override.reset(token)

    def close(self) -> None:
        self.traces.force_flush(timeout_millis=1000)
        self.meters.shutdown(timeout_millis=1000)
        self.traces.shutdown()
        self.trace_session.close()
        self.metric_session.close()
