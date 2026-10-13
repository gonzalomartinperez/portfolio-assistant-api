"""Closed technical topics; visitor text never becomes a web query."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.domain.evidence import blocks_private_query, tokens


@dataclass(frozen=True)
class WebTopic:
    name: str
    domain: str
    query: str


TOPICS = (
    WebTopic(
        'LangGraph',
        'docs.langchain.com',
        'LangGraph official documentation orchestration persistence streaming',
    ),
    WebTopic(
        'Neo4j',
        'neo4j.com',
        'Neo4j official documentation graph retrieval vector search',
    ),
    WebTopic(
        'pgvector',
        'github.com',
        'pgvector pgvector official README vector similarity indexing',
    ),
    WebTopic(
        'PostgreSQL',
        'www.postgresql.org',
        'PostgreSQL official documentation transaction isolation indexing',
    ),
    WebTopic(
        'FastAPI',
        'fastapi.tiangolo.com',
        'FastAPI official documentation asynchronous requests lifespan',
    ),
    WebTopic(
        'Next.js',
        'nextjs.org',
        'Next.js official documentation server client components rendering',
    ),
    WebTopic(
        'OpenTelemetry',
        'opentelemetry.io',
        'OpenTelemetry official documentation traces metrics instrumentation',
    ),
)


def technical_topic(question: str, evidence: str) -> WebTopic | None:
    """Require explicit technical explanation/currentness and a public profile anchor."""
    terms = tokens(question)
    if not evidence or blocks_private_query(question, terms):
        return None
    if re.search(
        r'https?://|www\.|@|\b(?:ignore|ignora|override|system prompt|prompt del sistema|password|contrasena|contraseña|reveal|revela|nationality|nacionalidad|edad|age|address|domicilio|weather|clima|pizza|gossip|celebrity|lottery|loteria|noticias|news)\b',
        question,
        re.IGNORECASE,
    ):
        return None
    if not re.search(
        r'\b(?:gonzalo|portfolio|portafolio|rampy|pequeverso|teamcubation|asistente|assistant)\b',
        question,
        re.IGNORECASE,
    ):
        return None
    if not re.search(
        r'\b(?:current|latest|today|official|explain|compare|actual|actuales|actualmente|reciente|oficial|explica|explicame|explícame|compara)\b',
        question,
        re.IGNORECASE,
    ):
        return None
    named = [topic for topic in TOPICS if topic.name.casefold() in question.casefold()]
    if len(named) != 1:
        return None
    topic = named[0]
    return topic if topic.name.casefold() in evidence.casefold() else None


def approved_web_url(url: str, topic: WebTopic) -> bool:
    """Exact HTTPS authority, bounded document URL; pgvector is one upstream repo."""
    if len(url) > 1024 or any(ord(char) < 33 for char in url):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.port not in (None, 443):
            return False
    except ValueError:
        return False
    return bool(
        parsed.scheme == 'https'
        and parsed.hostname == topic.domain
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and (
            topic.name != 'pgvector'
            or parsed.path == '/pgvector/pgvector'
            or parsed.path.startswith('/pgvector/pgvector/')
        )
    )
