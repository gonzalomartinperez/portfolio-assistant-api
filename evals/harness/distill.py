"""One-shot, deterministic selection of legacy families for the golden set.

RETIRED after this one run (assistant-quality.md section 5.2): the committed
``evals/golden/selection.json`` is its output and ``evals/golden/golden.jsonl`` is the
frozen result. Do not re-run it to change the golden set; edit items through review.

No network and no model. It loads the legacy families (``evals/assistant-intents.json``,
the adversarial prompts of ``evals/assistant.json`` and the scripted conversations of
``scripts/evaluate_conversations.py``), clusters them by (topic, expected behavior,
kind), and picks families per stratum quota (section 5.1) maximizing topic coverage.
Only the ``direct`` or ``conversational`` phrasing is ever chosen, never ``brief`` or
``evidence_limits``. Strata with no legacy source get a ``new:m2-4`` slot instead.
"""

import ast
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'evals' / 'golden' / 'selection.json'
LOCALES = ('en', 'es')

# Pairs per stratum (each pair is one EN and one ES item): section 5.1 quotas halved.
QUOTAS = {
    'answerable_core': 9,
    'language_policy': 2,
    'graph_multihop': 6,
    'abstain': 9,
    'adversarial': 6,
    'multi_turn': 3,
    'tool_use': 3,
    'memory': 2,
}

# Legacy families whose subject is absent from the frozen corpus snapshot.
NOT_IN_CORPUS = {
    'rampy-encryption': 'no conversation encryption in the snapshot',
    'rampy-graph-retrieval': 'Neo4j and GraphRAG are not in the snapshot',
    'projects-13': 'Pequeverso is only a client website entry',
    'projects-14': 'Pequeverso purpose is not documented',
    'projects-15': 'portfolio implementation is outside the profile files',
    'projects-18': 'Pequeverso results are not documented',
    'projects-20': 'source lists are not a corpus fact',
    'education-curriculum-transcript': 'the curriculum table is generated data outside the snapshot',
    'skills-22': 'Pequeverso stack is only partially documented',
}
# Legacy behavior by family id; everything else defaults to answer.
BEHAVIOR = {
    'personal-47': 'abstain',
    'personal-48': 'abstain',
    'personal-49': 'abstain',
    'personal-50': 'abstain',
    'boundaries-51': 'abstain',
    'boundaries-52': 'abstain',
    'boundaries-53': 'refuse',
    'boundaries-54': 'answer',
    'boundaries-55': 'refuse',
    'fit-44': 'false_premise',
}
MULTI_HOP = re.compile(
    r'\b(?:share|compare|differ|both|which technologies|where has|which databases'
    r'|retrieve information|same technologies)\b',
    re.IGNORECASE,
)
# Adversarial legacy prompts by threat category (ids of assistant.json, section 9).
ADVERSARIAL_CATEGORY = {
    1: 'prompt_extraction',
    2: 'prompt_extraction',
    3: 'private_data',
    4: 'cross_user',
    5: 'fabrication',
    6: 'attribution',
    7: 'qualifier_removal',
    8: 'overclaim',
    9: 'execution',
    10: 'execution',
    11: 'ssrf',
    12: 'execution',
    13: 'injected_source',
    14: 'authority',
    15: 'provider',
    16: 'provider',
    17: 'provider',
    18: 'private_data',
    19: 'url_bait',
    20: 'forced_language',
}
ADVERSARIAL_PRIORITY = (
    'prompt_extraction',
    'injected_source',
    'url_bait',
    'forced_language',
    'attribution',
    'cross_user',
    'private_data',
    'qualifier_removal',
)
# Scripted conversations worth replaying (at least two turns), by continuity feature.
SCENARIO_FEATURE = {
    'refinement': 'follow_up_resolution',
    'topic-switch': 'topic_change',
    'contribution': 'deepen_and_shorten',
    'spanish-topic-switch': 'topic_change',
    'spanish': 'deepen_and_shorten',
    'job': 'role_fit_follow_up',
}
SCENARIO_ORDER = ('refinement', 'topic-switch')
# Strata with no legacy family: new:m2-4 slots (tools and memory exist only in the
# assistant-experience plan; two abstain and one adversarial slot have no legacy prompt).
NEW_SLOTS = {
    'abstain': ('out_of_scope_news', 'unrelated_task'),
    'adversarial': ('persona_hijack',),
    'multi_turn': ('history_false_claim',),
    'tool_use': ('web_pgvector', 'web_langgraph', 'web_ambiguous_no_tool'),
    'memory': ('consent_off_cross_session', 'cross_user_isolation'),
}


def _scenarios() -> dict[str, list[str]]:
    tree = ast.parse((ROOT / 'scripts' / 'evaluate_conversations.py').read_text())
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ('SCENARIOS', 'CONTINUITY_SCENARIOS')
        ):
            found.update(ast.literal_eval(node.value))
    return found


def _kind(question: str) -> str:
    return 'multi_hop' if MULTI_HOP.search(question) else 'single'


def classify(family: dict[str, object]) -> dict[str, str]:
    identifier = str(family['id'])
    variants = family['variants']
    assert isinstance(variants, list)
    question = ' '.join(variant['en'] for variant in variants)
    return {
        'family': identifier,
        'topic': str(family['topic']),
        'behavior': BEHAVIOR.get(identifier, 'answer'),
        'kind': _kind(question),
        # variants[0] is the direct phrasing, variants[1] the conversational one.
        'variation': 'direct',
    }


def _round_robin(
    candidates: list[dict[str, str]], count: int, taken: set[str]
) -> list[dict[str, str]]:
    """Pick by topic coverage first (one per topic), then fill from the largest topics."""
    by_topic: dict[str, list[dict[str, str]]] = defaultdict(list)
    for candidate in candidates:
        if candidate['family'] not in taken:
            by_topic[candidate['topic']].append(candidate)
    picked: list[dict[str, str]] = []
    while len(picked) < count and any(by_topic.values()):
        order = sorted(by_topic, key=lambda t: (-len(by_topic[t]), t))
        for topic in order:
            if by_topic[topic] and len(picked) < count:
                picked.append(by_topic[topic].pop(0))
    taken.update(p['family'] for p in picked)
    return picked


def select() -> dict[str, object]:
    bank = json.loads((ROOT / 'evals' / 'assistant-intents.json').read_text())
    families = [classify(f) for f in bank['families']]
    usable = [f for f in families if f['family'] not in NOT_IN_CORPUS]
    taken: set[str] = set()
    chosen: dict[str, list[dict[str, str]]] = {}

    # Hardest retrieval first: multi-hop families fill the graph stratum.
    graph = [
        f
        for f in usable
        if f['kind'] == 'multi_hop'
        and f['behavior'] == 'answer'
        and f['topic'] in ('projects', 'skills', 'experience', 'education')
    ]
    chosen['graph_multihop'] = _round_robin(graph, QUOTAS['graph_multihop'], taken)
    abstain = [
        f for f in usable if f['behavior'] in ('abstain', 'refuse', 'false_premise')
    ]
    abstain = [
        f for f in abstain if f['family'] != 'boundaries-53'
    ]  # adversarial in nature
    chosen['abstain'] = _round_robin(
        abstain, QUOTAS['abstain'] - len(NEW_SLOTS['abstain']), taken
    )
    policy = [
        f for f in usable if f['topic'] == 'language' and f['family'] != 'language-60'
    ]
    chosen['language_policy'] = policy[: QUOTAS['language_policy']]
    taken.update(f['family'] for f in chosen['language_policy'])
    core = [
        f
        for f in usable
        if f['behavior'] == 'answer'
        and f['kind'] == 'single'
        and f['topic'] not in ('language', 'boundaries', 'personal')
    ]
    chosen['answerable_core'] = _round_robin(core, QUOTAS['answerable_core'], taken)

    selected: list[dict[str, object]] = []
    for stratum, items in chosen.items():
        for item in items:
            for locale in LOCALES:
                selected.append({**item, 'stratum': stratum, 'locale': locale})

    adversarial: dict[str, int] = {}
    for number, category in ADVERSARIAL_CATEGORY.items():
        adversarial.setdefault(category, number)
    for category in ADVERSARIAL_PRIORITY[
        : QUOTAS['adversarial'] - len(NEW_SLOTS['adversarial'])
    ]:
        for locale in LOCALES:
            selected.append(
                {
                    'family': f'adversarial-{adversarial[category]}',
                    'topic': category,
                    'behavior': 'refuse',
                    'kind': 'adversarial',
                    'variation': 'direct',
                    'stratum': 'adversarial',
                    'locale': locale,
                }
            )
    scenarios = _scenarios()
    for name in SCENARIO_ORDER:
        for locale in LOCALES:
            selected.append(
                {
                    'family': f'scenario-{name}',
                    'topic': SCENARIO_FEATURE[name],
                    'behavior': 'answer',
                    'kind': 'multi_turn',
                    'variation': 'scripted',
                    'turns': len(scenarios[name]),
                    'stratum': 'multi_turn',
                    'locale': locale,
                }
            )
    new = [
        {'slot': slot, 'stratum': stratum, 'locale': locale, 'provenance': 'new:m2-4'}
        for stratum, slots in NEW_SLOTS.items()
        for slot in slots
        for locale in LOCALES
    ]
    coverage: dict[str, list[str]] = defaultdict(list)
    for entry in selected:
        topic = str(entry['topic'])
        if topic not in coverage[str(entry['stratum'])]:
            coverage[str(entry['stratum'])].append(topic)
    return {
        'tool': 'evals/harness/distill.py (retired after this run)',
        'quotas_pairs': QUOTAS,
        'selected': selected,
        'new': new,
        'excluded_not_in_corpus': NOT_IN_CORPUS,
        'topic_coverage': dict(coverage),
    }


def write_manifest() -> None:
    """Refresh the per-item hashes of ``manifest.json`` after a reviewed item edit."""
    golden = ROOT / 'evals' / 'golden'
    manifest_path = golden / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    hashes: dict[str, str] = {}
    for line in (golden / 'golden.jsonl').read_text().splitlines():
        raw = json.loads(line)
        canonical = json.dumps(
            raw, ensure_ascii=False, sort_keys=True, separators=(',', ':')
        )
        hashes[raw['id']] = hashlib.sha256(canonical.encode()).hexdigest()
    manifest['items'] = dict(sorted(hashes.items()))
    manifest['item_count'] = len(hashes)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    )


def main() -> None:
    if '--write-manifest' in sys.argv[1:]:
        write_manifest()
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(select(), indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
