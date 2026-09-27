"""Real adapter composition for compatibility and retrieval evaluations."""

import asyncio
from dataclasses import asdict

from neo4j import GraphDatabase

from app.ai.retrieval import PublicRetrieval
from app.bootstrap.config import settings
from app.infrastructure.db import connect
from app.infrastructure.knowledge import KnowledgeIndex


def retrieve(question, locale='en', *, strategy='hybrid'):
    config = settings()
    with GraphDatabase.driver(
        config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
    ) as graph:
        sources = asyncio.run(
            PublicRetrieval(KnowledgeIndex(connect, graph), strategy).search(
                question, locale
            )
        )
    rows = [{**asdict(s), 'title': s.title} for s in sources]
    return rows, [sources[0].commit_sha] if sources else []
