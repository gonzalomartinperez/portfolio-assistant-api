"""Offline interoperability contracts; these are not public ingestion models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.analytics import Section
from app.domain.analytics_interactions import REGIONS, SHELL_REGIONS, Region

ExperienceName = Literal[
    'page_view',
    'section_view',
    'public_click',
    'product_interest',
    'affiliate_click',
    'checkout_intent',
]
PortfolioRoute = Literal[
    '/',
    '/about',
    '/work',
    '/work/filomena',
    '/stack',
    '/education',
    '/cv',
    '/contact',
    '/es',
    '/es/about',
    '/es/work',
    '/es/work/filomena',
    '/es/stack',
    '/es/education',
    '/es/cv',
    '/es/contact',
]
SECTION_ROUTES: dict[Section, str] = {
    'home': '/',
    'about': '/about',
    'work': '/work',
    'filomena': '/work/filomena',
    'stack': '/stack',
    'education': '/education',
    'cv': '/cv',
    'contact': '/contact',
}
COMMERCE_EVENTS = ('product_interest', 'affiliate_click', 'checkout_intent')
CONDITIONS: list[dict[str, object]] = [
    {
        'if': {'properties': {'event_name': {'const': 'public_click'}}},
        'then': {
            'required': ['cell_x', 'cell_y'],
            'properties': {
                'cell_x': {'type': 'integer'},
                'cell_y': {'type': 'integer'},
            },
        },
        'else': {
            'not': {'anyOf': [{'required': ['cell_x']}, {'required': ['cell_y']}]}
        },
    },
    {
        'if': {'properties': {'event_name': {'enum': list(COMMERCE_EVENTS)}}},
        'then': {
            'required': ['target_id'],
            'properties': {'target_id': {'type': 'string'}},
        },
        'else': {'not': {'required': ['target_id']}},
    },
]


class SiteExperience(BaseModel):
    """A bounded core still requires a product-owned route/target/region profile."""

    model_config = ConfigDict(
        extra='forbid', strict=True, json_schema_extra={'allOf': CONDITIONS}
    )
    schema_version: Literal[1]
    project: Literal['portfolio', 'pequeverso']
    source: Literal['site']
    event_id: str = Field(
        pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
    )
    event_name: ExperienceName
    route: str = Field(
        max_length=128, pattern=r'^/(?:[a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*)*)?$'
    )
    layout_revision: str = Field(max_length=64, pattern=r'^[a-z][a-z0-9-]*$')
    viewport_bucket: Literal['mobile', 'tablet', 'desktop']
    section_id: str = Field(max_length=64, pattern=r'^[a-z][a-z0-9-]*$')
    locale: Literal['en', 'es']
    cell_x: int | None = Field(default=None, ge=0, le=7)
    cell_y: int | None = Field(default=None, ge=0, le=7)
    target_id: str | None = Field(
        default=None, max_length=64, pattern=r'^[a-z][a-z0-9-]*$'
    )

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value: object) -> int:
        if type(value) is not int or value != 1:
            raise ValueError('invalid_experience_version')
        return 1

    @model_validator(mode='after')
    def dimensions(self):
        if self.event_name == 'public_click':
            if self.cell_x is None or self.cell_y is None:
                raise ValueError('click_cells_required')
        elif self.model_fields_set & {'cell_x', 'cell_y'}:
            raise ValueError('non_click_cells_forbidden')
        if self.event_name in COMMERCE_EVENTS:
            if self.target_id is None:
                raise ValueError('commerce_target_required')
        elif 'target_id' in self.model_fields_set:
            raise ValueError('non_commerce_target_forbidden')
        return self


def portfolio_conditions() -> list[dict[str, object]]:
    conditions = list(CONDITIONS)
    for section, path in SECTION_ROUTES.items():
        for locale in ('en', 'es'):
            route = path if locale == 'en' else '/es' + (path if path != '/' else '')
            conditions.append(
                {
                    'if': {'properties': {'route': {'const': route}}},
                    'then': {
                        'properties': {
                            'locale': {'const': locale},
                            'section_id': {
                                'enum': sorted(REGIONS[section] | SHELL_REGIONS)
                            },
                        }
                    },
                }
            )
    return conditions


class PortfolioExperience(SiteExperience):
    """Offline Portfolio profile for the two existing region-aware interaction events."""

    model_config = ConfigDict(json_schema_extra={'allOf': portfolio_conditions()})
    project: Literal['portfolio']
    event_name: Literal['public_click', 'section_view']
    route: PortfolioRoute
    layout_revision: Literal['portfolio-v1']
    section_id: Region

    @model_validator(mode='after')
    def reviewed_region(self):
        for section, path in SECTION_ROUTES.items():
            expected = (
                path if self.locale == 'en' else '/es' + (path if path != '/' else '')
            )
            if (
                self.route == expected
                and self.section_id in REGIONS[section] | SHELL_REGIONS
            ):
                return self
        raise ValueError('unreviewed_route_region')
