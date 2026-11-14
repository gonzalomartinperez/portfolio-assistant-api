"""Rebuild or verify the frozen public corpus snapshot under evals/corpus (ADR016)."""

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from app.adapters.portfolio.indexing import ALLOWED_REMOTES, ROOT_PATTERNS, git
from app.domain.portfolio_paths import canonical_key

CORPUS = Path('evals/corpus')
MANIFEST = 'manifest.json'
REPOSITORY = 'gonzalomartinperez/portfolio'


def snapshot_id(files: list[dict]) -> str:
    pairs = sorted((item['path'], item['sha256']) for item in files)
    digest = hashlib.sha256(json.dumps(pairs, separators=(',', ':')).encode())
    return 'corpus-' + digest.hexdigest()[:12]


def entry(path: str, data: bytes) -> dict:
    return {
        'path': path,
        'key': canonical_key(path),
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes': len(data),
    }


def read_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST).read_text())


def verify(root: Path) -> list[str]:
    """Return problems found; an empty list means the files match the manifest."""
    manifest = read_manifest(root)
    problems = []
    listed = {item['path'] for item in manifest['files']}
    for item in manifest['files']:
        target = root / item['path']
        if not target.is_file():
            problems.append(f'missing: {item["path"]}')
            continue
        current = entry(item['path'], target.read_bytes())
        if current != item:
            problems.append(f'changed: {item["path"]}')
    present = {
        path.relative_to(root).as_posix()
        for path in root.rglob('*')
        if path.is_file() and path.name != MANIFEST
    }
    problems += [f'unlisted: {path}' for path in sorted(present - listed)]
    if manifest['corpus_snapshot_id'] != snapshot_id(manifest['files']):
        problems.append('corpus_snapshot_id does not match the file hashes')
    return problems


def refresh(source: Path, ref: str, root: Path) -> None:
    remote = git(source, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in ALLOWED_REMOTES:
        raise SystemExit('only the public portfolio repository is allowed')
    commit = git(source, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')
    commit = commit.decode().strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise SystemExit('invalid commit')
    date = git(source, 'show', '-s', '--format=%cI', commit).decode().strip()
    files = []
    for line in git(source, 'ls-tree', '-r', '-z', commit).decode().split('\0'):
        if not line:
            continue
        metadata, path = line.split('\t', 1)
        mode, kind, _ = metadata.split()
        if any(pattern.fullmatch(path) for pattern in ROOT_PATTERNS):
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise SystemExit(f'unsupported file type: {path}')
            files.append(entry(path, git(source, 'show', f'{commit}:{path}')))
    if not files:
        raise SystemExit('no approved public files found')
    files.sort(key=lambda item: item['path'])
    before = (
        {item['key'] for item in read_manifest(root)['files']}
        if (root / MANIFEST).exists()
        else set()
    )
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.corpus-', dir=root.parent))
    for item in files:
        target = staging / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git(source, 'show', f'{commit}:{item["path"]}'))
    manifest = {
        'repository': REPOSITORY,
        'commit': commit,
        'date': date,
        'corpus_snapshot_id': snapshot_id(files),
        'files': files,
    }
    (staging / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    staging.chmod(0o755)
    backup = staging.with_name(staging.name + '.old')
    if root.exists():
        root.rename(backup)
    staging.rename(root)
    shutil.rmtree(backup, ignore_errors=True)
    after = {item['key'] for item in files}
    print(f'{manifest["corpus_snapshot_id"]} from {commit}')
    print('added keys:', ', '.join(sorted(after - before)) or '-')
    print('removed keys:', ', '.join(sorted(before - after)) or '-')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='portfolio checkout to read from')
    parser.add_argument('--ref', default='HEAD', help='portfolio commit to snapshot')
    parser.add_argument('--root', type=Path, default=CORPUS, help=argparse.SUPPRESS)
    parser.add_argument(
        '--check', action='store_true', help='verify committed files, no source needed'
    )
    args = parser.parse_args(argv)
    if args.check:
        problems = verify(args.root)
        for problem in problems:
            print(problem, file=sys.stderr)
        if not problems:
            print(read_manifest(args.root)['corpus_snapshot_id'], 'ok')
        return 1 if problems else 0
    if args.source is None:
        parser.error('--source is required unless --check is given')
    refresh(args.source, args.ref, args.root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
