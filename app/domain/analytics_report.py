"""Aggregate observations; they do not establish visitor identity or attention."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.domain.analytics import EventName, Section, Target
from app.domain.analytics_interactions import REGIONS, SHELL_REGIONS, Region, Viewport
from app.domain.analytics_periods import CalendarWindow, Period


@dataclass(frozen=True)
class AnalyticsQuery:
    period: Period = 'month'
    offset: int = 0
    section: Section = 'home'
    region_id: Region = 'home-featured'
    viewport: Viewport = 'desktop'
    locale: Literal['all', 'en', 'es'] = 'all'

    def __post_init__(self) -> None:
        if (
            self.period not in ('day', 'week', 'month')
            or type(self.offset) is not int
            or not 0 <= self.offset <= 2
            or self.section not in REGIONS
            or self.region_id not in REGIONS[self.section] | SHELL_REGIONS
            or self.viewport not in ('mobile', 'tablet', 'desktop')
            or self.locale not in ('all', 'en', 'es')
        ):
            raise ValueError('invalid_analytics_query')


@dataclass(frozen=True)
class ActivityTotals:
    page_views: int
    public_clicks: int
    section_exposures: int


@dataclass(frozen=True)
class DailyViews:
    day: date
    count: int


@dataclass(frozen=True)
class CountryViews:
    country: str
    count: int


@dataclass(frozen=True)
class SectionActivity:
    section: Section
    page_views: int
    public_clicks: int
    section_exposures: int


@dataclass(frozen=True)
class RegionActivity:
    region_id: Region
    public_clicks: int
    section_exposures: int


@dataclass(frozen=True)
class HeatmapCell:
    x: int
    y: int
    count: int


@dataclass(frozen=True)
class SemanticActivity:
    event_name: EventName
    section: Section
    locale: Literal['en', 'es']
    target: Target | None
    count: int


@dataclass(frozen=True)
class ProductReport:
    window: CalendarWindow
    generated_at: datetime
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    totals: ActivityTotals
    daily: tuple[DailyViews, ...]
    countries: tuple[CountryViews, ...]
    sections: tuple[SectionActivity, ...]
    regions: tuple[RegionActivity, ...]
    cells: tuple[HeatmapCell, ...]
    actions: tuple[SemanticActivity, ...]
    selected_region_exposures: int
    suppressed_cell_clicks: int
