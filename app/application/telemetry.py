"""Request correlation propagated across async tasks and delegated thread work."""

from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar('request_id', default=None)
