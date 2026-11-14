"""Do not bootstrap against PostgreSQL's temporary initdb socket server."""

from scripts import project_postgres_fixture as fixture


def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(fixture.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(
        fixture.time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds)
    )
    return now


def test_readiness_waits_for_final_listener_and_tolerates_initdb_shutdown(monkeypatch):
    now = clock(monkeypatch)
    target = fixture.ProjectPostgres('a' * 64, 'b' * 32, {})
    states = iter([b'\n', fixture.FixtureCommandError('private-sentinel'), b'*\n'])
    calls = []

    def query(statement, *, timeout):
        calls.append((statement, timeout))
        result = next(states)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(target, 'owner_sql', query)
    fixture.wait_for_postmaster(target)
    assert calls == [('SHOW listen_addresses', 3)] * 3
    assert now[0] == 1


def test_temporary_server_never_counts_as_ready_and_timeout_is_redacted(monkeypatch):
    import pytest

    now = clock(monkeypatch)
    target = fixture.ProjectPostgres('a' * 64, 'b' * 32, {})
    monkeypatch.setattr(target, 'owner_sql', lambda *args, **kwargs: b'\n')
    with pytest.raises(
        ValueError, match='owned PostgreSQL fixture did not become ready'
    ):
        fixture.wait_for_postmaster(target)
    assert now[0] == 30
