"""Bounded retrieval over the approved, versioned public portfolio projection."""

import hashlib
import re
import unicodedata
from urllib.parse import quote

from neo4j import GraphDatabase

from .config import settings
from .db import connect
from .knowledge import embed

STOP = {
    'about', 'again', 'como', 'con', 'cual', 'cuales', 'de', 'del', 'did', 'does',
    'donde', 'el', 'ella', 'en', 'es', 'esta', 'fue', 'gonzalo', 'his', 'how', 'is',
    'la', 'las', 'los', 'me', 'que', 'quien', 'se', 'the', 'this', 'una', 'what',
    'when', 'where', 'which', 'who', 'with', 'you', 'your',
}
ALIASES = {
    'study': {'education', 'university', 'universidad', 'studies', 'estudios'},
    'studied': {'education', 'university', 'universidad', 'studies', 'estudios'},
    'estudio': {'education', 'university', 'universidad', 'estudios'},
    'estudios': {'education', 'university', 'universidad'},
    'built': {'architecture', 'stack', 'technology', 'engineering', 'application', 'desarrollo'},
    'build': {'architecture', 'stack', 'technology', 'engineering', 'application', 'desarrollo'},
    'technologies': {'stack', 'technology', 'tecnologias'},
    'tecnologias': {'stack', 'technology', 'technologies'},
    'work': {'role', 'experience', 'trabajo'},
    'trabajo': {'role', 'experience', 'work'},
}
FIELDS = 'c.id,c.title,c.url,c.source_type,c.path,c.start_line,c.end_line,c.content,c.content_hash'


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize('NFKD', text.lower())
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    return {word for word in re.findall(r'[a-z0-9]+', normalized) if len(word) > 2 and word not in STOP}


def lexical_score(row: dict, terms: set[str], locale: str) -> float:
    content = tokens(row['content'])
    path = tokens(row['path'])
    if row['path'] == 'README.md':
        path.add('portfolio')
    expanded = terms | set().union(*(ALIASES.get(term, set()) for term in terms))
    anchors = expanded & (content | path)
    if not anchors:
        return 0
    score = 3 * len(terms & (content | path)) + len(anchors) + 2 * len(expanded & path)
    if 'portfolio' in terms and row['path'] == 'README.md':
        score *= 2
        if 'Engineering at a glance' in row['content']:
            score *= 5
    if terms & {'study', 'studied', 'estudio', 'estudios'} and row['path'].endswith('/education.ts') and row['start_line'] == 1:
        score *= 5
    if row['path'].endswith('/experience.ts') and 'contributions:' in row['content'] and terms & content:
        score *= 3
    if row['path'].endswith('/projects.ts') and terms & content:
        tech = bool(terms & {'technologies', 'technology', 'tecnologias', 'stack'})
        if (tech and 'stack: technologyNames' in row['content']) or (not tech and 'summary:' in row['content']):
            score *= 3
    if row['path'].startswith(f'src/content/{locale}/'):
        score *= 1.35
    elif row['path'].startswith('src/content/'):
        score *= 0.45
    return score


def verified(row: dict, source_commit: str, known_paths: set[str]) -> bool:
    path = row['path']
    if path not in known_paths or row['start_line'] < 1 or row['end_line'] < row['start_line']:
        return False
    expected = f'https://github.com/gonzalomartinperez/portfolio/blob/{source_commit}/{quote(path, safe="/")}#L{row["start_line"]}-L{row["end_line"]}'
    return row['url'] == expected and hashlib.sha256(row['content'].encode()).hexdigest() == row['content_hash']


def retrieve(question: str, locale: str = 'en', *, strategy: str = 'hybrid'):
    """Return only anchored, verified spans; vector similarity never establishes evidence alone."""
    terms = tokens(question)
    if not terms:
        return [], []
    with connect() as conn:
        version = conn.execute("SELECT id,source_commit FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1").fetchone()
        if not version:
            return [], []
        rows = conn.execute(f'SELECT {FIELDS} FROM chunks c WHERE c.knowledge_version=%s LIMIT 500', (version['id'],)).fetchall()
        paths = {r['path'] for r in conn.execute('SELECT path FROM source_files WHERE knowledge_version=%s', (version['id'],)).fetchall()}
        vector = conn.execute(f'SELECT {FIELDS} FROM chunks c WHERE c.knowledge_version=%s ORDER BY c.embedding <=> %s::vector LIMIT 12',
                              (version['id'], embed(question))).fetchall()
    scored = {row['id']: lexical_score(row, terms, locale) for row in rows}
    def preferred_locale(row):
        path = row['path']
        if not path.startswith('src/content/'):
            return True
        parts = path.split('/')
        counterpart = f'src/content/{locale}/' + '/'.join(parts[3:])
        return parts[2] == locale or counterpart not in paths

    eligible = {row['id']: row for row in rows if scored[row['id']] >= 3 and preferred_locale(row)
                and verified(row, version['source_commit'], paths)}
    lexical = sorted(eligible, key=lambda key: (-scored[key], key))
    vector_ids = [row['id'] for row in vector if row['id'] in eligible]
    graph_ids = []
    if strategy in ('hybrid', 'graph'):
        # Only approved Project names can seed this traversal; Cypher and limits are fixed.
        driver = None
        try:
            driver = GraphDatabase.driver(settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password), connection_timeout=2)
            with driver.session() as graph:
                graph_ids = [record['id'] for record in graph.run(
                    'MATCH (p:Project)-[:SUPPORTED_BY]->(d:Document {version:$version}) '
                    'WHERE toLower(p.name) IN $names RETURN d.id AS id LIMIT 8',
                    version=version['id'], names=sorted(terms)) if record['id'] in eligible]
        except Exception:
            # PostgreSQL owns the active knowledge version. Graph projection is optional at query time.
            graph_ids = []
        finally:
            if driver:
                driver.close()
    if strategy == 'vector':
        ranked = vector_ids
    elif strategy == 'graph':
        ranked = graph_ids
    else:
        ranks = {}
        for weight, ids in ((3.0, lexical), (0.4, vector_ids), (0.25, graph_ids)):
            for index, key in enumerate(ids):
                ranks[key] = ranks.get(key, 0) + weight / (10 + index)
        ranked = sorted(ranks, key=lambda key: (-ranks[key], -scored[key]))
    selected = [eligible[key] for key in ranked[:5] if key in eligible]
    return selected, [version['source_commit']]
