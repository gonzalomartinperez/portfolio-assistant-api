"""Preserve public indexing and locale selection across the portfolio content move."""

import asyncio
import hashlib
import subprocess
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from app.adapters.portfolio import indexing
from app.adapters.portfolio.indexing import corpus_identity, manifest_at_commit
from app.adapters.portfolio.projection import PublicFact
from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.application.knowledge import Chunk, Corpus
from app.domain.errors import RejectedError
from app.domain.knowledge import suggestions


def test_the_new_source_profile_cannot_reuse_an_incomplete_legacy_index():
    commit = 'a' * 40
    assert corpus_identity(commit, 'fixture')[0] != commit + '-v7'
    assert corpus_identity(commit, 'openai')[0] != commit + '-semantic-v8'


def test_duplicate_logical_profile_paths_fail_before_reading_or_embedding(
    monkeypatch, tmp_path
):
    listing = (
        '100644 blob ' + 'a' * 40 + '\tcontent/en/profile.ts\n'
        '100644 blob ' + 'b' * 40 + '\tsrc/content/en/profile.ts\n'
    ).encode()
    monkeypatch.setattr(indexing, 'git', lambda *args: listing)
    with pytest.raises(ValueError, match='ambiguous public profile'):
        manifest_at_commit(tmp_path, 'c' * 40)


@pytest.mark.parametrize('operation', ['candidates', 'starters'])
def test_legacy_profile_is_rejected_before_query_embedding_or_starter_use(operation):
    @contextmanager
    def connection():
        row = {'id': 'a' * 40 + '-v7', 'source_commit': 'a' * 40}
        yield SimpleNamespace(
            execute=lambda *args: SimpleNamespace(fetchone=lambda: row)
        )

    class Embeddings:
        provider = 'fixture'
        model = 'hash64-v1'

        async def query(self, text):
            raise AssertionError('legacy profile must fail before embedding IO')

    index = KnowledgeIndex(connection, None, Embeddings())
    with pytest.raises(RejectedError, match='knowledge_updating'):
        if operation == 'candidates':
            asyncio.run(index.candidates('Question'))
        else:
            index.starter_prompts('en')


def test_public_manifest_follows_only_the_eight_reviewed_content_moves(tmp_path):
    def git(*args):
        return subprocess.check_output(
            ['git', '-C', str(tmp_path), *args], text=True
        ).strip()

    git('init', '-q')
    git('config', 'user.name', 'Synthetic fixture')
    git('config', 'user.email', 'fixture@example.test')
    git('config', 'commit.gpgsign', 'false')
    paths = []
    for locale in ('en', 'es'):
        directory = tmp_path / 'src' / 'content' / locale
        directory.mkdir(parents=True)
        for topic in ('profile', 'experience', 'projects', 'education'):
            path = directory / f'{topic}.ts'
            path.write_text('Approved synthetic public profile fixture.\n')
            paths.append(str(path.relative_to(tmp_path)))
    (tmp_path / 'README.md').write_text('Synthetic public repository.\n')
    git('add', '.')
    git('commit', '-qm', 'legacy public source layout')
    assert {
        path for path, _ in manifest_at_commit(tmp_path, git('rev-parse', 'HEAD'))
    } == set(paths) | {'README.md'}
    git('mv', 'src/content', 'content')
    (tmp_path / 'content/en/secrets.ts').write_text('Unapproved synthetic file.\n')
    (tmp_path / 'content/en/profile.ts.backup').write_text('Unapproved backup.\n')
    git('add', '.')
    git('commit', '-qm', 'reviewed root content move')
    manifest = {
        path for path, _ in manifest_at_commit(tmp_path, git('rev-parse', 'HEAD'))
    }
    assert manifest == {path.removeprefix('src/') for path in paths} | {'README.md'}


@pytest.mark.parametrize('prefix', ['src/content', 'content'])
def test_starters_preserve_both_languages_and_achievement_source(prefix):
    paths = frozenset(
        f'{prefix}/en/{topic}.ts'
        for topic in ('profile', 'experience', 'projects', 'education')
    )
    assert len(suggestions(paths, 'en', achievements=True)) == 5
    assert suggestions(paths, 'es') == ()


@pytest.mark.parametrize('prefix', ['src/content', 'content'])
def test_projection_accepts_an_exact_public_source_path_in_either_layout(prefix):
    fact = PublicFact.model_validate(
        {
            'id': 'synthetic-project',
            'subject': {'en': 'Fixture', 'es': 'Ejemplo'},
            'topic': 'projects',
            'text': {'en': 'Public fixture.', 'es': 'Ejemplo público.'},
            'verified_on': date(2026, 10, 18),
            'source_path': f'{prefix}/en/projects.ts',
            'start_line': 1,
            'end_line': 1,
            'technologies': ['Python'],
            'attribution': 'personal',
        }
    )
    assert fact.source_path == f'{prefix}/en/projects.ts'


@pytest.mark.parametrize('prefix', ['src/content', 'content'])
def test_retrieval_preserves_locale_isolation_and_citations_after_the_move(prefix):
    commit = 'a' * 40
    chunks = []
    for locale in ('en', 'es'):
        path = f'{prefix}/{locale}/projects.ts'
        content = 'name: "Filomena", summary: "Filomena Python project"'
        chunks.append(
            Chunk(
                locale,
                'Fixture',
                f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{path}#L1-L1',
                'public',
                path,
                1,
                1,
                content,
                hashlib.sha256(content.encode()).hexdigest(),
            )
        )

    class Index:
        async def candidates(self, question):
            return Corpus(
                'fixture',
                commit,
                tuple(chunks),
                frozenset(chunk.path for chunk in chunks),
                tuple(chunk.id for chunk in chunks),
            )

    sources = asyncio.run(PublicRetrieval(Index()).search('What is Filomena?', 'en'))
    assert sources and all(
        source.path == f'{prefix}/en/projects.ts' for source in sources
    )
    assert all(
        f'/{commit}/{prefix}/en/projects.ts#L' in source.url for source in sources
    )


@pytest.mark.parametrize('prefix', ['src/content', 'content'])
@pytest.mark.parametrize(
    ('question', 'target', 'distractor'),
    [
        (
            'Explain LangGraph in the portfolio',
            'LangGraph',
            'LangGraph portfolio explain ' * 10,
        ),
        (
            'portfolio goals metrics',
            'Design goal for portfolio performance',
            'portfolio goals metrics ' * 10,
        ),
    ],
)
def test_professional_technical_and_goal_anchors_keep_priority_in_both_layouts(
    prefix, question, target, distractor
):
    commit = 'a' * 40
    chunks = []
    for identifier, path, content in (
        ('target', f'{prefix}/en/projects.ts', target),
        ('other', 'public/assistant-knowledge.json', distractor),
    ):
        chunks.append(
            Chunk(
                identifier,
                'Fixture',
                f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{path}#L1-L1',
                'public',
                path,
                1,
                1,
                content,
                hashlib.sha256(content.encode()).hexdigest(),
            )
        )

    class Index:
        async def candidates(self, question):
            return Corpus(
                'fixture',
                commit,
                tuple(chunks),
                frozenset(chunk.path for chunk in chunks),
                tuple(chunk.id for chunk in chunks),
            )

    evidence = asyncio.run(PublicRetrieval(Index()).search(question, 'en'))
    assert evidence and evidence[0].path == f'{prefix}/en/projects.ts'
