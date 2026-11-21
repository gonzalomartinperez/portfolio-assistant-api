"""Declarative retrieval rules: stable rule ids, vocabularies, weights and ablation switches.

Pure and standard-library only. ``DEFAULT_RULES`` equals today's literals, ``rules.toml``
mirrors it (a test pins the equality) and bootstrap loads the file through ``parse_rules``.
``disabled`` switches single rules off for ablation; the default is empty.
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# Re-ranking steps, in the first-match group (the first applicable step runs, then the chain stops).
OVERVIEW_FIRST = "overview_first"
AFFILIATION_FILTER = "affiliation_filter"
PERFORMANCE_METRICS = "performance_metrics"
EXACT_NAME = "exact_name"
# Re-ranking steps that all run, in order, when applicable.
QUALIFICATION_ANCHOR = "qualification_anchor"
RELATIONSHIP_ANCHORS = "relationship_anchors"
TECHNICAL_TOPIC_ANCHORS = "technical_topic_anchors"
GOALS_METRICS_ANCHOR = "goals_metrics_anchor"
# Candidate score boosts and multiplier.
BOOST_SPOKEN_LANGUAGES = "boost_spoken_languages"
BOOST_OVERVIEW_PROFILE_HEAD = "boost_overview_profile_head"
BOOST_COMPANY_CONTRIBUTIONS = "boost_company_contributions"
MULTIPLIER_ENTITY_PATH = "multiplier_entity_path"

# The closed set of ablatable rules.
RULE_IDS = frozenset(
    {
        BOOST_SPOKEN_LANGUAGES,
        BOOST_OVERVIEW_PROFILE_HEAD,
        BOOST_COMPANY_CONTRIBUTIONS,
        MULTIPLIER_ENTITY_PATH,
        OVERVIEW_FIRST,
        AFFILIATION_FILTER,
        PERFORMANCE_METRICS,
        EXACT_NAME,
        QUALIFICATION_ANCHOR,
        RELATIONSHIP_ANCHORS,
        TECHNICAL_TOPIC_ANCHORS,
        GOALS_METRICS_ANCHOR,
    }
)

_Lanes = tuple[float, float, float]


@dataclass(frozen=True)
class RetrievalRules:
    """Immutable query vocabulary, ranking settings and rule switches."""

    # Vocabularies (question analysis and re-ranking triggers).
    overview_pattern: str
    overview_terms: frozenset[str]
    repository_terms: frozenset[str]
    relationship_terms: frozenset[str]
    performance_terms: frozenset[str]
    technology_terms: frozenset[str]
    qualification_terms: frozenset[str]
    role_terms: frozenset[str]
    goal_terms: frozenset[str]
    measurement_terms: frozenset[str]
    goal_pattern: str
    # Boost weights (lexical score units; the entity path multiplier scales the whole score).
    spoken_languages_boost: float
    overview_profile_boost: float
    company_contributions_boost: float
    entity_path_multiplier: float
    # Fusion: weight / (offset + rank), lanes ordered lexical, vector, graph.
    fusion_offset: int
    semantic_weights: _Lanes
    lexical_weights: _Lanes
    relationship_graph_first: bool
    disabled: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate ranking settings for direct construction and replacement."""
        if not isinstance(self.disabled, frozenset):
            raise ValueError("expected a frozenset of rule ids")  # noqa: TRY004
        _known_rule_ids(self.disabled)
        for weight in (
            self.spoken_languages_boost,
            self.overview_profile_boost,
            self.company_contributions_boost,
            self.entity_path_multiplier,
        ):
            _number(weight)
        _offset(self.fusion_offset)
        for weights in (self.semantic_weights, self.lexical_weights):
            if not isinstance(weights, tuple):
                raise ValueError("expected a tuple of three weights")  # noqa: TRY004
            _lanes(weights)

    def enabled(self, rule_id: str) -> bool:
        """Return whether a registered rule participates in ranking."""
        return rule_id not in self.disabled


def _terms(value: object) -> frozenset[str]:
    if not isinstance(value, list | tuple) or not value:
        raise ValueError("expected a non-empty list of strings")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError("expected a non-empty list of non-empty strings")
    return frozenset(value)


def _pattern(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("expected a non-empty regular expression string")
    try:
        re.compile(value)
    except re.error as error:
        raise ValueError(f"invalid regular expression: {error}") from error
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("expected a number")  # noqa: TRY004
    try:
        weight = float(value)
    except OverflowError as error:
        raise ValueError("weights must be finite") from error
    if not math.isfinite(weight):
        raise ValueError("weights must be finite")
    if weight < 0:
        raise ValueError("weights must not be negative")
    return weight


_MAX_OFFSET = 10_000


def _offset(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= _MAX_OFFSET:
        raise ValueError("expected a positive integer")
    return value


def _lanes(value: object) -> _Lanes:
    if not isinstance(value, list | tuple) or len(value) != 3:
        raise ValueError("expected three weights: lexical, vector, graph")
    lexical, vector, graph = (_number(item) for item in value)
    return (lexical, vector, graph)


def _flag(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("expected true or false")  # noqa: TRY004
    return value


def _known_rule_ids(ids: frozenset[str]) -> None:
    unknown = sorted(map(str, ids - RULE_IDS))
    if unknown:
        raise ValueError(f"unknown rule ids: {', '.join(unknown)}; known: {sorted(RULE_IDS)}")


def _disabled(value: object) -> frozenset[str]:
    if not isinstance(value, list | tuple) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list of rule ids")
    ids = frozenset(value)
    _known_rule_ids(ids)
    return ids


DEFAULT_RULES = RetrievalRules(
    overview_pattern=r"(?i)(tell me about|cuéntame sobre|cuentame sobre|who is|quién es)\s+gonzalo",
    overview_terms=frozenset({"profile", "summary", "intro"}),
    repository_terms=frozenset({"repository", "repo", "repositorio", "portfolio", "readme"}),
    relationship_terms=frozenset(
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
    ),
    performance_terms=frozenset(
        {"performance", "improvements", "metrics", "metricas", "rendimiento"}
    ),
    technology_terms=frozenset({"technologies", "technology", "tecnologias", "stack"}),
    qualification_terms=frozenset(
        {
            "degree",
            "graduated",
            "graduation",
            "qualification",
            "education",
            "formacion",
            "formation",
            "estudou",
            "titulo",
            "universidad",
            "study",
            "studied",
            "estudio",
            "estudios",
        }
    ),
    role_terms=frozenset({"roles", "empleos", "puestos", "trabajos"}),
    goal_terms=frozenset({"goals", "targets", "metas", "objetivos"}),
    measurement_terms=frozenset(
        {
            "metrics",
            "measurements",
            "measured",
            "estimated",
            "mediciones",
            "medidas",
            "estimaciones",
            "rendimiento",
        }
    ),
    goal_pattern=r"(?i)\b(?:design goal|design target|objetivo de|meta de)\b",
    spoken_languages_boost=100.0,
    overview_profile_boost=100.0,
    company_contributions_boost=50.0,
    entity_path_multiplier=2.0,
    fusion_offset=10,
    semantic_weights=(1.0, 1.0, 0.5),
    lexical_weights=(3.0, 0.1, 0.5),
    relationship_graph_first=True,
)


# TOML section -> key -> (RetrievalRules field, validator).
_SCHEMA: dict[str, dict[str, tuple[str, Callable[[object], object]]]] = {
    "vocabulary": {
        "overview_pattern": ("overview_pattern", _pattern),
        "overview_terms": ("overview_terms", _terms),
        "repository_terms": ("repository_terms", _terms),
        "relationship_terms": ("relationship_terms", _terms),
        "performance_terms": ("performance_terms", _terms),
        "technology_terms": ("technology_terms", _terms),
        "qualification_terms": ("qualification_terms", _terms),
        "role_terms": ("role_terms", _terms),
        "goal_terms": ("goal_terms", _terms),
        "measurement_terms": ("measurement_terms", _terms),
        "goal_pattern": ("goal_pattern", _pattern),
    },
    "weights": {
        "spoken_languages": ("spoken_languages_boost", _number),
        "overview_profile_head": ("overview_profile_boost", _number),
        "company_contributions": ("company_contributions_boost", _number),
        "entity_path_multiplier": ("entity_path_multiplier", _number),
    },
    "fusion": {
        "offset": ("fusion_offset", _offset),
        "semantic": ("semantic_weights", _lanes),
        "lexical": ("lexical_weights", _lanes),
        "relationship_graph_first": ("relationship_graph_first", _flag),
    },
    "rules": {"disabled": ("disabled", _disabled)},
}


def _section(name: str, table: object, *, strict: bool) -> dict[str, Any]:
    if not isinstance(table, Mapping):
        raise ValueError(f"[{name}] must be a table")  # noqa: TRY004
    keys = _SCHEMA[name]
    unknown = sorted(str(key) for key in table if key not in keys)
    if unknown:
        raise ValueError(f"[{name}] has unknown keys: {', '.join(unknown)}")
    if strict and (missing := keys.keys() - table.keys()):
        raise ValueError(f"[{name}] missing keys: {', '.join(sorted(missing))}")
    values: dict[str, Any] = {}
    for key, value in table.items():
        attribute, validate = keys[key]
        try:
            values[attribute] = validate(value)
        except ValueError as error:
            raise ValueError(f"[{name}] {key}: {error}") from error
    return values


def parse_rules(mapping: Mapping[str, object], *, strict: bool = False) -> RetrievalRules:
    """Validate a TOML-shaped mapping, requiring every section and key in strict mode."""
    if not isinstance(mapping, Mapping):
        raise ValueError("retrieval rules must be a table")  # noqa: TRY004
    unknown = sorted(str(key) for key in mapping if key not in _SCHEMA)
    if unknown:
        raise ValueError(f"unknown sections: {', '.join(unknown)}")
    if strict and (missing := _SCHEMA.keys() - mapping.keys()):
        raise ValueError(f"missing sections: {', '.join(sorted(missing))}")
    values: dict[str, Any] = {}
    for name, table in mapping.items():
        values.update(_section(name, table, strict=strict))
    return replace(DEFAULT_RULES, **values)
