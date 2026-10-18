"""Bind isolated CI evidence to its actual source and reviewed build inputs."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BUILD_INPUTS = (
    'infra/docker/app/Dockerfile',
    'infra/docker/app/Dockerfile.dockerignore',
    'infra/docker/postgres/Dockerfile',
    'infra/docker/postgres/Dockerfile.dockerignore',
    'infra/compose/local.yaml',
    'pyproject.toml',
    'uv.lock',
)


def identity(root: Path, env: dict[str, str]) -> dict:
    source = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    if env.get('GITHUB_SHA') != source:
        raise ValueError('CI source revision does not match the checked-out candidate')
    workflow = env.get('GITHUB_WORKFLOW_SHA', '')
    base = env.get('CI_BASE_SHA', '')
    if not re.fullmatch(r'[a-f0-9]{40}', workflow) or (
        base and not re.fullmatch(r'[a-f0-9]{40}', base)
    ):
        raise ValueError('CI workflow/base identity is invalid')
    for name in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'):
        if not re.fullmatch(r'[1-9][0-9]*', env.get(name, '')):
            raise ValueError('CI run identity is invalid')
    hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in BUILD_INPUTS
    }
    return {
        'schema_version': 1,
        'source_sha': source,
        'base_sha': base or None,
        'workflow_sha': workflow,
        'run_id': env['GITHUB_RUN_ID'],
        'run_attempt': env['GITHUB_RUN_ATTEMPT'],
        'job': env.get('GITHUB_JOB'),
        'platform': {
            'os': env.get('RUNNER_OS'),
            'architecture': env.get('RUNNER_ARCH'),
        },
        'build_inputs_sha256': hashes,
        'image_transport': 'none; isolated same-source rebuild where needed',
    }


def clean_build_inputs(root: Path) -> bool:
    result = subprocess.run(
        [
            'git',
            '-C',
            str(root),
            'diff',
            '--quiet',
            'HEAD',
            '--',
            'app',
            'infra',
            'migrations',
            'contracts',
            'pyproject.toml',
            'uv.lock',
        ],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', action='append', default=[])
    args = parser.parse_args()
    if not clean_build_inputs(Path.cwd()):
        raise ValueError('CI build inputs differ from the reviewed candidate')
    report = identity(Path.cwd(), dict(os.environ))
    images = {}
    for image in args.image:
        if not re.fullmatch(r'portfolio-assistant-(?:api|postgres):[a-z0-9.-]+', image):
            raise ValueError('Unexpected CI image reference')
        image_id = subprocess.check_output(
            ['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], text=True
        ).strip()
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', image_id):
            raise ValueError('Invalid inspected CI image identity')
        images[image] = image_id
    report['images'] = images
    destination = Path('artifacts/ci-identity.json')
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, sort_keys=True) + '\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
