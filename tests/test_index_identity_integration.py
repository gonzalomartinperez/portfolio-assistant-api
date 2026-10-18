"""Real isolated stores exercise profile changes; provider transport stays synthetic."""

import hashlib
import os
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest
from neo4j import GraphDatabase

from app.adapters.portfolio import indexing

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires explicitly isolated PostgreSQL/pgvector and Neo4j',
    ),
]


@pytest.mark.parametrize('first', ['fixture', 'openai'])
def test_profile_switch_preserves_legacy_and_retired_projections(
    tmp_path, monkeypatch, first
):
    from app.bootstrap.config import Settings
    from app.bootstrap.maintenance import connect

    repo = tmp_path / 'public-fixture'
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args]).decode().strip()

    git('init', '-q')
    git('config', 'user.name', 'Fixture Test')
    git('config', 'user.email', 'fixture@example.invalid')
    git(
        'remote', 'add', 'origin', 'https://github.com/gonzalomartinperez/portfolio.git'
    )
    content = (
        'slug: "identity-fixture",\nname: "Identity fixture",\nstack: technologyNames([\n"Python",\n]),\n// '
        + uuid4().hex
    )
    path = 'src/content/en/projects.ts'
    source = repo / path
    source.parent.mkdir(parents=True)
    source.write_text(content)
    git('add', '.')
    git('commit', '-qm', 'fixture: profile identity')
    revision = git('rev-parse', 'HEAD')
    legacy = revision + '-v6'
    versions = [legacy] + [
        indexing.corpus_identity(revision, p)[0] for p in ('fixture', 'openai')
    ]
    record = next(indexing.chunks(path, content, revision))
    content_hash = record['content_hash']
    config = Settings(_env_file=None)
    configurations = {
        p: config.model_copy(
            update={
                'embeddings_provider': p,
                'openai_api_key': None,
                'allow_paid_ai': False,
            }
        )
        for p in ('fixture', 'openai')
    }
    calls = []
    owned_reservations = []
    accounting = indexing.EmbeddingAccounting

    class RecordingAccounting(accounting):
        def reserve_embedding(self, tokens, purpose):
            identifier = super().reserve_embedding(tokens, purpose)
            owned_reservations.append(identifier)
            return identifier

    class SyntheticClient:
        def __init__(self, **kwargs):
            self.embeddings = self

        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1] * 1536)],
                usage=SimpleNamespace(total_tokens=2),
            )

        def close(self):
            pass

    monkeypatch.setattr(indexing, 'create_sync_client', SyntheticClient)
    monkeypatch.setattr(indexing, 'EmbeddingAccounting', RecordingAccounting)
    with connect() as conn:
        original = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
        max_transaction_retry_time=0,
    )

    def snapshot(version):
        with connect() as conn:
            return conn.execute(
                'SELECT id,content_hash,url,embedding_provider,embedding_model FROM chunks WHERE knowledge_version=%s ORDER BY id',
                (version,),
            ).fetchall()

    try:
        # Reproduce the actual pre-upgrade IDs and legacy profile, not the new namespace.
        with driver.session(database=config.neo4j_database) as graph:
            indexing.project(graph, legacy, [record], {path: content})
        with connect() as conn:
            conn.execute(
                "INSERT INTO knowledge_versions(id,status,source_commit) VALUES (%s,'staging',%s)",
                (legacy, revision),
            )
            conn.execute(
                'INSERT INTO source_files(knowledge_version,path,blob_sha,sha256,bytes,parser_quality) VALUES (%s,%s,%s,%s,%s,%s)',
                (
                    legacy,
                    path,
                    git('rev-parse', 'HEAD:' + path),
                    hashlib.sha256(content.encode()).hexdigest(),
                    len(content.encode()),
                    'text_fallback:' + indexing.CHUNKER_VERSION,
                ),
            )
            conn.execute(
                'INSERT INTO chunks(id,knowledge_version,content,title,url,source_type,path,start_line,end_line,content_hash,embedding_provider,embedding_model,embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)',
                (
                    record['id'],
                    legacy,
                    content,
                    record['title'],
                    record['url'],
                    record['source_type'],
                    path,
                    record['start_line'],
                    record['end_line'],
                    content_hash,
                    'fixture',
                    'hash64-v1',
                    record['embedding'],
                ),
            )
            conn.execute(
                "UPDATE knowledge_versions SET status='retired' WHERE status='active'"
            )
            conn.execute(
                "UPDATE knowledge_versions SET status='active' WHERE id=%s", (legacy,)
            )
        snapshots = {legacy: snapshot(legacy)}
        other = 'openai' if first == 'fixture' else 'fixture'
        for provider in (first, other, first):
            result = indexing.sync(
                repo, configuration=configurations[provider], connection=connect
            )
            version = result['knowledge_version']
            assert result['reused_files'] == 1
            with connect() as conn:
                assert (
                    conn.execute(
                        "SELECT id FROM knowledge_versions WHERE status='active'"
                    ).fetchone()['id']
                    == version
                )
            for previous, rows in snapshots.items():
                assert snapshot(previous) == rows
            snapshots[version] = snapshot(version)
            assert all(
                row['embedding_provider'] == provider for row in snapshots[version]
            )
            ids = [row['id'] for rows in snapshots.values() for row in rows]
            assert len(ids) == len(set(ids))
            with driver.session(database=config.neo4j_database) as graph:
                for projected, rows in snapshots.items():
                    documents = {
                        r['id']
                        for r in graph.run(
                            'MATCH (d:Document {version:$version}) RETURN d.id AS id',
                            version=projected,
                        )
                    }
                    assert documents == {row['id'] for row in rows}
                    edges = list(
                        graph.run(
                            'MATCH (:Entity)-[r:RELATES {version:$version}]->(:Entity) RETURN r.document AS document',
                            version=projected,
                        )
                    )
                    assert edges and all(
                        edge['document'] in documents for edge in edges
                    )
        assert (
            len(calls) == 1
        )  # Reusing public vectors never repeats the synthetic paid operation.
        assert calls[0]['model'] == 'text-embedding-3-small'
        assert calls[0]['dimensions'] == 1536
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
                conn.execute(
                    'DELETE FROM public_embedding_cache WHERE content_hash=%s',
                    (content_hash,),
                )
                conn.execute(
                    'DELETE FROM spend_ledger WHERE id=ANY(%s)', (owned_reservations,)
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
