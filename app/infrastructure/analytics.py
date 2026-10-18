"""Transactional deduplication, global quotas and server-UTC aggregates."""

from datetime import datetime
from typing import Literal

from psycopg import sql

from app.domain.analytics import ProductEvent
from app.domain.analytics_country import country_label
from app.domain.analytics_interactions import PublicInteraction
from app.domain.analytics_report import AnalyticsQuery, ProductReport
from app.infrastructure.analytics_report import read_report


def prune_product_counts(conn) -> None:
    conn.execute(
        "DELETE FROM product_event_counts WHERE day < (now() AT TIME ZONE 'UTC')::date-6"
    )
    for table in ('product_daily_counts', 'product_interaction_counts'):
        conn.execute(
            sql.SQL(
                "DELETE FROM {} WHERE ctid IN (SELECT ctid FROM {} WHERE day < (now() AT TIME ZONE 'UTC')::date-92 LIMIT 1000)"
            ).format(sql.Identifier(table), sql.Identifier(table))
        )


class PostgresProductAnalytics:
    def __init__(self, connection):
        self.connection = connection

    def record(
        self, event: ProductEvent | PublicInteraction, country: str = 'unknown'
    ) -> Literal['accepted', 'duplicate', 'limited']:
        with self.connection() as conn:
            # One bounded global lane avoids retaining IPs and makes quotas atomic.
            conn.execute("SET LOCAL statement_timeout='2000ms'")
            conn.execute("SET LOCAL lock_timeout='500ms'")
            conn.execute('SELECT pg_advisory_xact_lock(472022)')
            conn.execute(
                "DELETE FROM product_event_dedupe WHERE event_id IN (SELECT event_id FROM product_event_dedupe WHERE received_at<now()-interval '1 day' LIMIT 1000)"
            )
            prune_product_counts(conn)
            conn.execute(
                "DELETE FROM product_event_dedupe WHERE event_id=%s AND received_at<now()-interval '1 day'",
                (event.event_id,),
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
                "SELECT (SELECT coalesce(sum(count),0) FROM product_event_counts WHERE day=(now() AT TIME ZONE 'UTC')::date)+(SELECT coalesce(sum(count),0) FROM product_interaction_counts WHERE day=(now() AT TIME ZONE 'UTC')::date) AS count"
            ).fetchone()
            if recent['count'] >= 60 or daily['count'] >= 10000:
                return 'limited'
            conn.execute(
                'INSERT INTO product_event_dedupe(event_id) VALUES (%s)',
                (event.event_id,),
            )
            if isinstance(event, ProductEvent):
                conn.execute(
                    "INSERT INTO product_event_counts(day,event_name,section,locale,target,count) VALUES ((now() AT TIME ZONE 'UTC')::date,%s,%s,%s,%s,1) ON CONFLICT (day,event_name,section,locale,target) DO UPDATE SET count=product_event_counts.count+1",
                    (event.name, event.section, event.locale, event.target or ''),
                )
                conn.execute(
                    "INSERT INTO product_daily_counts(day,event_name,section,locale,target,country,count) VALUES ((now() AT TIME ZONE 'UTC')::date,%s,%s,%s,%s,%s,1) ON CONFLICT (day,event_name,section,locale,target,country) DO UPDATE SET count=product_daily_counts.count+1",
                    (
                        event.name,
                        event.section,
                        event.locale,
                        event.target or '',
                        country_label(country)
                        if event.name == 'page_view'
                        else 'unknown',
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO product_interaction_counts(day,event_name,section,locale,region_id,layout_revision,viewport,cell_x,cell_y,count) VALUES ((now() AT TIME ZONE 'UTC')::date,%s,%s,%s,%s,%s,%s,%s,%s,1) ON CONFLICT (day,event_name,section,locale,region_id,layout_revision,viewport,cell_x,cell_y) DO UPDATE SET count=product_interaction_counts.count+1",
                    (
                        event.name,
                        event.section,
                        event.locale,
                        event.region_id,
                        event.layout_revision,
                        event.viewport,
                        event.cell_x if event.cell_x is not None else -1,
                        event.cell_y if event.cell_y is not None else -1,
                    ),
                )
            conn.execute(
                'INSERT INTO product_collection_status(singleton,first_observed_at,last_observed_at) VALUES (true,now(),now()) ON CONFLICT(singleton) DO UPDATE SET last_observed_at=excluded.last_observed_at'
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

    def report(self, query: AnalyticsQuery, now: datetime) -> ProductReport:
        return read_report(self.connection, query, now)
