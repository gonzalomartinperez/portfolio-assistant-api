"""Verify isolated local resources; production composition belongs to vps-ops."""

import json
import re
import subprocess
from pathlib import Path


def validate_postgres_recipe(source: str) -> None:
    stages = re.findall(r'^FROM (.+)$', source, re.MULTILINE)
    if (
        len(stages) != 2
        or not re.fullmatch(
            r'postgres:18\.6-alpine3\.24@sha256:[a-f0-9]{64} AS vector-build',
            stages[0],
        )
        or stages[1] != stages[0].removesuffix(' AS vector-build')
    ):
        raise ValueError(
            'PostgreSQL builder and runtime must share the pinned supported base'
        )
    required = (
        'https://codeload.github.com/pgvector/pgvector/tar.gz/refs/tags/v0.8.7',
        'cac0b10c360f05b2d521200105ba3697e773d4cd3731f5a915a7e37ebe0bea85  /tmp/pgvector.tar.gz',
        'sha256sum -c -',
        'make -j1 OPTFLAGS=""',
        'make DESTDIR=/extension install',
        'COPY --from=vector-build /extension/ /',
        'USER 70:70',
    )
    if any(value not in source for value in required) or any(
        value in source
        for value in ('-march=native', '--without-libxml', '--without-icu')
    ):
        raise ValueError(
            'PostgreSQL extension provenance, portability or runtime identity changed'
        )
    runtime = source.split('\nFROM ', 1)[1]
    if re.search(r'\b(?:build-base|clang21|llvm21-dev)\b', runtime):
        raise ValueError('PostgreSQL runtime must not install builder dependencies')


def main():
    local = json.loads(
        subprocess.check_output(
            [
                'docker',
                'compose',
                '-f',
                'infra/compose/local.yaml',
                'config',
                '--format',
                'json',
            ],
            text=True,
        )
    )
    for service in local['services'].values():
        assert 'container_name' not in service
        assert service['mem_limit'] == service['memswap_limit']
        assert int(service['mem_limit']) > 0
        assert float(service['cpus']) > 0
        assert int(service['pids_limit']) > 0
        assert service['logging']['driver'] == 'local'
        assert service['logging']['options']['max-file'] == '3'
        assert 'no-new-privileges:true' in service['security_opt']
        assert all(port['host_ip'] == '127.0.0.1' for port in service['ports'])
        if service['image'] == 'portfolio-assistant-postgres:18.6':
            assert service['build']['dockerfile'] == 'infra/docker/postgres/Dockerfile'
            validate_postgres_recipe(
                Path('infra/docker/postgres/Dockerfile').read_text()
            )
        else:
            assert '@sha256:' in service['image']
    assert 'shared_buffers=128MB' in local['services']['postgres']['command']
    assert 'max_connections=50' in local['services']['postgres']['command']
    for setting in (
        'NEO4J_dbms_usage__report_enabled',
        'NEO4J_server_bolt_telemetry_enabled',
    ):
        assert local['services']['neo4j']['environment'].get(setting) == 'false'
    print('Local Compose: root build context, loopback-only, bounded resources/logs.')


if __name__ == '__main__':
    main()
