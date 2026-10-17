"""Transactional deduplication, global quotas and server-UTC aggregates."""

from typing import Literal

from app.domain.analytics import ProductEvent


class PostgresProductAnalytics:
    def __init__(self, connection):
        self.connection = connection

    def record(
        self, event: ProductEvent
    ) -> Literal['accepted', 'duplicate', 'limited']:
        with self.connection() as conn:
            # One bounded global lane avoids retaining IPs and makes quotas atomic.
            conn.execute("SET LOCAL statement_timeout='2000ms'")
            conn.execute("SET LOCAL lock_timeout='500ms'")
            conn.execute('SELECT pg_advisory_xact_lock(472022)')
            conn.execute(
                "DELETE FROM product_event_dedupe WHERE event_id IN (SELECT event_id FROM product_event_dedupe WHERE received_at<now()-interval '1 day' LIMIT 1000)"
            )
            conn.execute(
                "DELETE FROM product_event_counts WHERE day < (now() AT TIME ZONE 'UTC')::date-6"
            )
            if conn.execute(
                'SELECT 1 FROM product_event_dedupe WHERE event_id=%s',
                (event.event_id,),
            ).fetchone():
                return 'duplicate'
            recent = conn.execute(
                "SELECT count(*) AS count FROM product_event_dedupe WHERE received_at>=now()-interval '1 minute'"
            ).fetchone()
            daily = conn.execute(
                "SELECT coalesce(sum(count),0) AS count FROM product_event_counts WHERE day=(now() AT TIME ZONE 'UTC')::date"
            ).fetchone()
            if recent['count'] >= 60 or daily['count'] >= 10000:
                return 'limited'
            conn.execute(
                'INSERT INTO product_event_dedupe(event_id) VALUES (%s)',
                (event.event_id,),
            )
            conn.execute(
                "INSERT INTO product_event_counts(day,event_name,section,locale,target,count) VALUES ((now() AT TIME ZONE 'UTC')::date,%s,%s,%s,%s,1) ON CONFLICT (day,event_name,section,locale,target) DO UPDATE SET count=product_event_counts.count+1",
                (event.name, event.section, event.locale, event.target or ''),
            )
        return 'accepted'

    def snapshot(self):
        with self.connection() as conn:
            conn.execute("SET LOCAL statement_timeout='2000ms'")
            rows = conn.execute(
                "SELECT day::text,event_name,section,locale,target,sum(count)::bigint AS count FROM product_event_counts WHERE day >= (now() AT TIME ZONE 'UTC')::date-6 GROUP BY day,event_name,section,locale,target ORDER BY day,event_name,section,locale,target"
            ).fetchall()
            return {
                'schema_version': 1,
                'project': 'portfolio',
                'window_days': 7,
                'country': 'unknown',
                'counts': rows,
            }
