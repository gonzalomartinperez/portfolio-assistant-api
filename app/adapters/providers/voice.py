"""Assemble the developer prompt from versioned pieces; presentation style never changes evidence policy."""

from datetime import date

from app.adapters.prompts import default_prompts
from app.domain.prompts import prompt_version, render


def developer_prompt(locale: str, web: bool, today: date) -> tuple[str, str]:
    """Return the developer message and its prompt_version (never logs prompt text)."""
    prompts = default_prompts()
    es = locale == 'es'
    language = 'neutral Latin American Spanish' if es else 'natural US English'
    pieces = [
        *([prompts['web-context']] if web else []),
        prompts['answer'],
        prompts['voice-recruiter'],
        prompts['voice-es' if es else 'voice-en'],
    ]
    values = {'answer': {'current_date': today.isoformat(), 'language': language}}
    message = ''.join(
        render(piece, **values.get(piece.id, {})) + ' ' for piece in pieces
    )
    return message, prompt_version(pieces)
