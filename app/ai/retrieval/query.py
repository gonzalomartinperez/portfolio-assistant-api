"""Question analysis: the intent flags every later retrieval stage derives from."""

import re
from dataclasses import dataclass

from app.domain.evidence import blocks_private_query, requested_affiliation, tokens

_OVERVIEW = re.compile(
    r"(?i)(tell me about|cuéntame sobre|cuentame sobre|who is|quién es)\s+gonzalo"
)
_OVERVIEW_TERMS = frozenset({"profile", "summary", "intro"})
_REPOSITORY_TERMS = frozenset({"repository", "repo", "repositorio", "portfolio", "readme"})
_RELATIONSHIP_TERMS = frozenset(
    {
        "compare",
        "comparison",
        "versus",
        "compara",
        "comparar",
        "connect",
        "connected",
        "shared",
        "share",
        "shares",
        "between",
        "both",
        "related",
        "comparten",
        "relacion",
        "entre",
        "ambos",
    }
)


@dataclass(frozen=True)
class QueryIntent:
    question: str
    terms: frozenset[str]
    overview: bool
    repository_question: bool
    relationship: bool
    affiliation: str | None


def build_intent(question: str) -> QueryIntent | None:
    """Return None when the question is private or has no searchable terms."""
    terms = tokens(question)
    if blocks_private_query(question, terms):
        return None
    overview = bool(_OVERVIEW.search(question))
    if overview:
        terms |= _OVERVIEW_TERMS
    if not terms:
        return None
    return QueryIntent(
        question=question,
        terms=frozenset(terms),
        overview=overview,
        repository_question=bool(terms & _REPOSITORY_TERMS),
        relationship=bool(terms & _RELATIONSHIP_TERMS),
        affiliation=requested_affiliation(question),
    )
