# Skill activation, 2026-11-14

Roadmap M3-6 evidence. Tool: `scripts/skill_activation_eval.py` (local, not run in CI). Router: `claude -p --model haiku`
on the owner's subscription (no API key), one fresh process per call in an empty directory with no tools and no
repository instructions. Each prompt lists all 15 skills as `name: description` plus one query and asks for the single
skill the model would load, or `none`. Protocol: 3 runs per query, a positive passes at a trigger fraction of 0.5 or
more, a negative below 0.5. Split: fixed 60/40 train/validation; numbers below are the validation split (106 queries,
318 router calls, 0 failed calls). Raw per-query picks: [skills-activation-2026-11-14.json](skills-activation-2026-11-14.json).

"First" is the first run of the final catalog (after `api-verify-release` was folded away and the descriptions of the
four existing repo skills were put into the "Use when ... Not for ..." form before measuring). "Final" is the last run.
No skill scored below 0.8, so no description was rewritten for accuracy. After develop gained the golden lane, the
retrieval harness and the contract lane, the `evaluate-assistant` description was updated to name them and that one skill
was re-run alone (validation, 3 runs, 24 calls): first 1.00, final 1.00. The first-run description hash is kept in the JSON
(`first.description_sha256`) next to the final one. All other skills: first equals final.

| Skill | First acc | Final acc | Precision | Recall | Queries |
| --- | --- | --- | --- | --- | --- |
| `api-change-storage` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `api-change-stream` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `api-change-use-case` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `api-maintain-knowledge` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `api-refresh-corpus` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `change-prompt` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `evaluate-assistant` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `implement-task` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `refresh-contract` | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| `resume-refactor` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `review-change` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `score-repo` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `update-dependencies` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `verify-release` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| `write-adr` | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| **overall** | 1.00 | 1.00 | 1.00 | 1.00 | 106 |

Gate (M3-6): no skill's final validation accuracy is more than 10 points below its first. Met: the largest change is 0.
Baseline for the seven core skills is their first numbers (all 1.00).

## Reading the result

- Overall: 46 true positives, 60 true negatives, 0 false positives, 0 false negatives on validation.
- Seven queries were unstable across the three runs without crossing the 0.5 line, all on skills whose queries
  were written earlier (core skills): for example `Start milestone M5 now` (resume-refactor), `Write the release notes`
  (review-change negative), `Write an ADR for moving to Vitest` (one run picked `api-change-storage`).
- Perfect scores on small, mostly clear-cut query sets say routing is healthy for these queries, not that the
  descriptions are optimal. Near-miss negatives that name the sibling skill are the discriminating part; add harder
  ones when a real misroute is seen.
- Limits: a small model routing from descriptions only; train split not run (reported for information only); the
  tool's `--out` merge assumes the same `--split` on re-runs. This is routing evidence, not proof of skill behavior.

Reproduce: `uv run python -m scripts.skill_activation_eval --split validation --jobs 4 --out artifacts/activation.json`
(about 21 minutes for all skills).
