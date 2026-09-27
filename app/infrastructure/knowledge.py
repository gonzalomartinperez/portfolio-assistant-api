import asyncio
import logging

from neo4j import Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.application.knowledge import Chunk, Corpus
from app.infrastructure.embedding import embed


class KnowledgeIndex:
    def __init__(self, connect, graph):
        self.connect = connect
        self.graph = graph

    async def candidates(self, question: str) -> Corpus | None:
        def read():
            with self.connect() as conn:
                version = conn.execute(
                    "SELECT id,source_commit FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if not version:
                    return None
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
                nearest = tuple(
                    r['id']
                    for r in conn.execute(
                        'SELECT id FROM chunks WHERE knowledge_version=%s ORDER BY embedding <=> %s::vector,id LIMIT 12',
                        (version['id'], embed(question)),
                    ).fetchall()
                )
            return Corpus(
                version['id'],
                version['source_commit'],
                tuple(Chunk(**r) for r in rows),
                paths,
                nearest,
            )

        return await asyncio.to_thread(read)

    async def relationships(
        self, version: str, terms: set[str], locale: str = 'en', expand: bool = False
    ) -> tuple[str, ...]:
        def read():
            try:
                with self.graph.session() as graph:
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
            except (Neo4jError, ServiceUnavailable, SessionExpired):
                logging.getLogger('portfolio_assistant').warning(
                    '{"operation":"graph_retrieval","status":"unavailable"}'
                )
                return ()

        return await asyncio.to_thread(read)
