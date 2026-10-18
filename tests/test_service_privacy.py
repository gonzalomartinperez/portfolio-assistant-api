"""Keep vendor usage reporting separate from authorized private observability."""

import os
from pathlib import Path

import pytest
import yaml
from neo4j import GraphDatabase

from app.bootstrap.config import settings


@pytest.mark.parametrize('scope', ['local', 'database', 'container'])
def test_neo4j_usage_reporting_is_explicitly_disabled(scope):
    if scope == 'local':
        config = yaml.safe_load(Path('infra/compose/local.yaml').read_text())
    else:
        config = yaml.safe_load(Path('.github/workflows/quality.yml').read_text())[
            'jobs'
        ][scope]
    environment = config['services']['neo4j'].get('environment') or config['services'][
        'neo4j'
    ].get('env', {})
    assert environment.get('NEO4J_dbms_usage__report_enabled') == 'false'
    assert environment.get('NEO4J_server_bolt_telemetry_enabled') == 'false'


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='requires isolated Neo4j fixture'
)
def test_neo4j_effective_vendor_reporting_settings_are_disabled():
    config = settings()
    names = ['dbms.usage_report.enabled', 'server.bolt.telemetry.enabled']
    with (
        GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            max_transaction_retry_time=0,
        ) as driver,
        driver.session(database=config.neo4j_database) as session,
    ):
        values = {
            row['name']: row['value']
            for row in session.run(
                'SHOW SETTINGS YIELD name,value WHERE name IN $names RETURN name,value',
                names=names,
            )
        }
    assert values == {name: 'false' for name in names}
