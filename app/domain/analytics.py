"""Closed product vocabulary; no visitor identity or arbitrary dimensions."""

from dataclasses import dataclass
from typing import Literal

EventName = Literal[
    'page_view',
    'navigation_click',
    'section_open',
    'cv_link_open',
    'contact_link_open',
    'company_link_open',
]
Section = Literal[
    'home', 'about', 'work', 'filomena', 'stack', 'education', 'cv', 'contact'
]
Target = Literal[
    'en',
    'es',
    'email',
    'linkedin',
    'github',
    'rampy',
    'teamcubation',
    'cooperativa-obrera',
    'independent',
]
TARGETS: dict[str, frozenset[str]] = {
    'page_view': frozenset(),
    'navigation_click': frozenset(),
    'section_open': frozenset(
        {'rampy', 'teamcubation', 'cooperativa-obrera', 'independent'}
    ),
    'cv_link_open': frozenset({'en', 'es'}),
    'contact_link_open': frozenset({'email', 'linkedin', 'github'}),
    'company_link_open': frozenset({'rampy', 'teamcubation', 'cooperativa-obrera'}),
}


@dataclass(frozen=True)
class ProductEvent:
    event_id: str
    name: EventName
    section: Section
    locale: Literal['en', 'es']
    target: Target | None = None

    def __post_init__(self) -> None:
        allowed = TARGETS[self.name]
        if (allowed and self.target not in allowed) or (
            not allowed and self.target is not None
        ):
            raise ValueError('invalid_event_target')
        if (
            self.name in ('section_open', 'company_link_open')
            and self.section != 'work'
        ):
            raise ValueError('invalid_event_section')
        if self.name == 'cv_link_open' and self.section != 'cv':
            raise ValueError('invalid_event_section')
