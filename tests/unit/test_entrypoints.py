import importlib
import tomllib

import pytest

from app.bootstrap.entrypoints import api, knowledge_sync, knowledge_watch, migrate, retention
from tests.support import ROOT


def scripts():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["project"]["scripts"]


@pytest.mark.parametrize("name", sorted(scripts()))
def test_script_target_resolves(name):
    module, function = scripts()[name].split(":")
    assert callable(getattr(importlib.import_module(module), function))


def test_console_scripts_live_under_bootstrap_entrypoints():
    for target in scripts().values():
        module, function = target.split(":")
        assert module.startswith("app.bootstrap.entrypoints.")
        assert function == "main"


def test_api_matches_container_command(monkeypatch):
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    api.main()
    assert calls == [
        (
            ("app.main:app",),
            {
                "host": "0.0.0.0",
                "port": 8000,
                "access_log": False,
                "proxy_headers": False,
                "timeout_graceful_shutdown": 15,
            },
        )
    ]


def test_migrate_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr("app.bootstrap.migrations.main", lambda: calls.append("m"))
    migrate.main()
    assert calls == ["m"]


def test_retention_prints_prune_result(monkeypatch, capsys):
    monkeypatch.setattr("app.bootstrap.maintenance.prune", lambda: {"pruned": 3})
    retention.main()
    assert capsys.readouterr().out == "{'pruned': 3}\n"


def test_knowledge_sync_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr("app.bootstrap.indexing.main", lambda: calls.append("s"))
    knowledge_sync.main()
    assert calls == ["s"]


def test_knowledge_watch_runs_worker(monkeypatch):
    calls = []

    async def run():
        calls.append("w")

    monkeypatch.setattr("app.bootstrap.knowledge_watch.run", run)
    knowledge_watch.main()
    assert calls == ["w"]


def test_python_m_knowledge_watch_shim_runs_the_bootstrap_worker(monkeypatch):
    import runpy
    import sys

    calls = []

    async def run():
        calls.append("w")

    monkeypatch.setattr("app.bootstrap.knowledge_watch.run", run)
    monkeypatch.delitem(sys.modules, "app.knowledge_watch", raising=False)
    runpy.run_module("app.knowledge_watch", run_name="__main__")
    assert calls == ["w"]
