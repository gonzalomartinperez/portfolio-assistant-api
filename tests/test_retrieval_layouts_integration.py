"""Retrieval cases give the same result on both public portfolio layouts (P0-1, ADR 012)."""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest
from neo4j import GraphDatabase

from app.adapters.portfolio import indexing
from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.bootstrap.config import Settings
from app.bootstrap.maintenance import connect
from app.domain.portfolio_paths import canonical_key

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires isolated PostgreSQL and Neo4j fixtures',
    ),
]

PUBLIC_REMOTE = 'https://github.com/gonzalomartinperez/portfolio.git'


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def _layouts(source: Path, repo: Path) -> dict[str, str]:
    """Clone the approved public corpus and commit the other content root next to it."""
    subprocess.run(
        ['git', 'clone', '-q', '--no-hardlinks', str(source), str(repo)], check=True
    )
    _git(repo, 'config', 'user.name', 'Synthetic layout fixture')
    _git(repo, 'config', 'user.email', 'fixture@example.test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    _git(repo, 'remote', 'set-url', 'origin', PUBLIC_REMOTE)
    original = _git(repo, 'rev-parse', 'HEAD')
    if (repo / 'src/content').is_dir():
        _git(repo, 'mv', 'src/content', 'content')
        moved = 'current'
    else:
        (repo / 'src').mkdir(exist_ok=True)
        _git(repo, 'mv', 'content', 'src/content')
        moved = 'legacy'
    _git(repo, 'commit', '-qm', f'synthetic {moved} content root')
    other = _git(repo, 'rev-parse', 'HEAD')
    if moved == 'current':
        return {'legacy': original, 'current': other}
    return {'legacy': other, 'current': original}


def _outcomes(index: KnowledgeIndex, cases: list[dict]) -> dict[str, tuple]:
    outcomes = {}
    for case in cases:
        sources = asyncio.run(
            PublicRetrieval(index, 'hybrid').search(case['question'], case['locale'])
        )
        keys = {canonical_key(source.path) for source in sources}
        content = '\n'.join(source.content for source in sources)
        if case['qrels']:
            passed = set(case['qrels']) <= keys and all(
                needle in content for needle in case['contains']
            )
        else:
            passed = not sources
        # Chunk ids hash the physical path, so equal-score ties may surface a different
        # secondary file per layout; compare the graded outcome and the relevant keys.
        outcomes[case['id']] = (passed, tuple(sorted(keys & set(case['qrels']))))
    return outcomes


def test_retrieval_cases_are_layout_neutral(tmp_path, monkeypatch):
    source = Path(os.getenv('PUBLIC_PORTFOLIO_REPO', 'public-portfolio'))
    if not (source / '.git').exists():
        pytest.skip('requires the pinned approved public corpus checkout')
    repo = tmp_path / 'portfolio'
    revisions = _layouts(source, repo)
    cases = json.loads(Path('evals/retrieval.json').read_text())
    config = Settings(_env_file=None).model_copy(
        update={
            'embeddings_provider': 'fixture',
            'openai_api_key': None,
            'allow_paid_ai': False,
        }
    )

    def forbidden_provider(**kwargs):
        raise AssertionError('fixture indexing must never construct an OpenAI client')

    monkeypatch.setattr(indexing, 'create_sync_client', forbidden_provider)
    versions = {
        layout: indexing.corpus_identity(revision, 'fixture')[0]
        for layout, revision in revisions.items()
    }
    with connect() as conn:
        original = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
        existing = {
            row['id'] for row in conn.execute('SELECT id FROM knowledge_versions')
        }
    # Only versions this test creates are removed; pre-existing ones are kept intact.
    created = [version for version in versions.values() if version not in existing]
    # Index the layout that is already active first, so it is never re-indexed.
    order = sorted(revisions, key=lambda layout: versions[layout] != original)
    driver = GraphDatabase.driver(
        config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
    )
    try:
        index = KnowledgeIndex(connect, driver, database=config.neo4j_database)
        results = {}
        for layout in order:
            indexing.sync(
                repo, revisions[layout], configuration=config, connection=connect
            )
            results[layout] = _outcomes(index, cases)
        assert results['current'] == results['legacy']
        assert all(passed for passed, _ in results['current'].values()), results
    finally:
        try:
            with connect() as conn:
                conn.execute(
                    "UPDATE knowledge_versions SET status='retired' WHERE status='active'"
                )
                conn.execute(
                    "UPDATE knowledge_versions SET status='active' WHERE id=%s",
                    (original,),
                )
                for table in ('chunks', 'source_files'):
                    conn.execute(
                        f'DELETE FROM {table} WHERE knowledge_version=ANY(%s)',
                        (created,),
                    )
                conn.execute(
                    'DELETE FROM knowledge_versions WHERE id=ANY(%s)', (created,)
                )
        finally:
            try:
                with driver.session(database=config.neo4j_database) as graph:
                    graph.run(
                        'MATCH (n) WHERE n.version IN $versions DETACH DELETE n',
                        versions=created,
                    ).consume()
            finally:
                driver.close()
