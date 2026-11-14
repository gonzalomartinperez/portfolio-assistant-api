---
name: evaluate-assistant
description: "Runs the offline assistant evaluations (golden replay, retrieval harness, fixture question bank), reads the report by stratum and locale, and turns a failing answer into a schema-valid eval item. Use when asked to evaluate the assistant, check retrieval metrics, read an eval report or add an eval item from a failure. Not for unit tests (use implement-task), writing retrieval rules (use api-maintain-knowledge) or prompt edits (use change-prompt); never opens the sealed holdout and never makes paid or live calls."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# evaluate-assistant

Tools: Read, Grep, Glob, Bash. This skill does not authorize commits, pushes, merges, paid calls or
deployment (AGENTS.md). Hard rules: never open `evals/full/holdout.sealed.jsonl`; no live or paid evaluation
(no `--mode openai`, no `--allow-paid`); re-recording and any spend are owner-only; no real API key is read.

## Checklist

- [ ] AGENTS.md and [the evaluation guide](../../../docs/assistant-evaluation.md) read
- [ ] Only fixture-mode commands run, against isolated fixtures when a database is needed
- [ ] Results reported as counts per stratum and locale, never as quoted answer text
- [ ] Anything that does not exist yet (no cassettes, `eval-record.yml`) is stated as "not available yet"
- [ ] New items validated with the loader before they are proposed

## What exists and what does not

| Piece | Command or path |
| --- | --- |
| Item schema, loader, 11 deterministic graders ([ADR011](../../../docs/adrs/011-eval-harness.md)) | `evals/harness/`; `uv run pytest -q tests/evals -p no:cacheprovider` |
| Golden set, 80 items, frozen, owner is CODEOWNER | `evals/golden/golden.jsonl`, `manifest.json`, `REVIEW.md` |
| Golden lane (cassette replay, [ADR013](../../../docs/adrs/013-provider-port-cassettes.md)) | `just eval-golden`, which runs `REQUIRE_GOLDEN_CASSETTES=1 uv run python -m evals.harness.golden`; exit 0 pass, 1 failing items, 3 re-record required |
| Full set, 384 development items | `evals/full/full.jsonl`, `evals/full/README.md` (report-only, no gate) |
| Sealed holdout, 100 items | `evals/full/holdout.sealed.jsonl`: never open it; the harness exposes counts only |
| Retrieval harness and baseline (ranx, 152 queries) | `uv run --group eval python -m evals.harness.retrieval --out artifacts/retrieval-report.json`, `--compare`, baseline `evals/baselines/retrieval.json`, notes `evals/retrieval/BASELINE.md` |
| Attack pack, 60 attacks | `evals/attacks/attacks.jsonl`; `uv run pytest -q tests/evals/test_attacks.py tests/evals/test_attack_rails.py` |
| Cost and latency budgets | `evals/baselines/budgets.json`, `tests/evals/test_budgets.py` |
| Question bank (legacy) | `evals/assistant.json`, `scripts.evaluate_assistant --mode fixture` |
| Committed cassettes | not available yet: none are recorded, so the golden lane exits 3 until the owner records |
| Replay of the full set (`--scope full`) | not available yet: the lane refuses it |
| No-retrieval ablation, retrieval ablations h1 to h5 other than `graph` | not available yet (the first needs a paid run; see `BASELINE.md`) |
| `eval-record.yml` recording workflow | not available yet: recording is `python -m evals.harness.golden --record`, owner-only |

## Procedure

1. Read the guide above and, for item rules, `evals/harness/items.py` and `evals/schema/item.schema.json`.
2. Offline harness tests, no services: `uv run pytest -q tests/evals -p no:cacheprovider`.
3. Golden lane: with isolated fixtures from [local development](../../../docs/local-development.md), `just eval-golden`.
   Exit 3 is a statement ("re-record required"), not a failure to fix: report it and stop. Never run `--record`:
   it is paid, needs `EVAL_RECORDING=1`, `EVAL_ENVIRONMENT=eval-live` and a budget, and is owner-only.
4. Retrieval, same isolated fixtures, no model call:
   `uv run --group eval python -m evals.harness.retrieval --out artifacts/retrieval-report.json --compare`.
   `--compare` is a paired ranx test against the baseline and exits 1 on a significant Recall@5 drop.
   Do not use `--write-baseline`: baselines only tighten and change through review.
5. Question bank: `uv run python -m scripts.build_assistant_bank --check`, then
   `uv run python -m scripts.evaluate_assistant --mode fixture --split development --limit 10 --output artifacts/eval-<name>.json`.
   `--split holdout` is the legacy bank's split: report it, never tune against it.
6. Read the output by stratum and locale. Report pass counts, failing ids, EN versus ES gap and the strategy table.
   Fixture embeddings are deterministic hashes, so retrieval vector numbers are plumbing, not semantic recall.
7. To add an item from a failure, copy only the question and the gold evidence, not the answer. Rules: closed
   assertion list; `answer` items assert `citations_nonempty`, `abstain` items assert `abstains`; gold keys in
   canonical form `<locale>/<topic>[#<entity>]`; Spanish written natively (tuteo, no voseo); `provenance`, `reviewer`
   and `corpus_snapshot_id` from `evals/corpus/manifest.json`. Stage in `artifacts/new-items.jsonl` and validate:
   `uv run python -c "from pathlib import Path; from evals.harness.loader import load_items; print(len(load_items(Path('artifacts/new-items.jsonl'))))"`.
8. Golden is frozen: an addition goes into `evals/golden/golden.jsonl` only in a PR the owner reviews, followed by
   `uv run python -m evals.harness.distill --write-manifest` and `uv run pytest -q tests/evals/test_golden_manifest.py`.
   A failure that is not yet golden material goes to the full set the same way (`evals/full/README.md`).
9. If `evals/full/holdout.sealed.jsonl` is mentioned, do not open, print, grep or quote it, and never tune on it.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Commands run and their final line (golden exit code included), counts per stratum and locale (with failing ids),
EN versus ES gap, what was not available yet, items proposed with their loader result, fixture versus live
evidence stated separately.
