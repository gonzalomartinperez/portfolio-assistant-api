"""Search pricing policy is testable without SDKs, settings, database or network."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.web_budget import WebBudget


def budget() -> WebBudget:
    return WebBudget(Decimal(9), Decimal('0.10'), Decimal('0.50'), Decimal('0.01'))


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0'])
@pytest.mark.parametrize('field', ['cutoff', 'input_price', 'output_price', 'fee'])
def test_budget_rejects_invalid_configuration(field, value):
    values = {
        'cutoff': Decimal(9),
        'input_price': Decimal('0.10'),
        'output_price': Decimal('0.50'),
        'fee': Decimal('0.01'),
    }
    values[field] = Decimal(value)
    with pytest.raises(ValueError):
        WebBudget(**values)


def test_full_window_and_long_context_threshold():
    policy = budget()
    assert policy.maximum == Decimal('0.231536')
    assert policy.cost(272000, 2048, 1) == Decimal('0.038224')
    assert policy.cost(272001, 2048, 1) == Decimal('0.065937')
    assert policy.cost(1, 0, 0) == Decimal('0.000001')
    assert policy.cost(0, 0, 0) == 0
    with pytest.raises(FrozenInstanceError):
        policy.fee = Decimal(0)


@pytest.mark.parametrize('usage', [(-1, 0, 0), (0, -1, 0), (0, 0, -1)])
def test_negative_usage_is_never_settled(usage):
    with pytest.raises(ValueError):
        budget().cost(*usage)
