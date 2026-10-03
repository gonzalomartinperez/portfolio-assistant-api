"""Runtime/provider, synchronization and language behavior without paid calls."""

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.application.conversation_context import Turn
from app.application.knowledge_watch import watch
from app.application.language import select_locale
from app.application.runs import citations
from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.domain.errors import DependencyUnavailableError
from app.domain.knowledge import suggestions
from app.infrastructure.embedding import OpenAIEmbeddings
from app.infrastructure.language import LocalLanguageDetector
from app.infrastructure.public_projection import PublicProjection, graph_facts
from app.presentation.middleware import BodyLimit
from tests.test_workflow import SOURCE


@pytest.mark.parametrize(
    'values',
    [
        {'openai_model': 'another-model'},
        {'openai_reasoning_effort': 'high'},
        {'langsmith_tracing': True},
        {'langchain_tracing_v2': True},
        {'langchain_tracing': True},
        {'langsmith_tracing_v2': True},
        {'openai_log': 'debug'},
        {'otel_sdk_disabled': False},
        {'embeddings_provider': 'openai'},
        {'ai_provider': 'unknown'},
        {'embedding_usd_per_million': 'NaN'},
    ],
)
def test_invalid_provider_or_tracing_configuration_fails_closed(values):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **values)


def test_slow_request_body_has_one_absolute_deadline():
    async def run():
        messages = []

        async def app(*args):
            raise AssertionError('timed-out body must never reach application')

        async def receive():
            await asyncio.sleep(0.1)
            return {'type': 'http.request', 'body': b'private', 'more_body': True}

        async def send(message):
            messages.append(message)

        await BodyLimit(app, timeout=0.01)(
            {'type': 'http', 'method': 'POST'}, receive, send
        )
        assert messages[0]['status'] == 408
        assert b'private' not in messages[1]['body']

    asyncio.run(run())


def test_private_errors_and_suggestions_are_not_cacheable():
    app = create_app(Settings(_env_file=None))
    app.state.knowledge = SimpleNamespace(
        starter_prompts=lambda locale: (
            'revision',
            'a' * 40,
            suggestions(frozenset({'src/content/es/projects.ts'}), locale),
        )
    )
    client = TestClient(app)
    response = client.get('/api/v1/knowledge/suggestions?locale=es')
    assert response.status_code == 200
    assert response.json()['items'][0]['question'].startswith('¿Qué proyectos')
    assert response.json()['source_commit'] == 'a' * 40
    assert 'no-store' in response.headers['cache-control']
    invalid = client.get('/api/v1/knowledge/suggestions?locale=fr')
    assert invalid.status_code == 422 and 'no-store' in invalid.headers['cache-control']
    error = client.post('/api/v1/session', headers={'Origin': 'https://evil.example'})
    assert error.status_code == 403 and 'no-store' in error.headers['cache-control']


def test_starters_disappear_when_their_source_is_removed():
    assert suggestions(frozenset(), 'en') == ()
    assert len(suggestions(frozenset({'src/content/en/projects.ts'}), 'en')) == 1
    assert suggestions(frozenset({'src/content/en/projects.ts'}), 'es') == ()


def test_language_precedence_and_unsupported_input():
    class Detector:
        def supported(self, text):
            return {'hello there friend': 'en', 'hola cómo estás': 'es'}.get(text)

    history = (Turn('user', 'hola cómo estás'),)
    assert select_locale('hello there friend', history, 'es', Detector()) == 'en'
    assert select_locale('Please answer in Spanish', history, 'en', Detector()) == 'es'
    assert select_locale('Responde en inglés', history, 'es', Detector()) == 'en'
    assert select_locale('bonjour', history, 'en', Detector()) == 'es'
    assert select_locale('bonjour', (), 'en', Detector()) == 'en'
    assert select_locale('https://example.org', (), 'es', Detector()) == 'es'


def test_real_offline_language_detector_and_ambiguous_names():
    detector = LocalLanguageDetector()
    assert detector.supported('What projects has Gonzalo developed recently?') == 'en'
    assert (
        detector.supported('¿Qué proyectos desarrolló Gonzalo durante su carrera?')
        == 'es'
    )
    assert detector.supported('Pequeverso') is None
    assert (
        detector.supported('Bonjour, quels projets a développé Gonzalo récemment?')
        is None
    )


def test_live_citations_only_include_references_actually_used():
    other = replace(SOURCE, id='second')
    assert [
        ref['id'] for ref in citations((SOURCE, other), 'Supported claim [2].', False)
    ] == ['second']
    assert citations((SOURCE,), 'No claim about Gonzalo.', False) == []
    with pytest.raises(ValueError):
        citations((SOURCE,), 'Unsupported source [9].', False)


def projection():
    return {
        'schema_version': '1',
        'facts': [
            {
                'id': 'example-project',
                'subject': {'en': 'Example', 'es': 'Ejemplo'},
                'topic': 'projects',
                'text': {'en': 'A public contribution.', 'es': 'Un aporte público.'},
                'verified_on': '2026-10-03',
                'source_path': 'src/content/en/projects.ts',
                'start_line': 1,
                'end_line': 2,
                'technologies': ['Python'],
                'attribution': 'personal',
            }
        ],
    }


def test_public_projection_is_strict_and_preserves_graph_provenance():
    value = PublicProjection.model_validate_json(json.dumps(projection()))
    edges = graph_facts(value, {'src/content/en/projects.ts': 'approved\nevidence'})
    assert edges['src/content/en/projects.ts'][1].object == 'Python'
    assert all(
        edge.start_line == 1 and edge.end_line == 2
        for edge in edges['src/content/en/projects.ts']
    )
    with pytest.raises(ValueError):
        graph_facts(value, {})
    with pytest.raises(ValueError):
        graph_facts(value, {'src/content/en/projects.ts': 'one line'})
    invalid = {**projection(), 'private_notes': 'not permitted'}
    with pytest.raises(ValidationError):
        PublicProjection.model_validate_json(json.dumps(invalid))
    invalid = projection()
    invalid['facts'].append(invalid['facts'][0])
    with pytest.raises(ValidationError):
        PublicProjection.model_validate_json(json.dumps(invalid))
    invalid = {
        **projection(),
        'personal': {'city': 'Example', 'country': 'Example', 'age': 30},
    }
    with pytest.raises(ValidationError):
        PublicProjection.model_validate_json(json.dumps(invalid))


@pytest.mark.parametrize('invalid', [False, True])
def test_openai_embedding_reserves_before_io_and_validates_response(invalid):
    calls = []

    class Accounting:
        def reserve_embedding(self, tokens, purpose):
            calls.append(('reserve', tokens, purpose))
            return 'operation'

        def settle_embedding(self, identifier, tokens):
            calls.append(('settle', identifier, tokens))

    class Client:
        def create(self, **kwargs):
            assert calls[0] == ('reserve', len(b'public text'), 'index')
            assert kwargs['model'] == 'text-embedding-3-small'
            assert kwargs['dimensions'] == 1536
            calls.append(('provider',))
            return SimpleNamespace(
                data=[
                    SimpleNamespace(embedding=[float('nan') if invalid else 0.1] * 1536)
                ],
                usage=SimpleNamespace(total_tokens=3),
            )

    adapter = OpenAIEmbeddings(SimpleNamespace(embeddings=Client()), Accounting())
    if invalid:
        with pytest.raises(ValueError):
            adapter.encode('public text', 'index')
        assert len(calls) == 2
    else:
        assert len(adapter.encode('public text', 'index')) == 1536
        assert calls[-1] == ('settle', 'operation', 3)
    with pytest.raises(ValueError):
        adapter.encode('x' * 16001, 'query')


def test_watcher_coalesces_changes_and_never_marks_failed_checks_fresh():
    async def run():
        stop, release = asyncio.Event(), asyncio.Event()
        observations, started, statuses = [], [], []

        class Source:
            count = 0

            async def latest(self):
                self.count += 1
                if self.count == 2:
                    raise DependencyUnavailableError('source_unavailable')
                if self.count == 1:
                    return 'a' * 40
                return 'c' * 40

        class Publisher:
            async def observe(self, revision):
                observations.append(revision)
                if revision == 'c' * 40:
                    release.set()

            async def publish(self, revision):
                started.append(revision)
                if revision == 'a' * 40:
                    await release.wait()
                    return revision == observations[-1]
                stop.set()
                return True

        await asyncio.wait_for(
            watch(Source(), Publisher(), stop, 0.005, statuses.append), 2
        )
        assert started == ['a' * 40, 'c' * 40]
        assert 'source_unavailable' in statuses and 'superseded' in statuses
        assert observations == ['a' * 40, 'c' * 40, 'c' * 40]

    asyncio.run(run())


def test_semantic_neighbors_are_not_discarded_for_lack_of_shared_words():
    import hashlib

    from app.ai.retrieval import PublicRetrieval
    from app.application.knowledge import Chunk, Corpus

    content = 'Reduced processing latency through service optimization.'
    path = 'src/content/en/experience.ts'
    commit = 'a' * 40
    chunk = Chunk(
        'semantic',
        'Public contribution',
        f'https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{path}#L1-L2',
        'code',
        path,
        1,
        2,
        content,
        hashlib.sha256(content.encode()).hexdigest(),
    )

    class Index:
        async def candidates(self, question):
            return Corpus(
                'version',
                commit,
                (chunk,),
                frozenset({path}),
                ('semantic',),
                semantic=True,
            )

        async def relationships(self, *args, **kwargs):
            return ()

    sources = asyncio.run(PublicRetrieval(Index()).search('snappier pages', 'en'))
    assert sources and sources[0].id == 'semantic'


def test_query_embedding_cancellation_preserves_unknown_reservation():
    async def run():
        called, closed = asyncio.Event(), asyncio.Event()

        class Accounting:
            settled = False

            def reserve_embedding(self, *args):
                return 'reserved'

            def settle_embedding(self, *args):
                self.settled = True

        class Client:
            async def create(self, **kwargs):
                called.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    closed.set()

        accounting = Accounting()
        adapter = OpenAIEmbeddings(
            None, accounting, async_client=SimpleNamespace(embeddings=Client())
        )
        task = asyncio.create_task(adapter.query('question'))
        await called.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set() and not accounting.settled

    asyncio.run(run())


def test_context_preserves_complete_qualifiers_without_truncating_a_span():
    from app.application.answer import bounded_sources, context

    long = replace(
        SOURCE, content='evidence ' * 1500 + 'Estimated; original baseline retained.'
    )
    second = replace(SOURCE, id='other', content='more evidence ' * 1500)
    selected = bounded_sources((long, second))
    assert selected == (long,)
    assert context(selected).endswith('Estimated; original baseline retained.')


def test_evaluation_bank_is_bilingual_and_holdout_is_separate():
    from pathlib import Path

    bank = json.loads(Path('evals/assistant.json').read_text())['cases']
    assert len(bank) == 120 and len({case['id'] for case in bank}) == 120
    assert sum(case['locale'] == 'en' for case in bank) == 60
    assert sum(case['locale'] == 'es' for case in bank) == 60
    assert sum(case['split'] == 'holdout' for case in bank) == 40
    assert not any('answer' in case for case in bank)


def test_evaluation_rejects_paid_mode_before_reading_settings(monkeypatch):
    from scripts.evaluate_assistant import configuration

    monkeypatch.setattr(
        'scripts.evaluate_assistant.Settings',
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError('configuration must not be read')
        ),
    )
    with pytest.raises(ValueError, match='--allow-paid'):
        configuration('openai', False)


def test_privileged_stdlib_scripts_keep_hosted_runner_python_compatibility():
    import ast
    from pathlib import Path

    for name in (
        'dependabot_automation',
        'dependabot_policy',
        'release_manifest',
        'validate_release_file',
    ):
        ast.parse(Path('scripts', name + '.py').read_text(), feature_version=(3, 12))


def test_code_samples_are_not_confused_with_source_references():
    answer = 'A technical example: `items[99]`.\n```python\nvalue = [99]\n```\nGrounded statement [1].'
    assert [ref['id'] for ref in citations((SOURCE,), answer, False)] == [SOURCE.id]


def test_explicit_previous_language_survives_a_short_followup():
    class Detector:
        def supported(self, text):
            return 'en' if text.startswith('Please') else None

    assert (
        select_locale(
            'Pequeverso', (Turn('user', 'Please answer in Spanish'),), 'en', Detector()
        )
        == 'es'
    )


def test_achievement_starter_requires_public_support_and_uses_supported_locale():
    paths = frozenset({'src/content/en/experience.ts'})
    assert all(prompt.topic != 'achievement' for prompt in suggestions(paths, 'en'))
    assert any(
        prompt.topic == 'achievement'
        for prompt in suggestions(paths, 'en', achievements=True)
    )
    assert suggestions(frozenset(), 'es', achievements=True) == ()


def test_graph_driver_outage_is_recoverable_for_knowledge_worker(monkeypatch, tmp_path):
    from neo4j.exceptions import ServiceUnavailable

    from app.infrastructure import knowledge_watch

    def unavailable(*args, **kwargs):
        raise ServiceUnavailable('synthetic unavailable graph')

    monkeypatch.setattr(knowledge_watch, 'sync', unavailable)
    publisher = knowledge_watch.PublicKnowledgePublisher(tmp_path)
    with pytest.raises(DependencyUnavailableError, match='candidate_failed'):
        asyncio.run(publisher.publish('a' * 40))
