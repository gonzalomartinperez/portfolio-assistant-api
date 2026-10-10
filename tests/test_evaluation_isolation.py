"""Evaluation must fail before opening clients when either target is unverifiable."""

from copy import deepcopy

import pytest

from app.bootstrap.config import Settings
from scripts.evaluation_isolation import EvaluationContainer, validate_targets


def config(**kwargs):
    return Settings(
        _env_file=None,
        database_url='postgresql://assistant:assistant@127.0.0.1:55444/assistant',
        neo4j_uri='bolt://127.0.0.1:57694',
        **kwargs,
    )


@pytest.fixture
def containers(monkeypatch):
    monkeypatch.setenv('COMPOSE_PROJECT_NAME', 'eval-tests')
    for name in (
        'EVALUATION_POSTGRES_CONTAINER',
        'EVALUATION_NEO4J_CONTAINER',
        'GITHUB_ACTIONS',
    ):
        monkeypatch.delenv(name, raising=False)
    return [
        {
            'Id': letter * 64,
            'Config': {
                'Image': image,
                'Labels': {
                    'com.docker.compose.project': 'eval-tests',
                    'com.docker.compose.service': service,
                },
            },
            'State': {'Running': True},
            'NetworkSettings': {
                'Ports': {port: [{'HostIp': '127.0.0.1', 'HostPort': host}]}
            },
        }
        for letter, image, service, port, host in (
            ('a', 'pgvector/pgvector:fixture', 'postgres', '5432/tcp', '55444'),
            ('b', 'neo4j:fixture', 'neo4j', '7687/tcp', '57694'),
        )
    ]


def inspect(data):
    return lambda names: [EvaluationContainer.model_validate(item) for item in data]


def test_valid_owned_loopback_targets(containers):
    validate_targets(config(), inspect=inspect(containers))


@pytest.mark.parametrize('target', ['postgres', 'neo4j'])
def test_remote_target_fails_before_docker_or_client_creation(target, containers):
    settings = config().model_copy(
        update={
            'database_url'
            if target == 'postgres'
            else 'neo4j_uri': 'postgresql://private-value@remote.example/assistant'
            if target == 'postgres'
            else 'bolt://remote.example:7687',
        }
    )

    def forbidden(names):
        raise AssertionError('must fail before inspecting containers')

    with pytest.raises(ValueError) as error:
        validate_targets(settings, inspect=forbidden)
    assert 'private-value' not in str(error.value)


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize(
    'fault', ['wrong-project', 'wrong-port', 'stopped', 'public-binding', 'wrong-image']
)
def test_unverifiable_service_rejected(index, fault, containers):
    data = deepcopy(containers)
    target = data[index]
    if fault == 'wrong-project':
        target['Config']['Labels']['com.docker.compose.project'] = 'another-agent'
    elif fault == 'wrong-port':
        next(iter(target['NetworkSettings']['Ports'].values()))[0]['HostPort'] = '1'
    elif fault == 'stopped':
        target['State']['Running'] = False
    elif fault == 'public-binding':
        next(iter(target['NetworkSettings']['Ports'].values())).append(
            {'HostIp': '0.0.0.0', 'HostPort': '55444'}
        )
    else:
        target['Config']['Image'] = 'unrelated:latest'
    with pytest.raises(ValueError):
        validate_targets(config(), inspect=inspect(data))


def test_github_services_require_explicit_ids_and_matching_ports(
    monkeypatch, containers
):
    monkeypatch.delenv('COMPOSE_PROJECT_NAME')
    with pytest.raises(ValueError, match='exact container IDs'):
        validate_targets(config(), inspect=inspect(containers))
    monkeypatch.setenv('EVALUATION_POSTGRES_CONTAINER', 'a' * 64)
    monkeypatch.setenv('EVALUATION_NEO4J_CONTAINER', 'b' * 64)
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    for target in containers:
        next(iter(target['NetworkSettings']['Ports'].values()))[0]['HostIp'] = '0.0.0.0'
        target['Config']['Labels'] = None
    validate_targets(config(), inspect=inspect(containers))


def test_duplicate_container_is_not_two_isolated_services(containers):
    containers[1]['Id'] = containers[0]['Id']
    with pytest.raises(ValueError, match='distinct'):
        validate_targets(config(), inspect=inspect(containers))


def test_declared_id_cannot_resolve_to_another_container(monkeypatch, containers):
    monkeypatch.delenv('COMPOSE_PROJECT_NAME')
    monkeypatch.setenv('EVALUATION_POSTGRES_CONTAINER', 'c' * 64)
    monkeypatch.setenv('EVALUATION_NEO4J_CONTAINER', 'b' * 64)
    with pytest.raises(ValueError, match='declared ID'):
        validate_targets(config(), inspect=inspect(containers))


def test_production_rejected_before_inspection(containers):
    with pytest.raises(ValueError, match='local development'):
        validate_targets(
            config().model_copy(update={'environment': 'production'}),
            inspect=inspect(containers),
        )
