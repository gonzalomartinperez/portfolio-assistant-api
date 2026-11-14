"""Breaking-change gate for the public contracts (expand-then-contract).

OpenAPI is compared with oasdiff (`breaking --fail-on ERR`); the SSE JSON Schema is compared with a
stdlib check that flags a removed event name or a removed required field. Both compare the working
tree with the pull request base. The `contract-major` label (CONTRACT_MAJOR=true) accepts a break:
the findings are still printed, the exit status is 0, and cross-repo consumers must follow
(docs/ci.md, "Cross-repo consumer job").
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OPENAPI = 'contracts/openapi.json'
SSE = 'contracts/sse.schema.json'


def resolve(schema: dict, node: dict) -> dict:
    ref = node.get('$ref')
    return schema['$defs'][ref.rsplit('/', 1)[-1]] if ref else node


def sse_shape(schema: dict) -> dict[str, set[str]]:
    """Map each event name to its required envelope and payload fields."""
    shape = {}
    for option in schema['oneOf']:
        event = resolve(schema, option)
        properties = event['properties']
        fields = {f'{name}' for name in event.get('required', [])}
        payload = resolve(schema, properties['payload'])
        fields |= {f'payload.{name}' for name in payload.get('required', [])}
        shape[properties['type']['const']] = fields
    return shape


def sse_breaking(base: dict, head: dict) -> list[str]:
    """Removed event names and removed required fields; additions are always allowed."""
    old, new = sse_shape(base), sse_shape(head)
    problems = [f'SSE event removed: {name}' for name in sorted(set(old) - set(new))]
    for name in sorted(set(old) & set(new)):
        problems += [
            f'SSE required field removed: {name}.{field}'
            for field in sorted(old[name] - new[name])
        ]
    return problems


def git_show(sha: str, path: str) -> str:
    return subprocess.run(
        ['git', 'show', f'{sha}:{path}'], check=True, capture_output=True, text=True
    ).stdout


def openapi_breaking(base: Path, head: Path) -> subprocess.CompletedProcess:
    binary = shutil.which('oasdiff')
    if binary is None:
        raise SystemExit(
            'oasdiff is not on PATH; install the pinned release (docs/ci.md)'
        )
    return subprocess.run(
        [binary, 'breaking', str(base), str(head), '--fail-on', 'ERR'],
        capture_output=True,
        check=False,
        text=True,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--head-root', default='.')
    parser.add_argument(
        '--major',
        action='store_true',
        default=os.environ.get('CONTRACT_MAJOR') == 'true',
        help='the pull request carries the contract-major label',
    )
    args = parser.parse_args(argv)
    root = Path(args.head_root)
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        base_openapi = Path(tmp, 'openapi.base.json')
        base_openapi.write_text(git_show(args.base_sha, OPENAPI))
        result = openapi_breaking(base_openapi, root / OPENAPI)
        print(result.stdout + result.stderr, end='')
        if result.returncode:
            failures.append('OpenAPI breaking changes (oasdiff)')
    sse = sse_breaking(
        json.loads(git_show(args.base_sha, SSE)), json.loads((root / SSE).read_text())
    )
    print('\n'.join(sse))
    if sse:
        failures.append('SSE breaking changes')
    if failures and args.major:
        print(f'contract-major label present; accepted: {", ".join(failures)}')
        return 0
    if failures:
        print(
            f'Blocked: {", ".join(failures)}. Expand then contract, or label the PR '
            'contract-major and update the consumers.',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
