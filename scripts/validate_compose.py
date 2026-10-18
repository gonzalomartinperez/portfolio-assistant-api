"""Verify isolated local resources; production composition belongs to vps-ops."""

import json
import re
import subprocess
from pathlib import Path


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
            base = Path('infra/docker/postgres/Dockerfile').read_text().splitlines()[0]
            assert re.fullmatch(
                r'FROM pgvector/pgvector:0\.8\.7-pg18@sha256:[a-f0-9]{64}', base
            )
        else:
            assert '@sha256:' in service['image']
    assert 'shared_buffers=128MB' in local['services']['postgres']['command']
    assert 'max_connections=50' in local['services']['postgres']['command']
    print('Local Compose: root build context, loopback-only, bounded resources/logs.')


if __name__ == '__main__':
    main()
