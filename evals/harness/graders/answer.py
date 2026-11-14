"""Graders over the answer text: language, abstention, forbidden claims, required facts."""

import re

from app.adapters.providers.language import LocalLanguageDetector
from evals.harness.graders._text import contains_phrase, fold, sentences
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_DETECTOR = LocalLanguageDetector()
_MARKERS = re.compile(r'\[\d+\]')

# Refusal context: a sentence that states absence or inability. Matched on folded text.
_REFUSAL = re.compile(
    r'\b(?:no (?:record|evidence|information|mention|public|data)'
    r'|not (?:in|mentioned|listed|found|documented|evidenced|part of|aware)'
    r"|cannot|can't|can not|couldn't|unable|don't|do not|doesn't|does not|didn't|did not"
    r"|isn't|is not|wasn't|was not|nothing"
    r'|no (?:tengo|hay|cuento|figura|puedo|aparece|consta|existe|se menciona|encuentro|dispongo|esta)'
    r'|sin (?:informacion|evidencia|registro)|ninguna? (?:informacion|evidencia|registro|mencion)'
    r'|tampoco)\b'
)


def language_is(
    item: Item,
    result: RunResult,
    ctx: GradingContext | None = None,
    *,
    expected: str | None = None,
) -> GradeResult:
    """The answer language, detected with the app's detector, equals the expected one."""
    want = expected or item.locale
    detected = _DETECTOR.supported(_MARKERS.sub('', result.answer))
    return GradeResult(
        f'language_is:{want}', detected == want, f'detected {detected}, expected {want}'
    )


def abstains(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """The run used the abstention path: flag set and no cited source."""
    ok = result.abstained and not result.citations and bool(result.answer.strip())
    return GradeResult(
        'abstains',
        ok,
        f'abstained={result.abstained}, citations={len(result.citations)}',
    )


def citations_empty(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    return GradeResult(
        'citations_empty', not result.citations, f'citations={len(result.citations)}'
    )


def forbidden_claims_absent(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """No forbidden claim outside a refusal context (a sentence with a refusal cue)."""
    asserted = []
    for sentence in (fold(s) for s in sentences(result.answer)):
        if _REFUSAL.search(sentence):
            continue
        asserted += [
            c.id for c in item.forbidden_claims if contains_phrase(sentence, c.match)
        ]
    return GradeResult(
        'forbidden_claims_absent',
        not asserted,
        f'asserted: {sorted(set(asserted))}' if asserted else 'none asserted',
    )


def required_facts_present(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Every required fact matches the answer after casefold and accent folding."""
    answer = fold(result.answer)
    missing = [
        f.id for f in item.required_facts if not contains_phrase(answer, f.match)
    ]
    return GradeResult(
        'required_facts_present',
        not missing,
        f'missing: {missing}' if missing else 'all present',
    )
