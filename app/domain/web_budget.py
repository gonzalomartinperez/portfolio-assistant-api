"""Immutable pricing policy for bounded official-documentation lookups."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal


@dataclass(frozen=True)
class WebBudget:
    cutoff: Decimal
    input_price: Decimal
    output_price: Decimal
    fee: Decimal

    def __post_init__(self) -> None:
        if any(
            not value.is_finite() or value <= 0
            for value in (self.cutoff, self.input_price, self.output_price, self.fee)
        ):
            raise ValueError('web budget and prices must be finite positive values')

    @property
    def maximum(self) -> Decimal:
        # Search can add input beyond the fixed query; reserve the full model window.
        return self.cost(1050000, 2048, 2)

    def cost(self, inputs: int, outputs: int, calls: int) -> Decimal:
        if min(inputs, outputs, calls) < 0:
            raise ValueError('invalid web usage')
        input_multiplier = 2 if inputs > 272000 else 1
        output_multiplier = Decimal('1.5') if inputs > 272000 else Decimal(1)
        return (
            (
                Decimal(inputs) * self.input_price * input_multiplier
                + Decimal(outputs) * self.output_price * output_multiplier
            )
            / Decimal(1000000)
            + self.fee * calls
        ).quantize(Decimal('0.000001'), rounding=ROUND_CEILING)
