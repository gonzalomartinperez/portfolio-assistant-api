import asyncio
import hashlib
import tomllib
from dataclasses import replace
from importlib.resources import files
from typing import TYPE_CHECKING

import pytest

from app.ai.retrieval import PublicRetrieval
from app.ai.retrieval.candidates import Eligible, eligible_chunks
from app.ai.retrieval.query import build_intent
from app.ai.retrieval.rerank import ANCHORS, FIRST_MATCH, rerank
from app.ai.retrieval.rules import DEFAULT_RULES, RULE_IDS, parse_rules
from app.application.knowledge import Chunk, Corpus

if TYPE_CHECKING:
    from app.ai.retrieval.rules import RetrievalRules

COMMIT = "a" * 40


def test_packaged_rules_match_all_enabled_defaults():
    with files("app.ai.retrieval").joinpath("rules.toml").open("rb") as source:
        assert parse_rules(tomllib.load(source), strict=True) == DEFAULT_RULES
    assert parse_rules({"rules": {"disabled": []}}) == DEFAULT_RULES
    assert all(DEFAULT_RULES.enabled(rule_id) for rule_id in RULE_IDS)


@pytest.mark.parametrize(
    ("mapping", "message"),
    [
        ([], "retrieval rules must be a table"),
        ({"extra": {}}, "unknown sections: extra"),
        ({"weights": []}, r"\[weights\] must be a table"),
        ({"fusion": {"extra": 0}}, r"\[fusion\] has unknown keys: extra"),
        ({"rules": {"disabled": ["missing"]}}, "unknown rule ids: missing"),
        ({"rules": {"disabled": "exact_name"}}, "expected a list of rule ids"),
        ({"vocabulary": {"goal_terms": [1]}}, "expected a non-empty list"),
        ({"vocabulary": {"goal_pattern": "("}}, "invalid regular expression"),
        ({"weights": {"spoken_languages": True}}, "expected a number"),
        ({"weights": {"entity_path_multiplier": -1}}, "weights must not be negative"),
        ({"weights": {"spoken_languages": float("nan")}}, "weights must be finite"),
        ({"fusion": {"semantic": [1, 2, -3]}}, "weights must not be negative"),
        ({"fusion": {"lexical": [1, 2]}}, "expected three weights"),
        ({"fusion": {"offset": -1}}, "expected a positive integer"),
        ({"fusion": {"offset": 0}}, "expected a positive integer"),
        ({"fusion": {"offset": 10**309}}, "expected a positive integer"),
        ({"fusion": {"offset": 60.0}}, "expected a positive integer"),
        ({"fusion": {"relationship_graph_first": 1}}, "expected true or false"),
    ],
)
def test_parse_rules_rejects_bad_input(mapping, message):
    with pytest.raises(ValueError, match=message):
        parse_rules(mapping)


def test_parse_rules_strict_requires_every_section_and_key():
    with files("app.ai.retrieval").joinpath("rules.toml").open("rb") as source:
        complete = tomllib.load(source)

    for section, table in complete.items():
        incomplete = complete.copy()
        del incomplete[section]
        with pytest.raises(ValueError, match=f"missing sections: {section}"):
            parse_rules(incomplete, strict=True)
        for key in table:
            incomplete_table = table.copy()
            del incomplete_table[key]
            with pytest.raises(ValueError, match=rf"\[{section}\] missing keys: {key}"):
                parse_rules({**complete, section: incomplete_table}, strict=True)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"disabled": frozenset({"missing"})}, "unknown rule ids: missing"),
        ({"spoken_languages_boost": -1}, "weights must not be negative"),
        ({"overview_profile_boost": float("inf")}, "weights must be finite"),
        ({"company_contributions_boost": float("nan")}, "weights must be finite"),
        ({"entity_path_multiplier": -1}, "weights must not be negative"),
        ({"entity_path_multiplier": float("inf")}, "weights must be finite"),
        ({"fusion_offset": -1}, "expected a positive integer"),
        ({"fusion_offset": 10.0}, "expected a positive integer"),
        ({"fusion_offset": True}, "expected a positive integer"),
        ({"semantic_weights": (1, 2)}, "expected three weights"),
        ({"lexical_weights": [1, 2, 3]}, "expected a tuple of three weights"),
        ({"lexical_weights": (1, 2, -3)}, "weights must not be negative"),
        ({"semantic_weights": (1, float("inf"), 3)}, "weights must be finite"),
    ],
)
def test_replacing_rules_validates_invariants(changes, message):
    with pytest.raises(ValueError, match=message):
        replace(DEFAULT_RULES, **changes)


def make_chunk(key: str, topic: str, content: str) -> Chunk:
    path = f"content/en/{topic}.ts"
    return Chunk(
        key,
        topic,
        f"https://github.com/gonzalomartinperez/portfolio/blob/{COMMIT}/{path}#L1-L1",
        "fixture",
        path,
        1,
        1,
        content,
        hashlib.sha256(content.encode()).hexdigest(),
    )


class FixtureIndex:
    """Serve two equally strong lexical matches and one vector and graph hit."""

    def __init__(self, *, semantic: bool) -> None:
        chunks = (
            make_chunk("lexical", "projects", "Latency analysis"),
            make_chunk("vector", "projects", "Latency results"),
        )
        self.corpus = Corpus(
            "v",
            COMMIT,
            chunks,
            frozenset(chunk.path for chunk in chunks),
            ("vector",),
            semantic=semantic,
        )

    async def candidates(self, question: str) -> Corpus:
        """Return the in-memory corpus."""
        return self.corpus

    async def relationships(
        self, version: str, terms: set[str], locale: str = "en", expand: bool = False
    ) -> tuple[str, ...]:
        """Return the sole graph hit."""
        return ("vector",)


def _ranked_ids(
    question: str, rules: RetrievalRules = DEFAULT_RULES, *, semantic: bool = False
) -> list[str]:
    retriever = PublicRetrieval(FixtureIndex(semantic=semantic), rules=rules)
    return [evidence.id for evidence in asyncio.run(retriever.search(question, "en"))]


def test_adding_a_relationship_term_changes_intent_and_evidence_order():
    question = "Latency"
    rules = replace(
        DEFAULT_RULES, relationship_terms=DEFAULT_RULES.relationship_terms | {"latency"}
    )
    original = build_intent(question, DEFAULT_RULES)
    expanded = build_intent(question, rules)

    assert original is not None
    assert not original.relationship
    assert expanded is not None
    assert expanded.relationship
    assert _ranked_ids(question) == ["lexical", "vector"]
    assert _ranked_ids(question, rules) == ["vector", "lexical"]


def test_fusion_offset_and_lane_weights_change_evidence_order():
    weighted = replace(DEFAULT_RULES, lexical_weights=(1.0, 0.2, 0.5))
    small_offset = parse_rules({"fusion": {"offset": 1, "lexical": [1.0, 0.2, 0.5]}})

    assert small_offset == replace(weighted, fusion_offset=1)
    assert _ranked_ids("Latency") == ["lexical", "vector"]
    assert _ranked_ids("Latency", weighted) == ["vector", "lexical"]
    assert _ranked_ids("Latency", small_offset) == ["lexical", "vector"]


def test_fusion_selects_lane_weights_by_corpus_semantic_flag():
    swapped = replace(
        DEFAULT_RULES,
        semantic_weights=DEFAULT_RULES.lexical_weights,
        lexical_weights=DEFAULT_RULES.semantic_weights,
    )

    assert _ranked_ids("Latency", semantic=False) == ["lexical", "vector"]
    assert _ranked_ids("Latency", semantic=True) == ["vector", "lexical"]
    assert _ranked_ids("Latency", swapped, semantic=False) == ["vector", "lexical"]
    assert _ranked_ids("Latency", swapped, semantic=True) == ["lexical", "vector"]


def test_disabling_relationship_graph_first_falls_back_to_fusion():
    graph_first = replace(DEFAULT_RULES, lexical_weights=(3.0, 0.1, 0.1))
    fused = replace(graph_first, relationship_graph_first=False)

    assert _ranked_ids("Compare latency", graph_first) == ["vector", "lexical"]
    assert _ranked_ids("Compare latency", fused) == ["lexical", "vector"]


BOOST_CASES = [
    ("boost_spoken_languages", "What languages does he speak?", "profile", 'language: "English"'),
    ("boost_overview_profile_head", "Tell me about Gonzalo", "profile", 'name: "Gonzalo"'),
    (
        "boost_company_contributions",
        "What did he build at Acme?",
        "experience",
        'company: "Acme", contributions: []',
    ),
    ("multiplier_entity_path", "Tell me about Widget", "projects", 'slug: "widget"'),
]


@pytest.mark.parametrize(("rule_id", "question", "topic", "content"), BOOST_CASES)
def test_candidate_boost_can_be_disabled(rule_id, question, topic, content):
    chunk = make_chunk("match", topic, content)
    corpus = Corpus("v", COMMIT, (chunk,), frozenset({chunk.path}), (), (), False)
    disabled = replace(DEFAULT_RULES, disabled=frozenset({rule_id}))
    all_enabled = replace(disabled, disabled=frozenset())
    intent = build_intent(question, DEFAULT_RULES)

    assert intent is not None
    default = eligible_chunks(corpus, intent, "en", DEFAULT_RULES)
    assert default == eligible_chunks(corpus, intent, "en", all_enabled)
    without = eligible_chunks(corpus, intent, "en", disabled)
    assert without.chunks == default.chunks
    assert without.scores["match"] < default.scores["match"]


RERANK_CASES = [
    ("overview_first", "Tell me about Gonzalo and his performance", "profile", "Profile summary"),
    (
        "affiliation_filter",
        "What performance did he report at Acme?",
        "experience",
        'company: "Acme"',
    ),
    (
        "performance_metrics",
        "What performance did Widget report?",
        "projects",
        'qualifier: "p95", value: 12',
    ),
    ("exact_name", "Tell me about Widget", "projects", 'name: "Widget"'),
    ("qualification_anchor", "What degree did he study?", "education", "Education summary"),
    ("relationship_anchors", "Compare Widget and Acme stack", "projects", "Widget summary"),
    ("technical_topic_anchors", "How did he use LangGraph?", "projects", "LangGraph summary"),
    (
        "goals_metrics_anchor",
        "What were the design goals and measurements?",
        "projects",
        "Design goal latency",
    ),
]


@pytest.mark.parametrize(("rule_id", "question", "topic", "content"), RERANK_CASES)
def test_rerank_step_can_be_disabled(rule_id, question, topic, content):
    # These declarations give later first-match steps something to promote.
    chunks = {
        "other": make_chunk("other", "projects", "General project description"),
        "later": make_chunk("later", "projects", 'name: "Widget", qualifier: "q", value: 3'),
        "match": make_chunk("match", topic, content),
    }
    if rule_id == "performance_metrics":
        chunks["later"] = make_chunk("later", "projects", 'name: "Widget"')
    if rule_id == "exact_name":
        chunks["later"] = make_chunk("later", "projects", "Another project")
    eligible = Eligible(chunks, {**dict.fromkeys(chunks, 10.0), "match": 20.0})
    intent = build_intent(question, DEFAULT_RULES)
    disabled = replace(DEFAULT_RULES, disabled=frozenset({rule_id}))
    all_enabled = replace(disabled, disabled=frozenset())

    assert intent is not None
    default = rerank(list(chunks), intent, eligible, DEFAULT_RULES)
    assert default[0] == "match"
    assert default == rerank(list(chunks), intent, eligible, all_enabled)
    assert rerank(list(chunks), intent, eligible, disabled) == list(chunks)


def test_rule_ids_cover_the_boosts_and_rerank_registry():
    boost_ids = {case[0] for case in BOOST_CASES}
    rerank_ids = {case[0] for case in RERANK_CASES}
    assert rerank_ids == {step.id for step in (*FIRST_MATCH, *ANCHORS)}
    assert boost_ids | rerank_ids == RULE_IDS
