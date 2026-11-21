import runpy

import pytest

from tests.support import ROOT


@pytest.mark.parametrize(
    ("file", "target"),
    [
        ("migrate.py", "portfolio_assistant.bootstrap.migrations.main"),
        ("knowledge_sync.py", "portfolio_assistant.bootstrap.indexing.main"),
    ],
)
def test_main_delegates_to_bootstrap(monkeypatch, file, target):
    calls = []
    monkeypatch.setattr(target, lambda: calls.append(file))
    runpy.run_path(str(ROOT / "src/app" / file), run_name="__main__")
    assert calls == [file]


@pytest.mark.parametrize(
    ("file", "target"),
    [
        ("migrate.py", "portfolio_assistant.bootstrap.migrations.main"),
        ("knowledge_sync.py", "portfolio_assistant.bootstrap.indexing.main"),
    ],
)
def test_import_does_not_run(monkeypatch, file, target):
    def fail():
        raise AssertionError("must not run on import")

    monkeypatch.setattr(target, fail)
    runpy.run_path(str(ROOT / "src/app" / file), run_name="imported")


def test_knowledge_sync_reexports():
    from app import knowledge_sync
    from portfolio_assistant.bootstrap import indexing
    from portfolio_assistant.bootstrap.entrypoints import knowledge_sync as entry

    assert knowledge_sync.main is entry.main
    assert knowledge_sync.sync is indexing.sync
