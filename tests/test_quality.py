import hashlib
import os

import pytest

from app.bootstrap.config import Settings
from app.domain.evidence import requested_affiliation, verified
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


@pytest.mark.parametrize(
    ('question', 'expected'),
    [
        ('Would he be a fit for AI Engineer?', None),
        ('Is he ready for Machine Learning roles?', None),
        ('Did he work for UnknownEmployer?', 'UnknownEmployer'),
        ('What was he building for UnknownEmployer?', 'UnknownEmployer'),
        ('What did he implement for UnknownEmployer?', 'UnknownEmployer'),
        ('What did he build at ExampleCompany?', 'ExampleCompany'),
        ('¿Qué construyó en ExampleCompany?', 'ExampleCompany'),
    ],
)
def test_affiliation_distinguishes_target_roles_from_employer_claims(
    question, expected
):
    assert requested_affiliation(question) == expected


@pytest.mark.integration
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
        (
            'Would he be a fit for AI Engineer?',
            'en',
            'src/content/en/experience.ts',
            'retrieval',
        ),
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


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.parametrize(
    ('peer', 'trusted', 'forwarded', 'expected'),
    [
        ('198.51.100.10', '', '203.0.113.4', '198.51.100.10'),
        ('198.51.100.10', '10.0.0.2', '203.0.113.4', '198.51.100.10'),
        ('10.0.0.2', '10.0.0.2', '203.0.113.4', '203.0.113.4'),
        ('10.0.0.2', '10.0.0.2', '192.0.2.99,203.0.113.4', '203.0.113.4'),
        ('10.0.0.2', '10.0.0.2', 'not-an-address', '10.0.0.2'),
        ('10.0.0.2', '10.0.0.2', ','.join(['203.0.113.4'] * 6), '10.0.0.2'),
        ('10.0.0.2', '10.0.0.2', '', '10.0.0.2'),
    ],
)
def test_forwarded_addresses_require_a_trusted_immediate_peer(
    peer, trusted, forwarded, expected
):
    from types import SimpleNamespace

    from starlette.requests import Request

    from app.presentation.http import client_ip

    request = Request(
        {
            'type': 'http',
            'client': (peer, 1000),
            'headers': [(b'x-forwarded-for', forwarded.encode())],
            'app': SimpleNamespace(
                state=SimpleNamespace(config=SimpleNamespace(trusted_proxy_ips=trusted))
            ),
        }
    )
    assert client_ip(request) == expected
