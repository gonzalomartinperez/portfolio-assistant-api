"""Conservative, explicit cost policy; no model determines spending authority."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Budget:
    monthly: Decimal
    cutoff: Decimal
    reservation: Decimal
    input_price: Decimal
    output_price: Decimal

    def __post_init__(self) -> None:
        values = (
            self.monthly,
            self.cutoff,
            self.reservation,
            self.input_price,
            self.output_price,
        )
        if any(not value.is_finite() or value <= 0 for value in values):
            raise ValueError('budget and prices must be finite positive values')
        if not self.reservation <= self.cutoff <= self.monthly:
            raise ValueError('reservation must fit cutoff and monthly budget')
        # UTF-8 bytes conservatively bound input tokens for the bounded prompt.
        maximum = self.cost(110000, 500)
        if self.reservation < maximum:
            raise ValueError('reservation must cover the bounded maximum model request')

    def cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError('usage cannot be negative')
        return (
            Decimal(input_tokens) * self.input_price
            + Decimal(output_tokens) * self.output_price
        ) / Decimal(1000000)
