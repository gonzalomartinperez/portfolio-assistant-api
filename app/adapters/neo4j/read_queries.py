"""Fixed public graph reads and separately bounded publication preparation."""

from collections.abc import Callable
from typing import Literal

from neo4j import Query, Result, Session

READ_TIMEOUT = 2.0
PREPARATION_TIMEOUT = 5.0

LOCALE_FILTER = (
    '(d.path STARTS WITH $prefix OR d.path STARTS WITH $root_prefix '
    'OR (NOT d.path STARTS WITH "src/content/" AND NOT d.path STARTS WITH "content/")) '
)
DIRECT_RELATIONSHIPS_QUERY = (
    'MATCH (p:Entity {version:$version})-[:SUPPORTED_BY]->(d:Document {version:$version}) '
    'WHERE p.normalized IN $names AND '
    + LOCALE_FILTER
    + 'RETURN DISTINCT d.id AS id ORDER BY id LIMIT 12'
)
RELATED_RELATIONSHIPS_QUERY = (
    'MATCH (seed:Entity {version:$version})-[a:RELATES]->(t:Entity {kind:"Technology",version:$version})'
    '<-[b:RELATES]-(other:Entity {version:$version}) '
    'WHERE seed.normalized IN $names AND seed.id<>other.id '
    'AND a.version=$version AND b.version=$version '
    'MATCH (d:Document {id:b.document,version:$version}) '
    'WHERE '
    + LOCALE_FILTER
    + 'RETURN d.id AS id,count(DISTINCT t.id) AS shared ORDER BY shared DESC,id LIMIT 12'
)
SUBJECTS_QUERY = (
    'MATCH (d:Document {id:$document,version:$version}) WITH d LIMIT 1 '
    'OPTIONAL MATCH (e:Entity {version:$version}) WHERE e.kind IN ["Project","Role"] '
    'RETURN DISTINCT e.normalized AS name ORDER BY name LIMIT 3'
)


def _verify_reads(
    run: Callable[[str, dict[str, object]], Result],
    version: str,
    document_id: str,
    *,
    locales: tuple[Literal['en', 'es'], ...],
) -> None:
    subjects: list[object] = []
    for row in run(SUBJECTS_QUERY, {'version': version, 'document': document_id}):
        if len(subjects) >= 3 or set(row.keys()) != {'name'}:
            raise ValueError('invalid public graph subject')
        subjects.append(row.get('name'))
    if not subjects:
        raise ValueError('public graph projection unavailable')
    names: list[str] = []
    if subjects != [None]:
        for name in subjects:
            if not isinstance(name, str) or not 1 <= len(name) <= 256:
                raise ValueError('invalid public graph subject')
            names.append(name)
    for locale in locales:
        for query in (DIRECT_RELATIONSHIPS_QUERY, RELATED_RELATIONSHIPS_QUERY):
            run(
                query,
                {
                    'version': version,
                    'names': names,
                    'prefix': f'src/content/{locale}/',
                    'root_prefix': f'content/{locale}/',
                },
            ).consume()


def prepare_reads(session: Session, version: str, document_id: str) -> None:
    def run(text: str, parameters: dict[str, object]) -> Result:
        return session.run(Query(text, timeout=PREPARATION_TIMEOUT), parameters)

    _verify_reads(run, version, document_id, locales=('en', 'es'))


def probe_reads(session: Session, version: str, document_id: str) -> None:
    with session.begin_transaction(timeout=READ_TIMEOUT) as transaction:

        def run(text: str, parameters: dict[str, object]) -> Result:
            return transaction.run(text, parameters)

        _verify_reads(run, version, document_id, locales=('en',))
