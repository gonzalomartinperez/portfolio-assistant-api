"""Scan tracked Git history/worktree with redacted output; never emit matched bytes."""

import json
import re
import subprocess
from pathlib import Path

PATTERNS = {
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'aws_access_key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github_token': re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    'github_fine_grained_token': re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    'openai_token': re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b'),
}


def matches(data: bytes) -> list[str]:
    """Return detector names only, never suspected secrets or source excerpts."""
    return [name for name, pattern in PATTERNS.items() if pattern.search(data)]


def main():
    objects = subprocess.check_output(
        ['git', 'rev-list', '--objects', '--all']
    ).splitlines()
    paths = {}
    for item in objects:
        oid, _, path = item.partition(b' ')
        paths[oid.decode()] = path.decode(errors='replace')
    info = subprocess.check_output(
        ['git', 'cat-file', '--batch-check'], input=('\n'.join(paths) + '\n').encode()
    ).splitlines()
    findings = []
    scanned = 0
    for item in info:
        oid, kind, _ = item.decode().split()
        if kind != 'blob':
            continue
        data = subprocess.check_output(['git', 'cat-file', 'blob', oid])
        scanned += 1
        for detector in matches(data):
            findings.append({'object': oid, 'path': paths[oid], 'detector': detector})
    tracked = subprocess.check_output(['git', 'ls-files', '-z']).split(b'\0')
    for name in tracked:
        if name and Path(name.decode()).is_file():
            for detector in matches(Path(name.decode()).read_bytes()):
                findings.append(
                    {
                        'path': name.decode(),
                        'detector': detector,
                        'location': 'worktree',
                    }
                )
    print(
        json.dumps(
            {
                'history_blobs_scanned': scanned,
                'findings': findings,
                'scope': 'Known credential patterns only; no values printed. Not proof that no secrets exist.',
            },
            indent=2,
        )
    )
    if findings:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
