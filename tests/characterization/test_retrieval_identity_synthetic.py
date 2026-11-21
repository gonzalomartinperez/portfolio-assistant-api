"""Synthetic corpora reach the branches the frozen snapshot never exercises.

Adjacent and non-adjacent experience chunks, duplicate companies, chunks without a start
date, corrupt hashes, legacy ``src/content`` paths and goal-free corpora are generated
here; the legacy module and the pipeline must agree on every one of them.
"""

import hashlib
import random
from typing import Any
from urllib.parse import quote

from hypothesis import given, settings
from hypothesis import strategies as st

from portfolio_assistant.ai.retrieval import PublicRetrieval
from portfolio_assistant.application.knowledge import Chunk, Corpus
from tests.characterization.legacy_retrieval import LegacyRetrieval
from tests.characterization.test_retrieval_identity import run

COMMIT = "a" * 40
WORDS = (
    "Rampy", "Acme", "Zed", "Filomena", "LangGraph", "Neo4j", "PostgreSQL", "pgvector",
    "roles", "puestos", "compare", "between", "entre", "degree", "study", "goals", "metrics",
    "measured", "performance", "technologies", "stack", "languages", "speak", "design goal",
    "tell me about Gonzalo", "at", "built for", "repository", "README", "Gonzalo", "did",
    "what", "work", "projects",
)  # fmt: skip
FRAGMENTS = (
    'company: "Rampy"', 'company: "Acme Corp"', 'company: "Zed"',
    'startedOn: "2021-03-01"', 'startedOn: "2019-01-05"', 'startedOn: "2023-07-09"',
    "contributions: [", 'qualifier: "p95"', "value: 12", 'name: "Filomena"',
    'name: "LangGraph"', 'slug: "rampy"', 'language: "English"', "design goal latency",
    "objetivo de latencia", "Neo4j graph", "PostgreSQL pgvector", "degree", "title", "Rampy",
    "Zed Acme",
)  # fmt: skip
PATHS = (
    *(f"content/{locale}/{topic}.ts" for locale in ("en", "es")
      for topic in ("profile", "experience", "projects", "education")),
    "README.md", "public/assistant-knowledge.json", "docs/x.md", "src/content/en/experience.ts",
)  # fmt: skip


def synthetic_chunks(rnd: random.Random) -> tuple[list[Chunk], list[str]]:
    chunks: list[Chunk] = []
    paths = [path for path in PATHS if rnd.random() < 0.85]
    for path in paths:
        line = 1
        for _ in range(rnd.randint(1, 4)):
            content = "\n".join(rnd.choice(FRAGMENTS) for _ in range(rnd.randint(1, 4)))
            if rnd.random() < 0.2:
                line += rnd.randint(1, 3)
            end = line + rnd.randint(1, 5) - 1
            url = (
                f"https://github.com/gonzalomartinperez/portfolio/blob/{COMMIT}/"
                f"{quote(path, safe='/')}#L{line}-L{end}"
            )
            digest = hashlib.sha256(content.encode()).hexdigest()
            if rnd.random() < 0.05:
                digest = "bad"
            chunks.append(Chunk(f"{path}:{line}", "t", url, "x", path, line, end, content, digest))
            line = end + 1
    return chunks, paths


def scenario(rnd: random.Random) -> tuple[Any, ...]:
    chunks, paths = synthetic_chunks(rnd)
    ids = [chunk.id for chunk in chunks] + ["unknown"]

    def pick() -> tuple[str, ...]:
        return tuple(rnd.choice(ids) for _ in range(rnd.randint(0, 10)))

    corpus = Corpus(
        "v", COMMIT, tuple(chunks), frozenset(paths), pick(), pick(), rnd.random() < 0.5
    )
    question = " ".join(rnd.choice(WORDS) for _ in range(rnd.randint(1, 7))) + rnd.choice("? ")
    if rnd.random() < 0.3:
        question = question.replace("at ", "at Rampy ")
    strategy = rnd.choice(["hybrid"] * 4 + ["vector", "lexical", "graph"])
    return strategy, corpus, pick(), question, rnd.choice(["en", "es"])


@settings(max_examples=600, deadline=None, derandomize=True)
@given(st.integers(min_value=0, max_value=2**32))
def test_synthetic_corpora_match_legacy(seed: int) -> None:
    # A seeded stdlib Random keeps the generated corpora rich; Hypothesis randoms shrink them.
    case = scenario(random.Random(seed))
    assert run(PublicRetrieval, *case) == run(LegacyRetrieval, *case)
