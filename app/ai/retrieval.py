"""Deterministic retrieval orchestration over injected indexes."""

import json
import logging
import re
import time
from dataclasses import asdict

from app.application.contracts import Evidence
from app.application.knowledge import KnowledgeIndex
from app.domain.evidence import (
    EvidenceRecord,
    lexical_score,
    requested_affiliation,
    tokens,
    verified,
)


class PublicRetrieval:
    def __init__(self, index: KnowledgeIndex, strategy: str = 'hybrid'):
        if strategy not in ('hybrid', 'vector', 'graph'):
            raise ValueError('unsupported retrieval strategy')
        self.index = index
        self.strategy = strategy

    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
        started = time.perf_counter()
        terms = tokens(question)
        if (
            terms
            & {
                'salary',
                'salario',
                'compensation',
                'availability',
                'disponibilidad',
                'secrets',
                'secretos',
            }
            or 'career-ops' in question.lower()
        ):
            return ()
        overview = bool(
            re.search(
                r'(?i)(tell me about|cuéntame sobre|cuentame sobre|who is|quién es)\s+gonzalo',
                question,
            )
        )
        if overview:
            terms |= {'profile', 'summary', 'intro'}
        repository_question = bool(
            terms & {'repository', 'repo', 'repositorio', 'portfolio', 'readme'}
        )
        if not terms:
            return ()
        corpus = await self.index.candidates(question)
        if corpus is None:
            return ()
        # Do not answer an explicit employer/project premise with unrelated evidence.
        affiliation = requested_affiliation(question)
        if affiliation:
            known_terms = set().union(
                *(tokens(chunk.content) for chunk in corpus.chunks)
            )
            if not tokens(affiliation) <= known_terms:
                return ()
        relationship = bool(
            terms
            & {
                'compare',
                'comparison',
                'versus',
                'compara',
                'comparar',
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
            # Editorial/development instructions are not evidence of professional contributions.
            if (
                not repository_question
                and not chunk.path.startswith('src/content/')
                and chunk.path != 'public/assistant-knowledge.json'
            ):
                continue
            row: EvidenceRecord = {
                'path': chunk.path,
                'content': chunk.content,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'url': chunk.url,
                'content_hash': chunk.content_hash,
            }
            score = lexical_score(row, terms, locale)
            if (
                overview
                and chunk.path.endswith('/profile.ts')
                and chunk.start_line == 1
            ):
                score += 100
            if (
                chunk.path.endswith('/experience.ts')
                and any(
                    tokens(name) & terms
                    for name in re.findall(r'company:\s*"([^"\n]+)"', chunk.content)
                )
                and 'contributions:' in chunk.content
            ):
                score += 50
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
        vector = [
            key
            for key in corpus.nearest
            if key in eligible and (corpus.semantic or scores[key] >= 3)
        ]
        lexical = list(
            dict.fromkeys(lexical + [key for key in corpus.lexical if key in eligible])
        )
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
            for weight, ids in (
                (1.0 if corpus.semantic else 3.0, lexical),
                (1.0 if corpus.semantic else 0.1, vector),
                (0.5, graph),
            ):
                for index, key in enumerate(ids):
                    ranks[key] = ranks.get(key, 0) + weight / (10 + index)
            ranked = sorted(ranks, key=lambda key: (-ranks[key], -scores[key], key))
        if self.strategy == 'hybrid':
            if overview:
                ranked.sort(
                    key=lambda key: (
                        not (
                            eligible[key].path.endswith('/profile.ts')
                            and eligible[key].start_line == 1
                        )
                    )
                )
            elif affiliation and not relationship:
                ranked = [
                    key
                    for key in ranked
                    if tokens(affiliation) <= tokens(eligible[key].content)
                ]
                ranked.sort(
                    key=lambda key: (
                        not any(
                            tokens(name) & tokens(affiliation)
                            for name in re.findall(
                                r'company:\s*"([^"\n]+)"', eligible[key].content
                            )
                        )
                    )
                )
            elif terms & {
                'performance',
                'improvements',
                'metrics',
                'metricas',
                'rendimiento',
            }:
                ranked.sort(
                    key=lambda key: (
                        not (
                            'qualifier:' in eligible[key].content
                            and 'value:' in eligible[key].content
                        )
                    )
                )
            elif not terms & {'technologies', 'technology', 'tecnologias', 'stack'}:
                ranked.sort(
                    key=lambda key: (
                        not any(
                            tokens(name) <= terms
                            for name in re.findall(
                                r'name:\s*"([^"\n]+)"', eligible[key].content
                            )
                            if tokens(name)
                        )
                    )
                )
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
