import runpy

from tests.support import ROOT


def test_module_reexports_run():
    from app import knowledge_watch
    from portfolio_assistant.bootstrap import knowledge_watch as bootstrap

    assert knowledge_watch.run is bootstrap.run


def test_main_runs_the_worker(monkeypatch):
    calls = []

    async def fake_run():
        calls.append("run")

    monkeypatch.setattr("portfolio_assistant.bootstrap.knowledge_watch.run", fake_run)
    runpy.run_path(str(ROOT / "src/app" / "knowledge_watch.py"), run_name="__main__")
    assert calls == ["run"]


def test_import_does_not_start_the_worker(monkeypatch):
    async def fail():
        raise AssertionError("worker must not start on import")

    monkeypatch.setattr("portfolio_assistant.bootstrap.knowledge_watch.run", fail)
    runpy.run_path(str(ROOT / "src/app" / "knowledge_watch.py"), run_name="imported")
