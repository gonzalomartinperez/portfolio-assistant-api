"""Closed technical topics; visitor text never becomes a web query."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

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
    if '\\' in url or len(url) > 1024 or any(ord(char) < 33 for char in url):
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
        and not any(part in ('.', '..') for part in unquote(parsed.path).split('/'))
        and (
            topic.name != 'pgvector'
            or parsed.path == '/pgvector/pgvector'
            or bool(
                re.fullmatch(
                    r'/pgvector/pgvector/blob/(?:main|master|[a-f0-9]{40})/README\.md',
                    parsed.path,
                )
            )
        )
    )


def canonical_web_url(url: str, topic: WebTopic) -> str | None:
    """Remove only OpenAI's known attribution parameter and safe document anchors."""
    try:
        parsed = urlsplit(url)
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None
    allowed = {
        ('utm_source', 'openai'),
        ('trk', 'article-ssr-frontend-pulse_little-text-block'),
    }
    if topic.name == 'pgvector' and re.fullmatch(
        r'/pgvector/pgvector/blob/(?:main|master|[a-f0-9]{40})/README\.md', parsed.path
    ):
        allowed.add(('plain', '1'))
    if (
        len(query) > 3
        or len({key for key, _ in query}) != len(query)
        or any(pair not in allowed for pair in query)
    ):
        return None
    if parsed.fragment and not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', parsed.fragment):
        return None
    canonical = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    return canonical if approved_web_url(canonical, topic) else None
