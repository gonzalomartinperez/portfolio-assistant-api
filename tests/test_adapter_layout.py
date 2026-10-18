"""Canonical adapter placement must preserve real SQL resources and operator entry points."""

import hashlib
import importlib
from pathlib import Path

import pytest

from scripts.check_architecture import dependency_errors

EXPECTED_MIGRATIONS = {
    '001_initial.sql': '1fb6eec4978ab719abe3cfd7154620bbe574fa09e48462687609749462814f62',
    '002_checkpoint_cleanup.sql': '2a99b300a76bd6af9cefe5f4f7e574d6e9aa0f6e9da976f3eb53ffc3789f0197',
    '003_cleanup_attempts.sql': '11b5dfd0394b32fd6869447aef126a99a15c899392f1eb9ee098b1648ed73bd0',
    '004_semantic_knowledge.sql': 'be759f65c43628b810b7514fe59a542aad6d6497ee3f67b00c0b7767138f168a',
    '005_embedding_cache.sql': '1d1a82342df550f26d8e624c3b41f4b052b0a1576d9fd3eae7e9ed6c8dcda331',
    '006_operational_measurements.sql': '107a55574bf72965828f02e7e360c5f0fcfb3742a9055b5af9bcbba7c0a22d9a',
    '007_product_analytics.sql': 'fd640ff7c7962ffc64a890c6e85fe10fca927d24d9bbe87cdbb1c19ddd757765',
    '008_spend_ledger_time_index.sql': '52395616951ddfe21b406b919aff6ec769591f312f7bb2f93cff2237cf421ed1',
    '009_product_interactions.sql': 'f3c287274520fdbc2310e826bf96e64fdc6a83aaa69a5c31ffd11c629e8f1364',
}


def test_nested_adapter_discovers_the_existing_nonempty_sql_inventory():
    migrations = importlib.import_module('app.adapters.postgres.migrations')
    paths = migrations.migration_paths()
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    } == EXPECTED_MIGRATIONS


def test_missing_migration_resources_never_validate_an_empty_history(
    tmp_path, monkeypatch
):
    migrations = importlib.import_module('app.adapters.postgres.migrations')
    monkeypatch.setattr(
        migrations, '__file__', str(tmp_path / 'app/adapters/postgres/migrations.py')
    )
    with pytest.raises(RuntimeError, match='migration resources'):
        migrations.migration_paths()


@pytest.mark.parametrize(
    'module', ['app.adapters.postgres.db', 'app.adapters.providers.answer']
)
def test_adapters_consume_owned_ports_without_bootstrap_or_legacy_backedges(module):
    assert (
        dependency_errors(module, 'from app.application.contracts import Usage') == []
    )
    assert dependency_errors(module, 'from app.bootstrap.config import settings')
    assert dependency_errors(module, 'from app.infrastructure.db import connect')


def test_only_operator_facades_retain_the_legacy_namespace():
    root = Path(__file__).parents[1] / 'app'
    allowed = {
        'db.py',
        'ledger.py',
        'checkpoints.py',
        'migrations.py',
        'indexing.py',
        '__init__.py',
    }
    assert {p.name for p in (root / 'infrastructure').glob('*.py')} == allowed
    for path in (root / 'infrastructure').glob('*.py'):
        assert not any(
            sql in path.read_text() for sql in ('SELECT ', 'INSERT INTO ', 'MATCH (')
        )
