"""One-shot, deterministic derivation of the retrieval query set and label candidates.

Every query is DERIVED from an existing asset (never invented): golden items
(``evals/golden/golden.jsonl``), the legacy retrieval cases (``evals/retrieval.json``) and
the legacy question families (``evals/assistant.json``, development split only). The output
is ``evals/retrieval/queries.jsonl`` and ``evals/retrieval/qrels.candidates.jsonl``; the
candidates carry a PROPOSED relevance that independent labellers confirm or overturn
(``evals/retrieval/LABELLING.md``), and ``evals.harness.qrels_resolve`` then writes
``qrels.jsonl``. No network, no model, and no sealed file is read.

Run once: ``uv run python -m evals.harness.derive_queries``. Re-running regenerates the
same bytes; do not hand-edit the generated files, change the selection rules instead.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / 'evals' / 'golden' / 'golden.jsonl'
LEGACY_RETRIEVAL = ROOT / 'evals' / 'retrieval.json'
LEGACY_FAMILIES = ROOT / 'evals' / 'assistant.json'
OUT_DIR = ROOT / 'evals' / 'retrieval'

LOCALES = ('en', 'es')
TOPICS = ('profile', 'experience', 'projects', 'education')
KINDS = (
    'direct',
    'relationship',
    'multi-hop',
    'temporal',
    'metric',
    'education',
    'no-answer',
)

# Golden strata whose retrieval behaviour is not a standalone-query question.
GOLDEN_SKIP = {'adversarial', 'memory', 'multi_turn', 'language_policy'}
TEMPORAL = re.compile(
    r'\b(recent|latest|current|currently|before-and-after|rebuilt|graduat\w*|since'
    r'|when|timeline|reciente|recientes|cuándo|cuando|desde|cambió)\b',
    re.IGNORECASE,
)
METRIC = re.compile(
    r'\b(metrics?|latency|token reductions?|performance|figures|numbers|measured'
    r'|mediciones|métricas|cifras|rendimiento)\b',
    re.IGNORECASE,
)
MULTI_HOP = re.compile(
    r'\b(share|compare|differ|both|across|where has|which roles|which projects'
    r'|comparten|compara|diferencian)\b',
    re.IGNORECASE,
)
# Legacy families that are not retrieval questions (meta, security, language switch).
FAMILY_SKIP = {'boundaries-53', 'currentness-public-revision'} | {
    f'language-{n}' for n in range(56, 60)
}
FAMILY_SKIP |= {
    'currentness-conflicting-facts',
    # Subject absent from or only partially present in the frozen snapshot (distill.NOT_IN_CORPUS).
    'projects-13',
    'projects-14',
    'projects-15',
    'projects-18',
    'projects-20',
    'skills-22',
    'education-curriculum-transcript',
    'rampy-encryption',
}
MAX_FAMILY_PAIRS = 30
# Families whose subject is absent from the frozen corpus (distill.NOT_IN_CORPUS):
# only the unambiguous ones become no-answer queries.
FAMILY_NO_EVIDENCE = {
    'rampy-graph-retrieval': 'GraphRAG is not in the frozen snapshot',
    'boundaries-52': 'unsupported employer',
    'boundaries-55': 'hiring promise',
    'personal-47': 'nationality is not public',
    'personal-49': 'home address is not public',
    'personal-50': 'date of birth is not public',
}
FAMILY_TOPICS = {
    'profile': ('profile',),
    'experience': ('experience',),
    'projects': ('projects',),
    'education': ('education',),
    'skills': ('experience', 'projects'),
    'metrics': ('experience', 'projects'),
    'fit': ('experience', 'profile'),
    'personal': ('profile',),
}
VARIATIONS = ('direct', 'conversational', 'evidence')
XLING_PREFIXES = ('answerable_core', 'graph_multihop')


def normalize(text: str) -> str:
    return re.sub(r'\W+', ' ', text.casefold()).strip()


def candidates_for(locale: str, keys: dict[str, int]) -> list[dict[str, Any]]:
    """All locale/topic keys with a proposed relevance (default 0)."""
    return [
        {'key': f'{loc}/{topic}', 'proposed': keys.get(f'{loc}/{topic}', 0)}
        for loc in (locale, *(other for other in LOCALES if other != locale))
        for topic in TOPICS
    ]


def classify_kind(
    text: str, strata: set[str], topic: str, expects_evidence: bool
) -> str:
    if not expects_evidence:
        return 'no-answer'
    if 'relationship' in strata or 'shared_technologies' in strata:
        return 'relationship' if 'relationship' in strata else 'multi-hop'
    if 'graph_multihop' in strata or MULTI_HOP.search(text):
        return 'multi-hop'
    if topic == 'education' or 'education' in strata:
        return 'education'
    if 'metrics' in strata or METRIC.search(text):
        return 'metric'
    if TEMPORAL.search(text):
        return 'temporal'
    return 'direct'


def family_of(kind: str, strata: set[str]) -> str:
    if 'tool_use' in strata:
        return 'tool_use'
    if kind == 'no-answer' or 'abstain' in strata:
        return 'abstain'
    if kind in ('relationship', 'multi-hop'):
        return 'graph_multihop'
    return 'answerable_core'


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]


class Builder:
    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []
        self.seen: set[tuple[str, str]] = set()

    def add(
        self,
        *,
        text: str,
        locale: str,
        kind: str,
        family: str,
        topic: str,
        source_type: str,
        source_id: str,
        pair_id: str,
        gold: dict[str, int],
        basis: str,
        cross_lingual: bool = False,
        query_class: str = '',
    ) -> bool:
        marker = (normalize(text), locale)
        if marker in self.seen:
            return False
        self.seen.add(marker)
        query_id = f'rq-{len(self.queries) + 1:03d}'
        self.queries.append(
            {
                'id': query_id,
                'question': text,
                'locale': locale,
                'kind': kind,
                'family': family,
                'topic': topic,
                'cross_lingual': cross_lingual,
                'class': query_class,
                'expects_evidence': kind != 'no-answer',
                'pair_id': pair_id,
                'source_type': source_type,
                'source_id': source_id,
            }
        )
        self.candidates.append(
            {
                'query_id': query_id,
                'question': text,
                'locale': locale,
                'proposal_basis': basis,
                'candidates': candidates_for(locale, gold),
            }
        )
        return True


def golden_queries(builder: Builder, items: list[dict[str, Any]]) -> None:
    by_id = {item['id']: item for item in items}
    for item in items:
        strata = set(item['strata'])
        if strata & GOLDEN_SKIP or len(item['turns']) != 1:
            continue
        gold = {key: 2 for key in item['gold_evidence_ids']}
        text = item['turns'][-1]['text']
        topic = next((s for s in strata if s in TOPICS), '')
        if not topic and gold:
            topic = gold_topic(next(iter(gold)))
        kind = classify_kind(text, strata, topic, bool(gold))
        family = family_of(kind, strata)
        parts = item['id'].split('-')
        query_class = next(
            (s for s in item['strata'] if s in ('unsupported_employer', 'personal')),
            '',
        )
        builder.add(
            text=text,
            locale=item['locale'],
            kind=kind,
            family=family,
            topic=topic or 'none',
            source_type='golden',
            source_id=item['id'],
            pair_id=f'gold-{parts[2]}-{parts[3]}',
            gold=gold,
            basis='gold_evidence_ids' if gold else 'no_gold_evidence',
            query_class=query_class,
        )
    # Cross-lingual stratum: the other language's text with the locale of the first.
    for item in items:
        strata = set(item['strata'])
        if (
            item['locale'] != 'en'
            or strata & GOLDEN_SKIP
            or not item['gold_evidence_ids']
            or len(item['turns']) != 1
            or not (strata & set(XLING_PREFIXES))
            or 'abstain' in strata
        ):
            continue
        counterpart = by_id.get(item['id'].replace('-en-', '-es-'))
        if counterpart is None:
            continue
        for text_item, locale_item in ((counterpart, item), (item, counterpart)):
            gold = {key: 2 for key in locale_item['gold_evidence_ids']}
            text = text_item['turns'][-1]['text']
            topic = next((s for s in strata if s in TOPICS), '')
            if not topic:
                topic = gold_topic(next(iter(gold)))
            kind = classify_kind(text, strata, topic, True)
            parts = item['id'].split('-')
            builder.add(
                text=text,
                locale=locale_item['locale'],
                kind=kind,
                family=family_of(kind, strata),
                topic=topic,
                source_type='golden',
                source_id=f'{text_item["id"]}+locale:{locale_item["locale"]}',
                pair_id=f'xling-{parts[2]}-{parts[3]}',
                gold=gold,
                basis='gold_evidence_ids',
                cross_lingual=True,
            )


def gold_topic(key: str) -> str:
    return key.split('/', 1)[1].split('#', 1)[0]


def legacy_retrieval(builder: Builder, cases: list[dict[str, Any]]) -> None:
    for case in cases:
        gold = {key: 2 for key in case['qrels']}
        kind = case['kind']
        if kind in ('ambiguity', 'no-answer') or not gold:
            kind = 'no-answer'
        elif kind not in KINDS:
            kind = 'direct'
        text = case['question']
        if kind == 'direct':
            kind = classify_kind(text, set(), gold_topic(next(iter(gold))), True)
        topic = gold_topic(next(iter(gold))) if gold else 'none'
        builder.add(
            text=text,
            locale=case['locale'],
            kind=kind,
            family=family_of(kind, set()),
            topic=topic,
            source_type='legacy_retrieval',
            source_id=case['id'],
            pair_id=f'legacy-{case["id"].removesuffix("-es")}',
            gold=gold,
            basis='legacy_qrels' if gold else 'no_gold_evidence',
            query_class='unsupported_employer'
            if case['id'] == 'unsupported-employer'
            else '',
        )


def family_hint(family_id: str, topic: str) -> tuple[str, ...]:
    if family_id.startswith(('rampy-', 'teamcubation-')):
        return ('experience',)
    if family_id.startswith(('filomena-', 'pequeverso-')):
        return ('projects',)
    if family_id.startswith('education-'):
        return ('education',)
    if family_id.startswith('profile-'):
        return ('profile',)
    return FAMILY_TOPICS.get(topic, ())


def legacy_families(builder: Builder, data: dict[str, Any], covered: set[str]) -> None:
    families: dict[str, dict[str, dict[str, str]]] = {}
    topics: dict[str, str] = {}
    for case in data['cases']:
        if case['split'] != 'development' or case['variation'] not in VARIATIONS:
            continue
        families.setdefault(case['family_id'], {}).setdefault(case['variation'], {})[
            case['locale']
        ] = case['question']
        topics[case['family_id']] = case['topic']
    eligible = [
        f for f in sorted(families) if f not in covered and f not in FAMILY_SKIP
    ]
    # Topic round-robin keeps the strata balanced under the pair cap.
    groups: dict[str, list[str]] = {}
    for family_id in eligible:
        groups.setdefault(topics[family_id], []).append(family_id)
    chosen: list[str] = []
    while len(chosen) < MAX_FAMILY_PAIRS and any(groups.values()):
        for topic_key in sorted(groups):
            if groups[topic_key] and len(chosen) < MAX_FAMILY_PAIRS:
                chosen.append(groups[topic_key].pop(0))
    for number, family_id in enumerate(sorted(chosen)):
        variants = families[family_id]
        # Prefer the variation that reads as temporal; otherwise rotate deterministically.
        variation = next(
            (v for v in VARIATIONS if TEMPORAL.search(variants[v]['en'])),
            VARIATIONS[number % len(VARIATIONS)],
        )
        hint = family_hint(family_id, topics[family_id])
        no_evidence = family_id in FAMILY_NO_EVIDENCE
        for locale in LOCALES:
            text = variants[variation][locale]
            gold = {} if no_evidence else {f'{locale}/{t}': 1 for t in hint}
            topic_name = hint[0] if hint else topics[family_id]
            kind = classify_kind(
                variants[variation]['en'],
                {'metrics'} if topics[family_id] == 'metrics' else set(),
                topic_name,
                not no_evidence,
            )
            builder.add(
                text=text,
                locale=locale,
                kind=kind,
                family=family_of(kind, set()),
                topic=topic_name if not no_evidence else 'none',
                source_type='legacy_family',
                source_id=f'{family_id}:{variation}',
                pair_id=f'family-{family_id}',
                gold=gold,
                basis='topic_hint' if gold else 'no_gold_evidence',
                query_class='unsupported_employer'
                if family_id == 'boundaries-52'
                else '',
            )


def golden_covered_families(items: list[dict[str, Any]]) -> set[str]:
    covered = set()
    for item in items:
        match = re.fullmatch(r'distilled:legacy-2026-10:(.+)', item['provenance'])
        if match:
            covered.add(match[1])
    return covered


def build() -> Builder:
    golden = read_jsonl(GOLDEN)
    builder = Builder()
    golden_queries(builder, golden)
    legacy_retrieval(builder, json.loads(LEGACY_RETRIEVAL.read_text(encoding='utf-8')))
    legacy_families(
        builder,
        json.loads(LEGACY_FAMILIES.read_text(encoding='utf-8')),
        golden_covered_families(golden),
    )
    return builder


def dumps(rows: list[dict[str, Any]]) -> str:
    return ''.join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows
    )


def main() -> int:
    builder = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'queries.jsonl').write_text(dumps(builder.queries), encoding='utf-8')
    (OUT_DIR / 'qrels.candidates.jsonl').write_text(
        dumps(builder.candidates), encoding='utf-8'
    )
    print(f'{len(builder.queries)} queries written to {OUT_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
