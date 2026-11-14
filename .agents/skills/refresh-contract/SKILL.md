---
name: refresh-contract
description: "Makes an additive change to the public API contract: regenerates the artifacts under contracts/ with contracts.export, checks drift and examples, and lists the consumer steps. Use when a response field, event, schema or OpenAPI artifact changes, or when the contract drift check fails. Not for stream lifecycle behavior (use api-change-stream) or database changes (use api-change-storage); a breaking change needs an ADR first (use write-adr)."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# refresh-contract

Tools: Read, Grep, Glob, Bash, Edit, Write. This skill does not authorize commits, pushes, merges or
deployment, and never edits the sibling web, portfolio or backoffice repositories (AGENTS.md). v1 wire artifacts
are preserved unless an ADR says otherwise.

## Checklist

- [ ] [API contract](../../../docs/reference/api-contract.md) and [frontend handoff](../../../docs/reference/frontend-handoff.md) read
- [ ] Change classified: additive (optional field, new optional value) or breaking (removal, rename, type change)
- [ ] `uv run python -m contracts.export` run; every changed artifact explained by the source change
- [ ] Examples and contract tests updated; consumer steps listed
- [ ] Breaking change stopped for an ADR

## What exists and what does not

`contracts/export.py` writes the artifacts and `contracts/manifest.json` (sha256 per artifact); `just check` and the
CI static job fail on drift (`git diff --exit-code contracts`). The CI `contract` job ([contract job and
breaking-change policy](../../../docs/reference/ci.md)) runs `uv run pytest -q -m contract` (SSE conformance, schema example
tests, Schemathesis, planted-break tests) and then `uv run python -m scripts.contract_diff --base-sha <PR base>`,
which runs oasdiff (`oasdiff breaking ... --fail-on WARN`, pinned v1.37.0, CI downloads it) on `contracts/openapi.json`
and a stdlib check on `contracts/sse.schema.json`. A PR label `contract-major` accepts a break: findings still print,
the gate passes, and a CHANGELOG entry is required. Locally the oasdiff tests skip with a reason when `oasdiff` is
not installed. Not available yet: the consumer cross job that regenerates the portfolio and backoffice clients
(`cross-repo.yml` has only the IAM and private contract-bytes jobs) and the nightly 500-example Schemathesis run.

## Procedure

1. Classify the change. A breaking change (removed or renamed field, narrower type, new required field, removed
   event or path) stops here: write an ADR first with write-adr and wait for the owner. Do not regenerate. The
   owner then adds the `contract-major` label; the CHANGELOG entry and consumer PRs follow.
2. Change the pydantic model or route (`app/presentation/`, `contracts/site_experience.py`), not the JSON by hand.
3. Regenerate: `uv run python -m contracts.export`, then `git diff --stat contracts`. Each changed artifact must
   trace to the edit; `contracts/manifest.json` changes with them.
4. Update examples when the change is visible on the wire (`contracts/send-message.examples.json`,
   `contracts/sse.examples.json`, [API contract](../../../docs/reference/api-contract.md)).
5. Prove it is additive: `uv run pytest -q -m contract -p no:cacheprovider` and
   `uv run python -m scripts.contract_diff --base-sha origin/develop` (needs `oasdiff` on PATH; if absent, say the
   diff was not run locally and that CI runs it). Then `just check` and `just test` through the test-runner agent.
6. List the consumer steps: the portfolio and backoffice import a committed snapshot in their own PRs and are never
   edited from here; record the API commit they should pin in [the frontend handoff](../../../docs/reference/frontend-handoff.md)
   when the owner asks.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Classification and reason, artifacts changed with their manifest hashes, tests run with their final line,
consumer steps, contract_diff result (or why it was not run), what was not available yet (consumer cross job).
