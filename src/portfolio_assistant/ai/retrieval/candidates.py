"""Eligibility, lexical scoring and the lexical, vector and graph candidate lanes."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import portfolio_assistant.ai.retrieval.source_shape as shape
from portfolio_assistant.ai.retrieval.rules import (
    BOOST_COMPANY_CONTRIBUTIONS,
    BOOST_OVERVIEW_PROFILE_HEAD,
    BOOST_SPOKEN_LANGUAGES,
    MULTIPLIER_ENTITY_PATH,
)
from portfolio_assistant.domain.evidence import (
    EvidenceRecord,
    asks_spoken_languages,
    lexical_score,
    tokens,
    verified,
)
from portfolio_assistant.domain.portfolio_paths import profile_parts, profile_paths

if TYPE_CHECKING:
    from portfolio_assistant.ai.retrieval.query import QueryIntent
    from portfolio_assistant.ai.retrieval.rules import RetrievalRules
    from portfolio_assistant.application.knowledge import Chunk, Corpus

ASSISTANT_KNOWLEDGE = "public/assistant-knowledge.json"
MIN_LEXICAL_SCORE = 3


@dataclass(frozen=True)
class Eligible:
    """Verified, locale-preferred chunks and their lexical scores."""

    chunks: dict[str, Chunk]
    scores: dict[str, float]


def unknown_affiliation(corpus: Corpus, affiliation: str | None) -> bool:
    """True when an explicit employer/project premise never appears in the corpus."""
    if not affiliation:
        return False
    known_terms = set().union(*(tokens(chunk.content) for chunk in corpus.chunks))
    return not tokens(affiliation) <= known_terms


def entity_paths(corpus: Corpus, terms: frozenset[str]) -> set[str]:
    """Explicit entity declarations anchor adjacent chunks in the same public document."""
    return {
        chunk.path
        for chunk in corpus.chunks
        if any(name.lower() in terms for name in shape.entity_names(chunk.content))
    }


def _in_scope(chunk: Chunk, intent: QueryIntent) -> bool:
    # Editorial/development instructions are not evidence of professional contributions.
    return (
        intent.repository_question
        or profile_parts(chunk.path) is not None
        or chunk.path == ASSISTANT_KNOWLEDGE
    )


def _spoken_languages_boost(chunk: Chunk, terms: set[str]) -> bool:
    return (
        asks_spoken_languages(terms)
        and shape.is_profile_file(chunk.path)
        and shape.has_language_entries(chunk.content)
    )


def _company_boost(chunk: Chunk, terms: set[str]) -> bool:
    return (
        shape.is_experience_file(chunk.path)
        and any(tokens(name) & terms for name in shape.company_names(chunk.content))
        and shape.has_contributions(chunk.content)
    )


def _score(
    chunk: Chunk,
    row: EvidenceRecord,
    intent: QueryIntent,
    terms: set[str],
    locale: str,
    rules: RetrievalRules,
) -> float:
    score: float = lexical_score(row, terms, locale)
    if rules.enabled(BOOST_SPOKEN_LANGUAGES) and _spoken_languages_boost(chunk, terms):
        score += rules.spoken_languages_boost
    if (
        rules.enabled(BOOST_OVERVIEW_PROFILE_HEAD)
        and intent.overview
        and shape.is_profile_head(chunk)
    ):
        score += rules.overview_profile_boost
    if rules.enabled(BOOST_COMPANY_CONTRIBUTIONS) and _company_boost(chunk, terms):
        score += rules.company_contributions_boost
    return score


def _preferred(chunk: Chunk, corpus: Corpus, locale: str) -> bool:
    profile = profile_parts(chunk.path)
    return (
        profile is None
        or profile[0] == locale
        or not any(path in corpus.paths for path in profile_paths(locale, profile[1]))
    )


def eligible_chunks(
    corpus: Corpus, intent: QueryIntent, locale: str, rules: RetrievalRules
) -> Eligible:
    """Collect verified chunks in scope and score their lexical relevance."""
    terms = set(intent.terms)
    entities = entity_paths(corpus, intent.terms)
    multiply = rules.enabled(MULTIPLIER_ENTITY_PATH)
    chunks: dict[str, Chunk] = {}
    scores: dict[str, float] = {}
    for chunk in corpus.chunks:
        if not _in_scope(chunk, intent):
            continue
        row: EvidenceRecord = {
            "path": chunk.path,
            "content": chunk.content,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "url": chunk.url,
            "content_hash": chunk.content_hash,
        }
        score = _score(chunk, row, intent, terms, locale, rules)
        if multiply and chunk.path in entities:
            score *= rules.entity_path_multiplier
        if _preferred(chunk, corpus, locale) and verified(row, corpus.commit, set(corpus.paths)):
            chunks[chunk.id] = chunk
            scores[chunk.id] = score
    return Eligible(chunks, scores)


def lexical_lane(corpus: Corpus, eligible: Eligible) -> list[str]:
    """Order strong lexical matches before eligible index-provided candidates."""
    scores = eligible.scores
    scored = sorted(
        (key for key in eligible.chunks if scores[key] >= MIN_LEXICAL_SCORE),
        key=lambda key: (-scores[key], key),
    )
    return list(dict.fromkeys(scored + [key for key in corpus.lexical if key in eligible.chunks]))


def vector_lane(corpus: Corpus, eligible: Eligible) -> list[str]:
    """Keep eligible neighbors, requiring lexical support for nonsemantic corpora."""
    return [
        key
        for key in corpus.nearest
        if key in eligible.chunks and (corpus.semantic or eligible.scores[key] >= MIN_LEXICAL_SCORE)
    ]
