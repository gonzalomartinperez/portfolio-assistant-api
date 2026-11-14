"""Deterministic graders (assistant-quality.md section 8.1) and the assertion registry."""

import re
from collections.abc import Callable

from evals.harness.graders.answer import (
    abstains,
    citations_empty,
    forbidden_claims_absent,
    language_is,
    required_facts_present,
)
from evals.harness.graders.budget import budget_respected
from evals.harness.graders.citations import (
    citation_urls_allowlisted,
    citations_in_retrieved,
    retrieval_gold_in_topk,
)
from evals.harness.graders.numbers import numbers_grounded
from evals.harness.graders.safety import no_canary, third_person_attribution
from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

Grader = Callable[[Item, RunResult, GradingContext | None], GradeResult]

REGISTRY: dict[str, Grader] = {
    'language_is': language_is,
    'citations_in_retrieved': citations_in_retrieved,
    'citation_urls_allowlisted': citation_urls_allowlisted,
    'numbers_grounded': numbers_grounded,
    'forbidden_claims_absent': forbidden_claims_absent,
    'abstains': abstains,
    'required_facts_present': required_facts_present,
    'no_canary': no_canary,
    'third_person_attribution': third_person_attribution,
    'retrieval_gold_in_topk': retrieval_gold_in_topk,
    'budget_respected': budget_respected,
    'citations_empty': citations_empty,
}


def grade(
    assertion: str, item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Run one assertion name (``language_is:<en|es>`` carries its language)."""
    if (match := re.fullmatch(r'language_is:(en|es)', assertion)) is not None:
        return language_is(item, result, ctx, expected=match[1])
    return REGISTRY[assertion](item, result, ctx)


def grade_item(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> tuple[GradeResult, ...]:
    return tuple(grade(name, item, result, ctx) for name in item.assertions)
