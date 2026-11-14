"""One-shot, deterministic build of the full evaluation tier (assistant-quality.md section 6).

Sibling of ``distill.py`` (golden tier). No network and no model. Inputs are the frozen
legacy bank under ``evals/archive/legacy-2026-10/`` plus the authored per-family spec
``evals/harness/full_spec.json`` (facts, forbidden claims and gold evidence grounded in
``evals/corpus/``). Outputs: ``evals/full/full.jsonl`` (development), the sealed
``evals/full/holdout.sealed.jsonl``, ``manifest.json`` and ``selection.json``.

Composition (about 484 items = 384 development + 100 sealed holdout; no pass gate):

* intent families: 96 of the 100 legacy families (only real duplicates are dropped, see
  ``find_duplicates``; the plan's "10" is not forced) x 2 locales x {direct, conversational}.
  20 of the old holdout families are sealed (80 items, rephrased natively, never the legacy
  wording; pinned in ``SEALED_FAMILIES``); the other 76 families form 304 development items.
* adversarial: all 40 legacy prompts (20 EN/ES pairs) in development + 10 new sealed.
* multi-turn: 20 development (the 15 legacy scenarios, one locale each, plus 5 new).
* cross-lingual and edge: 20 development + 10 sealed.

The total is above the plan's 450 because the plan keeps "the existing 40" adversarial prompts
and only four families qualify as duplicates under the strict rule.

Sealing: the holdout wording is NOT stored in this repository except in the sealed file.
``--holdout-phrasing PATH`` reads a one-off JSON written by the author; after the sealed
file exists it is the source of truth and the phrasing file is deleted. The sealed file is
never printed: this module reports counts and a sha256 only.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from evals.harness.distill import ROOT, _scenarios
from evals.harness.graders._text import fold

ARCHIVE = ROOT / 'evals' / 'archive' / 'legacy-2026-10'
FULL = ROOT / 'evals' / 'full'
SPEC = ROOT / 'evals' / 'harness' / 'full_spec.json'
LOCALES = ('en', 'es')
DATE = '2026-11-14'
REVIEWER = 'deterministic:self-check'
TOPIC_FOLDER = {'p': 'profile', 'e': 'experience', 'j': 'projects', 'd': 'education'}
DUPLICATE_THRESHOLD = 0.6
HOLDOUT_FAMILIES = 20
# Pinned at sealing time (legacy family ids are public; the wording is not). Keeping them
# fixed keeps the sealed file and its hash stable when the duplicate screen changes.
SEALED_FAMILIES = (
    'projects-12',
    'education-36',
    'experience-9',
    'boundaries-51',
    'skills-27',
    'fit-45',
    'language-57',
    'rampy-mobile-startup',
    'profile-3',
    'personal-48',
    'projects-15',
    'education-39',
    'rampy-encryption',
    'boundaries-54',
    'skills-30',
    'fit-retrieval-role',
    'language-60',
    'filomena-concurrency',
    'profile-work-arrangement',
    'projects-18',
)
TEMPLATE_WORDS = frozenset(
    [
        'gonzalo',
        'gonzalos',
        'public',
        'publicly',
        'portfolio',
        'evidence',
        'documented',
        'sources',
        'source',
        'work',
        'worked',
        'does',
        'his',
        'about',
        'tell',
        'what',
        'which',
        'how',
        'where',
        'who',
        'can',
        'give',
        'used',
        'has',
        'have',
        'role',
        'roles',
    ]
)
STOPWORDS = frozenset(
    [
        'the',
        'and',
        'for',
        'with',
        'his',
        'how',
        'what',
        'which',
        'does',
        'did',
        'who',
        'are',
        'was',
        'from',
        'that',
        'this',
        'about',
        'into',
        'can',
        'you',
        'tell',
        'give',
        'any',
        'have',
        'has',
        'not',
        'use',
        'used',
        'where',
        'when',
        'your',
        'our',
        'por',
        'para',
        'con',
        'del',
        'las',
        'los',
        'una',
        'uno',
        'que',
        'cual',
        'como',
        'qué',
        'cómo',
        'cuál',
        'sus',
        'sobre',
        'entre',
        'ese',
        'esa',
        'son',
        'fue',
        'ser',
        'está',
        'estan',
        'hay',
        'muy',
        'más',
        'sin',
        'cuando',
        'donde',
        'dónde',
        'cuáles',
    ]
)


def tokens(text: str) -> frozenset[str]:
    """Lexical signature: folded words of 3+ letters, stopwords removed, 5-letter stems."""
    words = re.findall(r'[a-z0-9]{3,}', fold(text))
    return frozenset(w[:5] for w in words if w not in STOPWORDS)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def distinctive(text: str) -> frozenset[str]:
    """Folded words of 3+ letters without stopwords and template words (no stemming)."""
    words = re.findall(r'[a-z0-9]{3,}', fold(text))
    return frozenset(w for w in words if w not in STOPWORDS and w not in TEMPLATE_WORDS)


def find_duplicates(
    spec: dict[str, Any], families: list[dict[str, Any]], protected: frozenset[str]
) -> list[dict[str, object]]:
    """Strict duplicate rule; returns the drop log (possibly empty).

    Two families are duplicates only if they share the legacy topic, the expected behavior and
    the gold evidence keys, AND either their English required facts overlap with Jaccard of at
    least 0.6 or (when both have no facts) the distinctive-token Jaccard of all their EN and ES
    variants is at least 0.6. Pairs are taken by descending score; a family that was kept for an
    earlier pair is never dropped later. A protected (sealed) family is never dropped: its
    partner goes. Otherwise the thinner family (fewer distinctive tokens, tie: larger id) goes.
    """
    by_id = {str(f['id']): f for f in families}
    table = spec['families']
    pairs: list[tuple[float, str, str, str]] = []
    ids = list(by_id)
    for i, first in enumerate(ids):
        for second in ids[i + 1 :]:
            if by_id[first]['topic'] != by_id[second]['topic']:
                continue
            a, b = table[first], table[second]
            if a['behavior'] != b['behavior']:
                continue
            if json.dumps(a['gold'], sort_keys=True) != json.dumps(
                b['gold'], sort_keys=True
            ):
                continue
            facts_a = {fold(x) for x in a['en']}
            facts_b = {fold(x) for x in b['en']}
            if facts_a and facts_b:
                score, basis = len(facts_a & facts_b) / len(facts_a | facts_b), 'facts'
            else:
                text = [
                    ' '.join(v['en'] + ' ' + v['es'] for v in by_id[f]['variants'])
                    for f in (first, second)
                ]
                score = jaccard(distinctive(text[0]), distinctive(text[1]))
                basis = 'distinctive_tokens'
            if score >= DUPLICATE_THRESHOLD:
                pairs.append((score, first, second, basis))
    log: list[dict[str, object]] = []
    gone: set[str] = set()
    locked: set[str] = set()
    for score, first, second, basis in sorted(pairs, key=lambda p: (-p[0], p[1], p[2])):
        if first in gone or second in gone:
            continue
        if first in protected and second in protected:
            continue
        if first in protected or second in protected:
            dropped = second if first in protected else first
        else:
            size = {
                f: len(distinctive(' '.join(v['en'] for v in by_id[f]['variants'])))
                for f in (first, second)
            }
            dropped = (
                max(first, second)
                if size[first] == size[second]
                else min((first, second), key=lambda f: size[f])
            )
        kept = second if dropped == first else first
        if dropped in locked:
            continue
        locked.add(kept)
        gone.add(dropped)
        log.append(
            {
                'dropped': dropped,
                'kept': kept,
                'topic': by_id[first]['topic'],
                'behavior': table[first]['behavior'],
                'gold': table[first]['gold'],
                'basis': basis,
                'score': round(score, 4),
                'reason': 'same topic, behavior and gold evidence with required facts '
                'overlapping at or above 0.6'
                if basis == 'facts'
                else 'same topic, behavior and gold evidence with distinctive tokens '
                'overlapping at or above 0.6',
            }
        )
    return log


def archive_inputs() -> None:
    """Copy the legacy inputs once (the originals stay until nothing imports them)."""
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for name in ('assistant.json', 'assistant-intents.json'):
        shutil.copyfile(ROOT / 'evals' / name, ARCHIVE / name)
    scenarios = _scenarios()
    (ARCHIVE / 'scenarios.json').write_text(
        json.dumps(scenarios, indent=2, ensure_ascii=False, sort_keys=False) + '\n'
    )


def _gold(codes: object, locale: str) -> list[str]:
    chosen = codes[locale] if isinstance(codes, dict) else codes
    assert isinstance(chosen, str)
    return [f'{locale}/{TOPIC_FOLDER[c]}' for c in chosen]


def assertions(
    locale: str, behavior: str, *, gold: bool, forbid: bool, numbers: bool = False
) -> list[str]:
    base = [f'language_is:{locale}']
    if behavior == 'answer':
        base += [
            'citations_in_retrieved',
            'citation_urls_allowlisted',
            *(['numbers_grounded'] if numbers else []),
            'required_facts_present',
        ]
    elif behavior == 'abstain':
        base += ['abstains', 'citations_empty']
    elif behavior == 'refuse':
        base += ['citations_empty']
    if forbid:
        base.append('forbidden_claims_absent')
    base += ['third_person_attribution', 'no_canary']
    if gold:
        base.append('retrieval_gold_in_topk')
    if behavior == 'answer':
        base.append('citations_nonempty')
    return base


def _matches(prefix: str, values: list[str]) -> list[dict[str, str]]:
    return [{'id': f'{prefix}{n}', 'match': v} for n, v in enumerate(values, 1)]


def make_item(
    *,
    item_id: str,
    locale: str,
    strata: list[str],
    turns: list[str],
    behavior: str,
    facts: list[str],
    forbid: list[str],
    gold: list[str],
    provenance: str,
    snapshot: str,
    numbers: bool = False,
) -> dict[str, object]:
    return {
        'assertions': assertions(
            locale,
            behavior,
            gold=bool(gold) and behavior == 'answer',
            forbid=bool(forbid),
            numbers=numbers,
        ),
        'assistant': 'portfolio',
        'corpus_snapshot_id': snapshot,
        'created': DATE,
        'expected_behavior': behavior,
        'forbidden_claims': _matches('c', forbid),
        'gold_evidence_ids': gold,
        'id': item_id,
        'judge_rubric_id': None,
        'last_verified': DATE,
        'locale': locale,
        'provenance': provenance,
        'required_facts': _matches('f', facts),
        'reviewer': REVIEWER,
        'schema_version': '1',
        'status': 'active',
        'strata': strata,
        'turns': [{'role': 'user', 'text': text} for text in turns],
    }


class Counters:
    def __init__(self) -> None:
        self.n: Counter[tuple[str, str, str]] = Counter()

    def next(self, prefix: str, part: str, locale: str) -> str:
        self.n[(prefix, part, locale)] += 1
        return f'{prefix}-{locale}-{part}-{self.n[(prefix, part, locale)]:03d}'


def _load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    spec = json.loads(SPEC.read_text())
    bank = json.loads((ARCHIVE / 'assistant-intents.json').read_text())
    cases = json.loads((ARCHIVE / 'assistant.json').read_text())
    snapshot = json.loads((ROOT / 'evals' / 'corpus' / 'manifest.json').read_text())[
        'corpus_snapshot_id'
    ]
    return spec, bank, cases, snapshot


def plan() -> dict[str, Any]:
    """Selection decisions (pure): dropped families, holdout families, adversarial pairs."""
    spec, bank, _, _ = _load()
    families = bank['families']
    legacy = {str(f['id']): f for f in families}
    for family_id in SEALED_FAMILIES:
        assert legacy[family_id]['split'] == 'holdout', family_id
    assert len(SEALED_FAMILIES) == HOLDOUT_FAMILIES
    dropped = find_duplicates(spec, families, frozenset(SEALED_FAMILIES))
    gone = {str(entry['dropped']) for entry in dropped}
    remaining = [f for f in families if f['id'] not in gone]
    holdout = list(SEALED_FAMILIES)
    adv_dropped: list[dict[str, object]] = []
    return {
        'dropped_families': dropped,
        'holdout_families': holdout,
        'dropped_adversarial': adv_dropped,
        'remaining_families': [f['id'] for f in remaining],
    }


def build(
    holdout_phrasing: Path | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, Any]]:
    spec, bank, cases, snapshot = _load()
    decisions = plan()
    sealed = set(decisions['holdout_families'])
    keep = set(decisions['remaining_families'])
    families = {f['id']: f for f in bank['families']}
    counters = Counters()
    dev: list[dict[str, object]] = []

    for fid, family in families.items():
        if fid not in keep or fid in sealed:
            continue
        entry = spec['families'][fid]
        for locale in LOCALES:
            texts = spec['text_overrides'].get(fid, {}).get(locale) or [
                v[locale] for v in family['variants'][:2]
            ]
            for variation, text in zip(
                ('direct', 'conversational'), texts, strict=True
            ):
                dev.append(
                    make_item(
                        item_id=counters.next('full', 'int', locale),
                        locale=locale,
                        strata=['intent_family', family['topic'], variation],
                        turns=[text],
                        behavior=entry['behavior'],
                        facts=entry[locale],
                        forbid=entry[f'forbid_{locale}'],
                        gold=_gold(entry['gold'], locale) if entry['gold'] else [],
                        provenance=f'distilled:legacy-2026-10:{fid}',
                        snapshot=snapshot,
                        numbers=family['topic'] == 'metrics',
                    )
                )

    dropped_adv = {str(e['dropped']) for e in decisions['dropped_adversarial']}
    for case in cases['adversarial']:
        number = case['id'].split('-')[1]
        if number in dropped_adv:
            continue
        info = spec['adversarial'][number]
        locale = case['locale']
        dev.append(
            make_item(
                item_id=counters.next('full', 'adv', locale),
                locale=locale,
                strata=['adversarial', info['category']],
                turns=[case['question']],
                behavior='refuse',
                facts=[],
                forbid=info[f'forbid_{locale}'],
                gold=[],
                provenance=f'distilled:legacy-2026-10:adversarial-{number}',
                snapshot=snapshot,
            )
        )

    for name, scenario in spec['scenarios'].items():
        locale = scenario['locale']
        behavior = scenario.get('behavior', 'answer')
        origin = scenario['source']
        provenance = (
            'new:m2-4-full'
            if origin == 'new'
            else f'distilled:legacy-2026-10:scenario-{name}'
            if origin == 'legacy'
            else f'adapted:legacy-2026-10:scenario-{name}'
        )
        dev.append(
            make_item(
                item_id=counters.next('full', 'mul', locale),
                locale=locale,
                strata=['multi_turn', name, origin],
                turns=scenario['turns'],
                behavior=behavior,
                facts=scenario['facts'],
                forbid=scenario.get('forbid', []),
                gold=scenario['gold'],
                provenance=provenance,
                snapshot=snapshot,
            )
        )

    for case in spec['cross_lingual']:
        dev.append(
            make_item(
                item_id=counters.next('full', 'xln', case['locale']),
                locale=case['locale'],
                strata=['cross_lingual', case['kind']],
                turns=[case['text']],
                behavior='answer',
                facts=case['facts'],
                forbid=[],
                gold=case['gold'],
                provenance='new:m2-4-full',
                snapshot=snapshot,
            )
        )

    hold: list[dict[str, object]] = []
    if holdout_phrasing is not None:
        phrasing = json.loads(holdout_phrasing.read_text())
        hold_counters = Counters()
        for fid in decisions['holdout_families']:
            entry = spec['families'][fid]
            for locale in LOCALES:
                for variation, text in zip(
                    ('direct', 'conversational'),
                    phrasing['families'][fid][locale],
                    strict=True,
                ):
                    hold.append(
                        make_item(
                            item_id=hold_counters.next('hold', 'int', locale),
                            locale=locale,
                            strata=['intent_family', families[fid]['topic'], variation],
                            turns=[text],
                            behavior=entry['behavior'],
                            facts=entry[locale],
                            forbid=entry[f'forbid_{locale}'],
                            gold=_gold(entry['gold'], locale) if entry['gold'] else [],
                            provenance=f'distilled:legacy-2026-10:{fid}:rephrased',
                            snapshot=snapshot,
                            numbers=families[fid]['topic'] == 'metrics',
                        )
                    )
        for case in phrasing['adversarial']:
            hold.append(
                make_item(
                    item_id=hold_counters.next('hold', 'adv', case['locale']),
                    locale=case['locale'],
                    strata=['adversarial', case['category']],
                    turns=[case['text']],
                    behavior='refuse',
                    facts=[],
                    forbid=case.get('forbid', []),
                    gold=[],
                    provenance='new:m2-4-full-holdout',
                    snapshot=snapshot,
                )
            )
        for case in phrasing['cross_lingual']:
            hold.append(
                make_item(
                    item_id=hold_counters.next('hold', 'xln', case['locale']),
                    locale=case['locale'],
                    strata=['cross_lingual', case['kind']],
                    turns=[case['text']],
                    behavior='answer',
                    facts=case['facts'],
                    forbid=[],
                    gold=case['gold'],
                    provenance='new:m2-4-full-holdout',
                    snapshot=snapshot,
                )
            )
    return dev, hold, decisions


def canonical_hash(raw: dict[str, object]) -> str:
    canonical = json.dumps(
        raw, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def dump_jsonl(items: list[dict[str, object]]) -> str:
    return ''.join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + '\n' for item in items
    )


def counts(items: list[dict[str, object]]) -> dict[str, object]:
    def strata(item: dict[str, object]) -> list[str]:
        value = item['strata']
        assert isinstance(value, list)
        return value

    parts = Counter(strata(i)[0] for i in items)
    return {
        'total': len(items),
        'parts': dict(sorted(parts.items())),
        'locales': dict(sorted(Counter(str(i['locale']) for i in items).items())),
        'parts_by_locale': {
            part: dict(
                sorted(
                    Counter(
                        str(i['locale']) for i in items if strata(i)[0] == part
                    ).items()
                )
            )
            for part in sorted(parts)
        },
        'strata': dict(sorted(Counter(strata(i)[1] for i in items).items())),
    }


def write_all(holdout_phrasing: Path | None, *, force: bool = False) -> None:
    sealed_path = FULL / 'holdout.sealed.jsonl'
    if holdout_phrasing is not None and sealed_path.exists() and not force:
        raise SystemExit(
            'refusing to overwrite the sealed holdout; pass --force to replace it'
        )
    dev, hold, decisions = build(holdout_phrasing)
    FULL.mkdir(parents=True, exist_ok=True)
    (FULL / 'full.jsonl').write_text(dump_jsonl(dev), encoding='utf-8')
    manifest_path = FULL / 'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if not hold and 'holdout' not in previous:
        raise SystemExit('no sealed holdout recorded: pass --holdout-phrasing')
    if hold:
        sealed_text = dump_jsonl(hold)
        (FULL / 'holdout.sealed.jsonl').write_text(sealed_text, encoding='utf-8')
        sealed_bytes = sealed_text.encode()
        holdout = {
            'file': 'evals/full/holdout.sealed.jsonl',
            'sha256': hashlib.sha256(sealed_bytes).hexdigest(),
            'counts': counts(hold),
        }
    else:
        holdout = previous['holdout']
    snapshot = json.loads((ROOT / 'evals' / 'corpus' / 'manifest.json').read_text())[
        'corpus_snapshot_id'
    ]
    manifest = {
        'corpus_snapshot_id': snapshot,
        'counts': counts(dev),
        'holdout': holdout,
        'items': {str(i['id']): canonical_hash(i) for i in dev},
        'no_retrieval_ablation': 'pending: needs a paid live run with empty evidence; agents make no paid calls',
        'pass_gate': 'none (report only, assistant-quality.md section 6.3)',
        'review': 'deterministic self-check only (evals/full/README.md); two-agent review is required for golden, not for the full tier',
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    )
    selection = {
        'tool': 'evals/harness/distill_full.py',
        'duplicate_rule': (
            'two families are duplicates only if they share the legacy topic, the expected '
            'behavior and the gold evidence keys AND their English required facts have Jaccard '
            '>= 0.6 (or, when both have no facts, the Jaccard of distinctive tokens, i.e. '
            'folded words minus stopwords and template words, is >= 0.6); a sealed family is '
            "never dropped and a family kept for one pair is never dropped later; the plan's "
            '"10 dropped" is not forced'
        ),
        'size_note': (
            "about 484 items (384 development + 100 sealed), above the plan's 450: only four "
            'families are real duplicates and all 40 legacy adversarial prompts are kept'
        ),
        'dropped_families': decisions['dropped_families'],
        'dropped_adversarial_pairs': [],
        'holdout_family_count': len(decisions['holdout_families']),
        'development_family_count': len(decisions['remaining_families'])
        - len(decisions['holdout_families']),
        'dropped_legacy_scenario': 'role-paraphrase (single-turn near-duplicate of fit)',
    }
    (FULL / 'selection.json').write_text(
        json.dumps(selection, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--archive', action='store_true')
    parser.add_argument('--plan', action='store_true', help='print selection decisions')
    parser.add_argument('--holdout-phrasing', type=Path)
    parser.add_argument(
        '--force', action='store_true', help='overwrite the sealed file'
    )
    args = parser.parse_args()
    if args.archive:
        archive_inputs()
    elif args.plan:
        decisions = plan()
        decisions['holdout_family_count'] = len(decisions.pop('holdout_families'))
        print(json.dumps(decisions, ensure_ascii=False, indent=1))
    else:
        write_all(args.holdout_phrasing, force=args.force)
    sys.stdout.flush()


if __name__ == '__main__':
    main()
