import hashlib
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import Settings
from app.provider import StreamingOpenAIAdapter, fixture_message
from app.retrieval import retrieve, verified


def test_production_configuration_fails_closed():
    with pytest.raises(ValueError, match='HTTPS origins'):
        Settings(environment='production')
    with pytest.raises(ValueError, match='paid provider'):
        Settings(ai_provider='openai', allow_paid_ai=False)


def test_responses_deltas_are_forwarded_before_completion(monkeypatch):
    monkeypatch.setattr('app.provider.settings', lambda: SimpleNamespace(allow_paid_ai=True, ai_provider='openai'))

    class Client:
        def create(self, **kwargs):
            assert kwargs['stream'] is True
            assert kwargs['input'][0]['role'] == 'developer'
            assert kwargs['input'][1]['role'] == 'user'
            yield SimpleNamespace(type='response.output_text.delta', delta='First ')
            yield SimpleNamespace(type='response.output_text.delta', delta='second')
            yield SimpleNamespace(type='response.completed', response=SimpleNamespace(usage=SimpleNamespace(input_tokens=12, output_tokens=2)))

    adapter = StreamingOpenAIAdapter(Client())
    events = adapter.stream('Question', 'Public evidence')
    assert next(events) == 'First '
    assert adapter.usage is None
    assert list(events) == ['second']
    assert adapter.usage.input_tokens == 12


def test_responses_incomplete_stream_fails_without_claiming_completion(monkeypatch):
    monkeypatch.setattr('app.provider.settings', lambda: SimpleNamespace(allow_paid_ai=True, ai_provider='openai'))

    class Client:
        def create(self, **kwargs):
            yield SimpleNamespace(type='response.output_text.delta', delta='Partial')

    events = StreamingOpenAIAdapter(Client()).stream('Question', 'Evidence')
    assert next(events) == 'Partial'
    with pytest.raises(RuntimeError, match='provider_interrupted'):
        next(events)


def test_citation_metadata_rejects_spoofed_url_and_hash():
    path = 'src/content/en/projects.ts'
    commit = 'a' * 40
    row = {'path': path, 'start_line': 1, 'end_line': 2, 'content': 'public evidence',
           'content_hash': hashlib.sha256(b'public evidence').hexdigest(),
           'url': f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{path}#L1-L2'}
    assert verified(row, commit, {path})
    assert not verified({**row, 'url': 'https://evil.example/'}, commit, {path})
    assert not verified({**row, 'content': 'changed'}, commit, {path})
    assert not verified(row, commit, {'src/content/en/profile.ts'})


@pytest.mark.skipif(os.getenv('TEST_INTEGRATION') != '1', reason='requires the reviewed public corpus in PostgreSQL and Neo4j')
@pytest.mark.parametrize(('question', 'locale', 'path', 'needle'), [
    ('What is Filomena?', 'en', 'src/content/en/projects.ts', 'Health-sciences exams'),
    ('Which technologies were used in Filomena?', 'en', 'src/content/en/projects.ts', 'Laravel'),
    ('What did Gonzalo do at Rampy?', 'en', 'src/content/en/experience.ts', 'Rampy'),
    ('¿Dónde estudió Gonzalo?', 'es', 'src/content/es/education.ts', 'Universidad Nacional del Sur'),
    ('How is the portfolio built?', 'en', 'README.md', 'Next.js'),
])
def test_reviewed_direct_questions(question, locale, path, needle):
    rows, commits = retrieve(question, locale)
    assert rows and rows[0]['path'] == path
    assert len(commits[0]) == 40
    evidence = '\n'.join(f'PUBLIC SOURCE {row["path"]} lines {row["start_line"]}-{row["end_line"]}:\n{row["content"]}' for row in rows)
    assert needle in fixture_message(question, evidence, locale)


@pytest.mark.skipif(os.getenv('TEST_INTEGRATION') != '1', reason='requires PostgreSQL and Neo4j')
def test_unknown_question_has_no_evidence_and_graph_is_bounded():
    assert retrieve('quasar xylophone', 'en')[0] == []
    graph, _ = retrieve('What is Filomena?', 'en', strategy='graph')
    hybrid, _ = retrieve('What is Filomena?', 'en', strategy='hybrid')
    assert graph and hybrid
    assert all(row['path'] == 'src/content/en/projects.ts' for row in graph)
    assert hybrid[0]['path'] == 'src/content/en/projects.ts'


@pytest.mark.skipif(os.getenv('TEST_INTEGRATION') != '1', reason='requires PostgreSQL public corpus')
def test_graph_outage_falls_back_to_verified_text(monkeypatch):
    monkeypatch.setattr('app.retrieval.GraphDatabase.driver', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('offline')))
    rows, _ = retrieve('What is Filomena?', 'en')
    assert rows and rows[0]['path'] == 'src/content/en/projects.ts'


@pytest.mark.skipif(os.getenv('TEST_INTEGRATION') != '1', reason='requires real PostgreSQL checkpointer and public corpus')
def test_graph_emits_provider_delta_before_generation_finishes(monkeypatch):
    from app import workflow
    from app.config import settings

    class Adapter:
        usage = SimpleNamespace(input_tokens=10, output_tokens=2)

        def stream(self, question, evidence):
            assert 'PUBLIC SOURCE' in evidence
            yield 'first '
            yield 'second'

    monkeypatch.setattr(workflow, 'settings', lambda: SimpleNamespace(ai_provider='openai', allow_paid_ai=True,
                                                                      reservation_usd='0.05', database_url=settings().database_url))
    monkeypatch.setattr(workflow, 'reserve', lambda *args: None)
    monkeypatch.setattr(workflow, 'settle', lambda *args: None)
    monkeypatch.setattr(workflow.StreamingOpenAIAdapter, 'from_config', lambda: Adapter())
    run_id = str(uuid4())
    state = {'question': 'What is Filomena?', 'locale': 'en', 'run_id': run_id, 'strategy': '',
             'rows': [], 'commits': [], 'evidence': '', 'answer': ''}
    try:
        events = list(workflow.stream_workflow(state, run_id))
        first_delta = next(index for index, event in enumerate(events) if event[0] == 'custom' and event[1].get('text') == 'first ')
        generated = next(index for index, event in enumerate(events) if event[0] == 'updates' and 'generate' in event[1])
        assert first_delta < generated
        assert events[generated][1]['generate']['answer'] == 'first second'
    finally:
        workflow.delete_checkpoint(run_id)
