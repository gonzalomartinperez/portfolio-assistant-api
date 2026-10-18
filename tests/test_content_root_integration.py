"""Real public-source worker, PostgreSQL and Neo4j across the content relocation."""

import asyncio
import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from neo4j import GraphDatabase

from app.adapters.portfolio import indexing
from app.adapters.portfolio.watch import PublicKnowledgePublisher
from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.application.knowledge_watch import watch
from app.bootstrap.config import Settings
from app.bootstrap.maintenance import connect

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires isolated PostgreSQL and Neo4j fixtures',
    ),
]


def test_worker_follows_layout_and_content_changes_without_losing_graph_provenance(
    tmp_path, monkeypatch
):
    def git(*args):
        return subprocess.check_output(
            ['git', '-C', str(tmp_path), *args], text=True
        ).strip()

    git('init', '-q')
    git('config', 'user.name', 'Synthetic public fixture')
    git('config', 'user.email', 'fixture@example.test')
    git('config', 'commit.gpgsign', 'false')
    git(
        'remote', 'add', 'origin', 'https://github.com/gonzalomartinperez/portfolio.git'
    )
    marker = uuid4().hex
    contents = {
        'profile': 'name: "RootFixturePerson", summary: "Public synthetic profile"',
        'projects': 'slug: "root-fixture-project",\nname: "RootFixtureProject",\nstack: technologyNames(["Python"]),\nsummary: "Public synthetic project"',
        'experience': 'slug: "root-fixture-company",\ncompany: "RootFixtureCompany",\nstack: technologyNames(["Python"]),\ncontributions: ["Public synthetic contribution"],',
        'education': 'qualification: "Fixture Degree", institution: "Fixture University"',
    }
    for locale in ('en', 'es'):
        directory = tmp_path / 'src/content' / locale
        directory.mkdir(parents=True)
        for topic, content in contents.items():
            (directory / f'{topic}.ts').write_text(content + '\n// ' + marker)
    (tmp_path / 'README.md').write_text('# Synthetic public repository\n' + marker)
    git('add', '.')
    git('commit', '-qm', 'legacy public layout')
    revisions = [git('rev-parse', 'HEAD')]
    git('mv', 'src/content', 'content')
    git('commit', '-qm', 'public root content layout')
    revisions.append(git('rev-parse', 'HEAD'))
    profile = tmp_path / 'content/en/profile.ts'
    profile.write_text(
        profile.read_text() + '\nsummary: "Updated public synthetic profile"'
    )
    git('add', '.')
    git('commit', '-qm', 'new public profile revision')
    revisions.append(git('rev-parse', 'HEAD'))
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
    versions = [
        indexing.corpus_identity(revision, 'fixture')[0] for revision in revisions
    ]
    with connect() as conn:
        original = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
        previous_watch = conn.execute(
            'SELECT observed_commit,checked_at FROM knowledge_watch WHERE singleton'
        ).fetchone()
    results = []

    def publish(repo: Path, revision: str, **kwargs):
        result = indexing.sync(
            repo, revision, configuration=config, connection=connect, **kwargs
        )
        results.append(result)
        return result

    publisher = PublicKnowledgePublisher(tmp_path, connection=connect, publish=publish)
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
        max_transaction_retry_time=0,
    )
    try:

        async def run_worker():
            stop = asyncio.Event()
            activated = []

            class Source:
                async def latest(self):
                    return revisions[min(len(activated), len(revisions) - 1)]

            def report(status):
                if status == 'activated':
                    activated.append(status)
                    if len(activated) == len(revisions):
                        stop.set()

            await asyncio.wait_for(watch(Source(), publisher, stop, 0.01, report), 60)

        asyncio.run(run_worker())
        assert [result['knowledge_version'] for result in results] == versions
        assert results[1]['files'] == 9 and results[1]['reused_files'] == 1
        assert results[2]['reused_files'] == 8
        assert (
            indexing.sync(
                tmp_path,
                revisions[-1],
                configuration=config,
                connection=connect,
                watched=True,
            )['changed']
            is False
        )
        index = KnowledgeIndex(connect, driver, freshness=90)
        for locale in ('en', 'es'):
            current, commit, prompts = index.starter_prompts(locale)
            assert (
                current == versions[-1]
                and commit == revisions[-1]
                and len(prompts) == 4
            )
            evidence = asyncio.run(
                PublicRetrieval(index, 'graph').search(
                    'Compare RootFixtureProject and RootFixtureCompany', locale
                )
            )
            assert evidence and all(
                source.path.startswith(f'content/{locale}/') for source in evidence
            )
            assert any(source.path.endswith('/projects.ts') for source in evidence)
            assert any(source.path.endswith('/experience.ts') for source in evidence)
            assert all(
                f'/{revisions[-1]}/{source.path}#L' in source.url for source in evidence
            )
        with connect() as conn:
            rows = conn.execute(
                'SELECT id,status FROM knowledge_versions WHERE id=ANY(%s)', (versions,)
            ).fetchall()
            assert {row['id']: row['status'] for row in rows} == {
                versions[0]: 'retired',
                versions[1]: 'retired',
                versions[2]: 'active',
            }
        with driver.session(database=config.neo4j_database) as graph:
            for version, revision in zip(versions, revisions, strict=True):
                edges = list(
                    graph.run(
                        'MATCH (:Entity)-[r:RELATES {version:$version}]->(:Entity) RETURN r.document AS document,r.url AS url,r.start_line AS start,r.end_line AS end',
                        version=version,
                    )
                )
                assert edges and all(
                    f'/blob/{revision}/' in edge['url'] and edge['start'] <= edge['end']
                    for edge in edges
                )
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
                conn.execute(
                    'DELETE FROM chunks WHERE knowledge_version=ANY(%s)', (versions,)
                )
                conn.execute(
                    'DELETE FROM source_files WHERE knowledge_version=ANY(%s)',
                    (versions,),
                )
                conn.execute(
                    'DELETE FROM knowledge_versions WHERE id=ANY(%s)', (versions,)
                )
                conn.execute('DELETE FROM knowledge_watch')
                if previous_watch:
                    conn.execute(
                        'INSERT INTO knowledge_watch(singleton,observed_commit,checked_at) VALUES (true,%s,%s)',
                        (
                            previous_watch['observed_commit'],
                            previous_watch['checked_at'],
                        ),
                    )
        finally:
            try:
                with driver.session(database=config.neo4j_database) as graph:
                    graph.run(
                        'MATCH (n) WHERE n.version IN $versions DETACH DELETE n',
                        versions=versions,
                    ).consume()
            finally:
                driver.close()
