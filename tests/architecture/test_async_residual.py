"""Ratchet the blocking I/O references documented by ADR 029."""

import ast
import re
from collections import Counter

import pytest

from tests.support import ROOT

ADR = ROOT / "docs/decisions/029-async-io-boundary.md"
ALLOWED = {
    "app.adapters.portfolio.watch": 3,
    "app.adapters.postgres.ledger": 2,
    "app.adapters.postgres.operations": 2,
    "app.adapters.postgres.runs": 6,
    "app.adapters.postgres.web_ledger": 2,
    "app.adapters.providers.embedding": 2,
    "app.adapters.retrieval": 3,
    "app.bootstrap.container": 4,
    "app.presentation.operations": 2,
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
    for path in sorted((ROOT / "app").rglob("*.py")):
        count = count_references(path.read_text(encoding="utf-8"))
        if count:
            module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
            counts[module] = count
    assert_residual(counts, ALLOWED)


def test_async_residual_matches_adr_inventory():
    modules = re.findall(r"^\| `(app\.[\w.]+)` \|", ADR.read_text(encoding="utf-8"), re.MULTILINE)
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
    allowed = {"app.example": 1}
    assert_residual({"app.example": count_references(baseline)}, allowed)
    with pytest.raises(AssertionError, match="Only lower allowances"):
        assert_residual({"app.example": count_references(f"{baseline}\n{extra}")}, allowed)


@pytest.mark.parametrize("actual", [{}, {"app.example": 1, "app.new_module": 1}])
def test_rejects_removed_reference_or_new_module(actual):
    with pytest.raises(AssertionError, match="Only lower allowances"):
        assert_residual(actual, {"app.example": 1})
