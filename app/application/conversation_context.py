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
    """Keep recent turns in chronological order, within 8,000 characters total."""
    result = []
    remaining = 8000
    for turn in reversed(turns[-12:]):
        content = turn.content[: min(2000, remaining)]
        if not content:
            break
        result.append(Turn(turn.role, content))
        remaining -= len(content)
    return tuple(reversed(result))


def is_followup(question: str) -> bool:
    """Recognize explicit reference/reframing cues without a paid routing call."""
    # An example *of a named subject* is a new topic, not a history reference.
    if re.search(
        r'(?i)\b(?:example(?:\s+(?:concrete|specific|practical|real|technical)){0,2}'
        r'\s+(?:of|at|for|from)\s+(?!that\b|this\b|it\b|those\b)|'
        r'ejemplo(?:\s+(?:concreto|específico|especifico|práctico|practico|real|técnico|tecnico)){0,2}'
        r'\s+(?:de|en|sobre)\s+(?!eso\b|ese\b|esa\b|esto\b))',
        question,
    ) or re.match(r'(?i)^\s*(?:instead|en cambio)\b', question):
        return False
    if re.search(
        r'(?i)\b(?:based on (?:his|her|their|that|this|the (?:previous|documented)) (?:documented )?work|'
        r'basad[ao]s? en (?:su|ese|este) (?:trabajo|experiencia)|'
        r'which (?:parts|of (?:those|them)|are (?:measured|estimated))|'
        r'cu[aá]les (?:son|fueron) (?:mediciones|medid[ao]s?|estimaciones|estimad[ao]s?))\b',
        question,
    ) or re.fullmatch(
        r'(?i)\s*(?:(?:now|ahora)\s+)?(?:'
        r'(?:(?:in|en)\s+)?(?:english|spanish|ingl[eé]s|español)(?:\s+(?:please|por favor))?|'
        r'(?:switch to|cambia a|habla|hablá)\s+(?:english|spanish|ingl[eé]s|español)|'
        r'(?:answer|respond|reply|responde|contesta)\s+(?:in|en)\s+(?:english|spanish|ingl[eé]s|español)'
        r'(?:\s+(?:and|y)\s+(?:separate|separa|distinguish|distingue|preserve|preserva)\b[^:?!]*)?'
        r')[.!?]?\s*',
        question,
    ):
        return True
    return bool(
        re.search(
            r'(?i)\b(example|shorter|brief|technically|translate|rephrase|summarize|that|it|those|there|'
            r'ejemplo|breve|resumilo|resúmelo|resumelo|tecnicamente|técnicamente|traducir|traduce|tradúcelo|traducelo|traducción|eso|ese|allí|ahí|hazlo|explícalo|explicalo)\b',
            question,
        )
    )


def retrieval_question(question: str, history: tuple[Turn, ...]) -> str:
    """Keep the visitor topic and its latest refinement; never use assistant claims."""
    if is_followup(question):
        refinement = ''
        earliest_reference = ''
        for turn in reversed(history):
            if turn.role != 'user':
                continue
            earliest_reference = turn.content[:1000]
            if not is_followup(turn.content):
                return '\n'.join(
                    part for part in (turn.content[:1000], refinement, question) if part
                )
            if not refinement:
                refinement = turn.content[:1000]
        if earliest_reference:
            return '\n'.join(dict.fromkeys((earliest_reference, refinement, question)))
    return question
