# ADR011: In-repo eval harness package with deterministic graders

Status: accepted (2026-11-14, master plan task M2-3).

## Context and problem

The existing evaluation code (`scripts/evaluate_assistant.py`, `evaluate_conversations.py`)
drives a bank of 1,000 cases and records answers for human review; it has no machine
graders, no item schema, and its isolation guard (`scripts/evaluation_isolation.py`)
is a script-level check. The [assistant quality plan](../master-plan/assistant-quality.md)
asks for a golden tier gated at 100% by deterministic graders (section 8.1), a closed
item schema (section 4), reports with counts per stratum (section 14) and an isolation
guard that rejects remote PostgreSQL and Neo4j (gap A1 of 2026-10).

engineering-standards v1.0.0 ships only an eval-tooling placeholder, so there is no
shared package to adopt. The sibling pequeverso-assistant-api uses a flat
`evals/{schema,graders,runner,cassette}.py` layout.

## Options

1. **Extend `scripts/evaluate_assistant.py` in place.** Smallest diff, but the script
   mixes server lifecycle, progress files and the legacy bank format; graders would be
   hard to unit test in isolation and the script is not type checked.
2. **New package `evals/harness/`** with pure graders, a pydantic item model, a loader,
   a runner over the real SSE path and a report writer. Strict mypy, 100% grader
   coverage, not shipped in the image.
3. **Third-party framework as the gate** (DeepEval, RAGAS, promptfoo). Rich metrics, but
   the safety-critical checks (language, abstention, canary, citation membership) must be
   deterministic code, LLM-judged metrics are off every gate until validated, promptfoo
   is OpenAI-owned and these tools add heavy dependencies and network paths. They stay
   available as optional sweeps, never as the gate.

## Decision

Option 2.

1. `evals/harness/items.py` is the item schema (pydantic v2, `extra="forbid"`);
   `evals/schema/item.schema.json` (JSON Schema 2020-12) is generated from it and a test
   fails on drift. Gold evidence uses the canonical keys of
   [ADR012](012-layout-neutral-evidence-keys.md).
2. `evals/harness/graders/` holds the eleven graders of section 8.1 plus
   `citations_empty` as pure functions `(item, result, ctx) -> GradeResult`. Details
   never quote the answer. Missing observations (retrieval, evidence, usage, canary)
   fail closed. Heuristic graders (refusal context, first-person attribution) document
   their limits in their module docstrings.
3. `runner.py` replays scripted turns through session, conversation and stream with an
   in-process ASGI transport and an injected `Provider`; `RecordingProvider` records the
   evidence and usage the wire does not expose. The cassette replayer of M2-7 plugs into
   the same port. First-delta time is measured inside `RecordingProvider`, because the
   ASGI transport buffers the body.

   Open item: the wire has no abstention flag. A completed run without citations is
   only a candidate; the `abstains` grader also requires an EN or ES abstention cue and
   no forbidden claim. A real flag in the run event would replace the text heuristic.
4. `isolation.py` accepts only explicit loopback PostgreSQL hosts and loopback Neo4j
   hosts (unix sockets are rejected, consistent with the owned-container guard; a
   non-loopback `PGHOST` or `PGHOSTADDR` in the environment is rejected) and then delegates to `scripts/evaluation_isolation.validate_targets` (owned containers).
   The runner refuses to start otherwise.
5. Reports (`report.py`) hold counts per stratum and locale with Wilson 95% intervals,
   failing ids, quarantined items (outside the gate) and optional pins, never answer text, and are written with mode 0600.
6. The package is outside the image: the Dockerfile context whitelists only `app/`,
   `migrations/` and `contracts/`. Ruff and strict mypy cover `evals`.

## Consequences

- Layout parity with pequeverso-assistant-api is at the item-schema level only; aligning
  the layout (and migrating to a shared package once engineering-standards ships one) is
  a later P6 task.
- The existing scripts keep working; the golden lane replaces them as the gate once M2-4
  freezes the golden set.
- Mutation testing of the graders (target 85) and the golden lane test module follow.

## Confirmation

- `tests/evals/test_graders.py`: every grader, EN and ES, passing, failing and edge cases;
  coverage of `evals/harness/graders/` measured with `coverage run --branch`.
- `tests/evals/test_items.py`: model validation, committed schema equals generated,
  assertion names equal the registry, loader errors carry file, line and item id,
  duplicate ids and normalized questions.
- `tests/evals/test_isolation.py`: remote and missing hosts rejected for PostgreSQL and
  Neo4j, loopback accepted, unix sockets rejected, remote targets rejected before containers
  are inspected.
- `tests/evals/test_runner.py`, `tests/evals/test_report.py`: SSE collection, grading
  pipeline, refusal on remote targets, report content and mode 0600; the real in-process
  run is an `integration` test.
