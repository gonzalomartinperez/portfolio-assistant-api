"""Indexed identities separate embedding profiles without changing source provenance."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.adapters.portfolio import indexing


@pytest.fixture
def capture_index(monkeypatch, tmp_path):
    """Exercise the real staging path, capturing rows before database insertion."""
    commit = 'a' * 40
    content = (
        '# Public fixture\nAn approved synthetic public profile for identity tests.'
    )
    inserted = []
    state = {'reuse': False}

    def git(repo, *args):
        if args[:2] == ('remote', 'get-url'):
            return b'https://github.com/gonzalomartinperez/portfolio.git'
        if args[0] == 'rev-parse':
            return commit.encode()
        if args[0] == 'ls-tree':
            return b'100644 blob bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\tREADME.md'
        if args[:2] == ('cat-file', '-s'):
            return str(len(content)).encode()
        assert args[:2] == ('cat-file', 'blob')
        return content.encode()

    def execute(sql, values=None):
        if sql.startswith('INSERT INTO chunks'):
            inserted.append(values)
        row = {'n': 1} if sql.startswith('SELECT count(*)') else None
        rows = []
        if state['reuse']:
            old = next(indexing.chunks('README.md', content, commit))
            old['id'] = 'a previous profile namespace must not be reused'
            if sql.startswith('SELECT id FROM knowledge_versions'):
                row = {'id': 'previous-profile'}
            elif sql.startswith('SELECT * FROM source_files'):
                rows = [
                    {
                        'path': 'README.md',
                        'blob_sha': 'b' * 40,
                        'parser_quality': 'markdown_sections:'
                        + indexing.CHUNKER_VERSION,
                        'sha256': old['content_hash'],
                        'bytes': len(content),
                    }
                ]
            elif sql.startswith('SELECT * FROM chunks'):
                rows = [old]
        return SimpleNamespace(fetchone=lambda: row, fetchall=lambda: rows)

    @contextmanager
    def connection():
        yield SimpleNamespace(execute=execute)

    class SemanticStub:
        provider = 'openai'
        model = 'text-embedding-3-small'
        dimensions = 1536

        def __init__(self, *args):
            pass

        def encode(self, text, purpose):
            return (0.1,) * self.dimensions

    driver = Mock()
    driver.session.return_value.__enter__ = Mock(return_value=Mock())
    driver.session.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(indexing, 'git', git)
    monkeypatch.setattr(indexing, 'OpenAIEmbeddings', SemanticStub)
    monkeypatch.setattr(indexing, 'create_sync_client', lambda **kwargs: Mock())
    monkeypatch.setattr(
        indexing.GraphDatabase, 'driver', lambda *args, **kwargs: driver
    )
    monkeypatch.setattr(indexing, 'project', lambda *args, **kwargs: 0)

    def run(provider, *, reuse=False):
        state['reuse'] = reuse
        configuration = SimpleNamespace(
            embeddings_provider=provider,
            openai_api_key=None,
            reserve_cutoff_usd='1',
            embedding_usd_per_million='0.02',
            neo4j_uri='bolt://fixture.invalid',
            neo4j_user='fixture',
            neo4j_password='fixture',
            neo4j_database='neo4j',
        )
        result = indexing._sync(
            tmp_path, 'HEAD', configuration=configuration, connection=connection
        )
        return result, inserted[-1]

    return run


def test_same_source_profiles_have_distinct_stored_ids_and_unchanged_provenance(
    capture_index,
):
    fixture, fixture_row = capture_index('fixture')
    semantic, semantic_row = capture_index('openai')
    assert fixture['knowledge_version'] != semantic['knowledge_version']
    assert fixture_row[0] != semantic_row[0]
    assert fixture_row[2:10] == semantic_row[2:10]
    assert capture_index('fixture')[1][0] == fixture_row[0]
    assert capture_index('openai')[1][0] == semantic_row[0]


@pytest.mark.parametrize(
    ('encoder', 'attribute', 'value'),
    [
        ('FixtureEmbeddings', 'dimensions', 1536),
        ('OpenAIEmbeddings', 'dimensions', 64),
        ('OpenAIEmbeddings', 'model', 'unreviewed-model'),
        ('OpenAIEmbeddings', 'provider', 'unreviewed-provider'),
    ],
)
def test_profile_drift_fails_before_provider_or_cache_io(
    monkeypatch, encoder, attribute, value
):
    monkeypatch.setattr(getattr(indexing, encoder), attribute, value)
    with pytest.raises(ValueError, match='reviewed schema/cache migration'):
        indexing.corpus_identity(
            'a' * 40, 'fixture' if encoder == 'FixtureEmbeddings' else 'openai'
        )


def test_new_profile_versions_preserve_legacy_corpora():
    commit = 'a' * 40
    fixture, _ = indexing.corpus_identity(commit, 'fixture')
    semantic, _ = indexing.corpus_identity(commit, 'openai')
    assert len({fixture, semantic, commit + '-v6', commit + '-semantic-v7'}) == 4


@pytest.mark.parametrize('provider', ['fixture', 'openai'])
def test_unchanged_file_reuse_recomputes_same_profile_identity(capture_index, provider):
    _, fresh = capture_index(provider)
    result, reused = capture_index(provider, reuse=True)
    assert result['reused_files'] == 1
    assert reused[0] == fresh[0]
    assert reused[2:10] == fresh[2:10]
