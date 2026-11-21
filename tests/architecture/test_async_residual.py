"""Ratchet the blocking I/O references documented by ADR 029."""

import ast
import re
from collections import Counter

import pytest

from tests.support import ROOT

ADR = ROOT / "docs/decisions/029-async-io-boundary.md"
ALLOWED = {
    "portfolio_assistant.adapters.portfolio.watch": 3,
    "portfolio_assistant.adapters.postgres.ledger": 2,
    "portfolio_assistant.adapters.postgres.operations": 2,
    "portfolio_assistant.adapters.postgres.runs": 6,
    "portfolio_assistant.adapters.postgres.web_ledger": 2,
    "portfolio_assistant.adapters.providers.embedding": 2,
    "portfolio_assistant.adapters.retrieval": 3,
    "portfolio_assistant.bootstrap.container": 4,
    "portfolio_assistant.presentation.operations": 2,
}


def count_references(source: str) -> int:
    nodes = list(ast.walk(ast.parse(source)))
    modules = {"asyncio"}
    functions = {"to_thread"}
    for node in nodes:
        if isinstance(node, ast.Import):
            modules.update(
                alias.asname or alias.name for alias in node.names if alias.name == "asyncio"
            )
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "asyncio":
            functions.update(
                alias.asname or alias.name for alias in node.names if alias.name == "to_thread"
            )

    # Count uses as values too, including lifespan cleanup callbacks.
    return sum(
        (isinstance(node, ast.Name) and node.id in functions)
        or (
            isinstance(node, ast.Attribute)
            and node.attr == "to_thread"
            and isinstance(node.value, ast.Name)
            and node.value.id in modules
        )
        for node in nodes
        if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load)
    )


def assert_residual(counts: dict[str, int], allowed: dict[str, int]) -> None:
    assert counts == allowed, (
        "Keep to_thread allowances and ADR 029 in sync. Only lower allowances."
    )


def test_async_residual_matches_allowances():
    counts = {}
    for path in sorted((ROOT / "src/portfolio_assistant").rglob("*.py")):
        count = count_references(path.read_text(encoding="utf-8"))
        if count:
            module = ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)
            counts[module] = count
    assert_residual(counts, ALLOWED)


def test_async_residual_matches_adr_inventory():
    modules = re.findall(
        r"^\| `(portfolio_assistant\.[\w.]+)` \|", ADR.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert_residual(dict(Counter(modules)), ALLOWED)


@pytest.mark.parametrize(
    "extra",
    [
        "asyncio.to_thread(work)",
        "from asyncio import to_thread\nto_thread(work)",
        "import asyncio as aio\naio.to_thread(work)",
        "from asyncio import to_thread as offload\nregister(offload)",
    ],
)
def test_rejects_extra_reference(extra):
    baseline = "register(asyncio.to_thread)"
    allowed = {"portfolio_assistant.example": 1}
    assert_residual({"portfolio_assistant.example": count_references(baseline)}, allowed)
    with pytest.raises(AssertionError, match="Only lower allowances"):
        assert_residual(
            {"portfolio_assistant.example": count_references(f"{baseline}\n{extra}")}, allowed
        )


@pytest.mark.parametrize(
    "actual", [{}, {"portfolio_assistant.example": 1, "portfolio_assistant.new_module": 1}]
)
def test_rejects_removed_reference_or_new_module(actual):
    with pytest.raises(AssertionError, match="Only lower allowances"):
        assert_residual(actual, {"portfolio_assistant.example": 1})
