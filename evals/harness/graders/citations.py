"""Graders over citations and retrieval."""

import re

from evals.harness.graders._text import MARKER, expand_marker
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_CONTEXT = GradingContext()
_MARKDOWN = re.compile(rf'```[\s\S]*?```|`[^`\n]*`|(?<![\w])({MARKER})(?!\()')
_BIBLIOGRAPHY = re.compile(r'^\s*\[\d+\]:?\s*https?://', re.MULTILINE)
_URL = re.compile(r'https?://[^\s)\]>"\']+')
_PINNED = re.compile(
    r'https://github\.com/gonzalomartinperez/portfolio/blob/[0-9a-f]{40}/\S+'
)


def _base(key: str) -> str:
    return key.split('#', 1)[0]


def key_retrieved(key: str, retrieved: tuple[str, ...]) -> bool:
    """File-level comparison: ``#entity`` suffixes are ignored on both sides.

    The run observes retrieval at file level, so entity presence is asserted by
    ``required_facts`` and the cited sources, not by this check.
    """
    return _base(key) in {_base(r) for r in retrieved}


def _markers(answer: str) -> set[int]:
    markers: set[int] = set()
    for found in _MARKDOWN.finditer(answer):
        if found[1]:
            markers |= expand_marker(found[1])
    return markers


def citations_nonempty(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """At least one citation marker in the answer maps to a cited source."""
    valid = {n for n in _markers(result.answer) if 1 <= n <= len(result.citations)}
    return GradeResult(
        'citations_nonempty', bool(valid), f'valid markers: {len(valid)}'
    )


def citations_in_retrieved(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Markers map to cited sources, cited sources were retrieved, no bibliography lines."""
    markers = _markers(result.answer)
    stray = sorted(n for n in markers if n < 1 or n > len(result.citations))
    if stray:
        return GradeResult(
            'citations_in_retrieved', False, f'markers without source: {stray}'
        )
    if _BIBLIOGRAPHY.search(result.answer):
        return GradeResult(
            'citations_in_retrieved', False, 'bibliography numbering for links'
        )
    if result.citations and result.retrieved_keys is None:
        return GradeResult(
            'citations_in_retrieved', False, 'retrieval was not observed'
        )
    retrieved = result.retrieved_keys or ()
    outside = [c.key for c in result.citations if not key_retrieved(c.key, retrieved)]
    return GradeResult(
        'citations_in_retrieved',
        not outside,
        f'not retrieved: {outside}' if outside else 'ok',
    )


def citation_urls_allowlisted(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Citation URLs are pinned portfolio URLs; answer URLs are cited or approved."""
    ctx = ctx or _CONTEXT

    def approved(url: str) -> bool:
        return any(
            url == a or url.startswith(a.rstrip('/') + '/') for a in ctx.approved_urls
        )

    cited = {c.url for c in result.citations}
    bad = [u for u in cited if not (_PINNED.fullmatch(u) or approved(u))]
    answer_urls = {u.rstrip('.,;:!?') for u in _URL.findall(result.answer)}
    bad += [u for u in answer_urls if u not in cited and not approved(u)]
    return GradeResult(
        'citation_urls_allowlisted',
        not bad,
        f'{len(bad)} url(s) not allowlisted' if bad else 'ok',
    )


def retrieval_gold_in_topk(
    item: Item, result: RunResult, ctx: GradingContext | None = None, *, k: int = 5
) -> GradeResult:
    """Every canonical gold key is among the first ``k`` retrieved sources."""
    if result.retrieved_keys is None:
        return GradeResult(
            'retrieval_gold_in_topk', False, 'retrieval was not observed'
        )
    top = result.retrieved_keys[:k]
    missing = [g for g in item.gold_evidence_ids if not key_retrieved(g, top)]
    return GradeResult(
        'retrieval_gold_in_topk',
        not missing,
        f'missing: {missing}' if missing else 'ok',
    )
