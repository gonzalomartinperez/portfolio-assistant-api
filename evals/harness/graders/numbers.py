"""numbers_grounded: every number in the answer exists in the evidence or the question."""

import re
from decimal import Decimal

from evals.harness.graders._text import fold, sentences
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_NUMBER = re.compile(r'\d+(?:[.,]\d+)*')
_NOISE = re.compile(r'https?://\S+|\[\d+\]|^\s*\d+[.)]\s', re.MULTILINE)
_QUALIFIER = re.compile(
    r'\b(?:estimated|estimate|reported|estimad[oa]s?|reportad[oa]s?)\b'
)


def _canon(text: str) -> str:
    return format(Decimal(text).normalize(), 'f')


def forms(token: str) -> frozenset[str]:
    """Canonical values a token may denote, covering es ``1.299,00`` and en ``1,299.00``."""
    dots, commas = token.count('.'), token.count(',')
    if not dots and not commas:
        return frozenset({_canon(token)})
    if dots and commas:
        decimal = '.' if token.rfind('.') > token.rfind(',') else ','
        thousands = ',' if decimal == '.' else '.'
        return frozenset({_canon(token.replace(thousands, '').replace(decimal, '.'))})
    separator = '.' if dots else ','
    if dots + commas > 1:
        return frozenset({_canon(token.replace(separator, ''))})
    head, _, tail = token.partition(separator)
    values = {_canon(f'{head}.{tail}')}
    if len(tail) == 3 and 1 <= len(head) <= 3 and head != '0':
        values.add(_canon(head + tail))  # "1.299" or "1,299" may be a thousands group
    return frozenset(values)


def _numbers(text: str) -> list[frozenset[str]]:
    return [forms(t) for t in _NUMBER.findall(_NOISE.sub(' ', text))]


def numbers_grounded(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Numbers are grounded; an estimated or reported qualifier in evidence survives."""
    if result.evidence_text is None:
        return GradeResult('numbers_grounded', False, 'evidence was not observed')
    evidence = _NOISE.sub(' ', result.evidence_text)
    source = evidence + '\n' + result.question
    known = set().union(*_numbers(source))
    qualified: set[str] = set()
    for sentence in sentences(evidence):
        if _QUALIFIER.search(fold(sentence)):
            qualified.update(*_numbers(sentence))
    ungrounded = 0
    unqualified = 0
    for sentence in sentences(_NOISE.sub(' ', result.answer)):
        has_qualifier = bool(_QUALIFIER.search(fold(sentence)))
        for value in _numbers(sentence):
            if not value & known:
                ungrounded += 1
            elif value & qualified and not has_qualifier:
                unqualified += 1
    ok = not ungrounded and not unqualified
    return GradeResult(
        'numbers_grounded',
        ok,
        f'ungrounded={ungrounded}, qualifier_dropped={unqualified}' if not ok else 'ok',
    )
