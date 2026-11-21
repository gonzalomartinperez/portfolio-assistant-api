"""Question analysis: the intent flags every later retrieval stage derives from."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.evidence import blocks_private_query, requested_affiliation, tokens

if TYPE_CHECKING:
    from app.ai.retrieval.rules import RetrievalRules


@dataclass(frozen=True)
class QueryIntent:
    """Search terms and intent flags derived from a visitor question."""

    question: str
    terms: frozenset[str]
    overview: bool
    repository_question: bool
    relationship: bool
    affiliation: str | None


def build_intent(question: str, rules: RetrievalRules) -> QueryIntent | None:
    """Return None when the question is private or has no searchable terms."""
    terms = tokens(question)
    if blocks_private_query(question, terms):
        return None
    overview = bool(re.search(rules.overview_pattern, question))
    if overview:
        terms |= rules.overview_terms
    if not terms:
        return None
    return QueryIntent(
        question=question,
        terms=frozenset(terms),
        overview=overview,
        repository_question=bool(terms & rules.repository_terms),
        relationship=bool(terms & rules.relationship_terms),
        affiliation=requested_affiliation(question),
    )
