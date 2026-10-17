"""Small storage capability for bounded anonymous product counts."""

from typing import Literal, Protocol

from app.domain.analytics import ProductEvent


class ProductAnalyticsPort(Protocol):
    def record(
        self, event: ProductEvent
    ) -> Literal['accepted', 'duplicate', 'limited']: ...


def accept_event(port: ProductAnalyticsPort, event: ProductEvent) -> None:
    from app.domain.errors import RejectedError

    if port.record(event) == 'limited':
        raise RejectedError('analytics_rate_limited', 429)
