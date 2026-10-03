"""Public starter prompts derived from the active corpus, never cached answers."""

from dataclasses import dataclass
from typing import Literal

Locale = Literal['en', 'es']


@dataclass(frozen=True)
class Suggestion:
    id: str
    topic: str
    question: str


PROMPTS = (
    (
        'profile',
        'profile',
        'What is Gonzalo working on, and what is his background?',
        '¿En qué trabaja Gonzalo y cuál es su trayectoria?',
    ),
    (
        'experience',
        'experience',
        'What has Gonzalo contributed in his recent roles?',
        '¿Qué aportó Gonzalo en sus trabajos recientes?',
    ),
    (
        'projects',
        'projects',
        'Which projects best illustrate Gonzalo’s work?',
        '¿Qué proyectos representan mejor el trabajo de Gonzalo?',
    ),
    ('education', 'education', 'What did Gonzalo study?', '¿Qué estudió Gonzalo?'),
)


def suggestions(
    paths: frozenset[str], locale: Locale, *, achievements: bool = False
) -> tuple[Suggestion, ...]:
    result = tuple(
        Suggestion(identifier, topic, spanish if locale == 'es' else english)
        for identifier, topic, english, spanish in PROMPTS
        if f'src/content/{locale}/{topic}.ts' in paths
    )

    if achievements and (
        f'src/content/{locale}/experience.ts' in paths
        or 'public/assistant-knowledge.json' in paths
    ):
        metric = Suggestion(
            'achievement',
            'achievement',
            'Which achievements are supported by public evidence?'
            if locale == 'en'
            else '¿Qué logros están respaldados por evidencia pública?',
        )
        return result[:3] + (metric,) + result[3:]
    return result
