"""Explicit, bounded sync of approved files from the public portfolio repository."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from itertools import pairwise
from pathlib import Path
from urllib.parse import quote

from neo4j import GraphDatabase

from app.bootstrap.config import settings
from app.infrastructure.db import connect
from app.infrastructure.embedding import embed
from app.infrastructure.graph import project

ROOT_PATTERNS = (
    re.compile(r'^src/content/(en|es)/(profile|experience|projects|education)\.ts$'),
    re.compile(r'^docs/(development|public-content|editorial-guidelines)\.md$'),
    re.compile(r'^README\.md$'),
)
SECRET_PATTERN = re.compile(
    r'(?i)(api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|BEGIN [A-Z ]+PRIVATE KEY)'
)
MAX_FILES = 80
MAX_BYTES = 60_000
CHUNKER_VERSION = 'sections35-v6'


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ['git', '-C', str(repo), *args],
        timeout=30,
        env={
            'PATH': os.defpath,
            'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_TERMINAL_PROMPT': '0',
        },
    )


def manifest_at_commit(repo: Path, commit: str):
    listed = git(repo, 'ls-tree', '-r', commit).decode().splitlines()
    allowed = []
    for line in listed:
        metadata, path = line.split('\t', 1)
        mode, kind, blob_sha = metadata.split()
        if any(pattern.fullmatch(path) for pattern in ROOT_PATTERNS):
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError(f'unsupported file type: {path}')
            allowed.append((path, blob_sha))
    if len(allowed) > MAX_FILES:
        raise ValueError('file limit exceeded')
    return allowed


def citation_url(commit: str, path: str, start: int, end: int):
    return f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{quote(path, safe="/")}#L{start}-L{end}'


def chunk_id(commit: str, path: str, start: int, content_hash: str):
    return hashlib.sha256(
        f'{CHUNKER_VERSION}:{commit}:{path}:{start}:{content_hash}'.encode()
    ).hexdigest()


def chunks(path: str, content: str, commit: str):
    lines = content.splitlines()
    boundaries = [0]
    if path.endswith('.md'):
        boundaries.extend(
            index
            for index, line in enumerate(lines)
            if index > 0 and re.match(r'^#{1,6} ', line)
        )
    boundaries.append(len(lines))
    for section_start, section_end in pairwise(boundaries):
        for start in range(section_start, section_end, 35):
            end = min(start + 35, section_end)
            block = '\n'.join(lines[start:end]).strip()
            if len(block) < 30:
                continue
            content_hash = hashlib.sha256(block.encode()).hexdigest()
            yield {
                'id': chunk_id(commit, path, start + 1, content_hash),
                'content': block,
                'title': path,
                'url': citation_url(commit, path, start + 1, end),
                'source_type': 'code' if path.endswith(('.ts', '.tsx')) else 'page',
                'path': path,
                'start_line': start + 1,
                'end_line': end,
                'content_hash': content_hash,
                'embedding': embed(block),
            }


def reused_record(old: dict, commit: str):
    path = old['path']
    return {
        **old,
        'id': chunk_id(commit, path, old['start_line'], old['content_hash']),
        'url': citation_url(commit, path, old['start_line'], old['end_line']),
    }


def sync(repo: Path, ref: str = 'HEAD'):
    # The lock spans both projections; only activation changes the authoritative pointer.
    with connect() as lock:
        lock.execute('SELECT pg_advisory_xact_lock(472022)')
        return _sync(repo, ref)


def _sync(repo: Path, ref: str):
    repo = repo.resolve(strict=True)
    remote = git(repo, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in (
        'https://github.com/gonzalomartinperez/portfolio',
        'https://github.com/gonzalomartinperez/portfolio.git',
        'git@github.com:gonzalomartinperez/portfolio.git',
    ):
        raise ValueError('only the public portfolio repository is allowed')
    commit = (
        git(repo, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')
        .decode()
        .strip()
    )
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('invalid commit')
    version = commit + '-v6'
    files = manifest_at_commit(repo, commit)
    with connect() as conn:
        existing = conn.execute(
            'SELECT status FROM knowledge_versions WHERE id=%s', (version,)
        ).fetchone()
        if existing and existing['status'] == 'active':
            return {'knowledge_version': version, 'changed': False, 'files': len(files)}
        previous = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        previous_version = previous['id'] if previous else None
        old_files = (
            {
                row['path']: row
                for row in conn.execute(
                    'SELECT * FROM source_files WHERE knowledge_version=%s',
                    (previous_version,),
                ).fetchall()
            }
            if previous_version
            else {}
        )
    file_manifest = []
    records = []
    documents = {}
    embedded_chunks = 0
    reused_files = 0
    for path, blob_sha in files:
        size = int(git(repo, 'cat-file', '-s', blob_sha))
        if size > MAX_BYTES:
            raise ValueError('source size limit exceeded')
        data = git(repo, 'cat-file', 'blob', blob_sha)
        content = data.decode('utf-8')
        if SECRET_PATTERN.search(content):
            raise ValueError(f'possible secret in {path}')
        documents[path] = content
        old_file = old_files.get(path)
        quality = f'{"markdown_sections" if path.endswith(".md") else "text_fallback"}:{CHUNKER_VERSION}'
        if (
            old_file
            and old_file['blob_sha'] == blob_sha
            and old_file['parser_quality'] == quality
        ):
            with connect() as conn:
                old_chunks = conn.execute(
                    'SELECT * FROM chunks WHERE knowledge_version=%s AND path=%s ORDER BY start_line',
                    (previous_version, path),
                ).fetchall()
            records.extend(reused_record(row, commit) for row in old_chunks)
            file_manifest.append(
                {
                    'path': path,
                    'blob_sha': blob_sha,
                    'sha256': old_file['sha256'],
                    'bytes': old_file['bytes'],
                }
            )
            reused_files += 1
            continue
        fresh = list(chunks(path, content, commit))
        records.extend(fresh)
        embedded_chunks += len(fresh)
        file_manifest.append(
            {
                'path': path,
                'blob_sha': blob_sha,
                'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data),
            }
        )
    if not records or len(records) > 500:
        raise ValueError('corpus must contain between 1 and 500 chunks')
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge_versions(id,status,source_commit) VALUES (%s,'staging',%s) ON CONFLICT(id) DO UPDATE SET status='staging'",
            (version, commit),
        )
        conn.execute('DELETE FROM chunks WHERE knowledge_version=%s', (version,))
        conn.execute('DELETE FROM source_files WHERE knowledge_version=%s', (version,))
        for item in file_manifest:
            conn.execute(
                'INSERT INTO source_files(knowledge_version,path,blob_sha,sha256,bytes,parser_quality) VALUES (%s,%s,%s,%s,%s,%s)',
                (
                    version,
                    item['path'],
                    item['blob_sha'],
                    item['sha256'],
                    item['bytes'],
                    f'{"markdown_sections" if item["path"].endswith(".md") else "text_fallback"}:{CHUNKER_VERSION}',
                ),
            )
        for record in records:
            conn.execute(
                'INSERT INTO chunks(id,knowledge_version,content,title,url,source_type,path,start_line,end_line,content_hash,embedding_provider,embedding_model,embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)',
                (
                    record['id'],
                    version,
                    record['content'],
                    record['title'],
                    record['url'],
                    record['source_type'],
                    record['path'],
                    record['start_line'],
                    record['end_line'],
                    record['content_hash'],
                    'fixture',
                    'hash64-v1',
                    record['embedding'],
                ),
            )
    driver = GraphDatabase.driver(
        settings().neo4j_uri,
        auth=(settings().neo4j_user, settings().neo4j_password),
        connection_timeout=3,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=0,
    )
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            facts_count = project(session, version, records, documents)
    finally:
        driver.close()
    with connect() as conn:
        count = conn.execute(
            'SELECT count(*) AS n FROM chunks WHERE knowledge_version=%s', (version,)
        ).fetchone()['n']
        if count != len(records):
            raise RuntimeError('vector projection incomplete')
        conn.execute(
            "UPDATE knowledge_versions SET status='retired' WHERE status='active'"
        )
        conn.execute(
            "UPDATE knowledge_versions SET status='active' WHERE id=%s", (version,)
        )
    return {
        'knowledge_version': version,
        'source_commit': commit,
        'changed': True,
        'files': len(file_manifest),
        'chunks': len(records),
        'embedded_chunks': embedded_chunks,
        'reused_files': reused_files,
        'manifest': file_manifest,
        'graph_facts': facts_count,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--source', choices=['local', 'github'], default='local')
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    if args.source == 'local':
        if not args.repo:
            parser.error('--repo is required for local sync')
        result = sync(args.repo, args.ref)
    else:
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
                'develop',
            )
            result = sync(repo, 'FETCH_HEAD')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
