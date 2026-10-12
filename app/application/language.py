"""Language policy; supported output is independent from visitor input language."""

import re
from typing import Literal, Protocol

from app.application.conversation_context import Turn

Locale = Literal['en', 'es']


class LanguageDetector(Protocol):
    def supported(self, text: str) -> Locale | None:
        """Return a confident supported language, or None for ambiguous/other input."""
        ...


def explicit_locale(question: str) -> Locale | None:
    explicit = re.search(
        r'(?i)\b(?:respond|reply|answer|responde|respondé|contesta|traduce|tradúcelo|translate)'
        r'[^.!?\n]{0,60}\b(?:in|en|to|al)\s+(english|inglés|ingles|spanish|español)\b',
        question,
    )
    if explicit:
        return 'en' if explicit[1].lower() in ('english', 'inglés', 'ingles') else 'es'
    preference = re.search(
        r'(?i)^\s*(?:(?:now|ahora)\s+)?(?:(?:in|en)\s+)?'
        r'(english|inglés|ingles|spanish|español)(?:\s+(?:please|por favor))?[.!?]?\s*$',
        question,
    ) or re.search(
        r'(?i)^\s*(?:switch to|cambia a|hablá|habla)\s+'
        r'(english|inglés|ingles|spanish|español)\b',
        question,
    )
    if preference:
        return (
            'en' if preference[1].lower() in ('english', 'inglés', 'ingles') else 'es'
        )
    return None


def select_locale(
    question: str, history: tuple[Turn, ...], hint: str, detector: LanguageDetector
) -> Locale:
    explicit = explicit_locale(question)
    if explicit:
        return explicit
    detected = detector.supported(question)
    if detected:
        return detected
    for turn in reversed(history):
        if turn.role == 'user':
            previous = explicit_locale(turn.content) or detector.supported(turn.content)
            if previous:
                return previous
    return 'es' if hint == 'es' else 'en'
