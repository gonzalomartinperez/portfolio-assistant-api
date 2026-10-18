"""Strict public interaction input; no raw coordinates, text or navigation targets."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.analytics import Section
from app.domain.analytics_interactions import (
    InteractionName,
    LayoutRevision,
    PublicInteraction,
    Region,
    Viewport,
)


class ProductInteractionBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[2]
    project: Literal['portfolio']
    source: Literal['site']
    event_id: str = Field(
        pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
    )
    event_name: InteractionName
    section: Section
    locale: Literal['en', 'es']
    region_id: Region
    layout_revision: LayoutRevision
    viewport: Viewport
    cell_x: int | None = Field(default=None, ge=0, le=7)
    cell_y: int | None = Field(default=None, ge=0, le=7)

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value: object) -> int:
        if type(value) is not int or value != 2:
            raise ValueError('invalid_analytics_version')
        return 2

    def event(self) -> PublicInteraction:
        return PublicInteraction(
            self.event_id,
            self.event_name,
            self.section,
            self.locale,
            self.region_id,
            self.layout_revision,
            self.viewport,
            self.cell_x,
            self.cell_y,
        )

    @model_validator(mode='after')
    def semantic_dimensions(self):
        self.event()
        return self
