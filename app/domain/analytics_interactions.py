"""Reviewed public regions and bounded aggregate-only interaction dimensions."""

from dataclasses import dataclass
from typing import Literal

from app.domain.analytics import Section

Region = Literal[
    'site-header',
    'site-footer',
    'home-featured',
    'home-experience',
    'home-about',
    'home-education',
    'home-contact',
    'about-story',
    'about-focus',
    'about-principles',
    'about-opportunities',
    'work-rampy',
    'work-teamcubation',
    'work-cooperativa',
    'work-independent',
    'work-projects',
    'filomena-problem',
    'filomena-approach',
    'filomena-outcomes',
    'filomena-evidence',
    'stack-catalogue',
    'stack-scope',
    'education-degree',
    'education-curriculum',
    'education-credentials',
    'education-evidence',
    'cv-downloads',
    'cv-summary',
    'contact-channels',
    'contact-resume',
]
Viewport = Literal['mobile', 'tablet', 'desktop']
InteractionName = Literal['public_click', 'section_exposure']
LayoutRevision = Literal['portfolio-v1']

REGIONS: dict[Section, frozenset[Region]] = {
    'home': frozenset(
        {
            'home-featured',
            'home-experience',
            'home-about',
            'home-education',
            'home-contact',
        }
    ),
    'about': frozenset(
        {'about-story', 'about-focus', 'about-principles', 'about-opportunities'}
    ),
    'work': frozenset(
        {
            'work-rampy',
            'work-teamcubation',
            'work-cooperativa',
            'work-independent',
            'work-projects',
        }
    ),
    'filomena': frozenset(
        {
            'filomena-problem',
            'filomena-approach',
            'filomena-outcomes',
            'filomena-evidence',
        }
    ),
    'stack': frozenset({'stack-catalogue', 'stack-scope'}),
    'education': frozenset(
        {
            'education-degree',
            'education-curriculum',
            'education-credentials',
            'education-evidence',
        }
    ),
    'cv': frozenset({'cv-downloads', 'cv-summary'}),
    'contact': frozenset({'contact-channels', 'contact-resume'}),
}
SHELL_REGIONS: frozenset[Region] = frozenset({'site-header', 'site-footer'})


@dataclass(frozen=True)
class PublicInteraction:
    event_id: str
    name: InteractionName
    section: Section
    locale: Literal['en', 'es']
    region_id: Region
    layout_revision: LayoutRevision
    viewport: Viewport
    cell_x: int | None = None
    cell_y: int | None = None

    def __post_init__(self) -> None:
        if (
            self.name not in ('public_click', 'section_exposure')
            or self.locale not in ('en', 'es')
            or self.layout_revision != 'portfolio-v1'
            or self.viewport not in ('mobile', 'tablet', 'desktop')
            or self.section not in REGIONS
        ):
            raise ValueError('invalid_interaction_dimensions')
        if self.region_id not in REGIONS[self.section] | SHELL_REGIONS:
            raise ValueError('invalid_interaction_region')
        if self.name == 'public_click':
            if any(
                type(value) is not int or not 0 <= value < 8
                for value in (self.cell_x, self.cell_y)
            ):
                raise ValueError('invalid_interaction_cell')
        elif self.cell_x is not None or self.cell_y is not None:
            raise ValueError('exposure_cells_forbidden')
