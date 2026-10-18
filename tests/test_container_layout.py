"""Canonical recipes preserve root contexts, resources and deployment ownership."""

import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.validate_compose import validate_postgres_recipe

ROOT = Path(__file__).parents[1]


def test_actual_recipes_have_separate_deny_default_contexts():
    for service in ('app', 'postgres'):
        recipe = ROOT / f'infra/docker/{service}/Dockerfile'
        assert recipe.is_file()
        ignore = recipe.with_name('Dockerfile.dockerignore').read_text()
        patterns = [
            line for line in ignore.splitlines() if line and not line.startswith('#')
        ]
        assert patterns[0] == '*'
        assert '**/.env*' in patterns
        assert '**/*.key' in patterns
        assert '!**' not in patterns
        assert '!artifacts/' not in patterns
        assert '!tests/' not in patterns
    assert not (ROOT / 'Dockerfile').exists()
    assert not (ROOT / 'Dockerfile.postgres').exists()
    assert not (ROOT / 'infra/docker/neo4j').exists()
    assert [
        line
        for line in (ROOT / '.dockerignore').read_text().splitlines()
        if line and not line.startswith('#')
    ] == ['*']


def test_local_compose_context_resolves_to_repository_root():
    source = ROOT / 'infra/compose/local.yaml'
    local = yaml.safe_load(source.read_text())
    assert local['name'] == 'portfolio-assistant-local'
    build = local['services']['postgres']['build']
    context = (source.parent / build['context']).resolve()
    assert context == ROOT
    assert context / build['dockerfile'] == ROOT / 'infra/docker/postgres/Dockerfile'
    assert '@sha256:' in local['services']['neo4j']['image']
    assert not (ROOT / 'compose.yaml').exists()


def test_workflow_builds_the_explicit_application_recipe():
    workflow = yaml.safe_load((ROOT / '.github/workflows/quality.yml').read_text())
    steps = workflow['jobs']['container']['steps']
    builds = [
        step['with']
        for step in steps
        if step.get('uses', '').startswith('docker/build-push-action@')
    ]
    assert len(builds) == 1
    assert builds[0]['context'] == '.'
    assert builds[0]['file'] == 'infra/docker/app/Dockerfile'
    assert builds[0]['load'] is True
    for step in steps:
        if 'docker compose' in step.get('run', ''):
            for line in step['run'].splitlines():
                if 'docker compose' in line:
                    assert '-f infra/compose/local.yaml' in line


def test_no_competing_production_controller_remains():
    for source in (
        'deploy/compose.yaml',
        'deploy/apply-release.sh',
        'deploy/nginx',
        '.github/workflow-templates/deploy-vps.yml',
    ):
        assert not (ROOT / source).exists()
    for source in ('nginx.conf', 'local-server.conf', 'api-proxy.conf', 'routes.conf'):
        assert (ROOT / 'tests/fixtures/proxy' / source).is_file()
    assert not (ROOT / 'tests/fixtures/proxy/server.conf').exists()


def test_postgres_bootstrap_resource_bytes_are_preserved():
    expected = {
        # Filled from the committed pre-move source, never from a live database.
        'project-postgres-bootstrap.psql': 'e8549aa4a3522b2cd32528b377c5d57e8c85bd7de9c0a771a6b662fa78261860',
        'project-pg_hba.conf': '66b44e8e9dbfc88b29a80f244944a2c671f41b28366bfe2d8d7ec6618e84b11d',
    }
    for filename, checksum in expected.items():
        assert (
            hashlib.sha256(
                (ROOT / 'infra/docker/postgres' / filename).read_bytes()
            ).hexdigest()
            == checksum
        )


def test_postgres_uses_one_supported_base_without_runtime_build_tools():
    validate_postgres_recipe((ROOT / 'infra/docker/postgres/Dockerfile').read_text())
    postgres = yaml.safe_load((ROOT / 'infra/compose/local.yaml').read_text())[
        'services'
    ]['postgres']
    assert postgres['volumes'] == ['postgres18_alpine_data:/var/lib/postgresql']
    assert postgres['healthcheck']['test'] == [
        'CMD',
        'pg_isready',
        '-h',
        '127.0.0.1',
        '-U',
        'assistant',
        '-d',
        'assistant',
    ]
    assert any('uid=70,gid=70' in mount for mount in postgres['tmpfs'])


@pytest.mark.parametrize(
    'old,new',
    [
        ('OPTFLAGS=""', 'OPTFLAGS="-march=native"'),
        ('sha256sum -c -', 'true'),
        ('USER 70:70', 'USER root'),
        ('USER 70:70', 'RUN apk add clang21\nUSER 70:70'),
        ('alpine3.24', 'edge'),
        ('COPY --from=vector-build /extension/ /', 'RUN apk add build-base'),
        ('make DESTDIR=/extension install', 'make install'),
    ],
)
def test_postgres_rejects_unverified_nonportable_or_privileged_recipe(old, new):
    source = (ROOT / 'infra/docker/postgres/Dockerfile').read_text()
    with pytest.raises(ValueError):
        validate_postgres_recipe(source.replace(old, new))
