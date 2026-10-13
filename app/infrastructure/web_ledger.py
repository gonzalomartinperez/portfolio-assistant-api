"""Search shares the atomic monthly ledger; no unknown usage is treated as free."""

import asyncio
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from app.bootstrap.config import Settings
from app.domain.errors import BudgetExhaustedError


class WebAccounting:
    def __init__(self, connection, config: Settings):
        self.connection = connection
        self.cutoff = Decimal(config.reserve_cutoff_usd)
        self.input_price = Decimal(config.input_usd_per_million)
        self.output_price = Decimal(config.output_usd_per_million)
        self.fee = Decimal(config.web_search_usd_per_call)
        # Built-in retrieval can add input beyond our fixed query. Cover the full model window at long-context rates.
        self.maximum = self.cost(1050000, 2048, 2)

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

    async def reserve(self) -> UUID:
        def operation():
            identifier = uuid4()
            with self.connection() as conn:
                conn.execute('SELECT pg_advisory_xact_lock(472019)')
                spent = conn.execute(
                    "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now(),'UTC')"
                ).fetchone()['amount']
                if spent + self.maximum > self.cutoff:
                    raise BudgetExhaustedError()
                conn.execute(
                    'INSERT INTO spend_ledger(id,kind,reserved_usd) VALUES (%s,%s,%s)',
                    (identifier, 'web_search', self.maximum),
                )
            return identifier

        return await asyncio.to_thread(operation)

    async def settle(
        self, identifier: UUID, input_tokens: int, output_tokens: int, calls: int
    ) -> None:
        cost = self.cost(input_tokens, output_tokens, calls)

        def operation():
            with self.connection() as conn:
                conn.execute(
                    "UPDATE spend_ledger SET actual_usd=%s,input_tokens=%s,output_tokens=%s WHERE id=%s AND kind='web_search' AND actual_usd IS NULL",
                    (cost, input_tokens, output_tokens, identifier),
                )

        await asyncio.to_thread(operation)
