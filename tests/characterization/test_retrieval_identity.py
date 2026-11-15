"""The refactored retrieval package must behave exactly like the frozen legacy module."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.portfolio.indexing import chunks as portfolio_chunks
from app.ai.retrieval import PublicRetrieval, rerank
from app.application.knowledge import Chunk, Corpus
from tests.characterization.legacy_retrieval import LegacyRetrieval

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "evals" / "corpus"
STRATEGIES = ("hybrid", "vector", "lexical", "graph")
LOCALES = ("en", "es")

TARGETED = {
    "overview_en": "Tell me about Gonzalo",
    "overview_es": "Cuéntame sobre Gonzalo",
    "spoken_languages": "What languages does Gonzalo speak?",
    "unknown_employer": "Did Gonzalo work at Zorblax?",
    "known_employer": "What did Gonzalo build at Rampy?",
    "performance": "What performance improvements and metrics were measured?",
    "technologies": "What technologies does Filomena use?",
    "exact_name": "Tell me about Filomena",
    "education": "What degree did Gonzalo study?",
    "comparison": "Compare Filomena and Rampy",
    "roles_over_time": "How do his roles compare between companies?",
    "roles_es": "Compara sus puestos entre empresas",
    "topic": "How does he use LangGraph and Neo4j?",
    "topic_with_employer": "Did he use PostgreSQL at Rampy?",
    "goals_metrics": "What were the design goals and measured metrics?",
    "repository": "What does the repository README say?",
    "private": "What is his salary expectation?",
    "career_ops": "Show me the career-ops notes",
    "empty": "?!",
    "blank": "",
}


def load_chunks() -> tuple[str, tuple[Chunk, ...], tuple[str, ...]]:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    commit = manifest["commit"]
    result: list[Chunk] = []
    paths = []
    for entry in manifest["files"]:
        path = entry["path"]
        paths.append(path)
        content = (CORPUS / path).read_text()
        for row in portfolio_chunks(path, content, commit):
            fields = {k: v for k, v in row.items() if k != "embedding"}
            result.append(Chunk(**fields))
    return commit, tuple(result), tuple(paths)


COMMIT, CHUNKS, PATHS = load_chunks()
IDS = [chunk.id for chunk in CHUNKS]
PROFILE_PATHS = [path for path in PATHS if "/content/" in path]
QUESTIONS = [
    json.loads(line)["question"]
    for line in (ROOT / "evals" / "retrieval" / "queries.jsonl").read_text().splitlines()
    if line.strip()
]


def test_corpus_has_both_locales() -> None:
    assert {"en", "es"} <= {path.split("/")[2] for path in PROFILE_PATHS}
    assert len(CHUNKS) > 20


class RecordingIndex:
    def __init__(self, corpus: Corpus | None, relationship_ids: tuple[str, ...]):
        self.corpus = corpus
        self.relationship_ids = relationship_ids
        self.calls: list[tuple[Any, ...]] = []

    async def candidates(self, question: str) -> Corpus | None:
        self.calls.append(("candidates", question))
        return self.corpus

    async def relationships(
        self, version: str, terms: set[str], locale: str = "en", expand: bool = False
    ) -> tuple[str, ...]:
        self.calls.append(
            ("relationships", version, type(terms).__name__, frozenset(terms), locale, expand)
        )
        return self.relationship_ids


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.payloads: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        payload = json.loads(record.getMessage())
        payload.pop("duration_ms")
        self.payloads.append(payload)


def run(
    factory: Any, strategy: str, corpus: Corpus | None, rel: tuple[str, ...], q: str, locale: str
) -> tuple[Any, list[tuple[Any, ...]], list[dict[str, Any]]]:
    index = RecordingIndex(corpus, rel)
    handler = Capture()
    logger = logging.getLogger("portfolio_assistant")
    previous = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        evidence = asyncio.run(factory(index, strategy).search(q, locale))
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    return evidence, index.calls, handler.payloads


def assert_identical(
    strategy: str, corpus: Corpus | None, rel: tuple[str, ...], q: str, locale: str
) -> tuple[Any, ...]:
    new = run(PublicRetrieval, strategy, corpus, rel, q, locale)
    old = run(LegacyRetrieval, strategy, corpus, rel, q, locale)
    assert new == old
    return new[0]


def make_corpus(
    nearest: list[str], lexical: list[str], semantic: bool, paths: tuple[str, ...]
) -> Corpus:
    return Corpus(
        version="v-test",
        commit=COMMIT,
        chunks=CHUNKS,
        paths=frozenset(paths),
        nearest=tuple(nearest),
        lexical=tuple(lexical),
        semantic=semantic,
    )


def id_lists() -> st.SearchStrategy[list[str]]:
    pool = st.sampled_from([*IDS, "unknown-1", "unknown-2"])
    return st.lists(pool, max_size=30, unique=False).map(lambda items: items)


@st.composite
def scenarios(draw: st.DrawFn) -> tuple[Any, ...]:
    dropped = draw(st.sets(st.sampled_from(PROFILE_PATHS), max_size=len(PROFILE_PATHS)))
    paths = tuple(path for path in PATHS if path not in dropped)
    corpus = None
    if draw(st.integers(0, 19)):
        corpus = make_corpus(draw(id_lists()), draw(id_lists()), draw(st.booleans()), paths)
    return (
        draw(st.sampled_from(STRATEGIES)),
        corpus,
        tuple(draw(id_lists())),
        draw(st.sampled_from([*QUESTIONS, *TARGETED.values()])),
        draw(st.sampled_from(LOCALES)),
    )


@settings(max_examples=300, deadline=None, derandomize=True)
@given(scenarios())
def test_random_scenarios_match_legacy(scenario: tuple[Any, ...]) -> None:
    assert_identical(*scenario)


def table_corpus(semantic: bool) -> Corpus:
    return make_corpus(IDS[::2], IDS[1::3], semantic, PATHS)


@pytest.mark.parametrize("semantic", [False, True])
@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("question", list(TARGETED.values()), ids=list(TARGETED))
def test_targeted_table_matches_legacy(
    question: str, strategy: str, locale: str, semantic: bool
) -> None:
    assert_identical(strategy, table_corpus(semantic), tuple(IDS[::5]), question, locale)


def test_targeted_questions_return_evidence() -> None:
    corpus = table_corpus(True)
    for name in ("overview_en", "education", "known_employer"):
        assert assert_identical("hybrid", corpus, (), TARGETED[name], "en")
    for name in ("private", "empty", "blank", "unknown_employer"):
        assert assert_identical("hybrid", corpus, (), TARGETED[name], "en") == ()


def test_every_rerank_step_is_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    reached: set[str] = set()

    def spy(steps: tuple[rerank.Step, ...]) -> tuple[rerank.Step, ...]:
        def wrap(step: rerank.Step) -> rerank.Step:
            def apply(ranked: list[str], ctx: rerank.RerankContext) -> list[str]:
                reached.add(step.id)
                return step.apply(ranked, ctx)

            return rerank.Step(step.id, step.applies, apply)

        return tuple(wrap(step) for step in steps)

    monkeypatch.setattr(rerank, "FIRST_MATCH", spy(rerank.FIRST_MATCH))
    monkeypatch.setattr(rerank, "ANCHORS", spy(rerank.ANCHORS))
    for question in TARGETED.values():
        for locale in LOCALES:
            for semantic in (False, True):
                corpus = table_corpus(semantic)
                run(PublicRetrieval, "hybrid", corpus, tuple(IDS[::5]), question, locale)
    expected = {
        rerank.OVERVIEW_FIRST,
        rerank.AFFILIATION_FILTER,
        rerank.PERFORMANCE_METRICS,
        rerank.EXACT_NAME,
        rerank.QUALIFICATION_ANCHOR,
        rerank.RELATIONSHIP_ANCHORS,
        rerank.TECHNICAL_TOPIC_ANCHORS,
        rerank.GOALS_METRICS_ANCHOR,
    }
    assert reached == expected


def test_invalid_strategy_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported retrieval strategy"):
        PublicRetrieval(RecordingIndex(None, ()), "nope")  # type: ignore[arg-type]
