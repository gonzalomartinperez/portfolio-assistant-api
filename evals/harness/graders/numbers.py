"""numbers_grounded: every number in the answer exists in the evidence or the question.

Limits (bag of numbers): grounding is set membership, not association. An answer
number that appears anywhere in the evidence or question counts as grounded even if
attached to a different fact; the qualifier rule is the only context-sensitive check.
Ambiguous single-separator tokens (``1,299`` / ``1.299``) are read by the item locale in
the answer (en: comma groups thousands, es: dot groups thousands) and both ways in the
evidence, so a thousands reading never grounds against a plain ``1`` or ``12.5``.
List numbering of one or two digits at a line start (``1.``, ``2)``) is ignored.
"""

import re
from decimal import Decimal

from evals.harness.graders._text import MARKER, fold, sentences
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_NUMBER = re.compile(r'\d+(?:[.,]\d+)*')
# Provider evidence headers carry line numbers and URLs; they are not evidence content.
_HEADER = re.compile(
    r'^PUBLIC SOURCE \[\d+\] \S+ lines \d+-\d+(?: canonical_url=\S+)?:$', re.MULTILINE
)
_NOISE = re.compile(rf'https?://\S+|{MARKER}|^[ \t]*\d{{1,2}}[.)][ \t]', re.MULTILINE)
_QUALIFIER = re.compile(
    r'\b(?:estimated|estimate|reported|estimad[oa]s?|reportad[oa]s?)\b'
)


def _canon(text: str) -> str:
    return format(Decimal(text).normalize(), 'f')


def _ambiguous(token: str) -> bool:
    """One separator followed by exactly three digits after a 1 to 3 digit head."""
    parts = re.split(r'[.,]', token)
    return (
        len(parts) == 2
        and len(parts[1]) == 3
        and 1 <= len(parts[0]) <= 3
        and parts[0] != '0'
    )


def _unambiguous(token: str) -> str:
    dots, commas = token.count('.'), token.count(',')
    if not dots and not commas:
        return _canon(token)
    if dots and commas:
        decimal = '.' if token.rfind('.') > token.rfind(',') else ','
        thousands = ',' if decimal == '.' else '.'
        return _canon(token.replace(thousands, '').replace(decimal, '.'))
    separator = '.' if dots else ','
    if dots + commas > 1:
        return _canon(token.replace(separator, ''))
    return _canon(token.replace(separator, '.'))


def readings(token: str) -> frozenset[str]:
    """Every value an evidence token may denote (both groupings when ambiguous)."""
    if not _ambiguous(token):
        return frozenset({_unambiguous(token)})
    return frozenset(
        {_canon(token.replace(',', '.')), _canon(re.sub(r'[.,]', '', token))}
    )


def reading(token: str, locale: str) -> str:
    """The single value an answer token denotes under the item locale."""
    if not _ambiguous(token):
        return _unambiguous(token)
    thousands = ',' if locale == 'en' else '.'
    sep = '.' if token.count('.') else ','
    if sep == thousands:
        return _canon(token.replace(sep, ''))
    return _canon(token.replace(',', '.'))


def _tokens(text: str) -> list[str]:
    return _NUMBER.findall(_NOISE.sub(' ', _HEADER.sub(' ', text)))


def numbers_grounded(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Numbers are grounded; an estimated or reported qualifier in evidence survives."""
    if result.evidence_text is None:
        return GradeResult('numbers_grounded', False, 'evidence was not observed')
    evidence = _HEADER.sub(' ', result.evidence_text)
    known: set[str] = set()
    for token in _tokens(evidence + '\n' + result.question):
        known |= readings(token)
    qualified: set[str] = set()
    for sentence in sentences(_NOISE.sub(' ', evidence)):
        if _QUALIFIER.search(fold(sentence)):
            for token in _NUMBER.findall(sentence):
                qualified |= readings(token)
    ungrounded = 0
    unqualified = 0
    for sentence in sentences(_NOISE.sub(' ', result.answer)):
        has_qualifier = bool(_QUALIFIER.search(fold(sentence)))
        for token in _NUMBER.findall(sentence):
            value = reading(token, item.locale)
            if value not in known:
                ungrounded += 1
            elif value in qualified and not has_qualifier:
                unqualified += 1
    ok = not ungrounded and not unqualified
    return GradeResult(
        'numbers_grounded',
        ok,
        f'ungrounded={ungrounded}, qualifier_dropped={unqualified}' if not ok else 'ok',
    )
