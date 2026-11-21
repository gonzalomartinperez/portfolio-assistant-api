"""Dependency direction and regression probes for ways around architectural rules."""

import pytest

from scripts.check_architecture import (
    architecture_errors,
    console_script_errors,
    cycle_errors,
    dependencies,
    dependency_errors,
    entry_point_errors,
)
from tests.support import ROOT as REPO_ROOT

ROOT = REPO_ROOT / "app"


def test_architecture():
    assert architecture_errors(ROOT) == []


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("app.domain.example", "from app import infrastructure"),
        ("app.domain.example", "from ..infrastructure import db"),
        ("app.application.example", "import app.presentation.http"),
        ("app.application.example", "from fastapi import Request"),
        (
            "app.application.example",
            "if TYPE_CHECKING:\n    from fastapi import Request",
        ),
        ("app.ai.example", "from app.adapters.postgres.db import connect"),
        ("app.presentation.example", "from app.bootstrap.container import create_app"),
        ("app.infrastructure.example", "from app.bootstrap.config import Settings"),
        ("app.adapters.postgres.db", "from app.bootstrap.container import create_app"),
        ("app.domain.example", "import os"),
        ("app.domain.example", "import urllib.request"),
        ("app.application.example", '__import__("app.adapters.postgres.db")'),
        ("app.application.example", "import importlib as i; i.import_module(name)"),
        (
            "app.application.example",
            "from importlib import import_module as load; load(name)",
        ),
        ("app.domain.example", "exec(source)"),
    ],
)
def test_rejects_dependency_bypasses(module, source):
    assert dependency_errors(module, source), (module, source)


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("app.domain.example", "from .evidence import tokens"),
        ("app.domain.example", "from urllib.parse import urlsplit"),
        ("app.application.example", "from app.domain import budget"),
        (
            "app.adapters.example",
            "from app.application.web_context import SearchAccounting",
        ),
    ],
)
def test_allows_owned_ports(module, source):
    assert dependency_errors(module, source) == []


@pytest.mark.parametrize(
    "source",
    [
        "from datetime import datetime\nx = datetime.now()",
        "from datetime import datetime\nx = datetime.utcnow()",
        "from datetime import datetime\nx = datetime.today()",
        "from datetime import date\nx = date.today()",
        "import time\nx = time.time()",
        "import datetime\nx = datetime.datetime.now()",
        "import datetime\nx = datetime.date.today()",
        "import datetime as d\nx = d.datetime.utcnow()",
        "from datetime import datetime as dt\nx = dt.now()",
        "from datetime import date as day\nx = day.today()",
        "import time as t\nx = t.time()",
        "from datetime import datetime\nfield(default_factory=datetime.now)",
        "from datetime import datetime\nfactory = datetime.utcnow",
        "import time\nfactory = time.time",
        "from time import time\nx = time()",
        "from time import time as clock\nx = clock()",
        "from datetime import UTC, datetime\nx = lambda: datetime.now(UTC).date()",
        "import time\nx = time.gmtime()",
        "import time\nx = time.localtime()",
        "from time import ctime\nx = ctime()",
        "import time\nx = time.strftime('%Y')",
    ],
)
def test_rejects_wall_clock_reads(source):
    for module in ("app.application.example", "app.adapters.example", "app.presentation.example"):
        assert any("wall-clock" in e for e in dependency_errors(module, source)), source


def test_allows_clock_adapter_and_monotonic_timers():
    adapter = "from datetime import UTC, datetime\nx = datetime.now(UTC)"
    assert dependency_errors("app.adapters.clock", adapter) == []
    monotonic = "import time\nfrom time import perf_counter, monotonic\nx = time.perf_counter()"
    assert dependency_errors("app.application.example", monotonic) == []
    assert dependency_errors("app.adapters.example", "from datetime import datetime\n") == []
    assert dependency_errors("app.adapters.example", "x = clock.now()") == []


def test_cycles_include_relative_imports_and_from_package_imports():
    assert dependencies("app.domain", "from . import b", package=True) == {"app.domain.b"}
    assert "app.domain.b" in dependencies("app.domain.a", "from . import b")
    assert "app.domain.a" in dependencies("app.domain.b", "import app.domain.a")
    assert cycle_errors(
        {
            "app.domain.a": dependencies("app.domain.a", "from . import b"),
            "app.domain.b": dependencies("app.domain.b", "import app.domain.a"),
        }
    )
    assert cycle_errors({"a": {"b"}, "b": {"c"}, "c": set()}) == []


def test_inner_and_http_layers_do_not_execute_queries():
    for layer in ("domain", "application", "presentation", "ai"):
        for path in (ROOT / layer).rglob("*.py"):
            source = path.read_text()
            assert not any(
                sql in source for sql in ("SELECT ", "INSERT INTO ", "UPDATE runs ", "MATCH (")
            ), path


@pytest.mark.parametrize(
    "source",
    [
        'if __name__ == "__main__":\n    main()',
        'if "__main__" == __name__:\n    main()',
    ],
)
def test_rejects_entry_points_outside_bootstrap_entrypoints(source):
    assert entry_point_errors("app.bootstrap.indexing", source)
    assert entry_point_errors("app.adapters.example", source)


def test_allows_entry_points_under_bootstrap_entrypoints_and_shims():
    source = 'if __name__ == "__main__":\n    main()'
    assert entry_point_errors("app.bootstrap.entrypoints.migrate", source) == []
    assert entry_point_errors("app.migrate", source) == []
    assert entry_point_errors("app.bootstrap.evaluation_export", source) == []


def test_console_scripts_must_target_bootstrap_entrypoints():
    good = '[project.scripts]\nassistant-api = "app.bootstrap.entrypoints.api:main"\n'
    assert console_script_errors(good) == []
    for target in ("app.main:run", "app.bootstrap.entrypoints.api:serve", "app.bootstrap:api"):
        bad = f'[project.scripts]\nx = "{target}"\n'
        assert console_script_errors(bad), target


def test_root_package_is_scanned_for_wall_clock_reads(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "__init__.py").write_text("import time\nSTARTED = time.time()\n")
    assert any("wall-clock" in error for error in architecture_errors(root))
