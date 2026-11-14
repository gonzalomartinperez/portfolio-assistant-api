"""Item model, committed JSON Schema and JSONL loader."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.harness.graders import REGISTRY
from evals.harness.items import (
    ASSERTION_NAMES,
    SCHEMA_PATH,
    generate_schema,
    normalized_question,
    schema_text,
)
from evals.harness.loader import ItemLoadError, load_items
from tests.evals.support import make_item

ITEM = {
    'id': 'gold-es-edu-001',
    'locale': 'es',
    'strata': ['answerable_core', 'education'],
    'turns': [{'role': 'user', 'text': '¿Dónde estudió Gonzalo?'}],
    'expected_behavior': 'answer',
    'required_facts': [{'id': 'uns', 'match': 'Universidad Nacional del Sur'}],
    'gold_evidence_ids': ['es/education'],
    'assertions': ['language_is:es', 'citations_in_retrieved', 'no_canary'],
    'provenance': 'distilled:legacy-2026-10:education-3',
    'reviewer': 'owner',
    'created': '2026-11-20',
    'last_verified': '2026-11-20',
    'corpus_snapshot_id': 'corpus-abc',
}


def test_committed_schema_equals_generated():
    assert SCHEMA_PATH.read_text() == schema_text()


def test_schema_is_2020_12_and_closed():
    schema = generate_schema()
    assert schema['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert schema['additionalProperties'] is False
    assert schema['properties']['locale']['enum'] == ['en', 'es']  # type: ignore[index]
    assert {'id', 'turns', 'assertions', 'corpus_snapshot_id'} <= set(
        schema['required']
    )  # type: ignore[call-overload]


def test_valid_and_invalid_items_against_the_model():
    assert make_item(**ITEM).id == 'gold-es-edu-001'
    for bad in ({**ITEM, 'extra': 1}, {**ITEM, 'locale': 'fr'}, {**ITEM, 'turns': []}):
        with pytest.raises(ValidationError):
            make_item(**bad)


def test_assertion_names_match_the_registry():
    assert set(REGISTRY) == set(ASSERTION_NAMES)


@pytest.mark.parametrize(
    'change',
    [
        {'assertions': ['made_up']},
        {'assertions': ['language_is:fr']},
        {'assertions': ['abstains', 'abstains']},
        {'assertions': []},
        {'gold_evidence_ids': ['src/content/en/projects.ts']},
        {'gold_evidence_ids': ['en/projects#Bad_Slug']},
        {'status': 'quarantined'},
        {
            'status': 'active',
            'quarantine': {'issue': '#1', 'owner': 'o', 'deadline': '2026-12-01'},
        },
        {'status': 'retired'},
        {'retired_reason': 'obsolete'},
        {'schema_version': '2'},
        {'id': 'Bad ID'},
        {'created': 'yesterday'},
        {'turns': [{'role': 'assistant', 'text': 'hi'}]},
        {'required_facts': [{'id': 'x', 'match': ' '}]},
    ],
)
def test_invalid_items_are_rejected(change):
    with pytest.raises(ValidationError):
        make_item(**change)


def test_status_variants_and_permissive_assistant_experience_fields():
    quarantined = make_item(
        status='quarantined',
        quarantine={'issue': '#12', 'owner': 'agent', 'deadline': '2026-12-01'},
    )
    assert quarantined.quarantine is not None
    assert make_item(status='retired', retired_reason='gold key removed').retired_reason
    item = make_item(
        tools={'expected': ['web_search'], 'query_fixed': True},
        memory_fixture={'consent': False, 'users': ['a', 'b']},
    )
    assert item.tools == {'expected': ['web_search'], 'query_fixed': True}
    assert item.memory_fixture is not None


def test_normalized_question_ignores_case_accents_and_punctuation():
    first = make_item(turns=[{'text': '¿Dónde  ESTUDIÓ Gonzalo?'}])
    second = make_item(turns=[{'text': 'donde estudio gonzalo'}])
    assert normalized_question(first) == normalized_question(second)


def write(path: Path, *lines: object) -> Path:
    path.write_text(
        '\n'.join(x if isinstance(x, str) else json.dumps(x) for x in lines) + '\n'
    )
    return path


def test_loader_accepts_valid_lines_and_skips_blank_ones(tmp_path):
    other = {**ITEM, 'id': 'gold-es-edu-002', 'turns': [{'text': 'Otra pregunta'}]}
    path = write(tmp_path / 'a.jsonl', ITEM, '', other)
    assert [i.id for i in load_items(path)] == ['gold-es-edu-001', 'gold-es-edu-002']


def test_loader_reports_file_line_and_id_for_every_problem(tmp_path):
    path = write(
        tmp_path / 'bad.jsonl',
        ITEM,
        '{not json',
        {**ITEM, 'id': 'gold-es-edu-003', 'locale': 'fr', 'turns': [{'text': 'x'}]},
        '[1]',
        {**ITEM, 'turns': [{'text': 'distinta'}]},
        {
            **ITEM,
            'id': 'gold-es-edu-009',
            'turns': [{'text': '¿DONDE estudio Gonzalo'}],
        },
    )
    with pytest.raises(ItemLoadError) as raised:
        load_items(path)
    lines = str(raised.value).splitlines()
    assert f'{path}:2: invalid JSON' in lines[0]
    assert f'{path}:3: item gold-es-edu-003: locale' in lines[1]
    assert f'{path}:4: item ?:' in lines[2]
    assert (
        f'{path}:5: item gold-es-edu-001: duplicate id (first at line 1)' in lines[-2]
    )
    assert (
        f'{path}:6: item gold-es-edu-009: duplicate question of gold-es-edu-001 (line 1)'
        in lines[-1]
    )
