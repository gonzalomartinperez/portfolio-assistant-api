"""Deterministic retrieval orchestration over injected indexes."""

import json
import logging
import re
import time
from dataclasses import asdict

from app.application.contracts import Evidence
from app.application.knowledge import KnowledgeIndex
from app.domain.evidence import EvidenceRecord, lexical_score, tokens, verified


class PublicRetrieval:
    def __init__(self, index: KnowledgeIndex, strategy: str = 'hybrid'):
        if strategy not in ('hybrid', 'vector', 'graph'):
            raise ValueError('unsupported retrieval strategy')
        self.index = index
        self.strategy = strategy

    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
        started = time.perf_counter()
        terms = tokens(question)
        if not terms:
            return ()
        corpus = await self.index.candidates(question)
        if corpus is None:
            return ()
        # Do not answer an explicit employer/project premise with unrelated evidence.
        affiliation = re.search(
            r'\b(?:at|for|en)\s+([A-Z][\w.-]+(?: [A-Z][\w.-]+){0,3})', question
        )
        if affiliation:
            known_terms = set().union(
                *(tokens(chunk.content) for chunk in corpus.chunks)
            )
            if not tokens(affiliation[1]) <= known_terms:
                return ()
        relationship = bool(
            terms
            & {
                'connect',
                'connected',
                'shared',
                'share',
                'shares',
                'between',
                'both',
                'related',
                'comparten',
                'relacion',
                'entre',
                'ambos',
            }
        )
        # Explicit entity declarations anchor adjacent chunks in the same public document.
        entity_paths = {
            chunk.path
            for chunk in corpus.chunks
            if any(
                name.lower() in terms
                for name in re.findall(r'(?:slug|name):\s*"([^"\n]+)"', chunk.content)
            )
        }
        eligible = {}
        scores = {}
        for chunk in corpus.chunks:
            row: EvidenceRecord = {
                'path': chunk.path,
                'content': chunk.content,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'url': chunk.url,
                'content_hash': chunk.content_hash,
            }
            score = lexical_score(row, terms, locale)
            if chunk.path in entity_paths:
                score *= 2
            parts = chunk.path.split('/')
            preferred = (
                not chunk.path.startswith('src/content/')
                or parts[2] == locale
                or f'src/content/{locale}/' + '/'.join(parts[3:]) not in corpus.paths
            )
            if preferred and verified(row, corpus.commit, set(corpus.paths)):
                eligible[chunk.id] = chunk
                scores[chunk.id] = score
        lexical = sorted(
            (key for key in eligible if scores[key] >= 3),
            key=lambda key: (-scores[key], key),
        )
        vector = [key for key in corpus.nearest if key in eligible and scores[key] >= 3]
        graph = []
        if self.strategy == 'graph' or (self.strategy == 'hybrid' and relationship):
            graph = [
                key
                for key in await self.index.relationships(
                    corpus.version, terms, locale, expand=relationship
                )
                if key in eligible
            ]
        if self.strategy == 'vector':
            ranked = vector
        elif self.strategy == 'graph':
            ranked = graph
        elif relationship and graph:
            ranked = list(dict.fromkeys(graph + lexical + vector))
        else:
            ranks: dict[str, float] = {}
            for weight, ids in ((3.0, lexical), (0.4, vector), (0.25, graph)):
                for index, key in enumerate(ids):
                    ranks[key] = ranks.get(key, 0) + weight / (10 + index)
            ranked = sorted(ranks, key=lambda key: (-ranks[key], -scores[key], key))
        logging.getLogger('portfolio_assistant').info(
            json.dumps(
                {
                    'operation': 'retrieval',
                    'strategy': self.strategy,
                    'graph_expansion': relationship,
                    'sources': min(5, len(ranked)),
                    'duration_ms': round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )
        return tuple(
            Evidence(
                **{
                    k: v
                    for k, v in asdict(eligible[key]).items()
                    if k != 'content_hash'
                },
                commit_sha=corpus.commit,
            )
            for key in ranked[:5]
        )
