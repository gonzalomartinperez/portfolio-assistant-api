"""Versioned aggregate read contract; validates bounded outgoing data independently."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.analytics import EventName, Section, Target
from app.domain.analytics_country import COUNTRIES
from app.domain.analytics_interactions import LayoutRevision, Region, Viewport
from app.domain.analytics_periods import Period


class StrictAggregate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ReportWindow(StrictAggregate):
    start: date
    end: date
    partial: bool


class ReportSelection(StrictAggregate):
    period: Period
    offset: int = Field(ge=0, le=2)
    section: Section
    region_id: Region
    viewport: Viewport
    locale: Literal['all', 'en', 'es']


class ReportTotals(StrictAggregate):
    page_views: int = Field(ge=0, le=310000)
    public_clicks: int = Field(ge=0, le=310000)
    section_exposures: int = Field(ge=0, le=310000)


class ReportDay(StrictAggregate):
    day: date
    count: int = Field(ge=1, le=10000)


class ReportCountry(StrictAggregate):
    country: str = Field(
        min_length=2,
        max_length=8,
        json_schema_extra={'enum': sorted(COUNTRIES | {'unknown', 'withheld'})},
    )
    count: int = Field(ge=1, le=310000)

    @field_validator('country')
    @classmethod
    def reviewed_country(cls, value: str) -> str:
        if value not in COUNTRIES and value not in ('unknown', 'withheld'):
            raise ValueError('invalid_country_label')
        return value


class ReportSection(ReportTotals):
    section: Section


class ReportRegion(StrictAggregate):
    region_id: Region
    public_clicks: int = Field(ge=0, le=310000)
    section_exposures: int = Field(ge=0, le=310000)


class ReportCell(StrictAggregate):
    x: int = Field(ge=0, le=7)
    y: int = Field(ge=0, le=7)
    count: int = Field(ge=3, le=310000)


class ReportAction(StrictAggregate):
    event_name: EventName
    section: Section
    locale: Literal['en', 'es']
    target: Target | None
    count: int = Field(ge=1, le=310000)


class ProductReportSnapshot(StrictAggregate):
    schema_version: Literal[2] = 2
    project: Literal['portfolio'] = 'portfolio'
    timezone: Literal['UTC'] = 'UTC'
    retention_days: Literal[93] = 93
    grid_size: Literal[8] = 8
    minimum_bucket: Literal[3] = 3
    coverage: Literal['received_events_only'] = 'received_events_only'
    country_collection: Literal['disabled', 'trusted_proxy_header']
    layout_revision: LayoutRevision = 'portfolio-v1'
    selection: ReportSelection
    window: ReportWindow
    generated_at: datetime
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    totals: ReportTotals
    daily: tuple[ReportDay, ...] = Field(max_length=31)
    countries: tuple[ReportCountry, ...] = Field(max_length=251)
    sections: tuple[ReportSection, ...] = Field(max_length=8)
    regions: tuple[ReportRegion, ...] = Field(max_length=7)
    cells: tuple[ReportCell, ...] = Field(max_length=64)
    actions: tuple[ReportAction, ...] = Field(max_length=128)
    selected_region_exposures: int = Field(ge=0, le=310000)
    suppressed_cell_clicks: int = Field(ge=0, le=310000)
