import runpy

from tests.support import ROOT


def test_main_prints_prune_result(monkeypatch, capsys):
    monkeypatch.setattr('app.bootstrap.maintenance.prune', lambda: {'pruned': 2})
    runpy.run_path(str(ROOT / 'app' / 'retention.py'), run_name='__main__')
    assert capsys.readouterr().out == "{'pruned': 2}\n"


def test_import_does_not_prune(monkeypatch, capsys):
    def fail():
        raise AssertionError('prune must not run on import')

    monkeypatch.setattr('app.bootstrap.maintenance.prune', fail)
    runpy.run_path(str(ROOT / 'app' / 'retention.py'), run_name='imported')
    assert capsys.readouterr().out == ''
