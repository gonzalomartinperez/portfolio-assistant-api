"""Exercise the shipped Import Linter contracts against isolated package trees."""

import re

import pytest

from tests.lint_imports_runner import invoke_lint_imports
from tests.support import ROOT

LAYERS = "Application layer direction"
EXTERNAL = "Inner layers avoid third-party and platform I/O imports"
CYCLES = "Application siblings are acyclic"


@pytest.fixture
def lint_package(tmp_path, monkeypatch):
    name = "architecture_probe"
    monkeypatch.syspath_prepend(str(tmp_path))
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").touch()
    for layer in ("bootstrap", "presentation", "adapters", "ai", "application", "domain"):
        child = package / layer
        child.mkdir()
        (child / "__init__.py").touch()
    for shim in ("main", "migrate", "retention", "knowledge_sync", "knowledge_watch"):
        (package / f"{shim}.py").touch()
    (package / "adapters/postgres").mkdir()
    for leaf in (
        "adapters/postgres/__init__.py",
        "adapters/postgres/db.py",
        "bootstrap/config.py",
        "bootstrap/container.py",
        "presentation/http.py",
    ):
        (package / leaf).touch()
    config = tmp_path / "pyproject.toml"
    config.write_text(re.sub(r'"app(?=[."])', f'"{name}', (ROOT / "pyproject.toml").read_text()))

    def run(sources):
        for path, source in sources.items():
            (package / path).write_text(source.replace("app.", f"{name}."))
        return invoke_lint_imports(["--no-cache", str(config)])

    return run


@pytest.mark.parametrize(
    ("path", "source", "contract"),
    [
        ("domain/example.py", "import app.adapters", LAYERS),
        ("application/example.py", "import app.presentation.http", LAYERS),
        ("adapters/example.py", "import app.presentation", LAYERS),
        ("ai/example.py", "from .. import adapters", LAYERS),
        ("ai/example.py", "from app.adapters.postgres.db import connect", LAYERS),
        ("presentation/example.py", "from app.bootstrap.container import create_app", LAYERS),
        ("adapters/example.py", "from app.bootstrap.config import settings", LAYERS),
        ("bootstrap/example.py", "import app.main", LAYERS),
        ("migrate.py", "import app.main", LAYERS),
        ("application/example.py", "import httpx", EXTERNAL),
        ("application/example.py", "from fastapi import Request", EXTERNAL),
        (
            "application/example.py",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from fastapi import Request",
            EXTERNAL,
        ),
        ("domain/example.py", "import os", EXTERNAL),
        ("domain/example.py", "from http import HTTPStatus", EXTERNAL),
        ("application/example.py", "import socket", EXTERNAL),
        ("domain/example.py", "import sqlite3", EXTERNAL),
        ("application/example.py", "import subprocess", EXTERNAL),
        # The three middle layers are independent in both directions.
        ("presentation/example.py", "import app.ai", LAYERS),
        ("presentation/example.py", "import app.adapters", LAYERS),
        ("adapters/example.py", "import app.ai", LAYERS),
        ("ai/example.py", "import app.presentation", LAYERS),
        # No layer below the shims imports any shim.
        *[
            ("bootstrap/example.py", f"import app.{shim}", LAYERS)
            for shim in ("main", "migrate", "retention", "knowledge_sync", "knowledge_watch")
        ],
    ],
)
def test_rejects_illegal_import(lint_package, path, source, contract):
    result = lint_package({path: source})
    assert result.exit_code == 1, result.output
    assert f"{contract} BROKEN" in result.output


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_rejects_sibling_cycle(lint_package, layer):
    result = lint_package(
        {
            f"{layer}/a.py": "from . import b",
            f"{layer}/b.py": "from . import a",
        }
    )
    assert result.exit_code == 1, result.output
    assert f"{CYCLES} BROKEN" in result.output


def test_allows_owned_ports_and_shims(lint_package):
    result = lint_package(
        {
            "domain/evidence.py": "from urllib.parse import urlsplit",
            "domain/example.py": "from . import evidence",
            "application/example.py": "from app.domain import evidence",
            "adapters/example.py": "from app.application import example",
            "ai/example.py": "from app.application import example\nimport app.domain",
            "presentation/example.py": "import app.application\nimport app.domain",
            "bootstrap/example.py": "import app.ai\nimport app.adapters\nimport app.presentation",
            "main.py": "import app.bootstrap\nimport app.domain",
            "migrate.py": "import app.adapters",
        }
    )
    assert result.exit_code == 0, result.output
    for contract in (LAYERS, EXTERNAL, CYCLES):
        assert f"{contract} KEPT" in result.output
