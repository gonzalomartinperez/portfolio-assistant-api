"""The frozen full tier and its sealed holdout (assistant-quality.md section 6).

Holdout rule: this module reads the sealed file only programmatically and never puts an
item id, a question or an answer in an assertion message. Failures print counts or paths.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from evals.harness.distill_full import (
    HOLDOUT_FAMILIES,
    canonical_hash,
    counts,
    find_duplicates,
)
from evals.harness.graders._text import contains_phrase, fold
from evals.harness.items import Item, SealedItem, normalized_question
from evals.harness.loader import load_items, sealed_aggregate
from evals.harness.report import ItemOutcome, build_report
from evals.harness.result import GradeResult
from tests.evals.test_golden_manifest import VOSEO_STRICT

ROOT = Path(__file__).resolve().parents[2]
FULL = ROOT / 'evals' / 'full'
CORPUS = ROOT / 'evals' / 'corpus'
ARCHIVE = ROOT / 'evals' / 'archive' / 'legacy-2026-10'
SEALED = FULL / 'holdout.sealed.jsonl'
PARTS = {
    'intent_family': (152, 152),
    'adversarial': (20, 20),
    'multi_turn': (10, 10),
    'cross_lingual': (10, 10),
}
HOLDOUT_PARTS = {
    'intent_family': (40, 40),
    'adversarial': (5, 5),
    'cross_lingual': (5, 5),
}
SEALED_SCAN_ROOTS = (
    'prompts',
    'app',
    'evals/harness',
    'evals/golden',
    'scripts',
    'docs',
    '.claude',
    '.agents',
    '.codex',
    'AGENTS.md',
    'CLAUDE.md',
    'CONTRIBUTING.md',
)


@pytest.fixture(scope='module')
def items() -> list[Item]:
    return load_items(FULL / 'full.jsonl')


@pytest.fixture(scope='module')
def holdout() -> list[Item]:
    return load_items(SEALED, sealed=True)


@pytest.fixture(scope='module')
def manifest() -> dict[str, object]:
    return json.loads((FULL / 'manifest.json').read_text())


@pytest.fixture(scope='module')
def corpus_manifest() -> dict[str, object]:
    return json.loads((CORPUS / 'manifest.json').read_text())


@pytest.fixture(scope='module')
def corpus_text(corpus_manifest: dict[str, object]) -> dict[str, str]:
    files = corpus_manifest['files']
    assert isinstance(files, list)
    return {f['key']: fold((CORPUS / f['path']).read_text()) for f in files}


def part(item: Item) -> str:
    return item.strata[0]


def _per_locale(group: list[Item]) -> tuple[int, int]:
    found = Counter(i.locale for i in group)
    return found['en'], found['es']


def test_development_counts_per_part_and_locale(items: list[Item]):
    assert len(items) == 384
    for name, expected in PARTS.items():
        assert _per_locale([i for i in items if part(i) == name]) == expected, name
    assert {part(i) for i in items} == set(PARTS)


def test_en_and_es_are_within_five_items(
    items: list[Item], holdout: list[Item], manifest: dict[str, object]
):
    for group in (items, holdout, [*items, *holdout]):
        en, es = _per_locale(group)
        assert abs(en - es) <= 5
    for name in PARTS:
        en, es = _per_locale([i for i in items if part(i) == name])
        assert abs(en - es) <= 5


def test_holdout_counts_are_the_sealed_design(holdout: list[Item]):
    assert len(holdout) == 100
    for name, expected in HOLDOUT_PARTS.items():
        assert _per_locale([i for i in holdout if part(i) == name]) == expected, name
    families = {
        i.provenance.split(':')[2] for i in holdout if part(i) == 'intent_family'
    }
    assert len(families) == HOLDOUT_FAMILIES
    assert {i.provenance for i in holdout if part(i) != 'intent_family'} == {
        'new:m2-4-full-holdout'
    }


def test_total_is_about_450_and_documented(items: list[Item], holdout: list[Item]):
    assert len(items) + len(holdout) == 484
    selection = json.loads((FULL / 'selection.json').read_text())
    assert '484' in selection['size_note']
    assert '484' in (FULL / 'README.md').read_text()


def _bad_count(group: list[Item]) -> int:
    """Items breaking the common rules; a number only, never an item."""
    prefixes = ('distilled:legacy-2026-10:', 'adapted:legacy-2026-10:', 'new:m2-4-full')
    return sum(
        not (
            i.status == 'active'
            and i.reviewer == 'deterministic:self-check'
            and str(i.created) == str(i.last_verified) == '2026-11-14'
            and i.provenance.startswith(prefixes)
        )
        for i in group
    )


def test_every_item_is_active_dated_and_self_checked(
    items: list[Item], holdout: list[Item]
):
    assert _bad_count(items) == 0
    bad = _bad_count(holdout)
    assert bad == 0, f'{bad} holdout items break the common rules'


def test_manifest_matches_the_development_file(
    items: list[Item], manifest: dict[str, object]
):
    hashes = {}
    for line in (FULL / 'full.jsonl').read_text().splitlines():
        raw = json.loads(line)
        hashes[raw['id']] = canonical_hash(raw)
    assert manifest['items'] == hashes
    raws = [json.loads(line) for line in (FULL / 'full.jsonl').read_text().splitlines()]
    assert manifest['counts'] == counts(raws)
    assert 'no_retrieval_ablation' in manifest
    assert str(manifest['no_retrieval_ablation']).startswith('pending:')
    assert str(manifest['pass_gate']).startswith('none')


def test_holdout_hash_and_counts_are_committed(
    holdout: list[Item], manifest: dict[str, object]
):
    sealed = manifest['holdout']
    assert isinstance(sealed, dict)
    assert sealed['sha256'] == hashlib.sha256(SEALED.read_bytes()).hexdigest()
    assert sealed['file'] == 'evals/full/holdout.sealed.jsonl'
    raws = [json.loads(line) for line in SEALED.read_text().splitlines()]
    assert sealed['counts'] == counts(raws)
    # The manifest keeps counts only: no id, question or per-item hash for the holdout.
    assert set(sealed) == {'file', 'sha256', 'counts'}
    assert 'hold-' not in json.dumps(manifest)


def test_corpus_snapshot_id(
    items: list[Item],
    holdout: list[Item],
    manifest: dict[str, object],
    corpus_manifest: dict[str, object],
):
    snapshot = corpus_manifest['corpus_snapshot_id']
    assert manifest['corpus_snapshot_id'] == snapshot
    wrong = sum(i.corpus_snapshot_id != snapshot for i in [*items, *holdout])
    assert wrong == 0, f'{wrong} items have a stale corpus snapshot'


def _grounding_failures(group: list[Item], corpus_text: dict[str, str]) -> list[str]:
    """Ids of items whose gold, facts or forbidden claims are not grounded in the corpus."""
    failures = []
    for item in group:
        gold_text = [corpus_text[k] for k in item.gold_evidence_ids if k in corpus_text]
        good = len(gold_text) == len(item.gold_evidence_ids)
        good &= len(set(item.gold_evidence_ids)) == len(item.gold_evidence_ids)
        good &= all('#' not in key for key in item.gold_evidence_ids)
        for fact in item.required_facts:
            good &= any(contains_phrase(text, fact.match) for text in gold_text)
        for claim in item.forbidden_claims:
            good &= not any(
                contains_phrase(text, claim.match) for text in corpus_text.values()
            )
        if item.expected_behavior == 'answer':
            good &= bool(item.required_facts) and bool(item.gold_evidence_ids)
            good &= item.gold_evidence_ids[0].startswith(f'{item.locale}/')
        else:
            good &= not item.gold_evidence_ids and not item.required_facts
        if not good:
            failures.append(item.id)
    return failures


def test_development_grounding(items: list[Item], corpus_text: dict[str, str]):
    assert _grounding_failures(items, corpus_text) == []


def test_holdout_grounding_reports_only_a_count(
    holdout: list[Item], corpus_text: dict[str, str]
):
    failures = _grounding_failures(holdout, corpus_text)
    assert len(failures) == 0, f'{len(failures)} sealed items are not grounded'


def test_es_items_have_no_voseo(items: list[Item], holdout: list[Item]):
    bad = [
        i.id
        for i in [*items, *holdout]
        if i.locale == 'es' and any(VOSEO_STRICT.search(turn.text) for turn in i.turns)
    ]
    assert [b for b in bad if not b.startswith('hold-')] == []
    assert not [b for b in bad if b.startswith('hold-')], 'voseo in sealed items'


def test_no_duplicate_ids_or_questions_across_both_files(
    items: list[Item], holdout: list[Item]
):
    both = [*items, *holdout]
    assert len({i.id for i in both}) == len(both)
    assert len({normalized_question(i) for i in both}) == len(both)


def _rule_breaks(group: list[Item]) -> int:
    count = 0
    for item in group:
        languages = [a for a in item.assertions if a.startswith('language_is:')]
        ok = languages == [f'language_is:{item.locale}']
        if item.expected_behavior == 'answer':
            ok &= 'citations_in_retrieved' in item.assertions
            ok &= 'citations_nonempty' in item.assertions
        if item.expected_behavior == 'abstain':
            ok &= 'citations_empty' in item.assertions
        count += not ok
    return count


def test_assertion_and_language_rules(items: list[Item], holdout: list[Item]):
    assert _rule_breaks(items) == 0
    broken = _rule_breaks(holdout)
    assert broken == 0, f'{broken} holdout items break the assertion rules'


def test_families_cover_the_legacy_bank(items: list[Item], holdout: list[Item]):
    bank = json.loads((ARCHIVE / 'assistant-intents.json').read_text())
    selection = json.loads((FULL / 'selection.json').read_text())
    legacy = {f['id'] for f in bank['families']}
    dropped = {e['dropped'] for e in selection['dropped_families']}
    development = {
        i.provenance.split(':')[2] for i in items if part(i) == 'intent_family'
    }
    sealed = {i.provenance.split(':')[2] for i in holdout if part(i) == 'intent_family'}
    assert len(dropped) == 4 and len(development) == 76 and len(sealed) == 20
    assert development | sealed | dropped == legacy
    assert not (development & sealed) and not (development | sealed) & dropped
    # Every development family has 2 locales x 2 phrasings; sealed ones the same.
    for group, size in ((items, 76), (holdout, 20)):
        rows = Counter(i.provenance for i in group if part(i) == 'intent_family')
        assert len(rows) == size and set(rows.values()) == {4}


def _spec(**families: dict[str, object]) -> dict[str, object]:
    return {'families': families}


def _family(identifier: str, topic: str, question: str) -> dict[str, object]:
    return {
        'id': identifier,
        'topic': topic,
        'variants': [{'en': question, 'es': question}],
    }


def _entry(gold: str, facts: list[str], behavior: str = 'answer') -> dict[str, object]:
    return {'behavior': behavior, 'gold': gold, 'en': facts, 'es': facts}


def test_duplicate_rule_is_strict_and_deterministic():
    spec = _spec(
        a=_entry('e', ['Rampy', 'Agno']),
        b=_entry('e', ['Rampy', 'Agno']),
        c=_entry('p', ['Rampy', 'Agno']),  # other gold: not a duplicate
        d=_entry('e', ['Rampy', 'Agno'], 'abstain'),  # other behavior
        e=_entry('e', ['Teamcubation']),  # other facts
    )
    families = [_family(n, 'experience', f'question {n}') for n in 'abcde']
    log = find_duplicates(spec, families, frozenset())  # type: ignore[arg-type]
    assert [(e['dropped'], e['kept']) for e in log] == [('b', 'a')]
    assert log == find_duplicates(spec, families, frozenset())  # type: ignore[arg-type]
    # A sealed family is never dropped; its partner goes.
    sealed = find_duplicates(spec, families, frozenset({'a'}))  # type: ignore[arg-type]
    assert [e['dropped'] for e in sealed] == ['b']
    protected = find_duplicates(spec, families, frozenset({'b'}))  # type: ignore[arg-type]
    assert [e['dropped'] for e in protected] == ['a']
    # Different topic: never duplicates.
    other = [_family('a', 'experience', 'x'), _family('b', 'skills', 'x')]
    assert find_duplicates(spec, other, frozenset()) == []  # type: ignore[arg-type]


def test_recorded_drops_are_real_duplicates():
    selection = json.loads((FULL / 'selection.json').read_text())
    dropped = selection['dropped_families']
    assert {e['dropped'] for e in dropped} == {
        'language-58',
        'metrics-31',
        'metrics-35',
        'filomena-legacy-migration',
    }
    assert all(e['score'] >= 0.6 and e['reason'] for e in dropped)
    assert selection['dropped_adversarial_pairs'] == []
    assert '450' in selection['size_note']


def test_legacy_inputs_are_archived():
    for name in ('assistant.json', 'assistant-intents.json', 'scenarios.json'):
        assert (ARCHIVE / name).is_file(), name
    scenarios = json.loads((ARCHIVE / 'scenarios.json').read_text())
    assert len(scenarios) == 16
    for name in ('assistant.json', 'assistant-intents.json'):
        original = ROOT / 'evals' / name
        if original.exists():  # originals stay while scripts and tests still read them
            assert original.read_bytes() == (ARCHIVE / name).read_bytes()


# Sealed-holdout rules (assistant-quality.md section 6.2).
def _scannable(root: Path) -> list[Path]:
    suffixes = {
        '.md',
        '.py',
        '.json',
        '.jsonl',
        '.toml',
        '.yml',
        '.yaml',
        '.txt',
        '.csv',
        '',
    }
    paths: list[Path] = []
    for name in SEALED_SCAN_ROOTS:
        base = ROOT / name
        if base.is_file():
            paths.append(base)
        elif base.is_dir():
            paths.extend(p for p in base.rglob('*') if p.is_file())
    return [p for p in paths if '__pycache__' not in p.parts and p.suffix in suffixes]


HOLDOUT_ID = re.compile(r'\bhold-(?:en|es)-(?:int|adv|xln)-\d{3}\b')


def _mentions_holdout(text: str, ids: set[str]) -> bool:
    return HOLDOUT_ID.search(text) is not None or any(i in text for i in ids)


def test_no_prompt_or_rule_file_mentions_a_holdout_id(holdout: list[Item]):
    ids = {i.id for i in holdout}
    assert len(ids) == 100
    for path in _scannable(ROOT):
        text = path.read_text(encoding='utf-8', errors='ignore')
        if _mentions_holdout(text, ids):
            pytest.fail(f'holdout id mentioned in {path.relative_to(ROOT)}')


def _normal(text: str) -> str:
    return re.sub(r'[\W_]+', ' ', fold(text)).strip()


def test_no_scanned_file_contains_a_sealed_question(holdout: list[Item]):
    questions = {_normal(t.text) for i in holdout for t in i.turns}
    assert len(questions) == 100
    for path in _scannable(ROOT):
        text = _normal(path.read_text(encoding='utf-8', errors='ignore'))
        if any(q in text for q in questions):
            pytest.fail(f'sealed question found in {path.relative_to(ROOT)}')


def test_scan_roots_cover_the_prompt_and_rule_locations():
    names = {p.name for p in _scannable(ROOT)}
    assert {'AGENTS.md', 'CLAUDE.md', 'workflow.py', 'distill_full.py'} <= names
    assert 'golden.jsonl' in names and 'file-moves.md' in names
    assert (ROOT / 'app' / 'ai').is_dir() and (ROOT / 'app' / 'domain').is_dir()


def test_the_scan_detects_a_planted_id():
    fake = 'hold-en-int-999'
    assert _mentions_holdout(f'see {fake} here', set())
    assert _mentions_holdout('see probe-1 here', {'probe-1'})
    assert not _mentions_holdout('no ids in this rule file', {'probe-1'})


def test_the_harness_exposes_only_aggregates_for_the_holdout(
    manifest: dict[str, object],
):
    aggregate = sealed_aggregate(SEALED)
    assert aggregate.total == 100
    assert aggregate.sha256 == manifest['holdout']['sha256']  # type: ignore[index]
    assert set(vars(aggregate)) == {'sha256', 'total', 'by_part', 'by_locale'}
    assert aggregate.by_part == {
        'adversarial': 10,
        'cross_lingual': 10,
        'intent_family': 80,
    }
    assert aggregate.by_locale == {'en': 50, 'es': 50}


def test_a_sealed_report_never_contains_item_ids():
    outcomes = [
        ItemOutcome(
            f'probe-en-int-{n:03d}',
            'en',
            ('intent_family', 'profile'),
            (GradeResult('abstains', n % 2 == 0, 'x'),),
        )
        for n in range(1, 7)
    ]
    sealed = build_report(outcomes, tier='holdout', run_id='r1', sealed=True)
    text = json.dumps(sealed)
    assert 'probe-' not in text
    assert sealed['sealed'] is True
    assert sealed['failed_assertion_counts'] == {'abstains': 3}
    assert sealed['failing_counts_by_stratum'] == {'intent_family': 3, 'profile': 3}
    open_report = build_report(outcomes, tier='full', run_id='r2')
    assert 'probe-en-int-001' in json.dumps(open_report)


def test_a_sealed_report_hides_small_cells_and_the_holdout_tier_must_be_sealed():
    def rows(stratum: str, count: int) -> list[ItemOutcome]:
        return [
            ItemOutcome(
                f'probe-{stratum}-{n}',
                'en',
                ('intent_family', stratum),
                (GradeResult('abstains', False, 'x'),),
            )
            for n in range(count)
        ]

    outcomes = [*rows('big', 6), *rows('small', 4)]
    report = build_report(outcomes, tier='holdout', run_id='r3', sealed=True)
    strata = report['by_stratum']
    assert isinstance(strata, dict)
    assert 'suppressed' in strata['small'] and strata['big']['total'] == 6
    assert 'small' not in report['failing_counts_by_stratum']  # type: ignore[operator]
    assert 'probe-' not in json.dumps(report)
    with pytest.raises(ValueError):
        build_report(outcomes, tier='holdout', run_id='r4')


def test_sealed_items_have_a_redacted_repr(holdout: list[Item]):
    first = holdout[0]
    assert isinstance(first, SealedItem)
    text = repr(first) + str(first) + repr(holdout[:3])
    assert first.turns[0].text not in text and first.id not in text
