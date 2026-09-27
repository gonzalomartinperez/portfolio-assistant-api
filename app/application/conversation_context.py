"""Bound visitor context independently from authoritative public evidence."""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Turn:
    """Session-local text; neither visitor nor prior assistant text verifies facts."""

    role: Literal['user', 'assistant']
    content: str


def bounded_history(turns: tuple[Turn, ...]) -> tuple[Turn, ...]:
    """Keep recent turns in chronological order, within 3,000 characters total."""
    result = []
    remaining = 3000
    for turn in reversed(turns[-6:]):
        content = turn.content[: min(1000, remaining)]
        if not content:
            break
        result.append(Turn(turn.role, content))
        remaining -= len(content)
    return tuple(reversed(result))


def is_followup(question: str) -> bool:
    """Recognize explicit reference/reframing cues without a paid routing call."""
    return bool(
        re.search(
            r'(?i)\b(example|shorter|brief|technically|translate|rephrase|that|it|those|'
            r'ejemplo|breve|tecnicamente|técnicamente|traducir|traduce|tradúcelo|traducelo|traducción|eso|ese|hazlo|explícalo|explicalo)\b',
            question,
        )
    )


def retrieval_question(question: str, history: tuple[Turn, ...]) -> str:
    """Resolve explicit follow-ups to the latest substantive visitor topic."""
    if is_followup(question):
        for turn in reversed(history):
            if turn.role == 'user' and not is_followup(turn.content):
                return f'{turn.content[:1000]}\n{question}'
    return question
