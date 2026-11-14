"""Canonical recipes preserve root contexts, resources and deployment ownership."""

import hashlib
import re

import pytest
import yaml

from scripts.validate_compose import validate_postgres_recipe
from tests.support import ROOT


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
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['container']['steps']
    builds = [
        step['with']
        for step in steps
        if step.get('uses', '').startswith('docker/build-push-action@')
    ]
    assert len(builds) == 3
    assert {build['file'] for build in builds} == {
        'infra/docker/app/Dockerfile',
        'infra/docker/postgres/Dockerfile',
    }
    assert sorted(build['target'] for build in builds if 'target' in build) == [
        'api',
        'worker',
    ]
    for build in builds:
        assert build['context'] == '.'
        assert build['load'] is True
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


APP_DOCKERFILE = ROOT / 'infra/docker/app/Dockerfile'


def app_stages() -> dict[str, str]:
    """Map each stage name to its instructions, in declaration order."""
    stages: dict[str, str] = {}
    name = ''
    for line in APP_DOCKERFILE.read_text().splitlines():
        match = re.match(r'FROM\s+\S+\s+AS\s+(\S+)', line)
        if match:
            name = match.group(1)
            stages[name] = ''
        elif name:
            stages[name] += line + '\n'
    return stages


def test_app_dockerfile_has_ordered_targets_with_api_last():
    assert list(app_stages()) == ['base', 'build', 'worker', 'api']


def test_app_dockerfile_pins_every_base_and_syntax_by_digest():
    text = APP_DOCKERFILE.read_text()
    assert re.match(r'# syntax=docker/dockerfile:1@sha256:[0-9a-f]{64}\n', text)
    stages = app_stages()
    images = [
        source
        for source in re.findall(r'^FROM\s+(\S+)', text, re.MULTILINE)
        if source not in stages
    ] + re.findall(r'COPY --from=(\S+:\S+)', text)
    assert len(images) == 2
    for image in images:
        assert re.search(r'@sha256:[0-9a-f]{64}$', image)
        assert ':latest' not in image


def test_app_dockerfile_cache_id_is_owned_by_this_repository():
    text = APP_DOCKERFILE.read_text()
    assert 'vps-ops' not in text
    assert 'id=portfolio-assistant-api-uv-py314,' in text
    assert '--no-install-project' in text
    assert '--locked --no-dev' in text


def test_git_is_installed_only_in_the_worker_stage():
    stages = app_stages()
    for name in ('base', 'build', 'api'):
        assert not re.search(r'\bgit=', stages[name])
    assert 'git=' in stages['worker']
    assert 'CMD ["assistant-knowledge-watch"]' in stages['worker']
    assert 'CMD ["assistant-api"]' in stages['api']


def test_api_stage_runs_unprivileged_with_readyz_and_labels():
    api = app_stages()['api']
    assert 'USER 65532:65532' in api
    assert 'STOPSIGNAL SIGTERM' in api
    assert 'EXPOSE 8000' in api
    assert 'http://127.0.0.1:8000/readyz' in api
    for key in ('title', 'source', 'version', 'revision', 'created', 'licenses'):
        assert f'org.opencontainers.image.{key}=' in api
    assert 'org.opencontainers.image.title="portfolio-assistant-api"' in api
    assert 'USER 65532:65532' in app_stages()['worker']
    assert 'portfolio-assistant-api-worker' in app_stages()['worker']


def test_bake_file_defines_both_targets_for_the_app_recipe():
    bake = (ROOT / 'docker-bake.hcl').read_text()
    assert 'targets = ["api", "worker"]' in bake
    for target in ('api', 'worker'):
        block = bake.split(f'target "{target}" {{')[1].split('\n}\n')[0]
        assert 'dockerfile = "infra/docker/app/Dockerfile"' in block
        assert f'target     = "{target}"' in block
        assert 'platforms  = ["linux/amd64"]' in block
    for variable in ('VERSION', 'REVISION', 'SOURCE_DATE_EPOCH'):
        assert f'variable "{variable}"' in bake


def test_structure_tests_match_each_image_target():
    api = yaml.safe_load(
        (ROOT / 'infra/docker/app/container-structure-test.yaml').read_text()
    )
    worker = yaml.safe_load(
        (ROOT / 'infra/docker/app/container-structure-test.worker.yaml').read_text()
    )
    assert api['schemaVersion'] == worker['schemaVersion'] == '2.0.0'
    assert api['metadataTest']['cmd'] == ['assistant-api']
    assert worker['metadataTest']['cmd'] == ['assistant-knowledge-watch']
    present = {t['path']: t['shouldExist'] for t in api['fileExistenceTests']}
    assert present['/usr/bin/git'] is False
    assert present['/usr/local/bin/pip'] is False
    assert present['/app/.venv/bin/assistant-api'] is True
    worker_present = {t['path']: t['shouldExist'] for t in worker['fileExistenceTests']}
    assert worker_present['/usr/bin/git'] is True
