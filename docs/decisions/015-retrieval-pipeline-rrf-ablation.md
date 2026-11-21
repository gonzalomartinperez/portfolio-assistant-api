# ADR015: Staged retrieval with declarative rules and paired ablation

Status: accepted (2026-11-21, master plan task M4-2, decision PAA-D18).

## Context and problem

The legacy retrieval `search` method had cyclomatic complexity 49 and combined
question analysis, candidate scoring, fusion, re-ranking and evidence selection.
Inline boosts were difficult to exercise independently. Their marginal effects
could not be measured without editing the search implementation.

## Decision drivers

- Preserve source ordering, provenance and the retrieval quality gate during the refactor.
- Measure each heuristic's contribution on the same labeled public corpus.
- Keep the runtime pipeline deterministic, testable offline and within cyclomatic complexity 10.

## Options

1. **Staged pipeline with declarative rules (chosen).** Keep the existing ranking behavior and
   expose vocabulary, weights and rule switches through a validated configuration.
2. **Keep the monolith.** Retain one implementation of search with fewer module boundaries,
   at the cost of complex control flow and no isolated measurements.
3. **Learn a ranker.** Train ranking weights from relevance judgments. This would require
   training data, an evaluation protocol and model maintenance beyond this change.

## Decision

Declarative configuration covers vocabularies, weights, fusion values and on/off switches.
Match predicates stay in code, and locale is handled by the pipeline without a per-rule locale.
Rule IDs give the harness a stable way to disable each candidate boost or re-ranking step.
This narrower scope and the fusion default below supersede parts of
[target-state section 5](../master-plan/target-state.md#5-retrieval-and-domain-refactor-paa-d18).

`DEFAULT_RULES` is canonical. Bootstrap loads its packaged
[rules.toml](../../src/portfolio_assistant/ai/retrieval/rules.toml) mirror in strict mode and injects the immutable
rules into the pipeline. The equality test parses the file in strict mode and compares it with
`DEFAULT_RULES`. A non-empty `disabled` list in the shipped file would ablate production
retrieval and fail that test.

Default fusion keeps offset 10 and the existing lexical, vector and graph weights.
The weights are `(1, 1, 0.5)` for semantic embeddings and `(3, 0.1, 0.5)` otherwise.
Relationship queries with graph hits still put the graph lane first.
Measure offset 60 as `hybrid_rrf60` with the same weights before changing the default.
The offset must be an integer from 1 to 10,000; `parse_rules` and `RetrievalRules` reject
anything else. The CI database job budget includes the ablation step's own 8-minute cap,
so the measurement cannot consume the time of the other steps. The step has no metric
thresholds (its deltas never fail CI), but a crash of the harness fails the job, because
the CI profile forbids hidden step failures in gated jobs.

A disabled additive boost contributes zero and a disabled multiplier leaves the
score unscaled. A disabled anchor leaves the current ranking unchanged and later
anchors still run. A disabled first-match step still consumes its position when
its predicate matches. The chain stops there and applicable anchors run as usual.
This measures the effect of removing one step without substituting a later one.

The harness reports paired deltas as hybrid minus variant under `rule_ablation`.
CI uses fixture embeddings with `corpus.semantic` false, so fusion exercises only the
lexical weight tuple. The 13 variants make multiple comparisons on a small query set.
A confidence interval that includes zero indicates an absence of evidence for an effect.
A rule with such a Recall@5 interval and no dependent golden item is eligible for deletion
in a later PR, as is a rule with a demonstrated negative contribution. Delete a rule only
if both the golden and retrieval gates stay green with the rule removed.

## Consequences

- Rule switches and weights can be changed without changing the pipeline control flow.
- The Python defaults and the packaged configuration must be updated together.
- The ablation report adds fixture evaluation time to the database job. It is retained
  as an artifact and the existing baseline comparison remains the quality gate.

## Confirmation

- The frozen [characterization tests](../../tests/characterization/) compare source
  order, provenance and index calls with the legacy retrieval implementation.
- [Rule tests](../../tests/unit/test_retrieval_rules.py) pin strict TOML equality and exercise
  each single-rule ablation, including first-match precedence.
- CI retains `artifacts/retrieval-report-ablation.json` from the database job.
- `uv run ruff check --select C901 src/portfolio_assistant/ai/retrieval` checks the complexity budget.
