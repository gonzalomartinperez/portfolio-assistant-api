from decimal import Decimal
from uuid import UUID, uuid4

from app.bootstrap.config import settings
from app.domain.errors import BudgetExhausted
from app.infrastructure.db import connect


def reserve(run_id: str, amount: Decimal) -> None:
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(472019)')
        spent = conn.execute(
            "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now())"
        ).fetchone()['amount']
        if spent + amount > Decimal(settings().reserve_cutoff_usd):
            raise BudgetExhausted()
        conn.execute(
            'INSERT INTO spend_ledger(id,run_id,kind,reserved_usd) VALUES (%s,%s,%s,%s)',
            (uuid4(), UUID(run_id), 'inference', amount),
        )


def settle(run_id: str, input_tokens: int, output_tokens: int) -> None:
    cost = (
        Decimal(input_tokens) * Decimal(settings().input_usd_per_million)
        + Decimal(output_tokens) * Decimal(settings().output_usd_per_million)
    ) / Decimal(1_000_000)
    with connect() as conn:
        conn.execute(
            'UPDATE spend_ledger SET actual_usd=%s WHERE run_id=%s',
            (cost, UUID(run_id)),
        )
