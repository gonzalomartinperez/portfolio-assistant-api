"""Readiness must execute the bounded reads rather than only open a connection."""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from neo4j import READ_ACCESS, GraphDatabase

from app.adapters.neo4j.read_queries import (
    DIRECT_RELATIONSHIPS_QUERY,
    PREPARATION_TIMEOUT,
    READ_TIMEOUT,
    RELATED_RELATIONSHIPS_QUERY,
    SUBJECTS_QUERY,
    prepare_reads,
    probe_reads,
)
from app.adapters.portfolio.indexing import graph_driver
from app.adapters.retrieval import KnowledgeIndex


@contextmanager
def public_connection():
    yield SimpleNamespace(
        execute=lambda *args: SimpleNamespace(fetchone=lambda: {'id': 'b' * 64})
    )


class Result:
    def __init__(self, rows, fail=False):
        self.rows = rows
        self.fail = fail
        self.consumed = False

    def __iter__(self):
        yield from self.rows
        self.consumed = True

    def consume(self):
        if self.fail:
            raise RuntimeError('synthetic graph read failure')
        self.consumed = True


class Session:
    def __init__(self, fail_on=None, subjects=None):
        self.calls = []
        self.results = []
        self.fail_on = fail_on
        self.subjects = (
            [{'name': 'alpha'}, {'name': 'beta'}] if subjects is None else subjects
        )
        self.closed = False
        self.transaction_options = None
        self.transaction_committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def run(self, query, parameters=None, **kwargs):
        parameters = {**(parameters or {}), **kwargs}
        self.calls.append((query, parameters))
        text = query if isinstance(query, str) else query.text
        rows = self.subjects if text == SUBJECTS_QUERY else [{'id': 'source'}]
        result = Result(rows, fail=len(self.calls) == self.fail_on)
        self.results.append(result)
        return result

    def begin_transaction(self, **options):
        self.transaction_options = options
        return Transaction(self)


class Transaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.session.transaction_committed = kind is None

    def run(self, query, parameters):
        return self.session.run(query, parameters)


class Driver:
    def __init__(self, session):
        self.target = session
        self.configuration = None

    def session(self, **configuration):
        self.configuration = configuration
        return self.target


def test_publication_preparation_consumes_both_locales_with_its_own_budget():
    session = Session()
    prepare_reads(session, 'a' * 40 + '-v8', 'b' * 64)
    assert len(session.calls) == 5 and all(r.consumed for r in session.results)
    assert all(query.timeout == PREPARATION_TIMEOUT == 5 for query, _ in session.calls)
    assert [query.text for query, _ in session.calls[1:]] == [
        DIRECT_RELATIONSHIPS_QUERY,
        RELATED_RELATIONSHIPS_QUERY,
    ] * 2
    assert [parameters['root_prefix'] for _, parameters in session.calls[1:]] == [
        'content/en/',
        'content/en/',
        'content/es/',
        'content/es/',
    ]


def test_readiness_uses_real_subjects_and_preserves_the_two_second_budget():
    session = Session()
    driver = Driver(session)
    index = KnowledgeIndex(public_connection, driver, database='synthetic-database')
    index.verify_ready('a' * 40 + '-v8')
    assert driver.configuration == {
        'database': 'synthetic-database',
        'default_access_mode': READ_ACCESS,
        'disable_auto_commit_retries': True,
    }
    assert session.closed and all(r.consumed for r in session.results)
    assert len(session.calls) == 3
    assert session.transaction_options == {'timeout': READ_TIMEOUT}
    assert READ_TIMEOUT == 2 and session.transaction_committed
    assert all(isinstance(query, str) for query, _ in session.calls)
    assert all(
        parameters['names'] == ['alpha', 'beta'] for _, parameters in session.calls[1:]
    )


@pytest.mark.parametrize('failure', [2, 3, 4, 5])
def test_partial_publication_preparation_propagates_read_failure(failure):
    with pytest.raises(RuntimeError, match='synthetic graph read failure'):
        prepare_reads(Session(fail_on=failure), 'a' * 40 + '-v8', 'b' * 64)


def test_expansion_failure_does_not_report_ready_and_closes_the_session():
    session = Session(fail_on=3)
    with pytest.raises(RuntimeError, match='synthetic graph read failure'):
        KnowledgeIndex(public_connection, Driver(session)).verify_ready(
            'a' * 40 + '-v8'
        )
    assert session.closed and session.results[1].consumed
    assert session.transaction_committed is False


@pytest.mark.parametrize(
    'subjects',
    [
        [{}],
        [{'name': ''}],
        [{'name': 42}],
        [{'name': 'a' * 257}],
        [{'name': 'name'}] * 4,
    ],
)
def test_probe_rejects_invalid_or_unbounded_graph_subjects(subjects):
    session = Session(subjects=subjects)
    with pytest.raises(ValueError, match='invalid public graph subject'):
        probe_reads(session, 'a' * 40 + '-v8', 'b' * 64)
    assert len(session.calls) == 1


def test_probe_requires_the_matching_postgres_document_in_the_graph():
    session = Session(subjects=[])
    with pytest.raises(ValueError, match='public graph projection unavailable'):
        probe_reads(session, 'a' * 40 + '-v8', 'b' * 64)
    assert len(session.calls) == 1 and session.transaction_committed is False


def test_documented_repository_only_corpus_needs_no_professional_entities():
    session = Session(subjects=[{'name': None}])
    probe_reads(session, 'a' * 40 + '-v8', 'b' * 64)
    assert session.transaction_committed is True
    assert all(parameters['names'] == [] for _, parameters in session.calls[1:])


def test_foreground_reads_remain_single_attempt_and_two_seconds():
    session = Session()
    driver = Driver(session)
    result = asyncio.run(
        KnowledgeIndex(None, driver).relationships(
            'a' * 40 + '-v8', {'alpha'}, 'es', expand=True
        )
    )
    assert result == ('source',)
    assert driver.configuration['disable_auto_commit_retries'] is True
    assert driver.configuration['default_access_mode'] == READ_ACCESS
    assert len(session.calls) == 2
    assert all(query.timeout == 2 for query, _ in session.calls)


def test_index_driver_explicitly_disables_implicit_retries_and_vendor_telemetry(
    monkeypatch,
):
    captured = {}

    def create(uri, **configuration):
        captured.update(configuration)
        return object()

    monkeypatch.setattr(GraphDatabase, 'driver', create)
    graph_driver(
        SimpleNamespace(
            neo4j_uri='bolt://fixture.invalid',
            neo4j_user='fixture',
            neo4j_password='fixture',
        )
    )
    assert captured['disable_auto_commit_retries'] is True
    assert captured['telemetry_disabled'] is True
    assert captured['max_transaction_retry_time'] == 0
