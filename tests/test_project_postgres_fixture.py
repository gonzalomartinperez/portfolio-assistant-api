"""Fixture authority and target validation fail before database/client creation."""

from copy import deepcopy

import pytest

from scripts import project_postgres_fixture as fixture
from scripts.evaluation_isolation import EvaluationContainer


def metadata():
    return {
        'Id': 'a' * 64,
        'Config': {
            'Image': 'portfolio-assistant-postgres:synthetic-fixture',
            'Labels': {
                fixture.LABEL: 'owned',
                'org.opencontainers.image.source': fixture.SOURCE,
            },
        },
        'State': {'Running': True},
        'NetworkSettings': {
            'Ports': {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '59443'}]}
        },
    }


def test_owned_loopback_database_is_accepted():
    value = EvaluationContainer.model_validate(metadata())
    assert fixture.validate_container(value, 'a' * 64, 'owned') == 59443


@pytest.mark.parametrize(
    'fault', ['owner', 'identity', 'source', 'stopped', 'public', 'port', 'extra']
)
def test_unverified_database_is_rejected(fault):
    value = deepcopy(metadata())
    if fault == 'owner':
        value['Config']['Labels'][fixture.LABEL] = 'another-agent'
    elif fault == 'identity':
        value['Id'] = 'b' * 64
    elif fault == 'source':
        value['Config']['Labels']['org.opencontainers.image.source'] = (
            'https://untrusted.invalid'
        )
    elif fault == 'stopped':
        value['State']['Running'] = False
    elif fault == 'public':
        value['NetworkSettings']['Ports']['5432/tcp'][0]['HostIp'] = '0.0.0.0'
    elif fault == 'port':
        value['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'] = '0'
    else:
        value['NetworkSettings']['Ports']['5432/tcp'].append(
            {'HostIp': '::', 'HostPort': '59443'}
        )
    with pytest.raises(ValueError):
        fixture.validate_container(
            EvaluationContainer.model_validate(value), 'a' * 64, 'owned'
        )


@pytest.mark.parametrize('authorized,paid', [(False, False), (True, True)])
def test_missing_authority_or_paid_configuration_never_reaches_docker(
    monkeypatch, authorized, paid
):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid fixture prerequisites reached Docker')

    monkeypatch.setattr(fixture, 'docker', forbidden)
    monkeypatch.setenv('AI_PROVIDER', 'openai' if paid else 'fixture')
    with (
        pytest.raises(ValueError),
        fixture.project_fixture(
            'portfolio-assistant-postgres:synthetic-fixture', authorized=authorized
        ),
    ):
        pytest.fail('invalid prerequisites opened a fixture')


def test_provider_environment_is_rejected_before_docker(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('provider environment reached Docker')

    monkeypatch.setattr(fixture, 'docker', forbidden)
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-fixture-marker')
    with (
        pytest.raises(ValueError, match='without provider credentials'),
        fixture.project_fixture(
            'portfolio-assistant-postgres:synthetic-fixture', authorized=True
        ),
    ):
        pytest.fail('provider environment opened a fixture')


def test_cleanup_never_removes_same_named_foreign_resource(monkeypatch):
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        return (
            b'owned-name\n'
            if args[1] == 'ls'
            else b'{"io.gmperez.portfolio-project-fixture":"another-agent"}'
        )

    monkeypatch.setattr(fixture, 'docker', command)
    with pytest.raises(ValueError, match='unverified fixture resource'):
        fixture.remove_owned('volume', 'owned-name', 'expected')
    assert not any(args[1] == 'rm' for args in calls)


def test_cleanup_of_absent_resource_is_idempotent(monkeypatch):
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        return b''

    monkeypatch.setattr(fixture, 'docker', command)
    fixture.remove_owned('container', 'owned-name', 'expected')
    assert len(calls) == 1 and calls[0][1] == 'ls'
