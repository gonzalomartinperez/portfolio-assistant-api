"""Search shares the atomic monthly ledger; no unknown usage is treated as free."""

import asyncio
from uuid import UUID, uuid4

from app.domain.errors import BudgetExhaustedError
from app.domain.web_budget import WebBudget


class WebAccounting:
    def __init__(self, connection, budget: WebBudget):
        self.connection = connection
        self.budget = budget

    async def reserve(self) -> UUID:
        def operation():
            identifier = uuid4()
            with self.connection() as conn:
                conn.execute('SELECT pg_advisory_xact_lock(472019)')
                spent = conn.execute(
                    "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now(),'UTC')"
                ).fetchone()['amount']
                if spent + self.budget.maximum > self.budget.cutoff:
                    raise BudgetExhaustedError()
                conn.execute(
                    'INSERT INTO spend_ledger(id,kind,reserved_usd) VALUES (%s,%s,%s)',
                    (identifier, 'web_search', self.budget.maximum),
                )
            return identifier

        return await asyncio.to_thread(operation)

    async def settle(
        self, identifier: UUID, input_tokens: int, output_tokens: int, calls: int
    ) -> None:
        cost = self.budget.cost(input_tokens, output_tokens, calls)

        def operation():
            with self.connection() as conn:
                conn.execute(
                    "UPDATE spend_ledger SET actual_usd=%s,input_tokens=%s,output_tokens=%s WHERE id=%s AND kind='web_search' AND actual_usd IS NULL",
                    (cost, input_tokens, output_tokens, identifier),
                )

        await asyncio.to_thread(operation)
