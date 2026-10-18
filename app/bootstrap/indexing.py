"""Explicit default wiring for the stable public-corpus operator command."""

import argparse
import json
import re
import tempfile
from functools import partial
from pathlib import Path
from threading import Event

from app.adapters.portfolio.indexing import git
from app.adapters.portfolio.indexing import sync as sync_projection
from app.adapters.postgres.db import connect
from app.bootstrap.config import settings


def sync(
    repo: Path, ref: str = 'HEAD', *, watched: bool = False, stop: Event | None = None
):
    config = settings()
    return sync_projection(
        repo,
        ref,
        configuration=config,
        connection=partial(connect, config.database_url),
        watched=watched,
        stop=stop,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--source', choices=['local', 'github'], default='local')
    parser.add_argument(
        '--ref', help='Local Git ref, or main/develop/full commit SHA for GitHub'
    )
    args = parser.parse_args()
    if args.source == 'local':
        if not args.repo:
            parser.error('--repo is required for local sync')
        result = sync(args.repo, args.ref or 'HEAD')
    else:
        ref = args.ref or 'main'
        if ref not in ('main', 'develop') and not re.fullmatch(r'[0-9a-f]{40}', ref):
            parser.error('GitHub ref must be main, develop or a full commit SHA')
        with tempfile.TemporaryDirectory(prefix='portfolio-public-sync-') as temp:
            repo = Path(temp) / 'gonzalomartinperez' / 'portfolio'
            repo.mkdir(parents=True)
            git(repo, 'init', '-q')
            git(
                repo,
                'remote',
                'add',
                'origin',
                'https://github.com/gonzalomartinperez/portfolio.git',
            )
            git(
                repo,
                '-c',
                'http.followRedirects=false',
                '-c',
                'protocol.allow=never',
                '-c',
                'protocol.https.allow=always',
                'fetch',
                '-q',
                '--depth=1',
                'origin',
                ref,
            )
            result = sync(repo, 'FETCH_HEAD')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
