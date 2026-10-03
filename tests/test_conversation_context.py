"""Context is bounded visitor data, never a replacement for public evidence."""

import asyncio

from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import AnswerCommand
from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from tests.test_workflow import SOURCE


def test_context_budget_keeps_recent_turns_without_promoting_roles():
    history = tuple(
        Turn('user' if i % 2 else 'assistant', str(i) * 1500) for i in range(10)
    )
    result = bounded_history(history)
    assert sum(len(turn.content) for turn in result) == 8000
    assert [turn.content[0] for turn in result] == ['4', '5', '6', '7', '8', '9']
    assert [turn.role for turn in result] == [
        'assistant',
        'user',
        'assistant',
        'user',
        'assistant',
        'user',
    ]


def test_followup_uses_visitor_topic_and_topic_change_drops_it():
    history = (
        Turn('user', 'What did he build at ExampleCompany?'),
        Turn('assistant', 'Unverified invented employer'),
        Turn('user', 'Give me an example'),
    )
    assert 'ExampleCompany' in retrieval_question('Explain that technically', history)
    assert 'invented' not in retrieval_question('Explain that technically', history)
    assert retrieval_question('Where did he study?', history) == 'Where did he study?'
    assert 'ExampleCompany' in retrieval_question('Hazlo más breve', history)
    assert 'ExampleCompany' in retrieval_question('Give me an example of that', history)
    assert 'ExampleCompany' in retrieval_question('Dame un ejemplo de eso', history)
    for question in (
        'Can you give me an example?',
        'Another example?',
        'Give me an example, please.',
        '¿Puedes darme un ejemplo?',
    ):
        assert 'ExampleCompany' in retrieval_question(question, history)


def test_workflow_resolves_retrieval_but_preserves_current_question_and_untrusted_history():
    class Retrieval:
        async def search(self, question, locale):
            assert (
                question == 'What did he build at ExampleCompany?\nGive me an example'
            )
            return (SOURCE,)

    class Provider:
        async def stream(self, question, evidence, locale, history=()):
            assert question == 'Give me an example'
            assert history[0].role == 'user'
            assert 'ExampleCompany' not in evidence
            assert 'Public evidence' in evidence
            yield 'Grounded answer'

    async def run():
        command = AnswerCommand(
            'context-test',
            'Give me an example',
            'en',
            (Turn('user', 'What did he build at ExampleCompany?'),),
        )
        events = [
            event
            async for event in LangGraphWorkflow(Retrieval(), Provider()).stream(
                command
            )
        ]
        assert events[-1].text == 'Grounded answer'

    asyncio.run(run())


def test_settings_errors_do_not_render_supplied_secret_values():
    import pytest

    from app.bootstrap.config import Settings

    with pytest.raises(ValueError) as error:
        Settings(environment='production', openai_api_key='sentinel-private-value')
    assert 'sentinel-private-value' not in str(error.value)


def test_spanish_translation_followups_keep_the_topic():
    history = (Turn('user', 'What did he build at Rampy?'),)
    for question in ('Tradúcelo al inglés', 'Traduce eso al español', 'traducelo'):
        assert 'Rampy' in retrieval_question(question, history)


def test_named_examples_replace_the_topic_for_later_followups():
    history = (
        Turn('user', 'What did he build at PreviousCompany?'),
        Turn('user', 'Give me an example of his work at CurrentCompany'),
        Turn('assistant', 'Unverified employer InventedCompany'),
    )
    for question in ('Explain that technically', 'Make it shorter'):
        query = retrieval_question(question, history)
        assert 'CurrentCompany' in query
        assert 'PreviousCompany' not in query
        assert 'InventedCompany' not in query
    spanish = (Turn('user', 'Dame un ejemplo de su trabajo en CurrentCompany'),)
    assert 'CurrentCompany' in retrieval_question('Hazlo más breve', spanish)


def test_referential_refinement_survives_a_further_followup():
    history = (
        Turn('user', 'What did he build at ExampleCompany?'),
        Turn('assistant', 'Unsupported technology InventedStack'),
        Turn('user', 'Which technologies did he use there?'),
    )
    query = retrieval_question('Give me an example', history)
    assert 'ExampleCompany' in query
    assert 'technologies' in query
    assert 'InventedStack' not in query
    assert retrieval_question('Instead, explain education', history) == (
        'Instead, explain education'
    )


def test_fixture_does_not_attribute_another_employers_contribution():
    from app.domain.fixture import fixture_message

    evidence = """PUBLIC SOURCE one lines 1-5:
company: "Rampy",
contributions: ["Built the public application backend with tested boundaries."],
PUBLIC SOURCE two lines 1-5:
company: "OtherEmployer",
contributions: ["Built an unrelated infrastructure migration for another employer."],
"""
    answer = fixture_message('What did he build at Rampy?', evidence, 'en')
    assert 'public application backend' in answer
    assert 'unrelated infrastructure' not in answer


def test_short_qualified_metric_keeps_its_source_citation():
    from dataclasses import replace

    from app.application.runs import citations
    from app.domain.fixture import fixture_message

    source = replace(
        SOURCE, content='value: "30%", label: "Latency", qualifier: "Estimated"'
    )
    answer = fixture_message(
        'performance metrics',
        f'PUBLIC SOURCE source lines 1-2:\n{source.content}',
        'en',
    )
    assert 'Latency: 30%. Estimated' in answer
    assert citations((source,), answer, True)[0]['id'] == source.id


def test_fixture_excludes_previous_employer_text_in_the_same_source_span():
    from app.domain.fixture import fixture_message

    evidence = """PUBLIC SOURCE one lines 1-35:
qualifier: "An estimated improvement for the previous employer only.",
company: "CurrentCompany",
contributions: ["Implemented a merchant portal with a reactive service boundary."],
company: "NextCompany",
contributions: ["Implemented an unrelated advertising platform elsewhere."],
"""
    answer = fixture_message('What did he build at CurrentCompany?', evidence, 'en')
    assert 'merchant portal' in answer
    assert 'previous employer' not in answer
    assert 'advertising platform' not in answer


def test_explicit_comparison_can_include_both_employers():
    from app.domain.fixture import fixture_message

    evidence = """PUBLIC SOURCE one lines 1-5:
company: "Rampy",
contributions: ["Built the public application backend with tested boundaries."],
PUBLIC SOURCE two lines 1-5:
company: "OtherEmployer",
contributions: ["Built another product with different infrastructure constraints."],
"""
    answer = fixture_message('Compare work at Rampy with OtherEmployer', evidence, 'en')
    assert 'public application backend' in answer
    assert 'different infrastructure constraints' in answer
