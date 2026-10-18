"""Real restricted persistence, HTTP compatibility, suppression and shared quotas."""

import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.domain.analytics import ProductEvent
from app.domain.analytics_periods import calendar_window
from app.infrastructure import migrations
from app.infrastructure.analytics import PostgresProductAnalytics
from scripts.project_postgres_fixture import project_fixture

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires owned local project database image',
    ),
]


def migrate_project(target, monkeypatch):
    migrator = Settings(
        _env_file=None,
        database_url=target.connection_info('portfolio_api_migrator'),
    )
    monkeypatch.setattr(migrations, 'settings', lambda: migrator)
    monkeypatch.setattr(
        migrations,
        'connect',
        lambda: psycopg.connect(migrator.database_url, row_factory=dict_row),
    )
    migrations.main()
    migrations.main()
    target.sql_as(
        'portfolio_api_migrator', Path('deploy/runtime-grants.sql').read_text()
    )
    return migrator


def test_real_interaction_and_legacy_routes_have_bounded_private_calendar_reports(
    monkeypatch,
):
    image = os.getenv('PROJECT_POSTGRES_IMAGE', 'portfolio-assistant-postgres:18.6')
    with project_fixture(image, authorized=True) as target:
        migrator = migrate_project(target, monkeypatch)
        token = 'synthetic-product-v2-read-token-000000'
        config = migrator.model_copy(
            update={
                'database_url': target.connection_info('portfolio_api_runtime'),
                'product_analytics_enabled': True,
                'product_analytics_country_enabled': True,
                'product_analytics_country_proxy_ips': '127.0.0.1',
                'ops_read_token': token,
                'ops_api_commit': 'a' * 40,
                'neo4j_uri': 'bolt://127.0.0.1:1',
            }
        )
        origin = {'Origin': 'http://localhost:3000'}
        authorization = {'Authorization': 'Bearer ' + token}
        with TestClient(create_app(config), client=('127.0.0.1', 50000)) as http:

            def send(name, **changes):
                body = {
                    'schema_version': 2,
                    'project': 'portfolio',
                    'source': 'site',
                    'event_id': str(uuid4()),
                    'event_name': name,
                    'section': 'home',
                    'locale': 'en',
                    'region_id': 'home-featured',
                    'layout_revision': 'portfolio-v1',
                    'viewport': 'desktop',
                    **changes,
                }
                return http.post(
                    '/api/v1/analytics/events', headers=origin, json=body
                ), body

            for _ in range(3):
                response, body = send('public_click', cell_x=0, cell_y=7)
                assert response.status_code == 204
            assert (
                http.post(
                    '/api/v1/analytics/events', headers=origin, json=body
                ).status_code
                == 204
            )
            assert send('public_click', cell_x=1, cell_y=1)[0].status_code == 204
            for _ in range(2):
                assert send('section_exposure')[0].status_code == 204
            for country in ('AR', 'AR', 'AR', 'US', 'XX'):
                response = http.post(
                    '/api/v1/analytics/events',
                    headers={**origin, 'CF-IPCountry': country},
                    json={
                        'schema_version': 1,
                        'project': 'portfolio',
                        'source': 'site',
                        'event_id': str(uuid4()),
                        'event_name': 'page_view',
                        'section': 'home',
                        'locale': 'en',
                    },
                )
                assert response.status_code == 204
            action = http.post(
                '/api/v1/analytics/events',
                headers=origin,
                json={
                    'schema_version': 1,
                    'project': 'portfolio',
                    'source': 'site',
                    'event_id': str(uuid4()),
                    'event_name': 'cv_link_open',
                    'section': 'cv',
                    'locale': 'es',
                    'target': 'en',
                },
            )
            assert action.status_code == 204
            assert http.get('/internal/ops/v2/product-analytics').status_code == 401
            detailed = http.get(
                '/internal/ops/v2/product-analytics', headers=authorization
            )
            assert detailed.status_code == 200
            assert 'no-store' in detailed.headers['cache-control']
            assert len(detailed.content) < 256000
            report = detailed.json()
            assert report['timezone'] == 'UTC' and report['window']['partial']
            assert report['totals'] == {
                'page_views': 5,
                'public_clicks': 4,
                'section_exposures': 2,
            }
            assert report['countries'] == [
                {'country': 'AR', 'count': 3},
                {'country': 'unknown', 'count': 1},
                {'country': 'withheld', 'count': 1},
            ]
            assert report['cells'] == [{'x': 0, 'y': 7, 'count': 3}]
            assert report['suppressed_cell_clicks'] == 1
            assert report['selected_region_exposures'] == 2
            assert report['actions'] == [
                {
                    'event_name': 'cv_link_open',
                    'section': 'cv',
                    'locale': 'es',
                    'target': 'en',
                    'count': 1,
                }
            ]
            legacy = http.get(
                '/internal/ops/v1/product-analytics', headers=authorization
            )
            assert legacy.status_code == 200 and legacy.json()['schema_version'] == 1
            assert (
                legacy.json()['window_days'] == 7
                and sum(row['count'] for row in legacy.json()['counts']) == 6
            )
            for suffix in (
                '?region_id=contact-channels',
                '?offset=3',
                '?period=rolling30',
                '?secret=raw',
                '?locale=en&locale=es',
            ):
                assert (
                    http.get(
                        '/internal/ops/v2/product-analytics' + suffix,
                        headers=authorization,
                    ).status_code
                    == 422
                )
            previous = calendar_window(datetime.now(UTC), 'month', 1)
            with psycopg.connect(
                target.connection_info('portfolio_api_migrator')
            ) as connection:
                connection.execute(
                    "INSERT INTO product_daily_counts VALUES (%s,'page_view','about','es','','unknown',12)",
                    (previous.start,),
                )
                connection.execute(
                    "INSERT INTO product_daily_counts VALUES (%s,'page_view','about','es','','unknown',7)",
                    (previous.end,),
                )
                today = datetime.now(UTC).date()
                for age in (92, 93):
                    connection.execute(
                        "INSERT INTO product_daily_counts VALUES (%s,'page_view','contact','en','','unknown',1)",
                        (today - timedelta(days=age),),
                    )
            history = http.get(
                '/internal/ops/v2/product-analytics?period=month&offset=1',
                headers=authorization,
            )
            assert history.status_code == 200
            assert history.json()['window'] == {
                'start': previous.start.isoformat(),
                'end': previous.end.isoformat(),
                'partial': False,
            }
            assert history.json()['totals']['page_views'] == 12
            before_limited = http.get(
                '/internal/ops/v2/product-analytics', headers=authorization
            ).json()['totals']
            with psycopg.connect(
                target.connection_info('portfolio_api_migrator')
            ) as connection:
                columns = connection.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='product_interaction_counts'"
                ).fetchall()
                assert {row[0] for row in columns} == {
                    'day',
                    'event_name',
                    'section',
                    'locale',
                    'region_id',
                    'layout_revision',
                    'viewport',
                    'cell_x',
                    'cell_y',
                    'count',
                }
                connection.execute(
                    'INSERT INTO product_event_dedupe(event_id) SELECT gen_random_uuid() FROM generate_series(1,60)'
                )
            assert send('section_exposure')[0].status_code == 429
            rejected = http.get(
                '/internal/ops/v2/product-analytics', headers=authorization
            )
            assert rejected.json()['totals'] == before_limited
            with psycopg.connect(
                target.connection_info('portfolio_api_migrator')
            ) as connection:
                retained = connection.execute(
                    "SELECT day FROM product_daily_counts WHERE section='contact' ORDER BY day"
                ).fetchall()
                assert retained == [(today - timedelta(days=92),)]
            before_restore = rejected.json()
        archive = target.dump('portfolio_assistant')
        target.restore('portfolio_assistant', archive)
        target.sql_as(
            'portfolio_api_migrator', Path('deploy/runtime-grants.sql').read_text()
        )
        with TestClient(create_app(config), client=('127.0.0.1', 50000)) as restored:
            response = restored.get(
                '/internal/ops/v2/product-analytics', headers=authorization
            )
            assert response.status_code == 200
            after_restore = response.json()
            for key in (
                'totals',
                'daily',
                'countries',
                'sections',
                'regions',
                'cells',
                'actions',
                'first_observed_at',
                'last_observed_at',
            ):
                assert after_restore[key] == before_restore[key]


def test_reversed_transaction_order_preserves_observation_extrema_and_accepts_both(
    monkeypatch,
):
    image = os.getenv('PROJECT_POSTGRES_IMAGE', 'portfolio-assistant-postgres:18.6')
    with project_fixture(image, authorized=True) as target:
        migrate_project(target, monkeypatch)
        connection_info = target.connection_info('portfolio_api_runtime')

        def connection():
            return psycopg.connect(connection_info, row_factory=dict_row)

        with connection() as older:
            first = older.execute('SELECT now() AS instant').fetchone()['instant']
            older.execute('SELECT pg_sleep(0.01)')
            store = PostgresProductAnalytics(connection)
            assert (
                store.record(ProductEvent(str(uuid4()), 'page_view', 'about', 'es'))
                == 'accepted'
            )
            with connection() as check:
                newer = check.execute(
                    'SELECT first_observed_at FROM product_collection_status'
                ).fetchone()['first_observed_at']
            assert first < newer

            @contextmanager
            def earlier_transaction():
                yield older

            assert (
                PostgresProductAnalytics(earlier_transaction).record(
                    ProductEvent(str(uuid4()), 'page_view', 'about', 'es')
                )
                == 'accepted'
            )
        with connection() as check:
            row = check.execute(
                'SELECT first_observed_at,last_observed_at FROM product_collection_status'
            ).fetchone()
            assert row == {'first_observed_at': first, 'last_observed_at': newer}
            assert (
                check.execute(
                    'SELECT sum(count) AS amount FROM product_daily_counts'
                ).fetchone()['amount']
                == 2
            )
