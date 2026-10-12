"""Reviewed graph projection. Labels/relationship types are fixed, values parameterized."""

import hashlib

from app.domain.graph import facts


def project(graph, version, records, documents, *, explicit_facts=None):
    graph.run(
        'CREATE CONSTRAINT document_identity IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE'
    ).consume()
    graph.run(
        'CREATE CONSTRAINT entity_identity IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE'
    ).consume()

    def write(tx):
        tx.run(
            'MATCH (n:Document {version:$version}) DETACH DELETE n', version=version
        ).consume()
        tx.run(
            'MATCH (n:Entity {version:$version}) DETACH DELETE n', version=version
        ).consume()
        tx.run(
            'UNWIND $records AS row CREATE (:Document {id:row.id,version:$version,title:row.title,url:row.url,path:row.path})',
            version=version,
            records=[
                {'id': r['id'], 'title': r['title'], 'url': r['url'], 'path': r['path']}
                for r in records
            ],
        ).consume()
        count = 0
        for path, content in documents.items():
            for fact in (
                facts(path, content)
                if explicit_facts is None
                else explicit_facts.get(path, ())
            ):
                supports = [
                    r
                    for r in records
                    if r['path'] == path
                    and r['start_line'] <= fact.end_line
                    and r['end_line'] >= fact.start_line
                ]
                subject = hashlib.sha256(
                    f'{version}:{fact.subject_kind}:{fact.subject.lower()}'.encode()
                ).hexdigest()
                target = hashlib.sha256(
                    f'{version}:{fact.object_kind}:{fact.object.lower()}'.encode()
                ).hexdigest()
                tx.run(
                    'MERGE (s:Entity {id:$id}) SET s.version=$version,s.kind=$kind,s.name=$name,s.normalized=$normalized',
                    id=subject,
                    version=version,
                    kind=fact.subject_kind,
                    name=fact.subject,
                    normalized=fact.subject.lower(),
                ).consume()
                tx.run(
                    'MERGE (o:Entity {id:$id}) SET o.version=$version,o.kind=$kind,o.name=$name,o.normalized=$normalized',
                    id=target,
                    version=version,
                    kind=fact.object_kind,
                    name=fact.object,
                    normalized=fact.object.lower(),
                ).consume()
                for record in supports:
                    tx.run(
                        'MATCH (s:Entity {id:$subject}),(o:Entity {id:$target}),(d:Document {id:$document}) '
                        'MERGE (s)-[r:RELATES {predicate:$predicate,document:$document}]->(o) '
                        'SET r.version=$version,r.url=$url,r.start_line=$start,r.end_line=$end '
                        'MERGE (s)-[:SUPPORTED_BY]->(d) MERGE (o)-[:SUPPORTED_BY]->(d)',
                        subject=subject,
                        target=target,
                        document=record['id'],
                        predicate=fact.predicate,
                        version=version,
                        url=record['url'],
                        start=fact.start_line,
                        end=fact.end_line,
                    ).consume()
                count += 1
        projected = tx.run(
            'MATCH (d:Document {version:$version}) RETURN count(d) AS n',
            version=version,
        ).single()['n']
        if projected != len(records):
            raise RuntimeError('graph projection incomplete')
        return count

    return graph.execute_write(write)
