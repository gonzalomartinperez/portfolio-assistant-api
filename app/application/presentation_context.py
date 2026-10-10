"""Untrusted presentation metadata, separate from evidence and conversation history."""

from dataclasses import dataclass
from typing import Literal

PortfolioPath = Literal[
    '/',
    '/about',
    '/work',
    '/work/filomena',
    '/education',
    '/cv',
    '/contact',
    '/stack',
    '/assistant',
    '/es',
    '/es/about',
    '/es/work',
    '/es/work/filomena',
    '/es/education',
    '/es/cv',
    '/es/contact',
    '/es/stack',
    '/es/assistant',
]
Theme = Literal['dark', 'light']
Presentation = Literal['compact', 'expanded', 'page']


@dataclass(frozen=True)
class PresentationContext:
    """Visitor-controlled hints; never facts, instructions or authorization."""

    theme: Theme
    opened_path: PortfolioPath
    current_path: PortfolioPath
    presentation: Presentation
