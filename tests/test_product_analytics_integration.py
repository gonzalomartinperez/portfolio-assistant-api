"""Real isolated PostgreSQL guarantees; run only in the explicit integration lane."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.domain.analytics import ProductEvent
from app.infrastructure.analytics import PostgresProductAnalytics
from app.infrastructure.db import connect

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1', reason='requires isolated PostgreSQL'
    ),
]


def test_product_counts_atomic_duplicate_replay_and_no_raw_payload():
    event = ProductEvent(str(uuid4()), 'page_view', 'education', 'es')
    store = PostgresProductAnalytics(connect)
    with connect() as conn:
        before = conn.execute(
            "SELECT coalesce(sum(count),0) AS count FROM product_event_counts WHERE day=(now() AT TIME ZONE 'UTC')::date AND event_name='page_view' AND section='education' AND locale='es'"
        ).fetchone()['count']
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            outcomes = list(executor.map(lambda _: store.record(event), range(12)))
        assert outcomes.count('accepted') == 1
        assert outcomes.count('duplicate') == 11
        from fastapi.testclient import TestClient

        from app.bootstrap.config import Settings
        from app.bootstrap.container import create_app

        token = 'synthetic-private-product-token-0000'
        application = create_app(
            Settings(
                _env_file=None,
                product_analytics_enabled=True,
                ops_read_token=token,
                ops_api_commit='a' * 40,
            )
        )
        application.state.product_analytics = store
        client = TestClient(application)
        replay = client.post(
            '/api/v1/analytics/events',
            headers={'Origin': 'http://localhost:3000'},
            json={
                'schema_version': 1,
                'project': 'portfolio',
                'source': 'site',
                'event_id': event.event_id,
                'event_name': event.name,
                'section': event.section,
                'locale': event.locale,
            },
        )
        assert replay.status_code == 204
        response = client.get(
            '/internal/ops/v1/product-analytics',
            headers={'Authorization': 'Bearer ' + token},
        )
        assert response.status_code == 200
        data = response.json()
        rows = [
            row
            for row in data['counts']
            if row['section'] == 'education'
            and row['locale'] == 'es'
            and row['event_name'] == 'page_view'
        ]
        assert sum(row['count'] for row in rows) == before + 1
        assert event.event_id not in str(data)
        assert data['country'] == 'unknown'
    finally:
        with connect() as conn:
            conn.execute(
                'DELETE FROM product_event_dedupe WHERE event_id=%s', (event.event_id,)
            )
            conn.execute(
                "DELETE FROM product_event_counts WHERE day=(now() AT TIME ZONE 'UTC')::date AND event_name='page_view' AND section='education' AND locale='es' AND target='' AND count=1"
            )
            conn.execute(
                "UPDATE product_event_counts SET count=count-1 WHERE day=(now() AT TIME ZONE 'UTC')::date AND event_name='page_view' AND section='education' AND locale='es' AND target='' AND count>1"
            )


def test_product_global_quota_rollback_and_expiry():
    ids = [str(uuid4()) for _ in range(61)]
    store = PostgresProductAnalytics(connect)
    try:
        with connect() as conn:
            for identifier in ids[:60]:
                conn.execute(
                    'INSERT INTO product_event_dedupe(event_id) VALUES (%s)',
                    (identifier,),
                )
            conn.execute(
                "UPDATE product_event_dedupe SET received_at=now()-interval '2 days' WHERE event_id=%s",
                (ids[0],),
            )
            conn.execute(
                'INSERT INTO product_event_dedupe(event_id) VALUES (%s)', (ids[60],)
            )
        assert (
            store.record(ProductEvent(str(uuid4()), 'page_view', 'home', 'en'))
            == 'limited'
        )
        assert (
            store.record(ProductEvent(ids[1], 'page_view', 'home', 'en')) == 'duplicate'
        )
        with connect() as conn:
            assert (
                conn.execute(
                    'SELECT 1 FROM product_event_dedupe WHERE event_id=%s', (ids[0],)
                ).fetchone()
                is None
            )
    finally:
        with connect() as conn:
            conn.execute(
                'DELETE FROM product_event_dedupe WHERE event_id=ANY(%s::uuid[])',
                (ids,),
            )


def test_product_daily_ceiling_does_not_record_a_rejected_event():
    from contextlib import contextmanager

    event = ProductEvent(str(uuid4()), 'page_view', 'stack', 'es')
    with connect() as conn, conn.transaction(force_rollback=True):
        conn.execute(
            "INSERT INTO product_event_counts(day,event_name,section,locale,target,count) VALUES ((now() AT TIME ZONE 'UTC')::date,'page_view','stack','es','',10000) ON CONFLICT (day,event_name,section,locale,target) DO UPDATE SET count=10000"
        )

        @contextmanager
        def transaction_connection():
            yield conn

        assert (
            PostgresProductAnalytics(transaction_connection).record(event) == 'limited'
        )
        assert (
            conn.execute(
                'SELECT 1 FROM product_event_dedupe WHERE event_id=%s',
                (event.event_id,),
            ).fetchone()
            is None
        )
