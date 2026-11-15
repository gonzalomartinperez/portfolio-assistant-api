"""Retrieval orchestration: candidates, lane strategy, fusion, re-ranking, selection."""

import json
import logging
import time
from typing import TYPE_CHECKING

from app.ai.retrieval.candidates import (
    Eligible,
    eligible_chunks,
    lexical_lane,
    unknown_affiliation,
    vector_lane,
)
from app.ai.retrieval.fusion import fuse
from app.ai.retrieval.query import QueryIntent, build_intent
from app.ai.retrieval.rerank import rerank
from app.ai.retrieval.select import LIMIT, select_evidence
from app.application.observability import phase

if TYPE_CHECKING:
    from app.application.contracts import Evidence
    from app.application.knowledge import Corpus, KnowledgeIndex

STRATEGIES = ("hybrid", "vector", "lexical", "graph")


def _fusion_weights(semantic: bool) -> tuple[float, float, float]:
    return (1.0, 1.0, 0.5) if semantic else (3.0, 0.1, 0.5)


def _rank(
    strategy: str,
    intent: QueryIntent,
    corpus: Corpus,
    eligible: Eligible,
    lanes: tuple[list[str], list[str], list[str]],
) -> list[str]:
    lexical, vector, graph = lanes
    single = {"vector": vector, "lexical": lexical, "graph": graph}
    if strategy in single:
        return single[strategy]
    if intent.relationship and graph:
        return list(dict.fromkeys(graph + lexical + vector))
    return fuse(
        (lexical, vector, graph), _fusion_weights(corpus.semantic), eligible.scores, offset=10
    )


class PublicRetrieval:
    """Retrieve cited public evidence using the selected candidate strategy."""

    def __init__(self, index: KnowledgeIndex, strategy: str = "hybrid"):
        """Bind an index and validate the requested retrieval strategy."""
        if strategy not in STRATEGIES:
            raise ValueError("unsupported retrieval strategy")
        self.index = index
        self.strategy = strategy

    async def _graph_lane(
        self, corpus: Corpus, intent: QueryIntent, eligible: Eligible, locale: str
    ) -> list[str]:
        if not (self.strategy == "graph" or (self.strategy == "hybrid" and intent.relationship)):
            return []
        with phase("graph_retrieval"):
            keys = await self.index.relationships(
                corpus.version, set(intent.terms), locale, expand=intent.relationship
            )
            return [key for key in keys if key in eligible.chunks]

    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
        """Return up to five verified sources, or no evidence for unsupported queries."""
        started = time.perf_counter()
        intent = build_intent(question)
        if intent is None:
            return ()
        with phase("vector_retrieval"):
            corpus = await self.index.candidates(question)
        if corpus is None or unknown_affiliation(corpus, intent.affiliation):
            return ()
        eligible = eligible_chunks(corpus, intent, locale)
        lanes = (
            lexical_lane(corpus, eligible),
            vector_lane(corpus, eligible),
            await self._graph_lane(corpus, intent, eligible, locale),
        )
        ranked = _rank(self.strategy, intent, corpus, eligible, lanes)
        if self.strategy == "hybrid":
            ranked = rerank(ranked, intent, eligible)
        self._log(intent, ranked, started)
        return select_evidence(ranked, eligible.chunks, corpus.commit)

    def _log(self, intent: QueryIntent, ranked: list[str], started: float) -> None:
        logging.getLogger("portfolio_assistant").info(
            json.dumps(
                {
                    "operation": "retrieval",
                    "strategy": self.strategy,
                    "graph_expansion": intent.relationship,
                    "sources": min(LIMIT, len(ranked)),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )
