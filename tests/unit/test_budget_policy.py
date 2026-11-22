"""Validation and cost boundaries for the model budget."""

from decimal import Decimal

import pytest

from portfolio_assistant.domain.budget import Budget


@pytest.fixture
def budget_values():
    return {
        "monthly": Decimal(10),
        "cutoff": Decimal(9),
        "reservation": Decimal("0.05"),
        "input_price": Decimal("0.1"),
        "output_price": Decimal("0.5"),
    }


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0"])
@pytest.mark.parametrize(
    "field", ["monthly", "cutoff", "reservation", "input_price", "output_price"]
)
def test_budget_requires_finite_positive_money_and_prices(budget_values, field, value):
    budget_values[field] = Decimal(value)

    with pytest.raises(ValueError, match=r"^budget and prices must be finite positive values$"):
        Budget(**budget_values)


@pytest.mark.parametrize(("field", "value"), [("cutoff", "0.04"), ("monthly", "8")])
def test_reservation_fits_the_cutoff_and_the_cutoff_fits_the_monthly_budget(
    budget_values, field, value
):
    budget_values[field] = Decimal(value)

    with pytest.raises(ValueError, match=r"^reservation must fit cutoff and monthly budget$"):
        Budget(**budget_values)


def test_reservation_can_equal_the_full_request_cost(budget_values):
    budget_values["reservation"] = Decimal("0.015096")
    policy = Budget(**budget_values)

    assert policy.cost(110_000, 8_192) == Decimal("0.015096")


def test_reservation_below_the_full_request_cost_is_rejected(budget_values):
    budget_values["reservation"] = Decimal("0.015095")

    with pytest.raises(
        ValueError, match=r"^reservation must cover the bounded maximum model request$"
    ):
        Budget(**budget_values)


@pytest.mark.parametrize("tokens", [(-1, 0), (0, -1)], ids=["input", "output"])
def test_negative_token_usage_has_a_specific_validation_error(budget_values, tokens):
    policy = Budget(**budget_values)

    with pytest.raises(ValueError, match=r"^usage cannot be negative$"):
        policy.cost(*tokens)
