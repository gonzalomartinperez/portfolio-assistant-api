import asyncio
import logging

from neo4j import Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.application.embeddings import Embeddings
from app.application.knowledge import Chunk, Corpus
from app.domain.errors import RejectedError
from app.infrastructure.embedding import FixtureEmbeddings, vector


class KnowledgeIndex:
    def __init__(
        self,
        connect,
        graph,
        embeddings: Embeddings | None = None,
        *,
        database: str = 'neo4j',
        freshness: int | None = None,
    ):
        self.connect = connect
        self.graph = graph
        self.embeddings = embeddings or FixtureEmbeddings()
        self.database = database
        self.freshness = freshness

    async def candidates(self, question: str) -> Corpus | None:
        def read():
            with self.connect() as conn:
                version = conn.execute(
                    "SELECT id,source_commit,embedding_provider,embedding_model FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if not version:
                    return None
                if self.freshness is not None:
                    watch = conn.execute(
                        "SELECT observed_commit, checked_at > now() - %s * interval '1 second' AS fresh FROM knowledge_watch WHERE singleton",
                        (self.freshness,),
                    ).fetchone()
                    if (
                        not watch
                        or not watch['fresh']
                        or watch['observed_commit'] != version['source_commit']
                    ):
                        raise RejectedError('knowledge_updating', 503)
                if (
                    version['embedding_provider'] != self.embeddings.provider
                    or version['embedding_model'] != self.embeddings.model
                ):
                    raise RejectedError('knowledge_updating', 503)
                rows = conn.execute(
                    'SELECT id,title,url,source_type,path,start_line,end_line,content,content_hash FROM chunks WHERE knowledge_version=%s ORDER BY id LIMIT 500',
                    (version['id'],),
                ).fetchall()
                paths = frozenset(
                    r['path']
                    for r in conn.execute(
                        'SELECT path FROM source_files WHERE knowledge_version=%s',
                        (version['id'],),
                    ).fetchall()
                )
                lexical = tuple(
                    r['id']
                    for r in conn.execute(
                        "SELECT id FROM chunks WHERE knowledge_version=%s AND search_document @@ websearch_to_tsquery('simple',%s) ORDER BY ts_rank(search_document,websearch_to_tsquery('simple',%s)) DESC,id LIMIT 12",
                        (version['id'], question, question),
                    ).fetchall()
                )
            return version, rows, paths, lexical

        snapshot = await asyncio.to_thread(read)
        if snapshot is None:
            return None
        version, rows, paths, lexical = snapshot
        encoded = vector(await self.embeddings.query(question))
        column = (
            'semantic_embedding'
            if self.embeddings.provider == 'openai'
            else 'embedding'
        )

        def neighbors():
            with self.connect() as conn:
                return tuple(
                    r['id']
                    for r in conn.execute(
                        f'SELECT id FROM chunks WHERE knowledge_version=%s AND {column} IS NOT NULL ORDER BY {column} <=> %s::vector,id LIMIT 12',
                        (version['id'], encoded),
                    ).fetchall()
                )

        nearest = await asyncio.to_thread(neighbors)
        return Corpus(
            version['id'],
            version['source_commit'],
            tuple(Chunk(**row) for row in rows),
            paths,
            nearest,
            lexical,
            self.embeddings.provider == 'openai',
        )

    async def relationships(
        self, version: str, terms: set[str], locale: str = 'en', expand: bool = False
    ) -> tuple[str, ...]:
        def read():
            try:
                with self.graph.session(database=self.database) as graph:
                    direct = graph.run(
                        Query(
                            'MATCH (p:Entity {version:$version})-[:SUPPORTED_BY]->(d:Document {version:$version}) '
                            'WHERE p.normalized IN $names AND (d.path STARTS WITH $prefix OR NOT d.path STARTS WITH "src/content/") RETURN DISTINCT d.id AS id ORDER BY id LIMIT 12',
                            timeout=2,
                        ),
                        version=version,
                        names=sorted(terms),
                        prefix=f'src/content/{locale}/',
                    )
                    ids = tuple(record['id'] for record in direct)
                    if not expand:
                        return ids
                    related = graph.run(
                        Query(
                            'MATCH (seed:Entity {version:$version})-[a:RELATES]->(t:Entity {kind:"Technology",version:$version})'
                            '<-[b:RELATES]-(other:Entity {version:$version}) '
                            'WHERE seed.normalized IN $names AND seed.id<>other.id '
                            'AND a.version=$version AND b.version=$version '
                            'MATCH (d:Document {id:b.document,version:$version}) '
                            'WHERE d.path STARTS WITH $prefix OR NOT d.path STARTS WITH "src/content/" '
                            'RETURN d.id AS id,count(DISTINCT t.id) AS shared ORDER BY shared DESC,id LIMIT 12',
                            timeout=2,
                        ),
                        version=version,
                        names=sorted(terms),
                        prefix=f'src/content/{locale}/',
                    )
                    neighbors = tuple(record['id'] for record in related)
                    # Keep seed evidence as well as the evidence reached through shared technology.
                    return tuple(
                        dict.fromkeys(ids[:2] + neighbors[:3] + ids[2:] + neighbors[3:])
                    )[:20]
            except Neo4jError, ServiceUnavailable, SessionExpired:
                logging.getLogger('portfolio_assistant').warning(
                    '{"operation":"graph_retrieval","status":"unavailable"}'
                )
                return ()

        return await asyncio.to_thread(read)

    def starter_prompts(self, locale):
        from app.domain.knowledge import suggestions

        with self.connect() as conn:
            version = conn.execute(
                "SELECT id,source_commit FROM knowledge_versions WHERE status='active'"
            ).fetchone()
            if not version:
                raise RejectedError('knowledge_updating', 503)
            if self.freshness is not None:
                watch = conn.execute(
                    "SELECT observed_commit, checked_at > now() - %s * interval '1 second' AS fresh FROM knowledge_watch WHERE singleton",
                    (self.freshness,),
                ).fetchone()
                if (
                    not watch
                    or not watch['fresh']
                    or watch['observed_commit'] != version['source_commit']
                ):
                    raise RejectedError('knowledge_updating', 503)
            paths = frozenset(
                row['path']
                for row in conn.execute(
                    'SELECT path FROM source_files WHERE knowledge_version=%s',
                    (version['id'],),
                ).fetchall()
            )
            achievements = bool(
                conn.execute(
                    'SELECT 1 FROM chunks WHERE knowledge_version=%s AND (path=%s OR path=%s) AND content LIKE %s AND content LIKE %s LIMIT 1',
                    (
                        version['id'],
                        f'src/content/{locale}/experience.ts',
                        'public/assistant-knowledge.json',
                        '%qualifier%',
                        '%value%',
                    ),
                ).fetchone()
            )
        return (
            version['id'],
            version['source_commit'],
            suggestions(paths, locale, achievements=achievements),
        )
