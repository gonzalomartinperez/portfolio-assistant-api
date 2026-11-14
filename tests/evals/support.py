"""Builders for eval items and run results."""

from typing import Any

from evals.harness.items import Item
from evals.harness.result import CitedSource, RunResult

PINNED = (
    'https://github.com/gonzalomartinperez/portfolio/blob/'
    + 'a' * 40
    + '/content/en/education.ts#L1-L5'
)


def make_item(**overrides: Any) -> Item:
    base: dict[str, Any] = {
        'id': 'gold-en-edu-001',
        'locale': 'en',
        'strata': ['answerable_core', 'education'],
        'turns': [{'role': 'user', 'text': 'Where did Gonzalo study?'}],
        'expected_behavior': 'answer',
        'assertions': ['required_facts_present', 'citations_nonempty'],
        'provenance': 'distilled:legacy-2026-10:education-3',
        'reviewer': 'owner',
        'created': '2026-11-20',
        'last_verified': '2026-11-20',
        'corpus_snapshot_id': 'corpus-abc',
    }
    return Item.model_validate({**base, **overrides})


def make_result(**overrides: Any) -> RunResult:
    return RunResult(
        **{
            'answer': 'Gonzalo studied at the Universidad Nacional del Sur.',
            **overrides,
        }
    )


def cite(key: str = 'en/education', url: str = PINNED) -> CitedSource:
    return CitedSource(key, url)
