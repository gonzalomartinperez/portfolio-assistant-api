"""Dependency direction and regression probes for ways around architectural rules."""

from pathlib import Path

import pytest

from scripts.check_architecture import (
    architecture_errors,
    cycle_errors,
    dependencies,
    dependency_errors,
)

ROOT = Path(__file__).parents[1] / 'app'


def test_architecture():
    assert architecture_errors(ROOT) == []


@pytest.mark.parametrize(
    ('module', 'source'),
    [
        ('app.domain.example', 'from app import infrastructure'),
        ('app.domain.example', 'from ..infrastructure import db'),
        ('app.application.example', 'import app.presentation.http'),
        ('app.application.example', 'from fastapi import Request'),
        (
            'app.application.example',
            'if TYPE_CHECKING:\n    from fastapi import Request',
        ),
        ('app.ai.example', 'from app.adapters.postgres.db import connect'),
        ('app.presentation.example', 'from app.bootstrap.container import create_app'),
        ('app.infrastructure.example', 'from app.bootstrap.config import Settings'),
        ('app.adapters.postgres.db', 'from app.bootstrap.container import create_app'),
        ('app.domain.example', 'import os'),
        ('app.domain.example', 'import urllib.request'),
        ('app.application.example', '__import__("app.adapters.postgres.db")'),
        ('app.application.example', 'import importlib as i; i.import_module(name)'),
        (
            'app.application.example',
            'from importlib import import_module as load; load(name)',
        ),
        ('app.domain.example', 'exec(source)'),
    ],
)
def test_rejects_dependency_bypasses(module, source):
    assert dependency_errors(module, source), (module, source)


@pytest.mark.parametrize(
    ('module', 'source'),
    [
        ('app.domain.example', 'from .evidence import tokens'),
        ('app.domain.example', 'from urllib.parse import urlsplit'),
        ('app.application.example', 'from app.domain import budget'),
        (
            'app.adapters.example',
            'from app.application.web_context import SearchAccounting',
        ),
    ],
)
def test_allows_owned_ports(module, source):
    assert dependency_errors(module, source) == []


def test_cycles_include_relative_imports_and_from_package_imports():
    assert dependencies('app.domain', 'from . import b', package=True) == {
        'app.domain.b'
    }
    assert 'app.domain.b' in dependencies('app.domain.a', 'from . import b')
    assert 'app.domain.a' in dependencies('app.domain.b', 'import app.domain.a')
    assert cycle_errors(
        {
            'app.domain.a': dependencies('app.domain.a', 'from . import b'),
            'app.domain.b': dependencies('app.domain.b', 'import app.domain.a'),
        }
    )
    assert cycle_errors({'a': {'b'}, 'b': {'c'}, 'c': set()}) == []


def test_inner_and_http_layers_do_not_execute_queries():
    for layer in ('domain', 'application', 'presentation', 'ai'):
        for path in (ROOT / layer).rglob('*.py'):
            source = path.read_text()
            assert not any(
                sql in source
                for sql in ('SELECT ', 'INSERT INTO ', 'UPDATE runs ', 'MATCH (')
            ), path
