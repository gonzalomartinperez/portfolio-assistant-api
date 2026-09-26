"""Explicit, bounded sync of approved files from the public portfolio repository."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from neo4j import GraphDatabase

from .config import settings
from .db import connect
from .knowledge import embed

ROOT_PATTERNS = (
    re.compile(r'^src/content/(en|es)/(profile|experience|projects|education)\.ts$'),
    re.compile(r'^docs/(development|public-content|editorial-guidelines)\.md$'),
    re.compile(r'^README\.md$'),
)
SECRET_PATTERN = re.compile(r'(?i)(api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|BEGIN [A-Z ]+PRIVATE KEY)')
MAX_FILES = 80
MAX_BYTES = 60_000


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(repo), *args])


def files_at_commit(repo: Path, commit: str):
    listed = git(repo, 'ls-tree', '-r', '--name-only', commit).decode().splitlines()
    allowed = [path for path in listed if any(pattern.fullmatch(path) for pattern in ROOT_PATTERNS)]
    if len(allowed) > MAX_FILES:
        raise ValueError('file limit exceeded')
    for path in allowed:
        data = git(repo, 'show', f'{commit}:{path}')
        if len(data) > MAX_BYTES:
            continue
        content = data.decode('utf-8')
        if SECRET_PATTERN.search(content):
            raise ValueError(f'possible secret in {path}')
        yield path, data, content


def chunks(path: str, content: str, commit: str):
    lines = content.splitlines()
    for start in range(0, len(lines), 35):
        block = '\n'.join(lines[start:start+35]).strip()
        if len(block) < 30:
            continue
        end = min(start + 35, len(lines))
        url = f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{quote(path, safe="/")}#L{start+1}-L{end}'
        content_hash = hashlib.sha256(block.encode()).hexdigest()
        yield {
            'id': hashlib.sha256(f'{commit}:{path}:{start+1}:{content_hash}'.encode()).hexdigest(),
            'content': block, 'title': path, 'url': url,
            'source_type': 'code' if path.endswith(('.ts', '.tsx')) else 'page',
            'path': path, 'start_line': start + 1, 'end_line': end,
            'content_hash': content_hash, 'embedding': embed(block),
        }


def sync(repo: Path, ref: str = 'HEAD'):
    repo = repo.resolve(strict=True)
    remote = git(repo, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in ('https://github.com/gonzalomartinperez/portfolio', 'https://github.com/gonzalomartinperez/portfolio.git', 'git@github.com:gonzalomartinperez/portfolio.git'):
        raise ValueError('only the public portfolio repository is allowed')
    commit = git(repo, 'rev-parse', ref).decode().strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('invalid commit')
    version = commit[:16] + '-v2'
    manifest = []
    records = []
    for path, data, content in files_at_commit(repo, commit):
        manifest.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        records.extend(chunks(path, content, commit))
    with connect() as conn:
        existing = conn.execute('SELECT status FROM knowledge_versions WHERE id=%s', (version,)).fetchone()
        if existing and existing['status'] == 'active':
            return {'knowledge_version': version, 'changed': False, 'files': len(manifest), 'chunks': len(records)}
        conn.execute("INSERT INTO knowledge_versions(id,status,source_commit) VALUES (%s,'staging',%s) ON CONFLICT(id) DO UPDATE SET status='staging'",
                     (version, commit))
        conn.execute('DELETE FROM chunks WHERE knowledge_version=%s', (version,))
        for record in records:
            conn.execute('INSERT INTO chunks(id,knowledge_version,content,title,url,source_type,path,start_line,end_line,content_hash,embedding_provider,embedding_model,embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)',
                         (record['id'], version, record['content'], record['title'], record['url'], record['source_type'],
                          record['path'], record['start_line'], record['end_line'], record['content_hash'],
                          'fixture', 'hash64-v1', record['embedding']))
    driver = GraphDatabase.driver(settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password))
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run('MATCH (n:Document {version:$version}) DETACH DELETE n', version=version).consume()
            for record in records:
                session.run('MERGE (d:Document {id:$id}) SET d.version=$version,d.title=$title,d.url=$url',
                            id=record['id'], version=version, title=record['title'], url=record['url']).consume()
                if 'projects.ts' in record['path'] or 'filomena' in record['path'].lower():
                    session.run('MERGE (p:Project {name:"Filomena"}) WITH p MATCH (d:Document {id:$id}) MERGE (p)-[:SUPPORTED_BY]->(d)',
                                id=record['id']).consume()
    finally:
        driver.close()
    with connect() as conn:
        count = conn.execute('SELECT count(*) AS n FROM chunks WHERE knowledge_version=%s', (version,)).fetchone()['n']
        if count != len(records):
            raise RuntimeError('vector projection incomplete')
        conn.execute("UPDATE knowledge_versions SET status='retired' WHERE status='active'")
        conn.execute("UPDATE knowledge_versions SET status='active' WHERE id=%s", (version,))
    output = {'knowledge_version': version, 'source_commit': commit, 'changed': True,
              'files': len(manifest), 'chunks': len(records), 'manifest': manifest}
    return output


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
            subprocess.check_call(['git', '-C', str(repo), 'init', '-q'])
            subprocess.check_call(['git', '-C', str(repo), 'remote', 'add', 'origin', 'https://github.com/gonzalomartinperez/portfolio.git'])
            subprocess.check_call(['git', '-C', str(repo), 'fetch', '-q', '--depth=1', 'origin', 'develop'])
            result = sync(repo, 'FETCH_HEAD')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
