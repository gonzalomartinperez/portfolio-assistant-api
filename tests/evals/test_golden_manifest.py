"""The frozen golden set (assistant-quality.md section 5): quotas, hashes and grounding."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from evals.harness.graders._text import contains_phrase, fold
from evals.harness.items import ASSERTION_NAMES, Item, normalized_question
from evals.harness.loader import load_items

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / 'evals' / 'golden'
CORPUS = ROOT / 'evals' / 'corpus'
QUOTAS = {
    'answerable_core': (11, 11),
    'graph_multihop': (6, 6),
    'abstain': (9, 9),
    'adversarial': (6, 6),
    'multi_turn': (3, 3),
    'tool_use': (3, 3),
    'memory': (2, 2),
}
VOSEO = re.compile(
    r'\b(?:tenés|querés|podés|sos|vos|contame|decime|mirá|fijate|sabés|decís|hablás'
    r'|pensás|necesitás|buscás|dame|mostrame|explicame|ayudame|contá|decí|vení|tené)\b',
    re.IGNORECASE,
)
# "dame" and "explicame" are valid tuteo imperatives with an accent-free spelling variant
# (es_no_accents items), so they are removed from the voseo check below.
VOSEO_STRICT = re.compile(
    VOSEO.pattern.replace('|dame|mostrame|explicame|ayudame', '|mostrame|ayudame'),
    re.IGNORECASE,
)


@pytest.fixture(scope='module')
def items() -> list[Item]:
    return load_items(GOLDEN / 'golden.jsonl')


@pytest.fixture(scope='module')
def manifest() -> dict[str, object]:
    return json.loads((GOLDEN / 'manifest.json').read_text())


@pytest.fixture(scope='module')
def corpus_manifest() -> dict[str, object]:
    return json.loads((CORPUS / 'manifest.json').read_text())


@pytest.fixture(scope='module')
def corpus_text(corpus_manifest: dict[str, object]) -> dict[str, str]:
    files = corpus_manifest['files']
    assert isinstance(files, list)
    return {f['key']: fold((CORPUS / f['path']).read_text()) for f in files}


def stratum(item: Item) -> str:
    return item.strata[0]


def test_counts_equal_the_quotas(items: list[Item]):
    assert len(items) == 80
    counts = Counter((stratum(i), i.locale) for i in items)
    assert counts == {
        (name, locale): n
        for name, pair in QUOTAS.items()
        for locale, n in zip(('en', 'es'), pair, strict=True)
    }
    assert Counter(i.locale for i in items) == {'en': 40, 'es': 40}


def test_every_item_is_active_reviewed_and_dated(items: list[Item]):
    for item in items:
        assert item.status == 'active'
        assert item.reviewer.startswith('agents:A+B')
        assert str(item.created) == str(item.last_verified) == '2026-11-14'
        assert item.provenance.startswith(('distilled:legacy-2026-10:', 'new:m2-4'))


def test_minority_locale_share_in_every_stratum(items: list[Item]):
    for name in QUOTAS:
        group = [i for i in items if stratum(i) == name]
        minority = min(Counter(i.locale for i in group).values())
        assert minority / len(group) >= 0.3, name


def test_manifest_matches_the_file(items: list[Item], manifest: dict[str, object]):
    lines = (GOLDEN / 'golden.jsonl').read_text().splitlines()
    hashes = {}
    for line in lines:
        raw = json.loads(line)
        canonical = json.dumps(
            raw, ensure_ascii=False, sort_keys=True, separators=(',', ':')
        )
        hashes[raw['id']] = hashlib.sha256(canonical.encode()).hexdigest()
    assert manifest['items'] == hashes
    counts = manifest['counts']
    assert isinstance(counts, dict)
    assert counts['strata'] == dict(Counter(stratum(i) for i in items))
    assert counts['locales'] == dict(Counter(i.locale for i in items))
    assert manifest['no_retrieval_ablation'].startswith('pending:')  # type: ignore[union-attr]


def test_corpus_snapshot_id(
    items: list[Item], manifest: dict[str, object], corpus_manifest: dict[str, object]
):
    snapshot = corpus_manifest['corpus_snapshot_id']
    assert manifest['corpus_snapshot_id'] == snapshot
    assert {i.corpus_snapshot_id for i in items} == {snapshot}


def test_gold_keys_exist_in_the_corpus_manifest(
    items: list[Item], corpus_manifest: dict[str, object]
):
    files = corpus_manifest['files']
    assert isinstance(files, list)
    keys = {f['key'] for f in files}
    for item in items:
        assert set(item.gold_evidence_ids) <= keys, item.id
        assert len(set(item.gold_evidence_ids)) == len(item.gold_evidence_ids), item.id
        assert all(k.startswith(f'{item.locale}/') for k in item.gold_evidence_ids)
        if item.expected_behavior == 'answer' and 'abstain' not in item.assertions:
            assert item.strata[0] in QUOTAS


def test_required_facts_occur_in_gold_evidence(
    items: list[Item], corpus_text: dict[str, str]
):
    for item in items:
        for fact in item.required_facts:
            assert any(
                contains_phrase(corpus_text[key], fact.match)
                for key in item.gold_evidence_ids
            ), f'{item.id}: {fact.match!r} not in {item.gold_evidence_ids}'


def test_forbidden_claims_are_false_for_the_corpus(
    items: list[Item], corpus_text: dict[str, str]
):
    for item in items:
        for claim in item.forbidden_claims:
            assert not any(
                contains_phrase(text, claim.match) for text in corpus_text.values()
            ), f'{item.id}: {claim.match!r} appears in the corpus'


def test_unsupported_employer_item_exists_and_is_absent(
    items: list[Item], corpus_text: dict[str, str]
):
    employer = [i for i in items if 'unsupported_employer' in i.strata]
    assert {i.locale for i in employer} == {'en', 'es'}
    for item in employer:
        assert item.expected_behavior == 'abstain'
        assert item.gold_evidence_ids == []
        assert all(
            not contains_phrase(text, c.match)
            for text in corpus_text.values()
            for c in item.forbidden_claims
        )


def test_no_duplicate_questions_or_ids(items: list[Item]):
    assert len({normalized_question(i) for i in items}) == len(items)
    assert len({i.id for i in items}) == len(items)


def test_es_items_have_no_voseo(items: list[Item]):
    for item in items:
        if item.locale == 'es':
            for turn in item.turns:
                assert VOSEO_STRICT.search(turn.text) is None, item.id


def test_at_least_eight_messy_spanish_items(items: list[Item]):
    messy = [i for i in items if i.locale == 'es' and 'es_variant' in i.strata]
    assert len(messy) >= 8
    assert all(i.locale == 'es' for i in items if 'es_variant' in i.strata)


# Rules that must hold whatever the model version (coordinator review fixes).
def test_abstain_items_assert_abstains(items: list[Item]):
    for item in items:
        if item.expected_behavior == 'abstain':
            assert 'abstains' in item.assertions, item.id


def test_language_assertion_equals_the_locale(items: list[Item]):
    for item in items:
        languages = [a for a in item.assertions if a.startswith('language_is:')]
        assert languages == [f'language_is:{item.locale}'], item.id


def test_no_duplicate_ids_inside_an_item(items: list[Item]):
    for item in items:
        assert len({f.id for f in item.required_facts}) == len(item.required_facts)
        assert len({f.id for f in item.forbidden_claims}) == len(item.forbidden_claims)
        assert len(set(item.gold_evidence_ids)) == len(item.gold_evidence_ids)
        assert set(item.assertions) <= set(ASSERTION_NAMES) | {
            f'language_is:{item.locale}'
        }


def test_gold_comparison_is_at_file_level(items: list[Item]):
    # Entity presence is asserted through required_facts, never an entity key suffix.
    for item in items:
        assert all('#' not in key for key in item.gold_evidence_ids), item.id
        if 'retrieval_gold_in_topk' in item.assertions:
            assert item.gold_evidence_ids, item.id


def test_answer_items_carry_the_citation_assertions(items: list[Item]):
    for item in items:
        if item.expected_behavior == 'answer':
            assert 'citations_in_retrieved' in item.assertions, item.id
            assert item.required_facts, item.id


def test_tool_and_memory_items_carry_their_fixtures(items: list[Item]):
    for item in items:
        if stratum(item) == 'tool_use':
            assert item.tools is not None
            assert item.tools['flags'] == {'web_access': True}
        if stratum(item) == 'memory':
            assert item.memory_fixture is not None
            assert item.memory_fixture['consent'] is False
            assert item.memory_fixture['store_calls_expected'] == 0
