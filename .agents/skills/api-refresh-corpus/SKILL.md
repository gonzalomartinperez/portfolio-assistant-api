---
name: api-refresh-corpus
description: "Refreshes the frozen public corpus snapshot under evals/corpus from the approved public portfolio repository and reports the canonical keys added or removed. Use when the snapshot is stale, the portfolio changed, or refresh_corpus --check fails. Not for indexing into a running database (use api-maintain-knowledge) or evaluation runs (use evaluate-assistant); only approved public content, never career-ops."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# api-refresh-corpus

Tools: Read, Grep, Glob, Bash, Edit. This skill does not authorize commits, pushes, merges, paid calls or
deployment (AGENTS.md). Only approved public portfolio content enters the corpus ([ADR016](../../../docs/adrs/016-frozen-public-corpus-snapshot.md)):
never career-ops, private exports or arbitrary remotes. Do not edit the portfolio checkout; only read it.

## Checklist

- [ ] The source is a local checkout whose `origin` is the approved public portfolio repository
- [ ] A full 40-character commit SHA chosen; the refresh is its own change touching nothing else
- [ ] `--check` passes before and after
- [ ] Removed keys compared with every gold key (golden, full, qrels); failures reported, not hidden
- [ ] Pins and docs naming the old commit updated

## Procedure

1. Verify the current snapshot offline: `uv run python -m scripts.refresh_corpus --check` (prints the
   `corpus_snapshot_id` and `ok`; problems are `missing`, `changed`, `unlisted` or an id mismatch).
2. Choose the portfolio commit: `git -C <portfolio-checkout> rev-parse <ref>` gives the full SHA. The script
   refuses any `origin` outside the approved allowlist and any file type that is not a regular blob.
3. Refresh: `uv run python -m scripts.refresh_corpus --source <portfolio-checkout> --ref <full-sha>`. It prints
   `added keys` and `removed keys` (canonical keys, [ADR012](../../../docs/adrs/012-layout-neutral-evidence-keys.md)).
4. Check gold keys: search the removed keys in `evals/golden/golden.jsonl`, `evals/full/full.jsonl` and
   `evals/retrieval/qrels.jsonl` (`gold_evidence_ids` and qrels) and in the legacy `evals/retrieval.json`. Never grep
   `evals/full/holdout.sealed.jsonl`; for it, ask the owner to check. Any hit is a loud failure: report the item
   ids and propose new keys; do not loosen expectations to pass. Golden changes need owner review (CODEOWNERS), then
   `uv run python -m evals.harness.distill --write-manifest`.
5. Update what names the commit: the `PINNED` constant in `tests/tooling/test_corpus_snapshot.py` and the
   snapshot id and commit in [ADR016](../../../docs/adrs/016-frozen-public-corpus-snapshot.md).
6. Verify: `uv run python -m scripts.refresh_corpus --check`, then
   `uv run pytest -q tests/tooling/test_corpus_snapshot.py tests/evals/test_golden_manifest.py tests/evals/test_full_manifest.py -p no:cacheprovider`
   and `just check`. The retrieval baseline (`evals/baselines/retrieval.json`, `evals/retrieval/BASELINE.md`) names the
   old corpus: mark it for the owner to re-baseline through evaluate-assistant, never write it here.
   Indexing the new snapshot into isolated databases is api-maintain-knowledge territory and needs fixture authority.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Old and new commit and `corpus_snapshot_id`, added and removed keys, gold keys that vanished (item ids), files
updated, commands run with their final line, what was not run (indexing, evaluation).
