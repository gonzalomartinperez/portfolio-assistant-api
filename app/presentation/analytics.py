"""Anonymous public ingestion and separately authorized aggregate reads."""

from dataclasses import asdict
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.application.analytics import accept_event, read_product_report
from app.domain.analytics import EventName, ProductEvent, Section, Target
from app.domain.analytics_interactions import Region, Viewport
from app.domain.analytics_periods import Period
from app.domain.analytics_report import AnalyticsQuery
from app.presentation.analytics_country import country_from_edge
from app.presentation.analytics_report_models import ProductReportSnapshot
from app.presentation.interaction_models import ProductInteractionBody
from app.presentation.operations import authorize

router = APIRouter()


class ProductEventBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[1]
    project: Literal['portfolio']
    source: Literal['site']
    event_id: str = Field(
        pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
    )
    event_name: EventName
    section: Section
    locale: Literal['en', 'es']
    target: Target | None = None

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value: object) -> int:
        if type(value) is not int or value != 1:
            raise ValueError('invalid_analytics_version')
        return 1

    def event(self) -> ProductEvent:
        return ProductEvent(
            str(UUID(self.event_id)),
            self.event_name,
            self.section,
            self.locale,
            self.target,
        )

    @model_validator(mode='after')
    def semantic_dimensions(self):
        self.event()
        return self


class ProductCount(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    day: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    event_name: EventName
    section: Section
    locale: Literal['en', 'es']
    target: str = Field(max_length=32)
    count: int = Field(ge=1, le=10000)


class ProductSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[1]
    project: Literal['portfolio']
    window_days: Literal[7]
    country: Literal['unknown']
    counts: list[ProductCount] = Field(max_length=4000)


def enabled(request: Request):
    if not request.app.state.config.product_analytics_enabled:
        raise HTTPException(404, 'analytics_disabled')


@router.post(
    '/api/v1/analytics/events',
    status_code=204,
    operation_id='recordProductEvent',
    dependencies=[Depends(enabled)],
)
def record(request: Request, body: ProductEventBody | ProductInteractionBody):
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'invalid_content_type')
    # Do not attach anonymous events to an authenticated session by accident.
    if request.headers.get('cookie') or request.headers.get('authorization'):
        raise HTTPException(400, 'analytics_credentials_forbidden')
    accept_event(
        request.app.state.product_analytics, body.event(), country_from_edge(request)
    )
    return Response(status_code=204)


@router.get(
    '/internal/ops/v1/product-analytics',
    response_model=ProductSnapshot,
    include_in_schema=False,
    dependencies=[Depends(authorize), Depends(enabled)],
)
def aggregates(request: Request):
    return request.app.state.product_analytics.snapshot()


@router.get(
    '/internal/ops/v2/product-analytics',
    response_model=ProductReportSnapshot,
    include_in_schema=False,
    dependencies=[Depends(authorize), Depends(enabled)],
)
def detailed_aggregates(
    request: Request,
    period: Period = 'month',
    offset: int = Query(default=0, ge=0, le=2),
    section: Section = 'home',
    region_id: Region = 'home-featured',
    viewport: Viewport = 'desktop',
    locale: Literal['all', 'en', 'es'] = 'all',
):
    keys = {'period', 'offset', 'section', 'region_id', 'viewport', 'locale'}
    if any(
        key not in keys or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(422, 'invalid_analytics_selection')
    try:
        selection = AnalyticsQuery(period, offset, section, region_id, viewport, locale)
    except ValueError:
        raise HTTPException(422, 'invalid_analytics_selection') from None
    report = read_product_report(request.app.state.product_analytics, selection)
    return ProductReportSnapshot.model_validate(
        {
            **asdict(report),
            'selection': asdict(selection),
            'country_collection': 'trusted_proxy_header'
            if request.app.state.config.product_analytics_country_enabled
            else 'disabled',
        }
    )
