"""The persistence adapter consumes pure pricing and retains atomic reservation order."""

import asyncio
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.domain.errors import BudgetExhaustedError
from app.domain.web_budget import WebBudget
from app.infrastructure.web_ledger import WebAccounting


@pytest.mark.parametrize('spent', [Decimal(0), Decimal('8.9')])
def test_injected_budget_controls_reservation_and_settlement(spent):
    statements = []

    def execute(sql, params=None):
        statements.append((sql, params))
        return SimpleNamespace(fetchone=lambda: {'amount': spent})

    @contextmanager
    def connection():
        yield SimpleNamespace(execute=execute)

    budget = WebBudget(Decimal(9), Decimal('0.10'), Decimal('0.50'), Decimal('0.01'))
    ledger = WebAccounting(connection, budget)

    async def run():
        if spent + budget.maximum > budget.cutoff:
            with pytest.raises(BudgetExhaustedError):
                await ledger.reserve()
            assert len(statements) == 2
            return
        identifier = await ledger.reserve()
        assert isinstance(identifier, UUID)
        assert statements[2][1] == (identifier, 'web_search', budget.maximum)
        # Reserving never invents known usage; only an explicit settlement changes it.
        assert not any('UPDATE' in sql for sql, _ in statements)
        await ledger.settle(identifier, 100, 50, 1)
        assert statements[3][1] == (budget.cost(100, 50, 1), 100, 50, identifier)

    asyncio.run(run())
    assert 'pg_advisory_xact_lock' in statements[0][0]
    assert 'sum(' in statements[1][0]
