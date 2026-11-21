"""Hybrid re-ranking: one first-match group, then ordered anchor steps."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import app.ai.retrieval.source_shape as shape
from app.ai.retrieval.rules import (
    AFFILIATION_FILTER,
    EXACT_NAME,
    GOALS_METRICS_ANCHOR,
    OVERVIEW_FIRST,
    PERFORMANCE_METRICS,
    QUALIFICATION_ANCHOR,
    RELATIONSHIP_ANCHORS,
    TECHNICAL_TOPIC_ANCHORS,
)
from app.domain.evidence import comparison_subjects, tokens
from app.domain.portfolio_paths import profile_parts
from app.domain.web_policy import TOPICS

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.ai.retrieval.candidates import Eligible
    from app.ai.retrieval.query import QueryIntent
    from app.ai.retrieval.rules import RetrievalRules


@dataclass(frozen=True)
class RerankContext:
    """Shared query intent and eligible candidates for each ranking step."""

    intent: QueryIntent
    eligible: Eligible
    rules: RetrievalRules


Ranked = list[str]


class Step(NamedTuple):
    """A named ranking operation with an applicability predicate."""

    id: str
    applies: Callable[[RerankContext], bool]
    apply: Callable[[Ranked, RerankContext], Ranked]


def _mentioning_affiliation(keys: Ranked, ctx: RerankContext) -> Ranked:
    if not ctx.intent.affiliation:
        return keys
    wanted = tokens(ctx.intent.affiliation)
    return [key for key in keys if wanted <= tokens(ctx.eligible.chunks[key].content)]


def _stable_first(ranked: Ranked, first: Callable[[str], bool]) -> Ranked:
    ranked.sort(key=lambda key: not first(key))
    return ranked


def overview_first(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Stably promote the first chunk of each profile document."""
    chunks = ctx.eligible.chunks
    return _stable_first(ranked, lambda key: shape.is_profile_head(chunks[key]))


def affiliation_filter(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Keep affiliation mentions and promote matching company declarations."""
    chunks = ctx.eligible.chunks
    wanted = tokens(ctx.intent.affiliation or "")
    ranked = _mentioning_affiliation(ranked, ctx)
    return _stable_first(
        ranked,
        lambda key: any(tokens(name) & wanted for name in shape.company_names(chunks[key].content)),
    )


def performance_metrics(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Stably promote chunks containing qualified metric values."""
    chunks = ctx.eligible.chunks
    return _stable_first(ranked, lambda key: shape.has_metric_entry(chunks[key].content))


def exact_name(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Stably promote chunks whose declared names occur in the query."""
    chunks = ctx.eligible.chunks
    terms = ctx.intent.terms
    return _stable_first(
        ranked,
        lambda key: any(
            tokens(name) <= terms
            for name in shape.declared_names(chunks[key].content)
            if tokens(name)
        ),
    )


# Only the first applicable step runs.
FIRST_MATCH: tuple[Step, ...] = (
    Step(OVERVIEW_FIRST, lambda ctx: ctx.intent.overview, overview_first),
    Step(
        AFFILIATION_FILTER,
        lambda ctx: bool(ctx.intent.affiliation) and not ctx.intent.relationship,
        affiliation_filter,
    ),
    Step(
        PERFORMANCE_METRICS,
        lambda ctx: bool(ctx.intent.terms & ctx.rules.performance_terms),
        performance_metrics,
    ),
    Step(EXACT_NAME, lambda ctx: not ctx.intent.terms & ctx.rules.technology_terms, exact_name),
)


def qualification_anchor(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Prepend eligible education headers while preserving unique ids."""
    qualification = [
        key for key, chunk in ctx.eligible.chunks.items() if shape.is_education_head(chunk)
    ]
    return list(dict.fromkeys(qualification + ranked))


def _subject_anchors(ranked: Ranked, subjects: tuple[str, ...], ctx: RerankContext) -> Ranked:
    anchors = []
    for subject in subjects:
        wanted = tokens(subject)
        matching = [key for key in ranked if wanted <= tokens(ctx.eligible.chunks[key].content)]
        if matching:
            anchors.append(max(matching, key=lambda key: ctx.eligible.scores[key]))
    return anchors


def _dated_role(
    ctx: RerankContext, key: str, following: str | None
) -> tuple[str, str, str, str | None] | None:
    chunks = ctx.eligible.chunks
    chunk = chunks[key]
    company = shape.first_company(chunk.content)
    if not company:
        return None
    adjacent = None
    if following and chunks[following].start_line == chunk.end_line + 1:
        adjacent = chunks[following].content
    text = shape.role_text(chunk.content, company, adjacent)
    start_date = shape.role_start_date(text)
    return (start_date, company[1], key, following) if start_date else None


def _dated_roles(ctx: RerankContext) -> list[tuple[str, str, str, str | None]]:
    chunks = ctx.eligible.chunks
    by_path: dict[str, list[str]] = {}
    for key, chunk in chunks.items():
        by_path.setdefault(chunk.path, []).append(key)
    dated = []
    for keys in by_path.values():
        keys.sort(key=lambda key: chunks[key].start_line)
        for index, key in enumerate(keys):
            role = _dated_role(ctx, key, keys[index + 1] if index + 1 < len(keys) else None)
            if role:
                dated.append(role)
    return dated


def _role_anchors(ctx: RerankContext) -> Ranked:
    anchors: Ranked = []
    companies: set[str] = set()
    companions = []
    for _, company_name, key, following in sorted(_dated_roles(ctx), reverse=True):
        if company_name not in companies:
            anchors.append(key)
            companies.add(company_name)
            if following and not shape.has_started_on(ctx.eligible.chunks[key].content):
                companions.append(following)
    return anchors + companions


def relationship_anchors(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Prepend subject matches or recent distinct roles for relationship queries."""
    chunks = ctx.eligible.chunks
    subjects = comparison_subjects(ctx.intent.question, tuple(c.content for c in chunks.values()))
    anchors = _subject_anchors(ranked, subjects, ctx)
    if not subjects and ctx.intent.terms & ctx.rules.role_terms:
        anchors += _role_anchors(ctx)
    return list(dict.fromkeys(anchors + ranked))


def _topic_anchor(topic_name: str, ctx: RerankContext) -> str | None:
    chunks = ctx.eligible.chunks
    matching = [key for key, chunk in chunks.items() if topic_name in chunk.content.casefold()]
    matching = _mentioning_affiliation(matching, ctx)
    if not matching:
        return None
    return min(
        matching,
        key=lambda key: (
            profile_parts(chunks[key].path) is None,
            -ctx.eligible.scores[key],
            key,
        ),
    )


def technical_topic_anchors(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Prepend the best eligible match for each technical topic in the query."""
    question = ctx.intent.question.casefold()
    names = [topic.name.casefold() for topic in TOPICS]
    anchors = [_topic_anchor(name, ctx) for name in names if name in question]
    return list(dict.fromkeys([key for key in anchors if key is not None] + ranked))


def goals_metrics_anchor(ranked: Ranked, ctx: RerankContext) -> Ranked:
    """Prepend the strongest profile goal match when one is available."""
    chunks = ctx.eligible.chunks
    goals = [
        key
        for key in chunks
        if profile_parts(chunks[key].path) is not None
        and re.search(ctx.rules.goal_pattern, chunks[key].content)
    ]
    goals = _mentioning_affiliation(goals, ctx)
    if not goals:
        return ranked
    return list(dict.fromkeys([max(goals, key=lambda key: ctx.eligible.scores[key]), *ranked]))


# Every applicable step runs, in this order, after the first-match group.
ANCHORS: tuple[Step, ...] = (
    Step(
        QUALIFICATION_ANCHOR,
        lambda ctx: bool(ctx.intent.terms & ctx.rules.qualification_terms),
        qualification_anchor,
    ),
    Step(RELATIONSHIP_ANCHORS, lambda ctx: ctx.intent.relationship, relationship_anchors),
    Step(TECHNICAL_TOPIC_ANCHORS, lambda ctx: not ctx.intent.overview, technical_topic_anchors),
    Step(
        GOALS_METRICS_ANCHOR,
        lambda ctx: bool(
            ctx.intent.terms & ctx.rules.goal_terms
            and ctx.intent.terms & ctx.rules.measurement_terms
        ),
        goals_metrics_anchor,
    ),
)


def _run(step: Step, ranked: Ranked, ctx: RerankContext) -> Ranked:
    return step.apply(ranked, ctx) if ctx.rules.enabled(step.id) else ranked


def rerank(
    ranked: Ranked, intent: QueryIntent, eligible: Eligible, rules: RetrievalRules
) -> Ranked:
    """Apply the first matching step followed by all applicable anchors.

    A disabled first-match step still consumes its position.
    """
    ctx = RerankContext(intent, eligible, rules)
    for step in FIRST_MATCH:
        if step.applies(ctx):
            ranked = _run(step, ranked, ctx)
            break
    for step in ANCHORS:
        if step.applies(ctx):
            ranked = _run(step, ranked, ctx)
    return ranked
