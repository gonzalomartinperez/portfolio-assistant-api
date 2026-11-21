"""Small storage capability for bounded anonymous product counts."""

from typing import Literal, Protocol

from portfolio_assistant.domain.analytics import ProductEvent
from portfolio_assistant.domain.analytics_interactions import PublicInteraction
from portfolio_assistant.domain.analytics_report import AnalyticsQuery, ProductReport


class ProductAnalyticsPort(Protocol):
    def record(
        self, event: ProductEvent | PublicInteraction, country: str = "unknown"
    ) -> Literal["accepted", "duplicate", "limited"]: ...


def accept_event(
    port: ProductAnalyticsPort,
    event: ProductEvent | PublicInteraction,
    country: str = "unknown",
) -> None:
    from portfolio_assistant.domain.errors import RejectedError

    if port.record(event, country) == "limited":
        raise RejectedError("analytics_rate_limited", 429)


class ProductAnalyticsReadPort(Protocol):
    def report(self, query: AnalyticsQuery) -> ProductReport: ...


def read_product_report(port: ProductAnalyticsReadPort, query: AnalyticsQuery) -> ProductReport:
    return port.report(query)
