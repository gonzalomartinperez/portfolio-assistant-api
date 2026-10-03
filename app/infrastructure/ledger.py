import asyncio
import json
import logging
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from app.application.contracts import Usage
from app.bootstrap.config import settings
from app.domain.errors import BudgetExhaustedError
from app.infrastructure.db import connect


def reserve(
    run_id: str, amount: Decimal, *, connection=connect, cutoff: Decimal | None = None
) -> None:
    if amount <= 0 or not amount.is_finite():
        raise ValueError('reservation must be finite and positive')
    cutoff = cutoff if cutoff is not None else Decimal(settings().reserve_cutoff_usd)
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(472019)')
        spent = conn.execute(
            "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now())"
        ).fetchone()['amount']
        if spent + amount > cutoff:
            raise BudgetExhaustedError()
        conn.execute(
            'INSERT INTO spend_ledger(id,run_id,kind,reserved_usd) VALUES (%s,%s,%s,%s)',
            (uuid4(), UUID(run_id), 'inference', amount),
        )


def settle(
    run_id: str,
    input_tokens: int,
    output_tokens: int,
    *,
    connection=connect,
    input_price: Decimal | None = None,
    output_price: Decimal | None = None,
) -> None:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError('usage cannot be negative')
    input_price = (
        input_price
        if input_price is not None
        else Decimal(settings().input_usd_per_million)
    )
    output_price = (
        output_price
        if output_price is not None
        else Decimal(settings().output_usd_per_million)
    )
    cost = (
        Decimal(input_tokens) * input_price + Decimal(output_tokens) * output_price
    ) / Decimal(1000000)
    cost = cost.quantize(Decimal('0.000001'), rounding=ROUND_CEILING)
    with connection() as conn:
        conn.execute(
            'UPDATE spend_ledger SET actual_usd=%s WHERE run_id=%s',
            (cost, UUID(run_id)),
        )
    logging.getLogger('portfolio_assistant').info(
        json.dumps(
            {
                'operation': 'usage_settled',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': str(cost),
            }
        )
    )


class PostgresAccounting:
    def __init__(self, connection, budget):
        self.connection = connection
        self.budget = budget

    async def reserve(self, run_id: str) -> None:
        await asyncio.to_thread(
            reserve,
            run_id,
            self.budget.reservation,
            connection=self.connection,
            cutoff=self.budget.cutoff,
        )

    async def settle(self, run_id: str, usage: Usage) -> None:
        await asyncio.to_thread(
            settle,
            run_id,
            usage.input_tokens,
            usage.output_tokens,
            connection=self.connection,
            input_price=self.budget.input_price,
            output_price=self.budget.output_price,
        )


class EmbeddingAccounting:
    """Independent ledger entries also cover indexing without a conversation run."""

    def __init__(self, connection, monthly: Decimal, price: Decimal):
        if not price.is_finite() or price <= 0:
            raise ValueError('embedding price must be positive')
        self.connection = connection
        self.monthly = monthly
        self.price = price

    def reserve_embedding(self, maximum_tokens: int, purpose: str) -> UUID:
        if purpose not in ('query', 'index') or maximum_tokens <= 0:
            raise ValueError('invalid embedding reservation')
        amount = max(
            Decimal(maximum_tokens) * self.price / Decimal(1000000), Decimal('0.000001')
        )
        amount = amount.quantize(Decimal('0.000001'), rounding=ROUND_CEILING)
        identifier = uuid4()
        with self.connection() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(472019)')
            spent = conn.execute(
                "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now())"
            ).fetchone()['amount']
            if spent + amount > self.monthly:
                raise BudgetExhaustedError()
            conn.execute(
                'INSERT INTO spend_ledger(id,kind,reserved_usd) VALUES (%s,%s,%s)',
                (identifier, 'embedding_' + purpose, amount),
            )
        return identifier

    def settle_embedding(self, identifier: UUID, tokens: int) -> None:
        if tokens < 0:
            raise ValueError('invalid embedding usage')
        with self.connection() as conn:
            conn.execute(
                'UPDATE spend_ledger SET actual_usd=%s WHERE id=%s AND actual_usd IS NULL',
                (
                    (Decimal(tokens) * self.price / Decimal(1000000)).quantize(
                        Decimal('0.000001'), rounding=ROUND_CEILING
                    ),
                    identifier,
                ),
            )
