import hashlib
import os

import pytest

from app.bootstrap.config import Settings
from app.domain.evidence import verified
from app.domain.fixture import fixture_message
from tests.support import retrieve


def test_production_configuration_fails_closed():
    with pytest.raises(ValueError, match='HTTPS origins'):
        Settings(environment='production')
    with pytest.raises(ValueError, match='paid provider'):
        Settings(ai_provider='openai', allow_paid_ai=False)


def test_citation_metadata_rejects_spoofed_url_and_hash():
    path = 'src/content/en/projects.ts'
    commit = 'a' * 40
    row = {
        'path': path,
        'start_line': 1,
        'end_line': 2,
        'content': 'public evidence',
        'content_hash': hashlib.sha256(b'public evidence').hexdigest(),
        'url': f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{path}#L1-L2',
    }
    assert verified(row, commit, {path})
    assert not verified({**row, 'url': 'https://evil.example/'}, commit, {path})
    assert not verified({**row, 'content': 'changed'}, commit, {path})
    assert not verified(row, commit, {'src/content/en/profile.ts'})


@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1',
    reason='requires the reviewed public corpus in PostgreSQL and Neo4j',
)
@pytest.mark.parametrize(
    ('question', 'locale', 'path', 'needle'),
    [
        (
            'What is Filomena?',
            'en',
            'src/content/en/projects.ts',
            'Health-sciences exams',
        ),
        (
            'Which technologies were used in Filomena?',
            'en',
            'src/content/en/projects.ts',
            'Laravel',
        ),
        (
            'What did Gonzalo do at Rampy?',
            'en',
            'src/content/en/experience.ts',
            'Rampy',
        ),
        (
            '¿Dónde estudió Gonzalo?',
            'es',
            'src/content/es/education.ts',
            'Universidad Nacional del Sur',
        ),
        ('How is the portfolio built?', 'en', 'README.md', 'Next.js'),
    ],
)
def test_reviewed_direct_questions(question, locale, path, needle):
    rows, commits = retrieve(question, locale)
    assert rows and rows[0]['path'] == path
    assert len(commits[0]) == 40
    evidence = '\n'.join(
        f'PUBLIC SOURCE {row["path"]} lines {row["start_line"]}-{row["end_line"]}:\n{row["content"]}'
        for row in rows
    )
    assert needle in fixture_message(question, evidence, locale)


@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='requires PostgreSQL and Neo4j'
)
def test_unknown_question_has_no_evidence_and_graph_is_bounded():
    assert retrieve('quasar xylophone', 'en')[0] == []
    graph, _ = retrieve('What is Filomena?', 'en', strategy='graph')
    hybrid, _ = retrieve('What is Filomena?', 'en', strategy='hybrid')
    assert graph and hybrid
    assert all(row['path'] == 'src/content/en/projects.ts' for row in graph)
    assert hybrid[0]['path'] == 'src/content/en/projects.ts'


@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='requires PostgreSQL public corpus'
)
def test_graph_outage_falls_back_to_verified_text(monkeypatch):
    async def unavailable(*args, **kwargs):
        return ()

    monkeypatch.setattr(
        'app.infrastructure.knowledge.KnowledgeIndex.relationships', unavailable
    )
    rows, _ = retrieve('What is Filomena?', 'en')
    assert rows and rows[0]['path'] == 'src/content/en/projects.ts'
