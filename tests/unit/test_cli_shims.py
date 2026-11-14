import runpy

import pytest

from tests.support import ROOT


@pytest.mark.parametrize(
    ('file', 'target'),
    [
        ('migrate.py', 'app.bootstrap.migrations.main'),
        ('knowledge_sync.py', 'app.bootstrap.indexing.main'),
    ],
)
def test_main_delegates_to_bootstrap(monkeypatch, file, target):
    calls = []
    monkeypatch.setattr(target, lambda: calls.append(file))
    runpy.run_path(str(ROOT / 'app' / file), run_name='__main__')
    assert calls == [file]


@pytest.mark.parametrize(
    ('file', 'target'),
    [
        ('migrate.py', 'app.bootstrap.migrations.main'),
        ('knowledge_sync.py', 'app.bootstrap.indexing.main'),
    ],
)
def test_import_does_not_run(monkeypatch, file, target):
    def fail():
        raise AssertionError('must not run on import')

    monkeypatch.setattr(target, fail)
    runpy.run_path(str(ROOT / 'app' / file), run_name='imported')


def test_knowledge_sync_reexports():
    from app import knowledge_sync
    from app.bootstrap import indexing

    assert knowledge_sync.main is indexing.main
    assert knowledge_sync.sync is indexing.sync
