# ADR013: Provider-port cassettes for the golden lane

Status: accepted (2026-11-14, master plan task M2-7, infrastructure only).

## Context and problem

The golden lane (ADR011) must run on every PR at 100% without a network or a paid call,
yet exercise the real prompt assembly. [assistant-quality.md](../master-plan/assistant-quality.md)
section 12 asks for cassettes, and DR-04 caps live-eval spend at USD 2 per campaign and
USD 8 per month with a hard stop in code.

## Options

1. **HTTP-level recording (VCR style).** Captures headers and bodies, which risks leaking
   credentials and breaks on any transport change.
2. **Cassettes at the `Provider` port**, keyed by the exact model request.
3. **Hand-written stub answers.** No guard against prompt or model drift.

## Decision

Option 2, in `evals/harness/cassettes.py`.

- **Format:** `evals/cassettes/<prompt_version_slug>/<key>.jsonl`. Row 1 is `meta` (key,
  prompt_version, model, reasoning effort, max output tokens), then ordered `delta` rows
  and one optional `usage` row. No headers, credentials or request bodies.
- **Key:** sha256 of the canonical JSON of (prompt_version, model, reasoning effort,
  max output tokens, assembled messages including evidence). Messages come from
  `assemble_request` in `app/adapters/providers/answer.py`, the function the real provider
  uses; the prompt date is pinned (`CASSETTE_DATE`). Web search is outside the lane.
- **Replay (record mode `none`, the default):** a missing key raises
  `CassetteMissingError`; the lane exits 3 ("re-record required"). The pytest lane skips
  with that reason when no cassettes exist, and fails when `REQUIRE_GOLDEN_CASSETTES=1`.
- **Re-record policy:** any change to the prompt version, model, effort, evidence or
  messages changes keys, so the PR must carry a re-recorded set. Recording writes
  missing keys only and never overwrites.
- **Recording gate:** `python -m evals.harness.golden --record` refuses unless
  `EVAL_RECORDING=1`, `EVAL_ENVIRONMENT=eval-live`, `ALLOW_PAID_AI=true` and an explicit
  `--campaign-budget-usd` of at most 2 are present. Before every call it reserves the
  worst case (input bytes as tokens, maximum output) against the campaign budget and the
  month total in the committed `spend-ledger.json` (USD 8 cap) and stops with
  `SpendCapError` (exit 4) if either would be exceeded; the owner is then asked. A
  missing or invalid ledger fails closed. A call without usage is charged the worst case.
- **Budgets:** `evals/baselines/budgets.json` holds the declared section 11 limits. Its
  `measured` block is empty and the limits are provisional until the first cassette
  replay; later values may regress by at most 20% (`evals/harness/budgets.py`). The check
  is not wired into the golden lane yet: it is enabled once the first recorded campaign
  fills `measured` (replay latency is near zero, so only token and cost budgets apply).
  The recorder itself re-checks the campaign flags, refuses non-positive prices and a
  cassette config that differs from the provider's model, effort or output limit, and
  rounds ledger charges up. The ledger assumes one recording process at a time.

## Consequences

- Recording the actual cassettes is a paid campaign and is not part of this change; it
  is parked for the owner. Until then the golden lane cannot be green and is not wired
  as a required CI job.
- Cassettes are data in the repository and need review like code.

## Confirmation

- `tests/evals/test_cassettes.py`: key sensitivity, round trip, missing key, format errors,
  recorder refusals and both caps, ledger fail-closed.
- `tests/evals/test_budgets.py`: limits, 20% regression, missing metrics.
- `tests/evals/test_golden.py`: replay lane (skip or require) and the recording flags.
