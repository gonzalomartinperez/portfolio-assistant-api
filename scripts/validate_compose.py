"""Verify local resource limits and the frozen shared-stack transfer reference."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    local = json.loads(
        subprocess.check_output(
            ['docker', 'compose', 'config', '--format', 'json'], text=True
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
        assert '@sha256:' in service['image']
    assert 'shared_buffers=128MB' in local['services']['postgres']['command']
    assert 'max_connections=50' in local['services']['postgres']['command']
    with tempfile.TemporaryDirectory() as directory:
        private = Path(directory, 'fixture.env')
        private.write_text('POSTGRES_USER=fixture\nPOSTGRES_DB=fixture\n')
        env = {
            **os.environ,
            'API_IMAGE': 'example.invalid/api@sha256:' + 'a' * 64,
            'WEB_IMAGE': 'example.invalid/web@sha256:' + 'b' * 64,
            'TLS_DIRECTORY': directory,
            **dict.fromkeys(
                (
                    'API_ENV_FILE',
                    'MIGRATION_ENV_FILE',
                    'POSTGRES_ENV_FILE',
                    'NEO4J_ENV_FILE',
                ),
                str(private),
            ),
        }
        data = json.loads(
            subprocess.check_output(
                [
                    'docker',
                    'compose',
                    '-f',
                    'deploy/compose.yaml',
                    '--profile',
                    'edge',
                    '--profile',
                    'maintenance',
                    'config',
                    '--format',
                    'json',
                ],
                env=env,
                text=True,
            )
        )
        services = data['services']
        assert {name for name, service in services.items() if service.get('ports')} == {
            'proxy'
        }
        assert data['networks']['data']['internal'] is True
        for name, service in services.items():
            assert 'container_name' not in service
            assert int(service['mem_limit']) > 0
            assert service['logging']['options']['max-file'] == '3'
            if name in ('postgres', 'neo4j'):
                assert set(service['networks']) == {'data'}
            else:
                assert service['read_only'] is True
                assert 'ALL' in service['cap_drop']
        assert services['migrate']['profiles'] == ['maintenance']
        assert '--no-proxy-headers' in services['api']['command']
    print(
        'Local Compose: loopback-only, bounded resources/logs. '
        'Frozen transfer reference: private data services and hardened containers.'
    )


if __name__ == '__main__':
    main()
