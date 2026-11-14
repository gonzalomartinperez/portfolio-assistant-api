"""Graders over the answer text: language, abstention, forbidden claims, required facts."""

import re

from app.adapters.providers.language import LocalLanguageDetector
from evals.harness.graders._text import MARKER, contains_phrase, fold
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_DETECTOR = LocalLanguageDetector()
_MARKERS = re.compile(MARKER)

# Refusal and abstention cues, matched on folded text (no accents, casefolded).
_CUES = (
    r'no (?:record|evidence|information|mention|public|data)'
    r'|not (?:in|mentioned|listed|found|documented|evidenced|part of|aware)'
    r"|cannot|can't|can not|couldn't|unable|don't|do not|doesn't|does not|didn't|did not"
    r"|isn't|is not|wasn't|was not|never"
    r'|no (?:tengo|hay|cuento|figura|puedo|aparece|consta|existe|se menciona|encuentro|dispongo|esta)'
    r'|sin (?:informacion|evidencia|registro)|ninguna? (?:informacion|evidencia|registro|mencion)'
    r'|tampoco|nunca|jamas'
    r"|won't|will not|rather than|instead of|lacks?|no (?:menciona|incluye|voy a)"
    r'|en lugar de|en vez de'
)
# Clause negation additionally accepts a bare "not" or "no" (never used for abstention).
_NEGATION = rf'{_CUES}|not|no'
# Extra phrasing that signals a scope refusal or abstention (used by ``abstains`` only).
_ABSTAIN_EXTRA = (
    r'only (?:answer|discuss|help)|outside (?:of )?(?:the |my )?(?:scope|portfolio)'
    r'|not able|prefer not|solo (?:puedo|respondo)|fuera de (?:mi|el) (?:alcance|portafolio)'
)
_ABSTENTION = re.compile(rf'\b(?:{_CUES}|{_ABSTAIN_EXTRA})\b')
_CUE_BEFORE = re.compile(rf'\b(?:{_NEGATION})\b')
_CUE_AFTER = re.compile(rf'^(?:\w+ ){{0,2}}(?:{_NEGATION})\b')
# A clause ends at these; a refusal cue only counts inside the claim's own clause.
_CLAUSE_BREAK = re.compile(
    r'[;:,\n]|[.!?](?:\s|$)'
    r'|\b(?:and|but|however|although|though|while|whereas|y|pero|aunque|mientras|sino'
    r'|sin embargo)\b'
)
_WINDOW_TOKENS = 8


def _negated(text: str, start: int, end: int) -> bool:
    """Whether the claim sits in a refusal context.

    True if a cue precedes the claim within 8 tokens of its own clause, or follows it
    directly (at most two tokens later) inside the same clause.
    """
    breaks = list(_CLAUSE_BREAK.finditer(text, 0, start))
    prefix = text[breaks[-1].end() if breaks else 0 : start]
    if _CUE_BEFORE.search(' '.join(prefix.split()[-_WINDOW_TOKENS:])):
        return True
    after = text[end:]
    stop = _CLAUSE_BREAK.search(after)
    clause = after[: stop.start()] if stop else after
    return _CUE_AFTER.match(clause.lstrip()) is not None


def asserted_claims(item: Item, answer: str) -> list[str]:
    """Ids of forbidden claims that occur in the whole answer outside a refusal context.

    Limits: clause splitting is lexical (a cue in a different clause never exempts);
    coordinated entities after "and" are not covered by an earlier cue (false failure).
    """
    folded = fold(answer)
    found = []
    for claim in item.forbidden_claims:
        pattern = re.compile(rf'(?<!\w){re.escape(fold(claim.match))}(?!\w)')
        if any(
            not _negated(folded, m.start(), m.end()) for m in pattern.finditer(folded)
        ):
            found.append(claim.id)
    return found


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
    """Uncited abstention: the wire has no flag, so also require a cue and no forbidden claim.

    Passes only if the run completed without citations, the answer contains an
    abstention or refusal cue (``_CUES`` and ``_ABSTAIN_EXTRA``, EN and ES) and no
    forbidden claim is asserted. A confident uncited invented answer fails.
    """
    problems = []
    if not result.abstained or result.citations:
        problems.append('not an uncited completed run')
    if _ABSTENTION.search(fold(result.answer)) is None:
        problems.append('no abstention cue')
    if asserted_claims(item, result.answer):
        problems.append('forbidden claim asserted')
    return GradeResult('abstains', not problems, '; '.join(problems) or 'ok')


def citations_empty(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    return GradeResult(
        'citations_empty', not result.citations, f'citations={len(result.citations)}'
    )


def forbidden_claims_absent(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """No forbidden claim outside a refusal context (see ``asserted_claims``)."""
    asserted = asserted_claims(item, result.answer)
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
