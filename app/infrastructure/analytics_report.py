"""Consistent bounded PostgreSQL reads mapped into application-owned aggregate values."""

from collections import Counter
from datetime import UTC

from app.domain.analytics_country import country_label
from app.domain.analytics_interactions import REGIONS
from app.domain.analytics_periods import calendar_window
from app.domain.analytics_report import (
    ActivityTotals,
    AnalyticsQuery,
    CountryViews,
    DailyViews,
    HeatmapCell,
    ProductReport,
    RegionActivity,
    SectionActivity,
    SemanticActivity,
)


def read_report(connection, query: AnalyticsQuery) -> ProductReport:
    with connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        conn.execute("SET LOCAL statement_timeout='2000ms'")
        conn.execute("SET LOCAL lock_timeout='500ms'")
        observed_at = conn.execute(
            'SELECT clock_timestamp() AS observed_at'
        ).fetchone()['observed_at']
        window = calendar_window(observed_at, query.period, query.offset)
        parameters = (window.start, window.end, query.locale, query.locale)
        status = conn.execute(
            'SELECT first_observed_at,last_observed_at FROM product_collection_status WHERE singleton'
        ).fetchone()
        daily_rows = conn.execute(
            "SELECT day,sum(count)::bigint AS count FROM product_daily_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND event_name='page_view' GROUP BY day ORDER BY day",
            parameters,
        ).fetchall()
        page_rows = conn.execute(
            "SELECT section,sum(count)::bigint AS count FROM product_daily_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND event_name='page_view' GROUP BY section ORDER BY section",
            parameters,
        ).fetchall()
        action_rows = conn.execute(
            "SELECT event_name,section,locale,target,sum(count)::bigint AS count FROM product_daily_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND event_name<>'page_view' GROUP BY event_name,section,locale,target ORDER BY event_name,section,locale,target",
            parameters,
        ).fetchall()
        country_rows = conn.execute(
            "SELECT country,sum(count)::bigint AS count FROM product_daily_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND event_name='page_view' GROUP BY country ORDER BY country",
            parameters,
        ).fetchall()
        interaction_rows = conn.execute(
            "SELECT section,event_name,sum(count)::bigint AS count FROM product_interaction_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) GROUP BY section,event_name ORDER BY section,event_name",
            parameters,
        ).fetchall()
        region_rows = conn.execute(
            "SELECT region_id,event_name,sum(count)::bigint AS count FROM product_interaction_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND section=%s AND viewport=%s AND layout_revision='portfolio-v1' GROUP BY region_id,event_name ORDER BY region_id,event_name",
            (*parameters, query.section, query.viewport),
        ).fetchall()
        cell_rows = conn.execute(
            "SELECT cell_x,cell_y,sum(count)::bigint AS count FROM product_interaction_counts WHERE day>=%s AND day<%s AND (%s='all' OR locale=%s) AND section=%s AND viewport=%s AND region_id=%s AND layout_revision='portfolio-v1' AND event_name='public_click' GROUP BY cell_x,cell_y ORDER BY cell_y,cell_x",
            (*parameters, query.section, query.viewport, query.region_id),
        ).fetchall()
    countries: Counter[str] = Counter()
    for row in country_rows:
        country = country_label(row['country'])
        countries[
            'withheld' if country != 'unknown' and row['count'] < 3 else country
        ] += row['count']
    pages = {row['section']: row['count'] for row in page_rows}
    interactions = {
        (row['section'], row['event_name']): row['count'] for row in interaction_rows
    }
    regions = {
        (row['region_id'], row['event_name']): row['count'] for row in region_rows
    }
    daily = tuple(DailyViews(row['day'], row['count']) for row in daily_rows)
    return ProductReport(
        window=window,
        generated_at=observed_at.astimezone(UTC),
        first_observed_at=status['first_observed_at'] if status else None,
        last_observed_at=status['last_observed_at'] if status else None,
        totals=ActivityTotals(
            page_views=sum(row.count for row in daily),
            public_clicks=sum(
                row['count']
                for row in interaction_rows
                if row['event_name'] == 'public_click'
            ),
            section_exposures=sum(
                row['count']
                for row in interaction_rows
                if row['event_name'] == 'section_exposure'
            ),
        ),
        daily=daily,
        countries=tuple(
            CountryViews(country, count) for country, count in sorted(countries.items())
        ),
        sections=tuple(
            SectionActivity(
                section,
                pages.get(section, 0),
                interactions.get((section, 'public_click'), 0),
                interactions.get((section, 'section_exposure'), 0),
            )
            for section in REGIONS
        ),
        regions=tuple(
            RegionActivity(
                region,
                regions.get((region, 'public_click'), 0),
                regions.get((region, 'section_exposure'), 0),
            )
            for region in sorted(
                REGIONS[query.section] | {'site-header', 'site-footer'}
            )
        ),
        cells=tuple(
            HeatmapCell(row['cell_x'], row['cell_y'], row['count'])
            for row in cell_rows
            if row['count'] >= 3
        ),
        actions=tuple(
            SemanticActivity(
                row['event_name'],
                row['section'],
                row['locale'],
                row['target'] or None,
                row['count'],
            )
            for row in action_rows
        ),
        selected_region_exposures=regions.get((query.region_id, 'section_exposure'), 0),
        suppressed_cell_clicks=sum(
            row['count'] for row in cell_rows if row['count'] < 3
        ),
    )
