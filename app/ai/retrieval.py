"""Deterministic retrieval orchestration over injected indexes."""

from dataclasses import asdict

from app.application.contracts import Evidence
from app.application.knowledge import KnowledgeIndex
from app.domain.evidence import lexical_score, tokens, verified


class PublicRetrieval:
    def __init__(self, index: KnowledgeIndex, strategy: str = 'hybrid'):
        if strategy not in ('hybrid', 'vector', 'graph'):
            raise ValueError('unsupported retrieval strategy')
        self.index = index
        self.strategy = strategy

    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
        terms = tokens(question)
        if not terms:
            return ()
        corpus = await self.index.candidates(question)
        if corpus is None:
            return ()
        eligible = {}
        scores = {}
        for chunk in corpus.chunks:
            row = asdict(chunk)
            score = lexical_score(row, terms, locale)
            parts = chunk.path.split('/')
            preferred = (
                not chunk.path.startswith('src/content/')
                or parts[2] == locale
                or f'src/content/{locale}/' + '/'.join(parts[3:]) not in corpus.paths
            )
            if (
                score >= 3
                and preferred
                and verified(row, corpus.commit, set(corpus.paths))
            ):
                eligible[chunk.id] = chunk
                scores[chunk.id] = score
        lexical = sorted(eligible, key=lambda key: (-scores[key], key))
        vector = [key for key in corpus.nearest if key in eligible]
        graph = []
        if self.strategy in ('graph', 'hybrid'):
            graph = [
                key
                for key in await self.index.relationships(corpus.version, terms)
                if key in eligible
            ]
        if self.strategy == 'vector':
            ranked = vector
        elif self.strategy == 'graph':
            ranked = graph
        else:
            ranks: dict[str, float] = {}
            for weight, ids in ((3.0, lexical), (0.4, vector), (0.25, graph)):
                for index, key in enumerate(ids):
                    ranks[key] = ranks.get(key, 0) + weight / (10 + index)
            ranked = sorted(ranks, key=lambda key: (-ranks[key], -scores[key], key))
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
