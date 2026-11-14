import importlib
import tomllib
from pathlib import Path

import pytest

from app.bootstrap import entrypoints

ROOT = Path(__file__).parent.parent


def scripts():
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    return data['project']['scripts']


@pytest.mark.parametrize('name', sorted(scripts()))
def test_script_target_resolves(name):
    module, function = scripts()[name].split(':')
    assert callable(getattr(importlib.import_module(module), function))


def test_api_matches_container_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        'uvicorn.run', lambda *args, **kwargs: calls.append((args, kwargs))
    )
    entrypoints.api()
    assert calls == [
        (
            ('app.main:app',),
            {
                'host': '0.0.0.0',
                'port': 8000,
                'access_log': False,
                'proxy_headers': False,
                'timeout_graceful_shutdown': 15,
            },
        )
    ]


def test_migrate_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr('app.bootstrap.migrations.main', lambda: calls.append('m'))
    entrypoints.migrate()
    assert calls == ['m']


def test_retention_prints_prune_result(monkeypatch, capsys):
    monkeypatch.setattr('app.bootstrap.maintenance.prune', lambda: {'pruned': 3})
    entrypoints.retention()
    assert capsys.readouterr().out == "{'pruned': 3}\n"


def test_knowledge_sync_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr('app.bootstrap.indexing.main', lambda: calls.append('s'))
    entrypoints.knowledge_sync()
    assert calls == ['s']


def test_knowledge_watch_runs_worker(monkeypatch):
    calls = []

    async def run():
        calls.append('w')

    monkeypatch.setattr('app.bootstrap.knowledge_watch.run', run)
    entrypoints.knowledge_watch()
    assert calls == ['w']


def test_python_m_knowledge_watch_shim_runs_the_bootstrap_worker(monkeypatch):
    import runpy
    import sys

    calls = []

    async def run():
        calls.append('w')

    monkeypatch.setattr('app.bootstrap.knowledge_watch.run', run)
    monkeypatch.delitem(sys.modules, 'app.knowledge_watch', raising=False)
    runpy.run_module('app.knowledge_watch', run_name='__main__')
    assert calls == ['w']
