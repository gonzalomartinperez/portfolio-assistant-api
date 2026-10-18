"""Compare exact production queries on fresh, explicitly owned synthetic fixtures."""

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

import psycopg
from neo4j import GraphDatabase, Query
from neo4j.exceptions import Neo4jError
from psycopg.rows import dict_row

from app.adapters.postgres.ledger import MONTHLY_SPEND_SQL
from app.adapters.postgres.migrations import check_schema
from app.adapters.retrieval import DIRECT_RELATIONSHIPS_QUERY
from app.bootstrap.config import Settings
from scripts.evaluation_isolation import validate_targets

REPEATS = 20
WARMUPS = 5
ROWS = 100000
VERSIONS = 100
ENTITIES = 200


def statistics_ms(samples):
    return {
        'median_ms': statistics.median(samples),
        'p95_ms': sorted(samples)[math.ceil(len(samples) * 0.95) - 1],
        'min_ms': min(samples),
        'max_ms': max(samples),
        'samples_ms': samples,
    }


def pg_measure(connection):
    reads, writes = [], []
    for index in range(WARMUPS + REPEATS):
        read = connection.execute(
            'EXPLAIN (ANALYZE,BUFFERS,WAL,FORMAT JSON) ' + MONTHLY_SPEND_SQL
        ).fetchone()['QUERY PLAN'][0]
        connection.execute('SAVEPOINT benchmark_write')
        write = connection.execute(
            'EXPLAIN (ANALYZE,BUFFERS,WAL,FORMAT JSON) '
            'INSERT INTO spend_ledger(id,kind,reserved_usd,actual_usd) '
            "SELECT gen_random_uuid(),'fixture_database_benchmark',0.000010,0.000010 "
            'FROM generate_series(1,1000)'
        ).fetchone()['QUERY PLAN'][0]
        connection.execute('ROLLBACK TO SAVEPOINT benchmark_write')
        connection.execute('RELEASE SAVEPOINT benchmark_write')
        if index >= WARMUPS:
            reads.append(read)
            writes.append(write)
    return {
        'read': statistics_ms([item['Execution Time'] for item in reads]),
        'write_1000': statistics_ms([item['Execution Time'] for item in writes]),
        'read_plan': reads[-1],
        'write_plan': writes[-1],
        'index_bytes': connection.execute(
            "SELECT pg_indexes_size('spend_ledger') AS bytes"
        ).fetchone()['bytes'],
        'amount': str(connection.execute(MONTHLY_SPEND_SQL).fetchone()['amount']),
    }


def graph_hits(profile):
    return profile['dbHits'] + sum(
        graph_hits(child) for child in profile.get('children', [])
    )


def execute_graph(graph, query, **parameters):
    graph.run(Query(query, timeout=60), **parameters).consume()


def graph_measure(graph):
    parameters = {
        'version': 'benchmark-v099',
        'names': ['entity-3', 'entity-8', 'entity-13', 'entity-25', 'entity-42'],
        'prefix': 'src/content/en/',
    }
    # Diagnostic planning is separate from the application's execution timeout.
    graph.run(
        Query('EXPLAIN ' + DIRECT_RELATIONSHIPS_QUERY, timeout=30), **parameters
    ).consume()
    samples, profiles, answers, warmups = [], [], [], []
    for index in range(WARMUPS + REPEATS):
        started = time.perf_counter()
        result = graph.run(
            Query(
                'PROFILE ' + DIRECT_RELATIONSHIPS_QUERY,
                timeout=30 if index < WARMUPS else 2,
            ),
            **parameters,
        )
        answer = [record['id'] for record in result]
        profile = result.consume().profile
        if index < WARMUPS:
            warmups.append((time.perf_counter() - started) * 1000)
        else:
            samples.append((time.perf_counter() - started) * 1000)
            profiles.append(profile)
            answers.append(answer)
    if not all(answer == answers[0] for answer in answers):
        raise ValueError('graph results changed between samples')
    return {
        'read': statistics_ms(samples),
        'profile': profiles[-1],
        'db_hits': graph_hits(profiles[-1]),
        'ids': answers[0],
        'diagnostic_warmup_ms': warmups,
    }


def benchmark(config, output):
    if (
        config.ai_provider != 'fixture'
        or config.embeddings_provider != 'fixture'
        or config.allow_paid_ai
    ):
        raise ValueError('benchmark requires fixture-only configuration')
    validate_targets(config)
    report = {
        'schema_version': 1,
        'synthetic_only': True,
        'paid_calls': 0,
        'rows': ROWS,
        'versions': VERSIONS,
        'entities_per_version': ENTITIES,
        'repeats': REPEATS,
        'warmups': WARMUPS,
        'graph_diagnostic_warmup_timeout_seconds': 30,
        'graph_sample_timeout_seconds': 2,
        'source_sha256': {
            name: hashlib.sha256(
                (Path(__file__).resolve().parents[1] / name).read_bytes()
            ).hexdigest()
            for name in (
                'scripts/benchmark_database_queries.py',
                'app/adapters/neo4j/projection.py',
                'app/adapters/retrieval.py',
                'app/adapters/postgres/ledger.py',
                'migrations/008_spend_ledger_time_index.sql',
            )
        },
    }
    with (
        psycopg.connect(
            config.database_url,
            row_factory=dict_row,
            connect_timeout=5,
            options='-c statement_timeout=30000 -c lock_timeout=5000',
        ) as connection,
        GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            connection_timeout=2,
            connection_acquisition_timeout=3,
            max_connection_pool_size=2,
            max_transaction_retry_time=0,
        ) as driver,
        driver.session(database=config.neo4j_database) as graph,
    ):
        # Reject existing app data before any mutation, including index changes.
        for table in (
            'sessions',
            'knowledge_versions',
            'spend_ledger',
            'operational_executions',
        ):
            if connection.execute(
                f'SELECT EXISTS(SELECT 1 FROM {table}) AS populated'
            ).fetchone()['populated']:
                raise ValueError('benchmark requires a fresh disposable database')
        if graph.run('MATCH (n) RETURN count(n) AS count').single()['count']:
            raise ValueError('benchmark requires an empty disposable graph')
        connection.execute('SELECT pg_advisory_xact_lock(472029)')
        connection.execute('DROP INDEX spend_ledger_created_at')
        connection.execute(
            'INSERT INTO spend_ledger(id,kind,reserved_usd,actual_usd,created_at) '
            "SELECT gen_random_uuid(),'fixture_database_benchmark',0.000010,0.000010,"
            "CASE WHEN i%1000<5 THEN date_trunc('month',now(),'UTC')+interval '1 hour' "
            "ELSE date_trunc('month',now(),'UTC')-interval '60 days'+(i%30)*interval '1 day' END "
            'FROM generate_series(1,100000) AS g(i)'
        )
        connection.execute('ANALYZE spend_ledger')
        report['pg_baseline'] = pg_measure(connection)
        started = time.perf_counter()
        connection.execute(
            'CREATE INDEX spend_ledger_created_at ON spend_ledger(created_at)'
        )
        report['pg_index_build_ms'] = (time.perf_counter() - started) * 1000
        connection.execute('ANALYZE spend_ledger')
        report['pg_candidate'] = pg_measure(connection)
        if report['pg_baseline']['amount'] != report['pg_candidate']['amount']:
            raise ValueError('monthly budget result changed')
        # All PostgreSQL fixture writes, including DDL, roll back together.
        connection.rollback()
        output.write_text(json.dumps(report, indent=2) + '\n')
        for query in (
            'CREATE CONSTRAINT document_identity IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE',
            'CREATE CONSTRAINT entity_identity IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE',
        ):
            execute_graph(graph, query)
        execute_graph(graph, 'DROP INDEX entity_version_normalized IF EXISTS')
        try:
            for version in range(VERSIONS):
                execute_graph(
                    graph,
                    'UNWIND range(0,199) AS i '
                    "CREATE (e:Entity {id:$version+'-entity-'+toString(i),version:$version,normalized:'entity-'+toString(i),kind:'Project'}) "
                    "CREATE (d:Document {id:$version+'-doc-'+toString(i),version:$version,path:'src/content/en/projects.ts'}) "
                    'CREATE (e)-[:SUPPORTED_BY]->(d)',
                    version=f'benchmark-v{version:03d}',
                )
            report['neo_baseline'] = graph_measure(graph)
            started = time.perf_counter()
            execute_graph(
                graph,
                'CREATE INDEX entity_version_normalized FOR (e:Entity) ON (e.version,e.normalized)',
            )
            execute_graph(graph, 'CALL db.awaitIndexes(60)')
            report['neo_index_build_ms'] = (time.perf_counter() - started) * 1000
            report['neo_candidate'] = graph_measure(graph)
            if report['neo_baseline']['ids'] != report['neo_candidate']['ids']:
                raise ValueError('graph lookup result changed')
            output.write_text(json.dumps(report, indent=2) + '\n')
        finally:
            execute_graph(
                graph, 'MATCH (n) WHERE n.id STARTS WITH "benchmark-v" DETACH DELETE n'
            )
            execute_graph(
                graph,
                'CREATE INDEX entity_version_normalized IF NOT EXISTS FOR (e:Entity) ON (e.version,e.normalized)',
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-owned-fixtures', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.seed_owned_fixtures:
        parser.error('explicit --seed-owned-fixtures is required')
    config = Settings(_env_file=None)
    try:
        validate_targets(config)
        check_schema(
            lambda: psycopg.connect(
                config.database_url, row_factory=dict_row, connect_timeout=5
            )
        )
        benchmark(config, args.output)
    except ValueError, psycopg.Error, Neo4jError:
        parser.exit(
            1, 'Benchmark stopped: fixture prerequisites or query validation failed.\n'
        )
    print(json.dumps({'status': 'completed', 'paid_calls': 0}))


if __name__ == '__main__':
    main()
