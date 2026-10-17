"""Real query plans and results, without hardware-sensitive latency gates."""

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from neo4j import GraphDatabase, Query

from app.bootstrap.config import settings
from app.infrastructure.db import connect
from app.infrastructure.knowledge import DIRECT_RELATIONSHIPS_QUERY
from app.infrastructure.ledger import MONTHLY_SPEND_SQL

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1', reason='isolated stores required'
    ),
]


def plan_nodes(plan):
    yield plan
    for child in plan.get('Plans', []):
        yield from plan_nodes(child)


def test_monthly_admission_uses_time_index_and_preserves_unsettled_cost():
    with connect() as conn:
        index = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND indexname='spend_ledger_created_at'"
        ).fetchone()
        assert index and '(created_at)' in index['indexdef']
        # Copy real migration-defined indexes; temporary rows never enter the budget ledger.
        conn.execute(
            'CREATE TEMP TABLE ledger_plan_probe (LIKE spend_ledger INCLUDING ALL) ON COMMIT DROP'
        )
        conn.execute(
            'INSERT INTO ledger_plan_probe(id,kind,reserved_usd,actual_usd,created_at) '
            "SELECT gen_random_uuid(),'embedding_index',0.000020,CASE WHEN i%2=0 THEN NULL ELSE 0.000010 END,"
            "CASE WHEN i%1000=0 THEN date_trunc('month',now(),'UTC') ELSE date_trunc('month',now(),'UTC')-interval '60 days' END "
            'FROM generate_series(1,50000) AS g(i)'
        )
        conn.execute('ANALYZE ledger_plan_probe')
        query = MONTHLY_SPEND_SQL.replace('spend_ledger', 'ledger_plan_probe')
        plan = conn.execute('EXPLAIN (FORMAT JSON) ' + query).fetchone()['QUERY PLAN'][
            0
        ]['Plan']
        assert any('Index' in node['Node Type'] for node in plan_nodes(plan))
        assert not any(node['Node Type'] == 'Seq Scan' for node in plan_nodes(plan))
        assert conn.execute(query).fetchone()['amount'] == Decimal('0.001000')


def test_versioned_graph_lookup_avoids_history_scan_and_keeps_support():
    config = settings()
    prefix = 'query-plan-' + uuid4().hex + '-'
    with (
        GraphDatabase.driver(
            config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
        ) as driver,
        driver.session(database=config.neo4j_database) as graph,
    ):
        indexes = list(
            graph.run(
                'SHOW INDEXES YIELD name,state WHERE name=$name RETURN name,state',
                name='entity_version_normalized',
            )
        )
        assert indexes and indexes[0]['state'] == 'ONLINE'
        try:
            graph.run(
                'UNWIND range(0,8191) AS i '
                "CREATE (e:Entity {id:$prefix+'entity-'+toString(i),version:$prefix+toString(toInteger(i/128)),normalized:'lookup-'+toString(i%128)}) "
                "MERGE (d:Document {id:$prefix+'doc-'+toString(toInteger(i/128))}) "
                "ON CREATE SET d.version=$prefix+toString(toInteger(i/128)),d.path='src/content/en/profile.ts' "
                'CREATE (e)-[:SUPPORTED_BY]->(d)',
                prefix=prefix,
            ).consume()
            parameters = {
                'version': prefix + '63',
                'names': ['lookup-3'],
                'prefix': 'src/content/en/',
            }
            # Bulk fixture insertion bypasses writer population; refresh native statistics.
            graph.run('CALL db.prepareForReplanning(30)').consume()
            # Compile separately; retain the production two-second execution limit.
            graph.run(
                Query('EXPLAIN ' + DIRECT_RELATIONSHIPS_QUERY, timeout=10), **parameters
            ).consume()
            result = graph.run(
                Query('PROFILE ' + DIRECT_RELATIONSHIPS_QUERY, timeout=2), **parameters
            )
            assert [record['id'] for record in result] == [prefix + 'doc-63']
            profile = result.consume().profile

            def hits(node):
                return node['dbHits'] + sum(
                    hits(child) for child in node.get('children', [])
                )

            # A missing lookup index scans 8,192 fixture entities (>16k DB hits).
            assert hits(profile) < 1000
        finally:
            graph.run(
                'MATCH (n) WHERE n.id STARTS WITH $prefix DETACH DELETE n',
                prefix=prefix,
            ).consume()
