import json
import os
from pathlib import Path

import pytest

from app.domain.graph import facts


def test_graph_facts_are_explicit_and_keep_supporting_line_spans():
    source = 'slug: "demo",\nname: "Demo",\nstack: technologyNames([\n"Python",\n"PostgreSQL",\n]),'
    edges = facts('src/content/en/projects.ts', source)
    uses = [edge for edge in edges if edge.predicate == 'USES']
    assert [(e.subject, e.object, e.start_line, e.end_line) for e in uses] == [
        ('Demo', 'Python', 2, 4),
        ('Demo', 'PostgreSQL', 2, 5),
    ]
    assert facts('private/experience.ts', 'Nothing explicit') == ()
    assert facts('README.md', 'Demo might use Java') == ()


@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='requires real seeded indexes'
)
def test_hybrid_retrieval_evaluation_and_relationship_provenance():
    from neo4j import GraphDatabase

    from app.bootstrap.config import settings
    from app.infrastructure.db import connect
    from tests.support import retrieve

    for case in json.loads(Path('evals/retrieval.json').read_text()):
        rows, _ = retrieve(case['question'], case['locale'])
        if not case['paths']:
            assert not rows, case['id']
            continue
        assert set(case['paths']) <= {r['path'] for r in rows}, case['id']
        for needle in case['contains']:
            assert needle in '\n'.join(r['content'] for r in rows), case['id']
    with connect() as conn:
        version = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
        ids = {
            r['id']
            for r in conn.execute(
                'SELECT id FROM chunks WHERE knowledge_version=%s', (version,)
            )
        }
    config = settings()
    with (
        GraphDatabase.driver(
            config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
        ) as driver,
        driver.session() as graph,
    ):
        edges = list(
            graph.run(
                'MATCH (:Entity)-[r:RELATES {version:$version}]->(:Entity) RETURN r.document AS document,r.url AS url,r.start_line AS start,r.end_line AS end',
                version=version,
            )
        )
        assert edges
        assert all(
            e['document'] in ids and '#L' in e['url'] and e['start'] <= e['end']
            for e in edges
        )
        shared = graph.run(
            'MATCH (p:Entity {name:"Filomena",version:$version})-[:RELATES]->(t:Entity {kind:"Technology"})<-[:RELATES]-(r:Entity {kind:"Role",version:$version}) RETURN count(DISTINCT r.id) AS n',
            version=version,
        ).single()['n']
        assert shared > 0


def test_source_rejects_unapproved_remote_and_option_ref(tmp_path):
    import subprocess

    from app.infrastructure.indexing import _sync

    repo = tmp_path / 'source'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            'remote',
            'add',
            'origin',
            'http://169.254.169.254/private',
        ],
        check=True,
    )
    with pytest.raises(ValueError, match='only the public'):
        _sync(repo, '--help')
