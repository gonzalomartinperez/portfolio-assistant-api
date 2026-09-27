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

    async def relationships(self, version: str, terms: set[str]) -> tuple[str, ...]:
        def read():
            try:
                with self.graph.session() as graph:
                    result = graph.run(
                        Query(
                            'MATCH (p:Project)-[:SUPPORTED_BY]->(d:Document {version:$version}) '
                            'WHERE toLower(p.name) IN $names RETURN DISTINCT d.id AS id ORDER BY id LIMIT 8',
                            timeout=2,
                        ),
                        version=version,
                        names=sorted(terms),
                    )
                    return tuple(record['id'] for record in result)
            except (Neo4jError, ServiceUnavailable, SessionExpired):
                logging.getLogger('portfolio_assistant').warning(
                    '{"operation":"graph_retrieval","status":"unavailable"}'
                )
                return ()

        return await asyncio.to_thread(read)
